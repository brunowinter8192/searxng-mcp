# Scraper Module

URL scraping and site exploration tools powered by Crawl4AI for SearXNG MCP server.

## scrape_url.py

**Purpose:** URL scraping orchestrator. Uses Crawl4AI's AsyncWebCrawler with multi-layer noise removal and PruningContentFilter to extract clean page content as markdown.
**Input:** URL string and optional maximum content length (default 15000).
**Output:** Filtered markdown content wrapped in TextContent, or error message with plugin hint on failure.

### scrape_url_workflow()

Main orchestrator. Attempts scrape with `networkidle` wait strategy first, falls back to `domcontentloaded` on timeout/error. Three noise-removal layers applied in sequence:

1. `remove_overlay_elements=True` — JS-based removal of cookie banners, modals, sticky elements from DOM before scraping
2. `excluded_selector=COOKIE_CONSENT_SELECTOR` — CSS selector matching 16 common cookie consent frameworks (CookieYes, OneTrust, Cookiebot, cc-banner, GDPR etc.), elements removed from HTML before markdown conversion
3. `PruningContentFilter(threshold=0.48)` + `fit_markdown` — content scoring filter removes remaining low-quality blocks

On empty result, returns error message with plugin hint if URL matches a known domain with dedicated MCP plugin (Reddit, arxiv).

Note: PruningFilter destroys code block formatting (whitespace stripped). Acceptable for MCP use case (relevance assessment). For full-fidelity export, use crawl_site.py with raw_markdown.

### try_scrape()

Attempts a single scrape with given wait strategy. Creates CrawlerRunConfig with all noise-removal layers, runs AsyncWebCrawler, returns fit_markdown content or empty string on any exception.

### truncate_content()

Truncates content if exceeding maximum length. Attempts to break at paragraph boundary for clean truncation. Appends truncation notice when content is cut.

### get_plugin_hint()

Checks URL against PLUGIN_HINTS dict. Returns hint string for domains with dedicated MCP plugins (reddit.com, arxiv.org), empty string otherwise.

### Constants

- `COOKIE_CONSENT_SELECTOR` — CSS selector string matching common cookie consent frameworks: CookieYes (cky-*), OneTrust, Cookiebot, cc-banner, GDPR, cookie-banner, cookie-consent, cookie-notice, cookie-law
- `PLUGIN_HINTS` — Dict mapping domains to plugin usage hints
- `DEFAULT_MAX_CONTENT_LENGTH` — 15000 chars

## explore_site.py

**Purpose:** Site structure reconnaissance. Crawls a website using BFS to discover all pages and build a summary with depth distribution, page counts, and character counts. No file export — analysis only.
**Input:** URL string and optional max_pages limit (default 200).
**Output:** TextContent with formatted Markdown summary (page count, total chars, depth distribution).

### explore_site_workflow()

Main orchestrator. Extracts domain from URL, runs BFS discovery crawl, builds site map, formats as Markdown.

### crawl_for_discovery()

BFS crawl with DomainFilter + ContentTypeFilter (text/html). Uses `wait_until="domcontentloaded"` for performance (explore only needs links, not rendered content). max_depth=10 internally. Returns raw CrawlResult list.

### build_site_map()

Aggregates crawl results into summary dict. Deduplicates URLs (trailing slash normalization), extracts depth from metadata, computes per-depth statistics.

### format_site_map()

Formats site map dict as readable Markdown. Includes domain, seed URL, total pages, total chars, and depth distribution. No individual URL listing (keeps output compact for LLM context).

## Architecture

Content extraction is delegated entirely to Crawl4AI (v0.8.0):
- **Browser management:** Crawl4AI manages Playwright/Patchright internally
- **JavaScript rendering:** scrape_url uses `networkidle` with `domcontentloaded` fallback; explore_site uses `domcontentloaded` only
- **Noise removal:** Three layers — DOM cleanup (overlays), CSS selector exclusion (cookie banners), content scoring (PruningFilter)
- **Markdown generation:** Two modes depending on use case:
  - **scrape_url (MCP tool):** PruningContentFilter(0.48) + fit_markdown — noise-filtered, for relevance assessment
  - **crawl_site (export script):** DefaultMarkdownGenerator without filter + raw_markdown — full fidelity, noise handled by downstream RAG cleanup agent
