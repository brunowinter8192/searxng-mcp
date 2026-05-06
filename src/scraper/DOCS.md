# Scraper Module

URL scraping and site exploration tools powered by Crawl4AI for SearXNG MCP server.

## scrape_url.py

**Purpose:** URL scraping orchestrator. Uses Crawl4AI's AsyncWebCrawler with PruningContentFilter to extract clean page content as markdown. Two-phase browser strategy: normal browser first, stealth fallback for anti-bot sites.
**Input:** URL string and optional maximum content length (default 15000).
**Output:** Filtered markdown content wrapped in TextContent, or error message with plugin hint on failure.

### scrape_url_workflow()

Main orchestrator. Two-phase approach:

1. **Phase 1: Normal browser** — Standard Crawl4AI without stealth patches. Works for most sites (Wikipedia, docs, blogs). Tries `networkidle` first, falls back to `domcontentloaded`.
2. **Phase 2: Stealth browser** — Only if Phase 1 returns empty. Uses `enable_stealth=True` + `UndetectedAdapter` + `AsyncPlaywrightCrawlerStrategy` (Level 3 anti-bot evasion). For sites with bot detection (e.g. TDS, some news sites).

Noise removal via `excluded_selector=COOKIE_CONSENT_SELECTOR` — CSS selectors matching common cookie consent frameworks. `remove_overlay_elements` is NOT used (destroys Wikipedia content by misclassifying DOM elements as overlays).

On empty result, returns error message with plugin hint if URL matches a known domain with dedicated MCP plugin (Reddit, arxiv).

### try_scrape()

Attempts a single scrape with given browser config, optional crawler strategy, and wait strategy. Returns `(content, garbage_type, status_code)` tuple. Checks `result.status_code` first — if >= 400, returns `("", "http_error", status_code)` immediately without content analysis (catches padded 404 pages). Content selection: `fit_markdown` if >= 200 chars (MIN_CONTENT_THRESHOLD), otherwise falls back to `raw_markdown`. This prevents PruningContentFilter from destroying table-heavy content (e.g. Wikipedia). Checks content via `is_garbage_content()` — if `cookie_wall` is detected, attempts `strip_consent_prefix()` first: if stripping yields different content that passes garbage detection, returns stripped content as success. All other garbage types (and cookie_wall when stripping fails) return empty string to trigger fallback chain.

### is_garbage_content()

Returns `str | None` — garbage type identifier or None if content is valid. Detects seven categories:
1. **`minimal_content`:** Empty content OR `len(content.strip()) < 50`. Checked FIRST before all others. Catches whitespace-only pages (gdpr.eu 1 char, PDF whitespace 87 bytes treated as HTML by Crawl4AI).
2. **`crawl4ai_error`:** "Crawl4AI Error:", "Document is empty", "page is not fully supported"
3. **`http_error`:** Short content (<1000 chars) with 404/403/NOT_FOUND/Access Denied keywords
4. **`nav_dump`:** ≥20 non-empty lines AND >60% are standalone markdown link lines (`[text](url)` on their own line). Catches large pages that are pure navigation with no content (e.g. 162KB AWS announcement pages).
5. **`cookie_wall`:** High density of cookie-related terms (>15 occurrences of "cookie"/"consent"/"duration" in first 5000 chars + "consent preferences" or "cookieyes" or "cookie preferences" present). Note: Amazon uses "cookie preferences" instead of "consent preferences".
6. **`login_wall`:** Short content (<2000 chars) with login/paywall patterns ("sign in", "log in", "login", "subscribe to continue", "create account", "premium content", "paywall", "members only", "subscriber only").
7. **`cloudflare`:** Short content (<500 chars) containing "checking your browser" or "enable javascript and cookies", OR "just a moment" + "cloudflare" anywhere.

`_GARBAGE_MESSAGES` dict maps each type to a human-readable error message for the caller. `try_scrape()` logs garbage type on every detection.

Called by both `try_scrape()` and `try_scrape_raw()` after content extraction.

### strip_consent_prefix()

Attempts to recover content from a cookie-wall page by stripping the leading consent block. Counts keyword density (CONSENT_WORDS: cookie, consent, einwilligung, tracking, akzeptieren, datenschutz, zweck) in the first 3000 chars. If density > CONSENT_DENSITY_THRESHOLD (5), searches for the first `#` or `##` heading after CONSENT_SKIP_OFFSET (300 chars) and returns content from that heading onward. Returns original content unchanged if density is low (baseline pages) or no heading is found after the offset.

### truncate_content()

Truncates content if exceeding maximum length. Attempts to break at paragraph boundary for clean truncation. Appends truncation notice when content is cut.

### log_scrape_failure()

Appends one JSONL failure record to `dev/scrape_pipeline/failures.jsonl`. Called at the final failure exit in `scrape_url_workflow()` when all 3 attempts are exhausted. Fields: `ts` (ISO 8601 UTC), `url`, `garbage_type`, `status_code`. Requires `SEARXNG_PROJECT_ROOT` env variable — silently skips if not set. Silent fail on any I/O error.

### get_plugin_hint()

Returns plugin hint only for domains with dedicated MCP plugins (uses `PLUGIN_ROUTED_DOMAINS` from `routing.py`). Returns empty string for all other domains.

### Constants

- `COOKIE_CONSENT_SELECTOR` — CSS selector string matching common cookie consent frameworks: CookieYes (cky-consent, cky-banner, cky-modal), OneTrust, Cookiebot, cc-banner, GDPR, cookie-banner, cookie-consent, cookie-notice, cookie-law. Note: `cky-modal` is critical — CookieYes stores the full Consent Preferences dialog (12K+ chars of cookie descriptions) in this container. Without it, only the small banner (236 chars) is removed.
- `DEFAULT_MAX_CONTENT_LENGTH` — 15000 chars
- `MIN_CONTENT_THRESHOLD` — 200 chars. fit_markdown below this triggers raw_markdown fallback.
- `CONSENT_WORDS` — keyword list for consent density scoring: cookie, consent, einwilligung, tracking, akzeptieren, datenschutz, zweck
- `CONSENT_DENSITY_THRESHOLD` — 5. Sum of CONSENT_WORDS occurrences in first 3000 chars must exceed this to trigger stripping.
- `CONSENT_SKIP_OFFSET` — 300 chars. Heading search starts at this offset to skip banner fragments before the actual content starts.

## scrape_url_raw.py

**Purpose:** Raw markdown scraping orchestrator for RAG indexing. Same two-phase browser strategy as `scrape_url.py` (normal → stealth fallback) but uses `DefaultMarkdownGenerator()` without PruningContentFilter and saves `raw_markdown` output to a .md file with `<!-- source: URL -->` header. Generates safe filename from URL (domain + path, max 120 chars).
**Input:** URL string and output directory path.
**Output:** TextContent with file path and char count on success, or error message on failure (Cloudflare-specific message when CF-protected).

## download_pdf.py

**Purpose:** PDF file download. Uses `requests.get()` with streaming to download PDFs from URLs and save them to disk. Validates Content-Type, extracts filename from Content-Disposition header or URL path. Also called automatically by `cli.py` when `scrape_url` or `scrape_url_raw` receives a URL ending in `.pdf` (auto-routing).
**Input:** URL string and optional output directory (default `~/Downloads/`).
**Output:** TextContent with file path and human-readable file size on success, or error message on failure.

## Architecture

Content extraction is delegated entirely to Crawl4AI (v0.8.0):
- **Browser strategy:** Normal browser first, Stealth (Level 3) as fallback. UndetectedAdapter breaks some sites (Wikipedia) by patching the browser too aggressively.
- **Cookie removal:** CSS selector exclusion via `excluded_selector`. Specific selectors per framework (CookieYes, OneTrust, Cookiebot, GDPR etc.). `remove_overlay_elements` is NOT used — it removes legitimate content on some sites.
- **Content filtering:** PruningContentFilter(0.48) + fit_markdown for relevance assessment. raw_markdown fallback when filtered content < 200 chars (table-heavy pages).
- **Markdown generation:** Three modes:
  - **scrape_url (MCP tool):** PruningContentFilter + fit_markdown — noise-filtered, for in-conversation reading
  - **scrape_url_raw (MCP tool):** DefaultMarkdownGenerator + raw_markdown — full fidelity, saves to file for RAG indexing
  - **crawl_site (export script):** DefaultMarkdownGenerator + raw_markdown — full fidelity, batch crawl, noise handled by downstream RAG cleanup agent
- **Known issue:** Crawl4AI captures stdout — always write debug output to files, not print()
- **Cookie-Wall debugging:** Inject JS to enumerate `[class*='cky']` elements and check textLen per element. The largest container is usually the unmissed consent dialog. Add its class to COOKIE_CONSENT_SELECTOR.
