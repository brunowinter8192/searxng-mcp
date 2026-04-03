# Search Pipeline

Test suite for evaluating and tuning SearXNG search result quality with profile-based parameter testing.

## Shared Config (pipeline root)

### profiles.yml

**Purpose:** Define parameter sets for different query types. Each profile maps to SearXNG API parameters.

**Format:**
```yaml
profile_name:
  category: general|science|it|news
  language: en|de|all
  time_range: null|day|month|year
  engines: null|"engine1,engine2"  # null = use category defaults
```

**Built-in profiles:**
- `general` — Default web search (all general-category engines, no time filter)
- `science` — Academic papers (Google Scholar + Semantic Scholar + CrossRef, last year)
- `it` — Technical content (general category, last year)
- `research` — All general-category engines, no time filter (best for broad discovery)
- `recent` — Recent content (general, last month)

### queries.txt

**Purpose:** Test queries with profile assignments.

One query per line. Lines starting with `#` are comments. `@profile: <name>` sets the profile for subsequent queries until the next `@profile` directive.

**Format:**
```
# --- Section Name ---
@profile: research
query one
query two

@profile: general
query three
```

## engines_eval/ → decisions/search01_engines

### 01_engines.py

**Purpose:** Run all test queries against SearXNG API with profile-based parameters and generate markdown report.
**Input:** queries.txt + profiles.yml (in pipeline root).
**Output:** Markdown report in `01_reports/` with timestamp.

#### CLI

```bash
# Standard run (each query uses its assigned profile)
./venv/bin/python dev/search_pipeline/engines_eval/01_engines.py

# A/B compare mode (non-general queries run twice: profile + general)
./venv/bin/python dev/search_pipeline/engines_eval/01_engines.py --compare
```

#### Key Functions

- `load_queries()` — Parses queries.txt with `@profile:` directives, returns `list[dict]` with `{query, profile}`
- `load_profiles()` — Reads profiles.yml
- `run_query(query, profile)` — Executes query with profile parameters (category, engines, language, time_range). Paginates across MAX_PAGES (3) pages per query, deduplicates by URL, returns up to TOP_K (30) results
- `build_report()` — Summary + per-query tables showing profile, score, engines, domain, URL, snippet. In compare mode: comparison tables per query with result count, avg score, domain overlap.
- `compute_settings_hash()` — MD5 hash of settings.yml for config identification

## engines_eval/ → decisions/search02_routing (fingerprint investigation)

### 20_tls_fingerprint.py

**Purpose:** Probe external JA3 fingerprint services to measure the TLS fingerprint of SearXNG-style httpx requests.
**Input:** No CLI args. Queries tls.browserleaks.com and ja3er.com.
**Output:** Markdown report in `20_reports/` with JA3 hash, TLS version, cipher count, User-Agent.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/20_tls_fingerprint.py
```

### 21_cipher_shuffle_verify.py

**Purpose:** Verify that SearXNG's cipher shuffling (`shuffle_ciphers()`) produces distinct JA3 hashes across requests — confirms fingerprint diversification is active.
**Input:** No CLI args. Sends 12 requests to tls.browserleaks.com with fresh SSL context per request.
**Output:** Markdown report in `20_reports/` with per-request JA3 hash table and verdict (unique count / total).

```bash
./venv/bin/python dev/search_pipeline/engines_eval/21_cipher_shuffle_verify.py
```

### 22_header_inspection.py

**Purpose:** Inspect which HTTP headers SearXNG-style requests send, as seen by the server.
**Input:** No CLI args. Sends 3 requests to httpbin.org/headers.
**Output:** Markdown report in `20_reports/` with per-request header tables and consistency analysis.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/22_header_inspection.py
```

### 23_suspension_threshold.py

**Purpose:** Measure at which query rate each engine gets suspended by SearXNG's internal suspension mechanism. Tests 8 engines across 4 phases (10s / 5s / 2s / 1s intervals, 6 queries each).
**Input:** No CLI args. Queries local SearXNG at `http://localhost:8080`.
**Output:** Markdown report in `20_reports/` with suspension threshold per engine and per-phase detail tables.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/23_suspension_threshold.py
```

### 23_google_retest.py

**Purpose:** One-shot retest of Google after `suspension_times=0` and `ban_time_on_fail=0` were set. Verifies SearXNG no longer pre-emptively blocks Google.
**Input:** No CLI args. Runs same 4-phase protocol as `23_suspension_threshold.py`, Google only.
**Output:** Markdown report in `20_reports/` with verdict (suspension flag present/absent) and per-request results.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/23_google_retest.py
```

### 24_engine_health_check.py

**Purpose:** Phase-1-only health check for 6 previously-suspended engines after SearXNG 2026.4.3 update. Confirms engines are returning results at conservative query rate (10s × 6 queries).
**Input:** No CLI args. Tests: Brave, Mojeek, Startpage, Google Scholar, Semantic Scholar, CrossRef.
**Output:** Markdown report in `20_reports/` with summary table (clean/flagged/status per engine) and per-engine detail.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/24_engine_health_check.py
```

## ranking_eval/ → decisions/search03_ranking

### 03_ranking.py

**Purpose:** Compare two search reports to identify which configuration produced better results.
**Input:** Two report files from `engines_eval/01_reports/` (CLI args or auto-selects latest two).
**Output:** Comparison report in `03_reports/` with timestamp.

#### CLI

```bash
# Compare latest two reports
./venv/bin/python dev/search_pipeline/ranking_eval/03_ranking.py

# Compare specific reports
./venv/bin/python dev/search_pipeline/ranking_eval/03_ranking.py engines_eval/01_reports/report_A.md engines_eval/01_reports/report_B.md
```

#### Metrics

- Results count per query
- Average score per query
- Domain overlap (shared/total)
- Winner (A/B/=) by avg score
- New/lost URLs per query (detail section)

## content_eval/ → decisions/search01_engines (content quality aspect)

### 04_content_eval.py

**Purpose:** Scrape top URLs from a search report and evaluate content quality. Uses the same scraping pipeline as the MCP scrape_url tool.
**Input:** Latest search report from `engines_eval/01_reports/` (or path via CLI argument).
**Output:** Summary report in `04_reports/` plus individual .md files per URL in `04_content_<report_stem>/`.

Imports `scrape_url_workflow` from `src/scraper/scrape_url` to ensure identical scraping behavior as the MCP tool. Scrapes top 5 URLs per query (TOP_N_PER_QUERY) with 2s delay. Content truncated to 50000 chars at paragraph boundary (EXCERPT_LENGTH) — effectively no truncation.

Fallback chain: scrape_url_workflow → SearXNG snippet → error marker. Each result tagged with source (scraped, snippet, failed). Garbage detection for cookie banners, cloudflare, login walls.

## weights_eval/ → decisions/search04_weights

### 10_engine_consensus.py

**Purpose:** Evaluate engine weight calibration via consensus analysis. Measures how often each engine's results are corroborated by other engines.
**Input:** Hardcoded test queries (13 queries, mix of technical, scientific, German-language).
**Output:** Markdown report in `10_reports/` with per-engine consensus metrics.

#### CLI

```bash
./venv/bin/python dev/search_pipeline/weights_eval/10_engine_consensus.py
```

#### Metrics per Engine

- **Total URLs**: Unique URLs returned across all queries
- **Consensus Rate**: % of engine's URLs also found by ≥1 other engine (higher = better signal quality)
- **Unique URLs**: URLs found exclusively by this engine (discovery value)
- **Avg Position**: Mean combined-ranking position across all results
- **Top-20 Coverage**: URLs contributed to the top-20 consensus results per query

#### Usage

1. Run script (takes ~30s for 13 queries with 2s delay)
2. Read report in `10_reports/`
3. Paste results into `decisions/search04_weights.md` Evidenz section
4. Calibrate weights based on consensus rate vs. unique value trade-off

## Workflow

1. Edit queries.txt with test queries and `@profile:` assignments
2. Optionally edit profiles.yml to add/modify parameter sets
3. Run: `./venv/bin/python dev/search_pipeline/engines_eval/01_engines.py`
4. Read report in `engines_eval/01_reports/`
5. Optionally compare: `./venv/bin/python dev/search_pipeline/engines_eval/01_engines.py --compare`
6. For content quality: `./venv/bin/python dev/search_pipeline/content_eval/04_content_eval.py`
7. Read content report in `content_eval/04_reports/` and individual files in `04_content_*/`
8. To tune SearXNG config: edit src/searxng/settings.yml, restart Docker, run again
9. Compare reports: `./venv/bin/python dev/search_pipeline/ranking_eval/03_ranking.py`
