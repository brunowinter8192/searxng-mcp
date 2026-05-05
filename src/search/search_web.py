# INFRASTRUCTURE
import asyncio
import html
import logging
import re
import time
from mcp.types import TextContent
from urllib.parse import urlparse

from src.search.browser import close_browser
from src.search.cache import cache_key, cache_write
from src.search.engines.google import GoogleEngine
from src.search.preview import fetch_previews
from src.search.engines.scholar import ScholarEngine
from src.search.engines.crossref import CrossRefEngine
from src.search.engines.duckduckgo import DuckDuckGoEngine
from src.search.engines.mojeek import MojeekEngine
from src.search.engines.lobsters import LobstersEngine
from src.search.engines.openalex import OpenAlexEngine
from src.search.engines.stack_exchange import StackExchangeEngine
from src.search.result import SearchResult

logger = logging.getLogger(__name__)

SNIPPET_LENGTH = 5000

ENGINES = {
    "google": GoogleEngine(),
    "google scholar": ScholarEngine(),
    "crossref": CrossRefEngine(),
    "duckduckgo": DuckDuckGoEngine(),
    "mojeek": MojeekEngine(),
    "lobsters": LobstersEngine(),
    "openalex": OpenAlexEngine(),
    "stack_exchange": StackExchangeEngine(),
}

GENERAL  = {"google", "duckduckgo", "mojeek"}
ACADEMIC = {"google_scholar", "openalex", "crossref"}  # "google_scholar" matches ScholarEngine.name
QA       = {"stack_exchange", "lobsters"}

ACADEMIC_PRIORITY = {"openalex": 1, "google_scholar": 2, "crossref": 3}
QA_PRIORITY       = {"stack_exchange": 1, "lobsters": 2}

TARGET_GENERAL  = 12
TARGET_ACADEMIC = 6
TARGET_QA       = 2

# Bloat-strip function — copied verbatim from dev/search_pipeline/snippet_quality_analysis.py
# (do not redefine: source of truth lives there)
def _strip_bloat(text: str) -> str:
    text = re.sub(r'^Web results', '', text)
    text = re.sub(r'^Featured snippet from the web', '', text)
    text = re.sub(r'\bRead more\b.*', '', text)
    text = re.sub(r'\d[\d,.]*[Kk+]? *(likes|comments|answers|posts) *·[^\n]*', '', text)
    text = re.sub(r'\S*›\S*', '', text)
    text = re.sub(r'\d{1,2} \w{3,9} \d{4} — ', '', text)
    text = re.sub(r'&[a-z]+;|&#\d+;', '', text)
    text = re.sub(r'Tagged with [\w, ]+\.?$', '', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return ' '.join(text.split())


# ORCHESTRATOR

# Search all enabled engines concurrently, merge+rank, preview, format, cache, return TextContent
async def search_web_workflow(
    query: str,
    language: str = "en",
    time_range: str | None = None,
    engines: str | None = None,
    _with_timings: bool = False,
    class_filter: frozenset[str] | None = None,
) -> list[TextContent] | tuple[list[TextContent], dict]:
    t_total = time.perf_counter()
    logger.info("Searching: %s (language=%s)", query, language)
    selected = _select_engines(engines)

    # Engine fanout phase
    raw_results: list = []
    engine_ms: dict[str, int] = {}
    t_fanout = time.perf_counter()
    if _with_timings:
        names_and_engines = list(selected.items())
        tasks = [_engine_with_timing(eng, query, language, 10) for _, eng in names_and_engines]
        timed = await asyncio.gather(*tasks)
        for (name, _), (eng_results, ms) in zip(names_and_engines, timed):
            raw_results.extend(eng_results)
            engine_ms[f"engine_{name.replace(' ', '_')}_ms"] = ms
    else:
        raw_results = await _query_engines_concurrent(query, language, 10, selected)
    engine_fanout_ms = round((time.perf_counter() - t_fanout) * 1000)

    # Merge-rank phase
    t0 = time.perf_counter()
    ranked, slot_counts = _merge_and_rank(raw_results, class_filter=class_filter)
    merge_rank_ms = round((time.perf_counter() - t0) * 1000)

    # Preview phase (before cache_write so snippet_source is og-aware)
    t0 = time.perf_counter()
    top20 = await fetch_previews(ranked[:20])
    preview_ms = round((time.perf_counter() - t0) * 1000)

    # Format + snippet selection phase (collects snippet_source + display text per URL)
    t0 = time.perf_counter()
    formatted_text, snippet_sources, snippet_texts = _format_results(query, top20)
    select_snippet_ms = round((time.perf_counter() - t0) * 1000)

    # Build og/meta index from preview-enriched top20 objects (ranked[:20] still has preview=None)
    og_meta = {r.url: r.preview for r in top20 if r.preview}

    # Cache write phase
    key = cache_key(query, language, engines, time_range, class_filter=class_filter)
    t0 = time.perf_counter()
    cache_write(key, ranked, query, language, engines, time_range,
                snippet_sources=snippet_sources, slot_counts=slot_counts,
                snippet_texts=snippet_texts, og_meta=og_meta)
    cache_write_ms = round((time.perf_counter() - t0) * 1000)

    total_ms = round((time.perf_counter() - t_total) * 1000)
    result = [TextContent(type="text", text=formatted_text)]

    if not _with_timings:
        return result
    timings = {
        "engine_fanout_ms": engine_fanout_ms,
        **engine_ms,
        "merge_rank_ms": merge_rank_ms,
        "preview_ms": preview_ms,
        "select_snippet_ms": select_snippet_ms,
        "cache_write_ms": cache_write_ms,
        "total_ms": total_ms,
    }
    return result, timings


# Run N queries sequentially in shared Chrome, close browser in finally
async def search_batch_workflow(
    queries: list[str],
    language: str = "en",
    time_range: str | None = None,
    engines: str | None = None,
    class_filter: frozenset[str] | None = None,
) -> list[list[TextContent]]:
    results = []
    try:
        for q in queries:
            results.append(await search_web_workflow(q, language, time_range, engines, class_filter=class_filter))
    finally:
        await close_browser()
    return results


# Synchronous wrapper for dev scripts — runs event loop internally
def fetch_search_results(
    query: str,
    category: str,
    language: str,
    time_range: str | None,
    engines: str | None,
    pageno: int
) -> list:
    selected = _select_engines(engines)
    results = asyncio.run(_query_engines_concurrent(query, language, 10, selected))
    return [
        {
            "url": r.url,
            "title": r.title,
            "content": r.snippet,
            "engines": [r.engine],
        }
        for r in results
    ]


# FUNCTIONS

# Filter engine registry by comma-separated names param or return all
def _select_engines(engines: str | None) -> dict:
    if not engines:
        return ENGINES
    names = [e.strip().lower() for e in engines.split(",")]
    return {k: v for k, v in ENGINES.items() if k in names}


# Query selected engines concurrently, collect all SearchResult objects
async def _query_engines_concurrent(query: str, language: str, max_results: int, selected: dict) -> list:
    tasks = [engine.search(query, language, max_results) for engine in selected.values()]
    results_per_engine = await asyncio.gather(*tasks, return_exceptions=True)
    combined = []
    for r in results_per_engine:
        if isinstance(r, Exception):
            logger.warning("Engine error: %s", r)
        else:
            combined.extend(r)
    return combined


# Wrap a single engine search call and return (results, elapsed_ms) for per-engine timing
async def _engine_with_timing(engine, query: str, language: str, max_results: int) -> tuple[list, int]:
    t0 = time.perf_counter()
    try:
        results = await engine.search(query, language, max_results)
        return results, round((time.perf_counter() - t0) * 1000)
    except Exception as e:
        logger.warning("Engine error: %s", e)
        return [], round((time.perf_counter() - t0) * 1000)


# Merge by URL, classify engines into slots, return overlap-ranked results + slot fill counts
def _merge_and_rank(results: list[SearchResult], target_count: int = 20, class_filter: frozenset[str] | None = None) -> tuple[list[SearchResult], dict]:
    # Step 1 — Merge by URL: aggregate engines list, snippets dict, min position, prefer non-empty title
    merged: dict[str, dict] = {}
    for r in results:
        if r.url not in merged:
            merged[r.url] = {
                "url":          r.url,
                "title":        r.title or "",
                "snippet":      r.snippet,
                "engines":      [r.engine],
                "snippets":     {r.engine: r.snippet} if r.snippet else {},
                "min_position": r.position,
            }
        else:
            m = merged[r.url]
            if r.engine not in m["engines"]:
                m["engines"].append(r.engine)
            if r.snippet:
                m["snippets"][r.engine] = r.snippet
            m["min_position"] = min(m["min_position"], r.position)
            if not m["title"] and r.title:
                m["title"] = r.title

    pool = list(merged.values())

    # Step 2 — Classify and rank within each class
    def n_general(m):  return sum(1 for e in m["engines"] if e in GENERAL)
    def n_academic(m): return sum(1 for e in m["engines"] if e in ACADEMIC)
    def n_qa(m):       return sum(1 for e in m["engines"] if e in QA)

    def best_academic_pri(m):
        return min((ACADEMIC_PRIORITY.get(e, 99) for e in m["engines"] if e in ACADEMIC), default=99)

    def best_qa_pri(m):
        return min((QA_PRIORITY.get(e, 99) for e in m["engines"] if e in QA), default=99)

    general_pool  = sorted(
        [m for m in pool if n_general(m) > 0],
        key=lambda m: (-n_general(m), m["min_position"]),
    )
    academic_pool = sorted(
        [m for m in pool if n_academic(m) > 0],
        key=lambda m: (m["min_position"], best_academic_pri(m)),
    )
    qa_pool = sorted(
        [m for m in pool if n_qa(m) > 0],
        key=lambda m: (m["min_position"], best_qa_pri(m)),
    )

    # Step 3 — Resolve per-class targets based on class_filter
    active = class_filter if class_filter else {"general", "academic", "qa"}
    if len(active) == 1:
        cls = next(iter(active))
        tg = 20 if cls == "general"  else 0
        ta = 20 if cls == "academic" else 0
        tq = 20 if cls == "qa"       else 0
    elif len(active) == 2:
        tg = (TARGET_GENERAL  if "general"  in active else 0)
        ta = (TARGET_ACADEMIC if "academic" in active else 0)
        tq = (TARGET_QA       if "qa"       in active else 0)
        # allocate sum of selected defaults, each to its own pool
    else:
        tg, ta, tq = TARGET_GENERAL, TARGET_ACADEMIC, TARGET_QA

    general_slots  = general_pool[:tg]
    academic_slots = academic_pool[:ta]
    qa_slots       = qa_pool[:tq]

    placed_urls = {m["url"] for m in general_slots + academic_slots + qa_slots}
    leftover = [m for m in pool if m["url"] not in placed_urls]
    leftover.sort(key=lambda m: (-len(m["engines"]), m["min_position"]))

    # Step 4 — Return ordered: top slots first, then remaining candidates for cache pagination
    ordered  = general_slots + academic_slots + qa_slots
    extended = ordered + leftover

    slot_counts = {
        "general":  len(general_slots),
        "academic": len(academic_slots),
        "qa":       len(qa_slots),
    }
    return [
        SearchResult(
            url=m["url"],
            title=m["title"],
            snippet=m["snippet"],
            engine=m["engines"][0],
            position=m["min_position"],
            engines=m["engines"],
            snippets=m["snippets"],
        )
        for m in extended
    ], slot_counts


# Select best snippet for a merged SearchResult per 7-rule priority chain; returns (snippet, source)
def _select_snippet(r: SearchResult) -> tuple[str, str]:
    engines  = set(r.engines)
    snippets = r.snippets
    og       = (r.preview or {}).get("og") or ""

    # Rule 1: OpenAlex or StackExchange — native structured, cleanest specialty source
    if "openalex" in engines and snippets.get("openalex"):
        return snippets["openalex"], "openalex"
    if "stack_exchange" in engines and snippets.get("stack_exchange"):
        return snippets["stack_exchange"], "stack_exchange"

    # Rule 2: CrossRef — already JATS-stripped or synthesized at parse time
    if "crossref" in engines and snippets.get("crossref"):
        return snippets["crossref"], "crossref"

    # Rule 3: Lobsters-only with no og preview — domain is the only clean fallback
    if engines == {"lobsters"} and not og:
        return urlparse(r.url).netloc, "lobsters_domain"

    # Rule 4: DDG snippet — query-relevant extract, 1% bloat
    ddg = snippets.get("duckduckgo", "")
    if ddg:
        return ddg, "duckduckgo"

    # Rule 5: Mojeek snippet — query-relevant extract, 7% bloat
    mojeek = snippets.get("mojeek", "")
    if mojeek:
        return mojeek, "mojeek"

    # Rule 6: og preview — page-generic meta description, 2% bloat
    if og:
        return og, "og"

    # Rule 7: Google or Scholar fallback — unescape HTML entities then strip bloat patterns
    raw = snippets.get("google", "") or snippets.get("google_scholar", "")
    if raw:
        stripped = _strip_bloat(html.unescape(raw))
        source = "google_strip" if "google" in snippets else "scholar_strip"
        return stripped, source

    return "", ""


# Format merged SearchResult list as plain text numbered list; returns (text, {url: source}, {url: display_text})
def _format_results(query: str, results: list[SearchResult]) -> tuple[str, dict[str, str], dict[str, str]]:
    if not results:
        return f'No results found for "{query}"', {}, {}
    lines = [f'Found {len(results)} results for "{query}"\n']
    sources: dict[str, str] = {}
    texts:   dict[str, str] = {}
    for idx, r in enumerate(results, 1):
        lines.append(f"{idx}. {r.title}")
        lines.append(f"   URL: {r.url}")
        snippet, source = _select_snippet(r)
        sources[r.url] = source
        texts[r.url]   = snippet
        if snippet:
            lines.append(f"   Snippet: {snippet[:SNIPPET_LENGTH]}")
        lines.append("")
    return "\n".join(lines), sources, texts
