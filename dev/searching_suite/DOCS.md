# Searching Suite

Test suite for evaluating and tuning SearXNG search result quality.

## usecase.md

**Purpose:** Documents the concrete use case driving query selection and tuning decisions.

Describes the Quant Finance / ML Trading research context: why these specific queries matter, what domain knowledge gaps exist, and what the search results should help achieve.

## queries.txt

**Purpose:** Test queries for search quality evaluation.

One query per line. Lines starting with # are comments. Grouped by use-case type (metasearch, trading/finance, general tech). Add or modify queries to match actual search patterns.

## 01_run_search.py

**Purpose:** Run all test queries against SearXNG API and generate markdown report.
**Input:** queries.txt (one query per line).
**Output:** Markdown report in 01_reports/ with timestamp.

### run_search_suite()

Main orchestrator. Loads queries, runs each against SearXNG API, builds and saves report.

### load_queries()

Reads queries.txt, filters comments and empty lines, returns list of query strings.

### compute_settings_hash()

Computes MD5 hash (first 8 chars) of settings.yml for config identification across reports.

### run_query()

Executes single query against SearXNG API at localhost:8080. Returns top 10 results as list of dicts. Uses requests directly (no MCP dependency).

### extract_domain()

Extracts netloc from URL for domain classification.

### build_report()

Builds full markdown report. Summary section includes total queries, avg results, multi-engine percentage, avg score, and top 10 domains. Per-query section shows ranked table with score, engines, domain, title, URL, and snippet (first 200 chars from SearXNG content field).

### save_report()

Writes report to 01_reports/ with timestamped filename.

## 02_evaluate_content.py

**Purpose:** Scrape top URLs from a search report and evaluate content quality. Uses the same scraping pipeline as the MCP scrape_url tool.
**Input:** Latest search report from 01_reports/ (or path via CLI argument).
**Output:** Summary report in 02_reports/ plus individual .md files per URL in 02_content_<report_stem>/.

Imports `scrape_url_workflow` from `src/scraper/scrape_url` to ensure identical scraping behavior as the MCP tool (same filters, fallbacks, cookie removal). Scrapes top 3 URLs per query with 2s delay between requests. Content truncated to 4000 chars at paragraph boundary.

Fallback chain when scraping fails: scrape_url_workflow (with all filters and networkidle→domcontentloaded fallback) → SearXNG snippet (from 01-report) → error marker. Each result is tagged with its source (scraped, snippet, failed) for traceability. Garbage detection flags content dominated by cookie banners, cloudflare pages, or login walls.

### evaluate_content()

Main orchestrator. Resolves report path, parses queries and URLs, scrapes content with fallback, saves individual .md files and summary report.

### resolve_report_path()

Returns CLI argument path or latest report from 01_reports/.

### parse_search_report()

Regex-parses 01-report markdown. Extracts query text, URLs, scores, domains, titles, and snippets from per-query tables.

### scrape_all_urls()

Iterates all queries and their top URLs. Calls scrape_url_workflow per URL with asyncio.sleep delay between requests.

### scrape_with_fallback()

Calls scrape_url_workflow, checks result for error messages. Falls back to snippet on empty/error results. Returns content string and source label.

### is_garbage_content()

Detects cookie banners, cloudflare challenges, and login walls by counting garbage pattern matches. Content with 3+ matches is classified as garbage.

### truncate_content()

Truncates content at paragraph boundary if exceeding max length.

### url_to_filename()

Generates safe filesystem name from URL (netloc + path, special chars replaced with underscore, max 120 chars).

### save_content_files()

Saves individual .md file per URL in 02_content_<report_stem>/ directory. Each file contains metadata header (title, URL, domain, score, source, query) and content body.

### build_report()

Generates summary markdown report with scrape statistics (scraped/snippet/failed counts) and per-query sections referencing content files.

### save_report()

Writes report to 02_reports/ with timestamped filename.

## Workflow

1. Edit queries.txt with test queries
2. Run: `./venv/bin/python dev/searching_suite/01_run_search.py`
3. Read report in 01_reports/
4. Run: `./venv/bin/python dev/searching_suite/02_evaluate_content.py`
5. Read content report in 02_reports/ and individual files in 02_content_*/
6. Evaluate: Is the content relevant? Are the right domains showing up?
7. Change config in src/searxng/settings.yml
8. Restart: `docker compose restart searxng`
9. Run again, compare reports
