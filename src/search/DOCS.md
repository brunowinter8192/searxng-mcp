# search/

pydoll-based parallel search pipeline. Replaces the former `src/searxng/` SearXNG-Docker wrapper (deleted 2026-04-15 in engine-cut). Exposes `search_web_workflow()` (single-query, fan-out across engines via asyncio.gather) and `search_batch_workflow()` (N queries sequentially in one warm-Chrome session, used by the CLI `search_batch` subcommand) — both consumed by `cli.py`. Plus `fetch_search_results()` sync wrapper consumed by dev scripts.

**Active engines (8):** google, google scholar, duckduckgo, mojeek, lobsters (pydoll); crossref, openalex, stack_exchange (HTTP). See `decisions/stealth00_engine_status.md` for the drop decision on brave / startpage / semantic scholar / bing. See `decisions/search05_engine_expansion.md` for DDG + Mojeek + Lobsters + OpenAlex + SE integration rationale (HN + Bing dropped 2026-05-04, Marginalia deferred).

## search_web.py

**Purpose:** Search orchestrator. Three entry points:
- `search_web_workflow(query, ..., engine_timeout=None, class_filter=None, _with_timings=False)` — single query, fan-out across all active engines via `asyncio.gather` of `_engine_with_timing` tasks (acquires per-engine rate-limiter token at workflow level, then optionally wraps `engine.search()` in `asyncio.wait_for(engine_timeout)` — production passes None, smoke passes 8.0), then `_merge_and_rank` (URL-merge with engine-aggregation + overlap-rank within `GENERAL = {google, duckduckgo, mojeek}` + slot allocation `12 general / 6 academic {google scholar, openalex, crossref} / 2 Q&A {stack_exchange, lobsters} → 20 URLs total`, hard allocation no overflow). `class_filter` restricts allocation to a subset of classes per the `--general` / `--academic` / `--qa` CLI flags (single class = 20 of that class, two classes = sum of defaults, all/none = 12/6/2). After ranking: `fetch_previews(top_n=20)`, `_select_snippet` per URL via score-based selection (candidates: all engine snippets + og + meta; score = `clean_len × lexical_density`; MIN_FLOOR=40 char floor; best-of-worst fallback when no candidate clears floor) producing both the chosen snippet text and the `snippet_source` label per URL, `cache.cache_write` for the FULL ranked list (~60-80 URLs, not just top-20 — backs `search_more`) including `snippet_source`, `og`, `meta`, `snippet_display`, and `slot_counts`. Returns top-20 as `list[TextContent]`; with `_with_timings=True` returns `(list, dict)` where `dict.engine_details` maps engine name → `{status, ms}` for diagnostic rendering by the smoke harness.
- `search_batch_workflow(queries, ...)` — N queries sequentially through `search_web_workflow` in the SAME process (Chrome stays warm via shared singleton in `browser.py`), `close_browser()` in finally clause keeps teardown inside the active event loop. Used by `cli.py search_batch` subcommand to amortize Chrome cold-start across multiple queries (~5s boot + ~1s/query vs ~5s boot per query in subprocess-per-call mode).
- `fetch_search_results()` — sync wrapper for dev scripts.

**Bloat-strip patterns** for the Google/Scholar fallback in `_select_snippet` are imported from `dev/search_pipeline/snippet_quality_analysis.py` (single source of truth, do not redefine). 9 patterns: URL breadcrumb (`›`), Read-more, `^Web results`, `^Featured snippet from the web`, social-proof, Scholar ellipsis, Mojeek nav-dump, HTML entities, `Tagged with` suffix.

**Input:** Query string (or list), category, language, time range, engine filter.
**Output:** `list[TextContent]` (single workflow), `list[list[TextContent]]` (batch workflow), or `list[dict]` (sync wrapper). Side effect: writes disk cache under `~/.cache/searxng/<key>.json`.

## browser.py

**Purpose:** pydoll Chrome lifecycle. Starts a single shared Chrome instance on first call, creates a new tab per engine for isolation. Applies fingerprint patches (WebGL, canvas, permissions) at launch. Two cleanup paths:
- `close_browser()` — async, used inside an active event loop (e.g. by `search_batch_workflow` in finally). Issues CDP `Browser.close` and waits for response.
- `kill_stale_chrome()` — sync `pkill -f "user-data-dir=<SESSION_DIR>"`, registered as `atexit` handler in `cli.py`. Replaces the previous async-CDP atexit which incurred a deterministic 60s timeout per CLI invocation (event-loop mismatch — see `decisions/`/session 2026-04-30 forensic).

**Input:** None (singleton on first access).
**Output:** pydoll Chrome instance and new tab contexts.

## rate_limiter.py

**Purpose:** Per-engine token bucket rate limiter with exponential backoff. Module-level `_limiters: dict[str, RateLimiter]` registry; engines populate it at module-import (`_limiters["<name>"] = RateLimiter(max_requests=4, window_seconds=60)`), workflow consumes via `get_limiter(name).acquire()` BEFORE invoking `engine.search()`. The acquire-call moved out of the engines into the workflow (`search_web._engine_with_timing`) on 2026-05-05 so that the smoke's `engine_timeout` watchdog wraps only actual engine work, not the rate-limiter wait phase. Engines retain `limiter.backoff()` and `limiter.reset_backoff()` calls in their search() body for CAPTCHA/error response.
**Input:** Engine name (via `get_limiter`).
**Output:** Async context that blocks until a token is available; sleep up to 60s when bucket exhausted.

## preview.py

**Purpose:** Async preview fetcher. `fetch_previews(results, top_n=20)` hits the top-N result URLs in parallel (concurrency=8, timeout=3s per URL), extracts `og:description` + `meta name="description"` via lxml xpath, attaches as `preview: dict | None` to each `SearchResult` via `dataclasses.replace`. Silent skip on any fetch failure. Called from `search_web_workflow` after `_merge_and_rank`, before `_format_results`. Also used by `05_search_smoke.py`. Charset handling (post-2026-05-05): reads charset from HTTP `Content-Type` header (regex), defaults to UTF-8 when absent, passes explicit encoding to `lxml_html.HTMLParser(encoding=_enc)` — fixes mojibake from servers that don't declare charset and lxml falls back to ISO-8859-1. Entity decoding via `_deep_unescape` (idempotent loop of `html.unescape` until fixed-point) on og/meta values — handles double/triple-encoded HTML entities in attribute values (e.g. cookie-banner pages).
**Input:** `list[SearchResult]`, optional `top_n` int.
**Output:** `list[SearchResult]` with `preview` field populated for top-N (None for rest or failed fetches).

## cache.py

**Purpose:** Disk cache for search results. Backs the `search_more` CLI subcommand for pagination beyond the first 20 URLs without re-running the engine fan-out. Cache key: `sha256(query|language|engines|time_range|sorted_class_filter)[:16]` — class_filter included in key (post-dl9-v3) so search_more must be invoked with the same `--general`/`--academic`/`--qa` flag combination to hit cache. Path: `~/.cache/searxng/<key>.json`. TTL: 1 hour, mtime-based. Atomic writes via `tempfile.NamedTemporaryFile(dir=cache_dir, delete=False)` + `os.replace(tmp, final)` — prevents partial reads on concurrent CLI calls. JSON structure stores `{query, language, engines, time_range, timestamp, returned_count, slot_counts: {general, academic, qa}, urls: [{url, title, snippet, engines, snippets, snippet_source, og, meta, snippet_display}, ...]}` — `urls` is the full ranked list so search_more can slice from offset 20. `snippet_source` records which source the score-based selection picked per URL (engine name, `"og"`, or `"meta"`); `og` / `meta` / `snippet_display` carry the actual texts (None for URLs beyond top-20 — preview phase only ran for top-20).
**Input:** Cache key, ranked URL list, search params.
**Output:** Persisted JSON dict; cache_read returns the dict on hit (mtime within TTL) or None on miss/expired. `format_cached_slice` formats a slice for the search_more output with a header annotation indicating cache state.

## result.py

**Purpose:** `SearchResult` dataclass (url, title, snippet, engine, position, preview, engines, snippets). `preview: dict | None = None` field carries `{"og": str|None, "meta": str|None}` from `preview.py`. `engines: list[str]` and `snippets: dict[str, str]` are populated by `_merge_and_rank` in `search_web.py` when multiple engines return the same URL — `engines` carries the engine names for overlap-counting and slot-allocation, `snippets` keys engine-name → that engine's raw snippet text so `_select_snippet` can pick the best source per URL. All engine constructors leave preview/engines/snippets at default empty.
**Input:** —
**Output:** —

## engines/

Per-engine parser modules. Each exports an `Engine` class with `search(query, language, max_results)` returning `list[SearchResult]`.

**Rate-limiter integration (post-2026-05-05):** each engine module registers its limiter at module-import via `_limiters["<name>"] = RateLimiter(max_requests=4, window_seconds=60)`. The `await limiter.acquire()` call has been LIFTED out of every engine's `search()` method into the workflow (`search_web._engine_with_timing`). Engines retain `limiter.backoff()` and `limiter.reset_backoff()` calls inside `search()` for per-engine CAPTCHA/error tracking. This separation lets the smoke's `engine_timeout` watchdog wrap only actual engine work — rate-limit waits happen outside the watchdog.

**Entity decoding (post-2026-05-05):** title fields and CrossRef synthesis container-title are wrapped in a `_deep_unescape` helper (idempotent `html.unescape` loop) to handle double-encoded entities like `&amp;nbsp;` → `\u00a0`. OpenAlex's `_reconstruct_abstract` applies `html.unescape` per-word on the inverted_index BEFORE joining + outer unescape after — handles double-encoded word keys like `&amp;quot;voters&amp;quot;` → `"voters"`.

### engines/base.py

**Purpose:** Abstract `BaseEngine` parent class. Defines the engine interface (name, URL builder, parser, rate-limiter hook).

### engines/google.py

**Purpose:** Google Search via pydoll. Three-layer consent handling: (1) SOCS cookie injection per-tab via `Network.setCookie` BEFORE navigation (primary bypass), (2) inline-consent body-text detection ("Before you continue" / "We use cookies and data") + button click on the search URL, (3) `consent.google.com` redirect handler as fallback. DOM parsing via `#rso h3` + `.MjjYud` selectors, parse_js without IIFE (pydoll's `execute_script` already wraps in function scope). Wait timeouts calibrated to dev p95: `MAX_WAIT_CYCLES=3`, `WAIT_INTERVAL=0.2s`. Rate-limit pre-registered at `max_requests=4, window_seconds=60` (uniform 4 req/min, normalized 2026-05-04). `limiter.backoff()` only on CAPTCHA (`/sorry/` URL) or exception — not on EMPTY (no-results ≠ rate-limit signal).

### engines/scholar.py

**Purpose:** Google Scholar via pydoll. DOM parsing via `.gs_r.gs_or.gs_scl` + `.gs_rt`. Rate-limit pre-registered at `max_requests=4, window_seconds=60` (uniform 4 req/min, normalized 2026-05-04). CAPTCHA detection via `/sorry/` URL path. Consent redirect handling via `consent.google.com` domain check + JS button click. `limiter.backoff()` only on CAPTCHA or exception — not on EMPTY. Note: `_JS_PARSE` uses flat JS (var declarations first, `return JSON.stringify` at end) — pydoll's `execute_script` rejects multi-line scripts that start with `return` as first statement (`SyntaxError: Illegal return statement`); verified fix 2026-05-03.

### engines/crossref.py

**Purpose:** CrossRef REST API via httpx (no browser needed). Uses polite pool `mailto` header for higher rate limits. Rate-limit pre-registered at `max_requests=4, window_seconds=60` (uniform 4 req/min, normalized 2026-05-04). Snippet construction (post-bead-a45 2026-05-04): when `abstract` field is present (~16% of returns), strips all XML tags including JATS namespaces (`<jats:p>`, `<ns4:p>`) via generic `re.sub(r'<[^>]+>', '', x)` plus `html.unescape`; when `abstract` is absent (~84% of returns), synthesizes from `author[0].family` + initial of `given` + ` et al.` (if multi-author) + ` (year)` + `, container-title[0]` — e.g. `"de Groot, C. (2022), Asynchronous Python Programming with Asyncio and Async/await"`. Returns bibliographic metadata as `SearchResult` entries.

### engines/duckduckgo.py

**Purpose:** DuckDuckGo web search via pydoll (`html.duckduckgo.com/html/` GET endpoint). No consent handling needed — DDG html-endpoint does not show a consent banner. No cookie injection needed — `kl=wt-wt` (worldwide, no region filter) is included directly in the GET URL. DOM-based CAPTCHA detection (`form#challenge-form`). URL cleaning extracts the actual destination from DDG's redirect wrapper (`duckduckgo.com/l/?uddg=<encoded>`). Rate-limit pre-registered at `max_requests=4, window_seconds=60` (uniform 4 req/min, normalized 2026-05-04). `limiter.backoff()` only on CAPTCHA or exception — not on EMPTY. Selectors: `#links > div.web-result` (result containers), `h2 a` (title + href), `a.result__snippet` (snippet) — verified live 2026-05-03.

### engines/mojeek.py

**Purpose:** Mojeek web search via pydoll (mojeek.com/search GET endpoint). Own crawler index — not Bing-derivative, third independent index after Google + DDG. No consent handling, no CAPTCHA detection (none observed in DOM probe 2026-05-03), no URL cleaning (direct hrefs, no redirect wrapper). Rate-limit pre-registered at `max_requests=4, window_seconds=60` (uniform 4 req/min, normalized 2026-05-04). `limiter.backoff()` only on exception — not on EMPTY. Selectors: `ul.results-standard > li > a.ob` (container anchor with direct `href`), `li h2 a` (title text), `li p.s` (snippet) — verified live 2026-05-03.

### engines/lobsters.py

**Purpose:** Lobste.rs web search via pydoll (lobste.rs/search GET endpoint). Link-aggregator for tech/programming content — smaller index than general engines, bias toward quality technical posts. No consent handling, no CAPTCHA detection (none observed in DOM probe 2026-05-03), no URL cleaning (direct hrefs, no redirect wrapper). Rate-limit pre-registered at `max_requests=4, window_seconds=60` (uniform 4 req/min, normalized 2026-05-04). `limiter.backoff()` only on exception — not on EMPTY. Selectors: `li.story` (result containers), `a.u-url` (href + title text), `a.domain` (snippet — domain-as-displayed, may include path prefix for GitHub repos). Snippet = domain only by design; `og:description` from preview-fetch fills the description field downstream — verified live 2026-05-03.

### engines/openalex.py

**Purpose:** OpenAlex academic graph via httpx (no browser, no auth, no API key required). Successor to Microsoft Academic Graph — ~250M works (papers, preprints, books, datasets), free and open. Polite-pool identifier loaded from `OPENALEX_MAILTO` env var (no default; set to any identifier email to avoid throttling from the anonymous pool). Rate-limit pre-registered at `max_requests=4, window_seconds=60`. Abstract reconstruction: OpenAlex stores abstracts as an inverted index (`word → [positions]`); `_reconstruct_abstract` inverts back to text by sorting words by first position and joining. URL strategy: `ids.arxiv` (full arXiv URL) > `doi` (full DOI URL, `https://doi.org/...`) > `id` (OpenAlex work URL, `https://openalex.org/W...`). Fields used: `id, doi, title, abstract_inverted_index, authorships, publication_year, cited_by_count, ids, primary_location`. Citation suffix added 2026-05-04: when `cited_by_count > 50`, appends ` (Cited N×)` to the snippet for visibility of high-impact papers (threshold tunable via constant, see `decisions/search07_ranking_format.md`).

### engines/stack_exchange.py

**Purpose:** Stack Exchange API via httpx (no browser, no auth required). Targets `stackoverflow.com` by default via `search/advanced` endpoint. API key optional: set `STACK_EXCHANGE_API_KEY` env var for 10k req/day; without key, anonymous quota is 300 req/day (logged once as warning on first call). Snippet from `body` field (HTML stripped + truncated to 500 chars) when `filter=withbody`; fallback to `"Score N · K answers · tagged x,y"` if body absent. Title HTML-decoded via `html.unescape`. Rate-limit pre-registered at `max_requests=4, window_seconds=60`.

## Stealth Decisions

Active stealth configuration lives in `src/search/browser.py` (hardcoded JS patches, UA, window size, Chrome options) and per-engine files (SOCS cookie for Google). `dev/search_pipeline/config.yml` no longer carries browser or stealth parameters — all that was stress-test scaffolding now removed. Historical research from the 9-engine exploration is documented in `decisions/stealth00_engine_status.md` (overview + dropped-engine verdicts) and `decisions/stealth01_fingerprint.md` through `stealth07_captcha.md` (per-layer detail).
