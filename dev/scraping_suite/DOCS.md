# Scraping Suite

Quality monitoring and configuration testing for the URL scraper module.

## 01_run_baseline.py

**Purpose:** Scrapes all test domains using the production `scrape_url_workflow` and saves results as numbered iterations with metadata (char count, word count, timestamp).
**Output:** `01_baselines/<domain>/iteration_<N>.md` + `metadata_<N>.json`

```bash
python dev/scraping_suite/01_run_baseline.py
```

## 02_compare_iterations.py

**Purpose:** Compares the last two iterations per domain to detect regressions. Generates unified diffs and classifies changes by magnitude (IDENTICAL, MINOR_CHANGE, MODERATE_CHANGE, MAJOR_CHANGE).
**Input:** `01_baselines/`
**Output:** `02_iteration_reports/diff_report_<timestamp>.txt`

```bash
python dev/scraping_suite/02_compare_iterations.py
```

## 03_compare_filters.py

**Purpose:** Tests multiple Crawl4AI content filter configurations (PruningFilter at various thresholds, BM25ContentFilter, raw) against test URLs. Saves raw and fit markdown for each config. Includes code block integrity check.
**Output:** `03_filter_comparison/<domain>_<config>_raw.md` / `_fit.md`

URLs are processed in parallel (PARALLEL_URLS=5, Semaphore). The 5 configs per URL run serially (fast, no benefit from parallelism).

```bash
python dev/scraping_suite/03_compare_filters.py
python dev/scraping_suite/03_compare_filters.py https://example.com
```

## 04_filter_debug.py

**Purpose:** Instruments the scraping pipeline step-by-step to show what each filter removes at each stage. Reports include node counts, character counts, percentage deltas, and markdown previews of removed content. Used during active profile development.
**Output:** `04_filter_reports/<profile>/<domain>_<timestamp>.txt`

```bash
python dev/scraping_suite/04_filter_debug.py https://de.wikipedia.org/wiki/Biber
python dev/scraping_suite/04_filter_debug.py --profile wiki
python dev/scraping_suite/04_filter_debug.py --all
```

## 05_compare_content_source.py

**Purpose:** Tests Crawl4AI's `content_source` parameter across many URLs per domain. Scrapes each URL with 6 configurations in parallel (5 URLs concurrent, 6 configs per URL concurrent) and saves the raw markdown output as individual .md files for manual inspection. Max 20 URLs per domain.
**Input:** Crawling suite reports from `../crawling_suite/01_reports/*.json`
**Output:** `05_content_source/<domain>/<config>/<NN>_<slug>.md`

Configs tested:

| Config | content_source | Filter | Markdown Field |
|--------|---------------|--------|----------------|
| cleaned_html | cleaned_html | none | raw_markdown |
| cleaned_html_pruning | cleaned_html | PruningFilter 0.48 | fit_markdown |
| raw_html | raw_html | none | raw_markdown |
| raw_html_pruning | raw_html | PruningFilter 0.48 | fit_markdown |
| fit_html | fit_html | none | raw_markdown |
| fit_html_pruning | fit_html | PruningFilter 0.48 | fit_markdown |

```bash
python dev/scraping_suite/05_compare_content_source.py --all
python dev/scraping_suite/05_compare_content_source.py --domain searxng_docs
python dev/scraping_suite/05_compare_content_source.py --url https://example.com
```

## 06_js_rendering.py

**Purpose:** Tests multiple Crawl4AI browser configurations for JS-heavy sites that fail with default settings. Compares content yield (char count, word count) across configs with different wait strategies: domcontentloaded baseline, networkidle, extended delay, CSS selector wait, and full page scan.
**Output:** `06_js_rendering/<domain>_<slug>_<config>.md`

```bash
python dev/scraping_suite/06_js_rendering.py
python dev/scraping_suite/06_js_rendering.py https://docs.trychroma.com/docs/overview/telemetry
```

## Workflows

### Regression (01 -> 02)

Standard workflow when changing the production scraper. Run baseline, then compare with previous iteration.

### Filter Exploration (03 -> 04)

Explore filter configurations. 03 gives broad comparison, 04 gives step-by-step pipeline transparency.

### Content Source (05)

Large-scale comparison of which HTML source + filter combination produces the best markdown for downstream cleanup agents. Output is raw .md files for manual review.

## domains.txt

Test URLs for scripts 01-04. One URL per line, comments with `#`.
