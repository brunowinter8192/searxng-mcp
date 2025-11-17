# URL Scraper Tool

Parallel async web scraping with JavaScript rendering and content extraction.

## Project Structure

```
scraper/
├── scrape_urls.py        # Main orchestrator
├── html_parser.py        # stdlib HTMLParser wrapper
├── content_filter.py     # Tag filtering and content extraction
├── markdown_formatter.py # HTML to Markdown conversion
└── DOCS.md              # This file
```

## scrape_urls.py

**Purpose:** Orchestrates the complete scraping pipeline from URL fetching to content extraction.

**Input:** List of URLs and optional concurrency limit

**Output:** List of dictionaries containing URL, extracted Markdown content, success status, and error information

### scrape_urls_workflow()

Orchestrates the parallel scraping and extraction process. Initializes browser, creates semaphore for concurrency control, spawns async tasks for each URL, gathers raw HTML results, extracts content from all results, and formats the final output. Uses asyncio.gather with return_exceptions=True for graceful error handling.

### init_browser()

Starts Playwright async API and launches headless Chromium browser. Returns browser object for reuse across all requests. Single browser instance reduces overhead.

### scrape_single_url()

Scrapes one URL within semaphore-controlled concurrency. Creates isolated browser context, navigates to URL with 30-second timeout, waits for DOM content load, extracts full HTML, and closes context. Returns raw HTML string.

### cleanup_browser()

Closes browser instance and releases resources. Called after all scraping completes.

### extract_all_content()

Processes list of raw HTML results through extraction pipeline. Preserves exceptions for error handling. Returns list of extracted Markdown strings or exceptions.

### extract_single_content()

Converts single HTML string to clean Markdown. Calls parse_html to build structure, filter_content to remove boilerplate, and to_markdown for final conversion.

### format_results()

Transforms extracted results into standardized output format. Each result includes url, content (Markdown), success boolean, and error field.

## html_parser.py

**Purpose:** Parses raw HTML into structured node representation using Python stdlib HTMLParser.

**Input:** Raw HTML string

**Output:** Dictionary with nodes list and tag stack

### parse_html()

Creates HTMLContentParser instance, feeds HTML string, and returns parsed structure. Entry point for HTML parsing.

### HTMLContentParser

Subclass of stdlib HTMLParser. Maintains tag stack for nesting awareness. Builds list of nodes representing start tags, end tags, text content, and self-closing tags. Each node includes type, tag name, attributes, and parent context.

### handle_starttag()

Pushes tag onto stack and records start node with attributes.

### handle_endtag()

Pops matching tag from stack and records end node.

### handle_data()

Records text content with parent tag context for semantic awareness.

### handle_startendtag()

Records self-closing tags like img and br.

### get_result()

Returns complete parsed structure with all nodes and current tag stack.

## content_filter.py

**Purpose:** Removes boilerplate HTML elements and extracts main content area.

**Input:** Parsed HTML structure from html_parser

**Output:** Filtered list of nodes containing only relevant content

### filter_content()

Orchestrates filtering process. First removes skip tags (nav, footer, script, etc.), then extracts main content area if found.

### remove_skip_tags()

Iterates through nodes and removes entire subtrees of skip tags. Tracks nesting depth to handle nested skip tags correctly. Skip tags include nav, footer, header, aside, script, style, noscript, iframe, svg.

### extract_main_content()

Searches for main or article tags as primary content containers. If found, returns only nodes within that container. Falls back to returning all filtered nodes if no content container found.

### find_content_tag_start()

Searches for first occurrence of priority content tags (main, then article). Returns index or -1 if not found.

### find_matching_end()

Given start index of content tag, finds corresponding closing tag by tracking nesting depth. Returns end index or -1.

## markdown_formatter.py

**Purpose:** Converts filtered HTML nodes to clean Markdown text.

**Input:** List of filtered nodes from content_filter

**Output:** Clean Markdown string with proper formatting

### to_markdown()

Orchestrates Markdown conversion. Converts nodes to raw Markdown, cleans excessive whitespace, and truncates if content exceeds MAX_CONTENT_LENGTH (15000 characters).

### convert_nodes_to_markdown()

Main conversion engine. Iterates through nodes and applies tag-specific Markdown formatting. Handles headings (h1-h6), paragraphs, emphasis (strong, em), code (inline and block), links, images, lists (ordered and unordered with nesting), blockquotes, horizontal rules, and line breaks. Maintains list stack for proper indentation.

### clean_whitespace()

Removes excessive blank lines (max 2 consecutive), collapses multiple spaces, and trims leading/trailing whitespace.

### truncate_content()

Limits content length for LLM context management. Truncates at paragraph boundary when possible. Appends truncation notice when content is cut.

## Configuration

DEFAULT_CONCURRENCY: 5 parallel requests
TIMEOUT_MS: 30000ms page load timeout
MAX_CONTENT_LENGTH: 15000 characters before truncation
SKIP_TAGS: nav, footer, header, aside, script, style, noscript, iframe, svg
CONTENT_TAGS: main, article (priority containers)

## Error Handling

Fail-fast philosophy with graceful degradation per URL. Individual failures captured as exceptions and returned in result structure. HTML parsing errors propagate up. Content extraction failures result in empty content with error message.
