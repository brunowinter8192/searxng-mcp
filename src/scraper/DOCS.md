# Scraper Module

URL scraping tool with JavaScript rendering for SearXNG MCP server.

## scrape_url.py

**Purpose:** Single URL scraper with JavaScript rendering and HTML to markdown conversion using networkidle wait strategy.
**Input:** Single URL string and optional maximum content length.
**Output:** Dictionary containing url, markdown content, success status, and error.

### scrape_url_workflow()

Main orchestrator function. Coordinates browser initialization, URL content fetching, content extraction, and result formatting. Manages browser lifecycle and ensures cleanup. Called directly by server.py tool definition. Uses networkidle wait strategy for complete JavaScript rendering.

### init_browser()

Initializes headless Chromium browser instance using Playwright. Returns browser object for page scraping.

### fetch_url_content()

Fetches HTML content from URL using Playwright with networkidle wait strategy. Creates isolated browser context, navigates to URL with timeout, waits for all network activity to settle before extracting page HTML content, and closes context. Returns raw HTML string or exception on failure.

### cleanup_browser()

Releases browser resources by closing the browser instance. Ensures proper cleanup even on errors.

### extract_single_content()

Converts single HTML string to markdown. Orchestrates parsing, filtering, and markdown conversion pipeline with configurable maximum content length.

### format_success_result()

Formats successful scrape result into structured dictionary. Returns url, content, success flag set to true, and null error.

### format_error_result()

Formats error result into structured dictionary. Returns url, empty content, success flag set to false, and error message string.

### parse_html()

Parses HTML string into structured representation using HTMLContentParser. Returns dictionary with nodes array and tag stack state.

### filter_content()

Filters parsed content to extract main content. Removes navigation, footer, script, and other non-content elements. Extracts content from main or article tags when present.

### to_markdown()

Converts filtered nodes to markdown string with configurable maximum length. Orchestrates node conversion, whitespace cleaning, and content truncation.

### HTMLContentParser

Custom HTMLParser subclass that builds structured representation of HTML document. Tracks tag hierarchy and extracts text content with parent tag context. Handles opening tags, closing tags, text data, and self-closing tags.

### remove_skip_tags()

Removes all nodes belonging to skip tags like aside, script, style, noscript, iframe, svg. Tracks nesting depth to handle nested skip tags correctly. Less aggressive than previous version to preserve legitimate content.

### extract_main_content()

Extracts content from main, article, or section tags when present. Returns all nodes if no main content container found. Prioritizes main tag, then article tag, then section tags with content-related class or id attributes.

### find_content_tag_start()

Finds index of first content tag with improved priority detection. Searches for main, article, or section tags. For section tags, checks class and id attributes for content-related keywords like 'content', 'main', or 'article'. Returns -1 if not found.

### find_matching_end()

Finds index of matching end tag for given start tag. Tracks nesting depth to handle nested same-name tags correctly.

### convert_nodes_to_markdown()

Converts parsed nodes to markdown string. Handles headings, paragraphs, lists, links, images, code blocks, blockquotes, and inline formatting. Maintains list stack for proper nesting and link href for anchor tags.

### clean_whitespace()

Removes excessive whitespace from markdown text. Collapses multiple newlines, removes multiple spaces, and trims leading/trailing whitespace.

### truncate_content()

Truncates content if exceeding maximum length. Attempts to break at paragraph boundary for clean truncation. Appends truncation notice when content is cut.
