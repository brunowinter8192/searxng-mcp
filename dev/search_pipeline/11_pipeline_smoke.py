#!/usr/bin/env python3
"""Full pipeline smoke -- search_web_workflow per query, slot deduction from cache, markdown report."""

# INFRASTRUCTURE
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.search.browser import close_browser
from src.search.cache import cache_key, cache_read
from src.search.search_web import search_web_workflow

SCRIPT_DIR   = Path(__file__).parent
QUERIES_FILE = SCRIPT_DIR / "queries.txt"
REPORT_DIR   = SCRIPT_DIR / "01_reports"

GENERAL_NAMES  = {"google", "duckduckgo", "mojeek"}
ACADEMIC_NAMES = {"google_scholar", "openalex", "crossref"}
QA_NAMES       = {"stack_exchange", "lobsters"}

TARGET_GENERAL  = 12
TARGET_ACADEMIC = 4
TARGET_QA       = 2
TARGET_TOTAL    = 20


# ORCHESTRATOR

# Run search_web_workflow per query, read structured cache data, write report
async def run_pipeline_smoke(max_queries: int | None, language: str) -> None:
    queries = _load_queries(QUERIES_FILE, max_queries)
    print(f"Pipeline smoke | Queries: {len(queries)} | Language: {language}", file=sys.stderr)
    records = []
    try:
        for qi, query in enumerate(queries, 1):
            await search_web_workflow(query, language, None, None)
            key  = cache_key(query, language, None, None)
            hit  = cache_read(key)
            urls = hit.get("urls", []) if hit else []
            record = _build_record(query, urls)
            records.append(record)
            s = record["slots"]
            print(
                f"[{qi}/{len(queries)}] {query!r} -> urls={len(urls)} "
                f"G={s['GENERAL']} A={s['ACADEMIC']} Q={s['QA']}",
                file=sys.stderr,
            )
    finally:
        await close_browser()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = _write_report(records, language)
    ok = sum(1 for r in records if r["total_urls"] > 0)
    print(f"\nReport: {path}", file=sys.stderr)
    print(f"Done: {ok}/{len(records)} queries with results", file=sys.stderr)


# FUNCTIONS

# Load queries from file, one per line, skip blanks, honour max_queries limit
def _load_queries(path: Path, max_queries: int | None) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    qs = [ln.strip() for ln in lines if ln.strip()]
    return qs[:max_queries] if max_queries else qs


# Deduce slot class from engines list: GENERAL > ACADEMIC > QA > OVERFLOW?
def _deduce_class(engines: list[str]) -> str:
    s = set(engines)
    if s & GENERAL_NAMES:   return "GENERAL"
    if s & ACADEMIC_NAMES:  return "ACADEMIC"
    if s & QA_NAMES:        return "QA"
    return "OVERFLOW?"


# Annotate top-20 cache urls with deduced class, count slots per class
def _build_record(query: str, urls: list[dict]) -> dict:
    top20 = urls[:TARGET_TOTAL]
    annotated = []
    for entry in top20:
        annotated.append({
            "url":     entry["url"],
            "title":   entry.get("title", ""),
            "engines": entry.get("engines", []),
            "snippet": entry.get("snippet", ""),
            "class":   _deduce_class(entry.get("engines", [])),
        })
    slots: dict[str, int] = {"GENERAL": 0, "ACADEMIC": 0, "QA": 0, "OVERFLOW?": 0}
    for a in annotated:
        slots[a["class"]] += 1
    return {
        "query":      query,
        "urls":       annotated,
        "total_urls": len(annotated),
        "slots":      slots,
    }


# Write markdown report to 01_reports/pipeline_smoke_<ts>.md, return path
def _write_report(records: list[dict], language: str) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"pipeline_smoke_{ts}.md"

    lines: list[str] = [
        f"# Pipeline Smoke Report -- {ts}",
        "",
        f"**Language:** {language}  ",
        f"**Queries:** {len(records)}  ",
        f"**Queries with results:** {sum(1 for r in records if r['total_urls'] > 0)}",
        "",
        "## Engine Class Definitions",
        "",
        "| Class    | Engines                               | Output slots |",
        "|----------|---------------------------------------|-------------|",
        "| GENERAL  | google, duckduckgo, mojeek            | 12 |",
        "| ACADEMIC | google_scholar, openalex, crossref     |  4 |",
        "| QA       | stack_exchange, lobsters               |  2 |",
        "| OVERFLOW | non-placed candidates (any class)      |  2 |",
        "",
        "> Slot class per URL is deduced from the `engines` field in cache -- heuristic for review,",
        "> not a replay of internal slot allocation. OVERFLOW is an allocation mechanism, not an",
        "> engine class; OVERFLOW? label means no engine from GENERAL/ACADEMIC/QA returned this",
        "> URL (should not occur in practice since all 8 active engines belong to one of the 3 classes).",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| # | Query | Total | GENERAL | ACADEMIC | QA | OVERFLOW? |",
        "|---|-------|-------|---------|----------|----|-----------|",
    ]

    for i, r in enumerate(records, 1):
        q = r["query"][:55].replace("|", "\\|")
        s = r["slots"]
        lines.append(
            f"| {i} | {q} | {r['total_urls']} "
            f"| {s['GENERAL']} | {s['ACADEMIC']} | {s['QA']} | {s['OVERFLOW?']} |"
        )

    lines += ["", "---", ""]

    for qi, r in enumerate(records, 1):
        s = r["slots"]
        lines += [f"## Q{qi}: {r['query']}", ""]
        if not r["urls"]:
            lines += ["*No results returned.*", "", "---", ""]
            continue
        for idx, a in enumerate(r["urls"], 1):
            title       = a["title"] if a["title"] else "(no title)"
            engines_str = ", ".join(a["engines"])
            snippet     = (a["snippet"] or "")[:400].replace("\n", " ")
            lines += [
                f"{idx}. **[{a['class']}]** {title}",
                f"   URL: {a['url']}",
                f"   Engines: {engines_str}",
            ]
            if snippet:
                lines.append(f"   Snippet: {snippet}")
            lines.append("")
        lines.append(
            f"Slots filled: GENERAL {s['GENERAL']}/{TARGET_GENERAL}, "
            f"ACADEMIC {s['ACADEMIC']}/{TARGET_ACADEMIC}, "
            f"QA {s['QA']}/{TARGET_QA}, "
            f"total {r['total_urls']}/{TARGET_TOTAL}"
        )
        lines += ["", "---", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Full pipeline smoke: search_web_workflow per query, slot deduction from cache."
    )
    parser.add_argument(
        "--max-queries",
        dest="max_queries",
        type=int,
        default=None,
        help="Limit to first N queries from queries.txt (default: all)",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="ISO language code (default: en)",
    )
    args = parser.parse_args()
    asyncio.run(run_pipeline_smoke(args.max_queries, args.language))
