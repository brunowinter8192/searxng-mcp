# dev/search_pipeline/

## Role

Production-mode smoke test suite for all 8 active search engines. Each per-engine smoke invokes the production engine class from `src/search/engines/` directly — no standalone pydoll setup, rate-limiter active, selectors and config internal to the engine class. Multi-engine smoke (`05`) fans out across all engines in parallel via `asyncio.gather`. `config.yml` retained for run parameters used by `02_burst_smoke.py` only.

## Layout

| File | Purpose |
|------|---------|
| `config.yml` | Run params (`queries_file`, `page_load_timeout`, `consent_settle`) and report path (`output_dir`) — used by `02_burst_smoke.py` only |
| `queries.txt` | 30 baseline queries (Tech 8 + Science 6 + German 6 + Niche 5 + Broad 5) |
| `01_google_smoke.py` | Google production-mode smoke — imports `GoogleEngine` from `src/`, calls `.search()` per query, rate-limiter active (4 req/60s), writes `google_smoke_<ts>.md` to `01_reports/`. Status: OK / EMPTY / ERROR |
| `02_burst_smoke.py` | Burst smoke against the production CLI — invokes `searxng-cli search_batch` per batch (one subprocess per N queries, warm Chrome amortized) and writes `burst_<ts>.md` to `01_reports/`. Exists to validate the prod CLI path under the architectural rate pattern (4 queries per burst, optional cooldown). CLI flags: `--queries-per-burst N` (default 4), `--cooldown S` (default 60), `--max-queries N` (default all from queries.txt). |
| `04_ddg_smoke.py` | DuckDuckGo production-mode smoke — imports `DuckDuckGoEngine` from `src/`, calls `.search()` per query, rate-limiter active (4 req/60s), writes `ddg_smoke_<ts>.md` to `01_reports/`. Status: OK / EMPTY / ERROR |
| `05_search_smoke.py` | Multi-engine comparison smoke — imports all 8 engine classes from `src/`, fans out per-engine in parallel via `asyncio.gather`, merges by URL preserving per-engine snippets, fetches previews via `src/search/preview.py`, writes `search_smoke_<ts>.md` to `01_reports/`. CLI flags: `--engines` (default: google duckduckgo), `--max-queries N`. |
| `06_mojeek_smoke.py` | Mojeek production-mode smoke — imports `MojeekEngine` from `src/`, calls `.search()` per query, rate-limiter active (4 req/60s), writes `mojeek_smoke_<ts>.md` to `01_reports/`. Status: OK / EMPTY / ERROR |
| `07_lobsters_smoke.py` | Lobsters production-mode smoke — imports `LobstersEngine` from `src/`, calls `.search()` per query, rate-limiter active (4 req/60s), writes `lobsters_smoke_<ts>.md` to `01_reports/`. Status: OK / EMPTY / ERROR |
| `08_scholar_smoke.py` | Google Scholar smoke runner — imports `ScholarEngine` from `src/`, calls `.search()` directly (pydoll browser managed by `src/search/browser.py` singleton), runs 30 baseline queries. Rate limiter is engine-internal (4 req/60s → ~7.5 min total). Writes `scholar_smoke_<ts>.md` to `01_reports/`. Status taxonomy: OK (≥3 results) / EMPTY / SUSPECT / ERROR. |
| `09_openalex_smoke.py` | OpenAlex smoke runner — imports `OpenAlexEngine` from `src/`, calls `.search()` directly (pure HTTP, no browser), runs 30 baseline queries. Writes `openalex_smoke_<ts>.md` to `01_reports/`. Status taxonomy: OK / EMPTY / RATE_LIMITED / ERROR. OPENALEX_MAILTO env var forwarded automatically via engine. |
| `10_stack_exchange_smoke.py` | Stack Exchange smoke runner — imports `StackExchangeEngine` from `src/`, calls `.search()` directly (pure HTTP, no browser), runs 30 baseline queries against `api.stackexchange.com/2.3/search/advanced?site=stackoverflow`. Writes `se_smoke_<ts>.md` to `01_reports/`. Status taxonomy: OK / EMPTY / RATE_LIMITED / ERROR. Set `STACK_EXCHANGE_API_KEY` env var for 10k/day quota (without key: anonymous 300/day). |
| `11_pipeline_smoke.py` | Full-pipeline smoke — calls `search_web_workflow(query, _with_timings=True, engine_timeout=N)` per query (vs 05's per-engine fanout that bypasses `_merge_and_rank`), reads cache after each call. Per-URL block in MD output: title + URL + engines list + `source: SOURCE \| display: '...'` (chosen snippet) + `og: ... \| meta: ...` + per-engine snippet lines — singular baseline format that downstream investigation scripts (snippet_quality_analysis) parse without re-running queries. Per-query timing line + `Slot fill: GENERAL X/12, ACADEMIC Y/6, QA Z/2` (no OVERFLOW post-dl9-v3). Per-engine status/timing inline (`Engines: google=OK/200ms ddg=TIMEOUT/8002ms ...`) plus `Per-Engine Status Aggregate` section at end (OK/EMPTY/TIMEOUT/ERROR counts per engine across all queries). Writes `pipeline_smoke_<ts>.md` to `01_reports/`. CLI flags: `--max-queries N`, `--language` (default `en`), `--engine-timeout N` (float seconds, default None — pass 8.0 to enable per-engine watchdog around actual search work, with rate-limiter wait happening outside the watchdog). Use this script when reviewing the production ranking output as the user would see it AND when needing the structured baseline for downstream investigations. |
| `empty_classify_se.py` | Classification probe for Stack Exchange EMPTY queries — direct httpx against api.stackexchange.com (no rate limiter, no API key) for the 15 SE-EMPTY queries from the canonical 2026-05-04 multi-engine smoke. Two probes per query: `site=stackoverflow` (production-identical) + `site=stackexchange` (cross-site fallback for ENGINE_NICHE detection). Output `empty_classify_se_<ts>.md` to `01_reports/`. Status taxonomy: ENGINE_EMPTY / ENGINE_NICHE / RATE_LIMITED / PIPELINE_BUG / UNKNOWN. |
| `empty_classify_lobsters.py` | Classification probe for Lobsters EMPTY queries — pydoll browser with 3s wait (vs production 600ms) for the 11 Lobsters-EMPTY queries from the same smoke. Captures story count, page title, HTML snippet, plus screenshots for first 3 queries (`empty_classify_lobsters_screenshots/`). Output `empty_classify_lobsters_<ts>.md` to `01_reports/`. Status taxonomy: ENGINE_EMPTY / PIPELINE_BUG / BOT_BLOCK / UNKNOWN. |
| `snippet_quality_analysis.py` | Per-source bloat + lexical-density analysis over the singular pipeline_smoke baseline (auto-finds newest `pipeline_smoke_*.md` via glob+sort, no hardcoded filename). 11 sources (8 engines + scholar_strip derived bucket + og + meta), 9 bloat-pattern regexes (URL breadcrumb, Read-more, Web-results prefix, Featured-snippet prefix, social-proof, Scholar ellipsis, Mojeek nav-dump, HTML entities, Tag noise) + 1 JATS-XML pattern. Output sections: (1) per-source aggregated stats table (mean_clean_len, lex_density, % bloated, usefulness), (2) 8×8 engine-overlap matrix, (3) all-URLs side-by-side per-URL block with ⭐-Winner annotation per URL, (4) `Best by usefulness` aggregate (which source wins most often per length×density score across all URLs), (5) per-class breakdown of best-by-usefulness (GENERAL / ACADEMIC / QA winners). EN+DE combined stopword list for lexical_density (avoids penalizing German queries). Output `snippet_quality_<ts>.md` to `01_reports/`. |
| `engine_distribution_analysis.py` | Per-engine slot-count and slot-share analysis over the singular pipeline_smoke baseline (auto-finds newest `pipeline_smoke_*.md` via glob+sort). Imports `parse_smoke_report` from `snippet_quality_analysis.py`. Output sections: (1) slot-count total per engine (Total / GENERAL / ACADEMIC / QA / Solo / Overlap columns; column-sum footer shows actual vs URL-count baseline), (2) Per-Engine Status Aggregate quoted through from smoke tail (OK / EMPTY / TIMEOUT / ERROR), (3) slot-share + two baselines per engine within class — uniform (1/N) and OK-adjusted (engine OK / class OK sum) — with signed Δ columns; three sub-tables GENERAL / ACADEMIC / QA, (4) per-query distribution matrix (30 rows × 8 engine columns, cell = slot-count contributed by that engine in that query). Output `engine_distribution_<ts>.md` to `01_reports/`. |
| `snippet_selection_simulator.py` | Dry-run of new snippet-selection logic over the pipeline_smoke baseline (auto-finds newest `pipeline_smoke_*.md`). Imports `parse_smoke_report`, `strip_bloat`, `lexical_density` from `snippet_quality_analysis.py`. Selection: for each URL gather all non-empty sources (og, meta, per-engine snippets), score each as `clean_len × lex_density`, pick highest; if all sources below MIN_FLOOR=40 chars use best-of-worst fallback. Output sections: (1) Summary — analyzed/no-content/floor-trigger counts, NEW source distribution table, per-class NEW source distribution table, (2) Per-Query Picks — all 30 queries × all URLs, showing picked source, score, clean_len, ⚠ floor-trigger tag, and first 200 chars of picked snippet, (3) Floor-Triggered Cases — list of URLs where all sources were below MIN_FLOOR. Output `snippet_selection_<ts>.md` to `01_reports/`. |
| `01_reports/` | Singular baseline + investigation evidence: `pipeline_smoke_<ts>.md` (the canonical baseline produced by `11_pipeline_smoke.py`, contains all 600 URLs with per-source snippets — input for all investigation scripts), `snippet_quality_<ts>.md` (analysis output of `snippet_quality_analysis.py`), `empty_classify_se_<ts>.md` + `empty_classify_lobsters_<ts>.md` + `empty_classify_lobsters_screenshots/` (forensic probes from 2026-05-04 retained as historical evidence). Per-engine standalone smoke reports (`google_smoke_*.md` etc.) are NOT retained on dev — those scripts (`01_google_smoke.py` etc.) still exist for ad-hoc per-engine debugging but their outputs are gitignored / cleaned up. |

## Production Baseline

**Date:** 2026-05-04  
**Run:** `05_search_smoke.py --engines google duckduckgo mojeek lobsters "google scholar" crossref openalex stack_exchange --max-queries 30`  
**Report:** `01_reports/search_smoke_20260504_023641.md`

### Per-Engine Results (from full-pool smoke)

| Engine | OK | EMPTY | ERROR | Notes |
|--------|-----|-------|-------|-------|
| Google | 30 | 0 | 0 | Uniform 4 req/min, no backoff on EMPTY |
| DuckDuckGo | 30 | 0 | 0 | Uniform 4 req/min, no backoff on EMPTY |
| Mojeek | 30 | 0 | 0 | Uniform 4 req/min, no backoff on EMPTY |
| Lobsters | 19 | 11 | 0 | Link-aggregator; German + non-tech queries EMPTY (expected) |
| Google Scholar | 29 | 1 | 0 | Uniform 4 req/min (up from 3), no backoff on EMPTY |
| CrossRef | 30 | 0 | 0 | HTTP API, backoff only on 429/403 |
| OpenAlex | 26 | 4 | 0 | HTTP API, 4 EMPTY on niche dev-tool queries |
| Stack Exchange | 15 | 15 | 0 | HTTP API, 15 EMPTY on German + niche queries (expected) |

**KPI:** 30/30 queries with results from ≥1 engine. Wall time <12 min.

### Per-Engine Standalone Baselines

#### Google
- **Result (standalone):** 30/30 OK — prior standalone runs 2026-04-21 (stress baseline), production-mode from 2026-05-04
- **Stack:** headless Chrome via `GoogleEngine` (src/), uniform 4 req/min, no backoff on EMPTY, SOCS cookie injection per-tab, fingerprint patches, selectors `#rso h3` + `.MjjYud`

#### DuckDuckGo
- **Result (standalone):** 30/30 OK — first prod-mode standalone 2026-05-03, `01_reports/ddg_smoke_20260503_174043.md` (archived)
- **Stack:** headless Chrome via `DuckDuckGoEngine` (src/), uniform 4 req/min, no backoff on EMPTY, GET `html.duckduckgo.com/html/`

#### Mojeek
- **Result (standalone):** 7/30 OK at 0-delay stress (cascade above 4 req/min); at uniform 4 req/min: 30/30 OK in full-pool run
- **Stack:** headless Chrome via `MojeekEngine` (src/), uniform 4 req/min, no backoff on EMPTY
- **Rate-limit break (stress only):** 403 at query 10 (~1.2 req/s burst). Production 4 req/min stays well within threshold.

#### Google Scholar
- **Result:** 28/30 OK standalone — `01_reports/scholar_smoke_20260504_004124.md` (archived); 29/30 in full-pool run
- **Stack:** headless Chrome via `ScholarEngine` (src/), uniform 4 req/min (up from 3), no backoff on EMPTY
- **JS fix (2026-05-03):** `_JS_PARSE` rewritten from IIFE-with-leading-`return` to flat JS. Root cause: pydoll `execute_script` wraps single-line `return` scripts but passes multi-line raw to `Runtime.evaluate` where top-level `return` is illegal.

#### OpenAlex
- **Result:** 26/30 OK — `01_reports/openalex_smoke_20260504_003111.md` (archived); 4 EMPTY on non-academic queries
- **Stack:** pure httpx, `OpenAlexEngine` (src/), rate limiter 4 req/60s, ~7 min for 30 queries

#### Lobsters
- **Result:** 19/30 OK at production rate (4 req/min) in full-pool run; 16/30 at 0-delay stress
- **Stack:** headless Chrome via `LobstersEngine` (src/), uniform 4 req/min, no backoff on EMPTY
- **Notes:** Link-aggregator — smaller index; German + off-topic queries EMPTY (expected). Snippet = domain only by design.

#### Stack Exchange
- **Result:** 15/30 OK — consistent across standalone (`01_reports/se_smoke_20260504_012742.md`, archived) and full-pool run
- **Stack:** pure httpx, `StackExchangeEngine` (src/), rate limiter 4 req/60s, site=stackoverflow, filter=withbody, anonymous quota
- **Notes:** 15 EMPTY — German queries (6) + niche dev-tool queries. Token bucket paces to 59s wait every 4 queries.

#### 05 — Multi-engine comparison
- **Script:** `05_search_smoke.py` — imports from `src/` (not standalone), uses production engine instances
- **Design:** per-engine fanout avoids `search_web_workflow` merge so per-engine snippets are preserved for comparison
- **Preview:** calls `src/search/preview.py fetch_previews()` per query on the URL union — adds og/meta block per URL
- **Report:** `01_reports/search_smoke_<ts>.md` — per-query section with engine-set badges, per-engine snippets, preview block

## Running

```bash
# Google prod-mode smoke (30 queries via GoogleEngine, ~7.5 min at 4 req/min)
./venv/bin/python3 dev/search_pipeline/01_google_smoke.py

# DuckDuckGo prod-mode smoke (30 queries via DuckDuckGoEngine, ~7.5 min at 4 req/min)
./venv/bin/python3 dev/search_pipeline/04_ddg_smoke.py

# Burst against prod CLI (30 queries in 4-per-burst, no cooldown, ~1.7 min)
./venv/bin/python3 dev/search_pipeline/02_burst_smoke.py --queries-per-burst 4 --cooldown 0

# Burst with steady-state rate cap (30 queries, 4-per-burst, 60s cooldown between, ~9 min)
./venv/bin/python3 dev/search_pipeline/02_burst_smoke.py --queries-per-burst 4 --cooldown 60

# Mojeek prod-mode smoke (30 queries via MojeekEngine, ~7.5 min at 4 req/min)
./venv/bin/python3 dev/search_pipeline/06_mojeek_smoke.py

# Lobsters prod-mode smoke (30 queries via LobstersEngine, ~7.5 min at 4 req/min)
./venv/bin/python3 dev/search_pipeline/07_lobsters_smoke.py

# Google Scholar smoke (30 queries via ScholarEngine, ~7.5 min at 4 req/min)
./venv/bin/python3 dev/search_pipeline/08_scholar_smoke.py

# OpenAlex smoke (30 queries via OpenAlexEngine, ~7.5 min at 4 req/min)
OPENALEX_MAILTO=yourname@example.com ./venv/bin/python3 dev/search_pipeline/09_openalex_smoke.py

# Stack Exchange smoke (30 queries via StackExchangeEngine, ~7.5 min at 4 req/min)
./venv/bin/python3 dev/search_pipeline/10_stack_exchange_smoke.py
# with API key (10k/day quota):
STACK_EXCHANGE_API_KEY=your_key ./venv/bin/python3 dev/search_pipeline/10_stack_exchange_smoke.py

# Multi-engine comparison smoke — canonical baseline (all 8 engines, 30 queries, ~7.5 min)
./venv/bin/python3 dev/search_pipeline/05_search_smoke.py --engines google duckduckgo mojeek lobsters "google scholar" crossref openalex stack_exchange --max-queries 30

# Multi-engine smoke with query limit for quick validation
./venv/bin/python3 dev/search_pipeline/05_search_smoke.py --engines google duckduckgo --max-queries 5

# Single query diagnostic
./venv/bin/python3 dev/search_pipeline/00_single_query.py "your query here"
```
