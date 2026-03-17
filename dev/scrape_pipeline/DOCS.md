# Scrape Pipeline

Quality monitoring and configuration testing for the URL scraper module.

## 01_baseline.py

**Purpose:** Scrapes all test domains using the production `scrape_url_workflow` and saves results as numbered iterations with metadata (char count, word count, timestamp).
**Output:** `01_baselines/<domain>/iteration_<N>.md` + `metadata_<N>.json`

```bash
python dev/scrape_pipeline/01_baseline.py
```

## 02_regression.py

**Purpose:** Compares the last two iterations per domain to detect regressions. Generates unified diffs and classifies changes by magnitude (IDENTICAL, MINOR_CHANGE, MODERATE_CHANGE, MAJOR_CHANGE).
**Input:** `01_baselines/`
**Output:** `02_reports/diff_report_<timestamp>.txt`

```bash
python dev/scrape_pipeline/02_regression.py
```

## 03_browser.py

**Purpose:** Tests multiple Crawl4AI browser configurations for JS-heavy sites that fail with default settings. Compares content yield (char count, word count) across configs with different wait strategies: domcontentloaded baseline, networkidle, extended delay, CSS selector wait, and full page scan.
**Output:** `03_reports/<domain>_<slug>_<config>.md`

```bash
python dev/scrape_pipeline/03_browser.py
python dev/scrape_pipeline/03_browser.py https://docs.trychroma.com/docs/overview/telemetry
```

## 04_filtering.py

**Purpose:** Tests multiple Crawl4AI content filter configurations (PruningFilter at various thresholds, BM25ContentFilter, raw) against test URLs. Saves raw and fit markdown for each config. Includes code block integrity check.
**Output:** `04_reports/<domain>_<config>_raw.md` / `_fit.md`

URLs are processed in parallel (PARALLEL_URLS=5, Semaphore). The 5 configs per URL run serially (fast, no benefit from parallelism).

```bash
python dev/scrape_pipeline/04_filtering.py
python dev/scrape_pipeline/04_filtering.py https://example.com
```

## 05_filter_debug.py

**Purpose:** Instruments the scraping pipeline step-by-step to show what each filter removes at each stage. Reports include node counts, character counts, percentage deltas, and markdown previews of removed content. Used during active profile development.
**Output:** `05_reports/<profile>/<domain>_<timestamp>.txt`

```bash
python dev/scrape_pipeline/05_filter_debug.py https://de.wikipedia.org/wiki/Biber
python dev/scrape_pipeline/05_filter_debug.py --profile wiki
python dev/scrape_pipeline/05_filter_debug.py --all
```

## 06_content_source.py

**Purpose:** Tests Crawl4AI's `content_source` parameter across many URLs per domain. Scrapes each URL with 6 configurations in parallel (5 URLs concurrent, 6 configs per URL concurrent) and saves the raw markdown output as individual .md files for manual inspection. Max 20 URLs per domain.
**Input:** Explore pipeline reports from `../explore_pipeline/01_reports/*.json`
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
python dev/scrape_pipeline/06_content_source.py --all
python dev/scrape_pipeline/06_content_source.py --domain searxng_docs
python dev/scrape_pipeline/06_content_source.py --url https://example.com
```

## Workflows

### Regression (01 -> 02)

Standard workflow when changing the production scraper. Run baseline, then compare with previous iteration.

### Browser Debug (03)

For JS-heavy sites that fail with default settings. Compare wait strategies to find what works.

### Filter Exploration (04 -> 05)

Explore filter configurations. 04 gives broad comparison, 05 gives step-by-step pipeline transparency.

### Content Source (06)

Large-scale comparison of which HTML source + filter combination produces the best markdown for downstream cleanup agents. Requires explore_pipeline/01_reports as input. Output is raw .md files for manual review.

## domains.txt

Test URLs for scripts 01-05. One URL per line, comments with `#`.
