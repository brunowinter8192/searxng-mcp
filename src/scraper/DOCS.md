# Scraper Module

URL scraping tool powered by Crawl4AI for SearXNG MCP server. Extracts clean, LLM-friendly markdown from any URL with automatic content filtering and JavaScript rendering.

## scrape_url.py

**Purpose:** URL scraping orchestrator. Uses Crawl4AI's AsyncWebCrawler with PruningContentFilter to extract main content as clean markdown.
**Input:** URL string and optional maximum content length (default 15000).
**Output:** Filtered markdown content wrapped in TextContent, or error message on failure.

### scrape_url_workflow()

Main orchestrator. Creates Crawl4AI browser and run configuration, fetches URL, extracts fit_markdown (heuristically filtered content). Truncates at paragraph boundary if exceeding max_content_length.

### truncate_content()

Truncates content if exceeding maximum length. Attempts to break at paragraph boundary for clean truncation. Appends truncation notice when content is cut.

## Architecture

Content extraction is delegated entirely to Crawl4AI (v0.8.0):
- **Browser management:** Crawl4AI manages Playwright/Patchright internally
- **Content filtering:** PruningContentFilter with threshold 0.48 removes navigation, sidebars, footers automatically
- **Markdown generation:** DefaultMarkdownGenerator produces clean markdown with headings, lists, tables, code blocks
- **No per-site configuration needed:** Works generically across all website types
