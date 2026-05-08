# dev/search_pipeline/inspections/

## Role

DOM-inspection tooling for engine selector drift recovery. Use when a browser-based engine returns persistent EMPTY or TIMEOUT for queries that should match — meaning the production selectors no longer match the rendered DOM (engine updated their markup).

This directory is NOT for one-shot debug scripts. It holds reusable methodology and committed inspection reports as historical evidence.

## Workflow

```
Engine returns EMPTY/TIMEOUT for N consecutive queries
    → run inspect_engine_dom.py <engine_name> "<sample_query>"
    → read report: H1 (broken selectors) + H2 (new data-test-id candidates) + Diagnosis
    → update _JS_WAIT + _JS_PARSE in src/search/engines/<engine>.py
    → smoke-test via dev/search_pipeline/<engine>_smoke.py
```

## Scripts

### inspect_engine_dom.py

**Purpose:** navigate to engine search page via production browser (pydoll stealth, JS rendered), run 7 heuristics, write timestamped MD report.

```bash
# Basic (3s JS wait, usually sufficient)
./venv/bin/python dev/search_pipeline/inspections/inspect_engine_dom.py semantic_scholar "transformer attention mechanism"

# Extended wait (consent banner / slow React hydration)
./venv/bin/python dev/search_pipeline/inspections/inspect_engine_dom.py semantic_scholar "transformer attention mechanism" --wait-s 5
```

**CLI:**
| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `engine` | yes | — | Engine name (see ENGINE_REGISTRY) |
| `query` | yes | — | Sample search query |
| `--wait-s` | no | 3.0 | Fixed post-navigate wait (seconds) for JS render |

**Output:** `dev/search_pipeline/inspections/<engine>_YYYYMMDD_HHMMSS.md`

**Heuristics reported:**
| # | Name | What it surfaces |
|---|------|-----------------|
| H1 | Current-selector presence | Which production selectors still match (count) vs broken (0) |
| H2 | data-test-id inventory | All `data-test-id` values filtered by semantic keywords — primary signal for SS-style engines |
| H3 | Repeating class clusters | First-class groups with ≥4 occurrences — surfaces new result-row class names |
| H4 | Class-substring scan | Elements whose class contains `paper`, `result`, `card`, `row`, etc. |
| H5 | data-* attribute scan | All distinct `data-*` attribute names (count ≥ 3) — surfaces structural IDs |
| H6 | HTML snippet | `outerHTML` of top H3 cluster element (2000 char cap) — manual confirmation |
| H7 | External link count | Confirms results rendered at all (0 = page blocked/consent/error) |

**Engine registry:** add new engines to `ENGINE_REGISTRY` in `inspect_engine_dom.py`. Current status:

| Engine | Status |
|--------|--------|
| `semantic_scholar` | Configured |
| `google` | TODO stub |
| `google_scholar` | TODO stub |
| `duckduckgo` | TODO stub |
| `mojeek` | TODO stub |
| `lobsters` | TODO stub |

## Committed Reports

| File | Date | Query | Outcome |
|------|------|-------|---------|
| `semantic_scholar_20260508_*.md` | 2026-05-08 | transformer attention mechanism | Diagnosed `div.cl-paper-row` drift → new selectors identified |
