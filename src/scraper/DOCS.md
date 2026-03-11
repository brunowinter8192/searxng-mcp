# Scraper Module

URL scraping tool powered by Crawl4AI for SearXNG MCP server. Extracts LLM-friendly filtered markdown from any URL with JavaScript rendering.

## scrape_url.py

**Purpose:** URL scraping orchestrator. Uses Crawl4AI's AsyncWebCrawler with PruningContentFilter to extract noise-filtered page content as markdown. Optimized for readability and relevance assessment — navigation menus, sidebars, footers and cookie banners are filtered out.
**Input:** URL string and optional maximum content length (default 15000).
**Output:** Filtered markdown content wrapped in TextContent, or error message on failure.

### scrape_url_workflow()

Main orchestrator. Creates Crawl4AI browser and run configuration with PruningContentFilter (threshold 0.48), fetches URL, extracts fit_markdown (noise-filtered content). Truncates at paragraph boundary if exceeding max_content_length. Note: PruningFilter destroys code block formatting (whitespace stripped) — this is acceptable for the MCP use case (relevance assessment). For full-fidelity content export, use crawl_site.py which uses raw_markdown without filter.

### truncate_content()

Truncates content if exceeding maximum length. Attempts to break at paragraph boundary for clean truncation. Appends truncation notice when content is cut.

## explore_site.py

**Purpose:** Site structure reconnaissance. Crawls a website using BFS to discover all pages and build a summary with depth distribution, page counts, and character counts. No file export — analysis only.
**Input:** URL string and optional max_pages limit (default 200).
**Output:** Dict with seed_url, domain, total_pages, total_chars, depth_distribution (count + chars per level).

### explore_site_workflow()

Main orchestrator. Extracts domain from URL, runs BFS discovery crawl, builds site map from results.

### crawl_for_discovery()

BFS crawl with DomainFilter + ContentTypeFilter (text/html). Uses max_depth=10 internally to discover full site structure. Returns raw CrawlResult list.

### build_site_map()

Aggregates crawl results into summary. Deduplicates URLs (trailing slash normalization), extracts depth from `result.metadata["depth"]` (set by Crawl4AI BFS strategy), computes per-depth statistics. Returns only aggregated counts, no individual URL list.

## Architecture

Content extraction is delegated entirely to Crawl4AI (v0.8.0):
- **Browser management:** Crawl4AI manages Playwright/Patchright internally
- **JavaScript rendering:** `wait_until="networkidle"` ensures JS-heavy sites are fully rendered
- **Markdown generation:** Two modes depending on use case:
  - **scrape_url (MCP tool):** PruningContentFilter(0.48) + fit_markdown — noise-filtered, readable, for relevance assessment. Code blocks may lose formatting.
  - **crawl_site (export script):** DefaultMarkdownGenerator without filter + raw_markdown — full fidelity, preserves code blocks. Noise handled by downstream cleanup agent in RAG pipeline.
- **No per-site configuration needed:** Works generically across all website types
