# Scraper Module

URL scraping tool with profile-based routing and JavaScript rendering for SearXNG MCP server.

## routing.py

**Purpose:** URL-based profile routing. Matches incoming URLs against domain patterns to select the appropriate scraping profile.
**Input:** URL string.
**Output:** Profile configuration dictionary with all scraping parameters.

### resolve_profile()

Main orchestrator. Takes URL, loads config from profiles.yml, matches domain against routing patterns, returns profile dict. Falls back to "default" profile when no routing pattern matches.

### load_config()

Loads and caches YAML config from profiles.yml. Uses module-level cache to avoid repeated file reads.

### match_url_to_profile()

Matches URL hostname against routing patterns using fnmatch for wildcard support (e.g., `*.wikipedia.org`). Returns profile name string or "default" if no match.

## profiles.yml

**Purpose:** Configuration file defining scraping profiles and URL-to-profile routing.

Each profile defines scraping parameters optimized for a category of websites. The routing section maps domain patterns to profile names. Adding a new domain requires one line in the routing section.

Profile parameters control three pipeline phases: fetch (wait_until, selector_timeout, content_selectors), filter (skip_table_classes, nav_patterns, noise_url_patterns, noise_text_patterns), and markdown cleanup (markdown_cleanup tag list selecting which cleanup functions to run).

Available profiles: default (generic, no site-specific filters), wiki (Wikipedia with citation/table/navigation removal), sphinx (Sphinx documentation with source button/paragraph marker removal), blog (Medium-style with paywall/UI noise removal), js_rendered (SPA sites with networkidle wait strategy).

## scrape_url.py

**Purpose:** Main orchestrator for single URL scraping with profile-based configuration. Resolves profile from URL, then coordinates HTML parsing, content filtering, and markdown conversion using profile parameters.
**Input:** Single URL string and optional maximum content length.
**Output:** Plain markdown content string wrapped in TextContent, or error message string on failure.

### scrape_url_workflow()

Main orchestrator function. Resolves scraping profile from URL via routing.py, coordinates browser initialization, URL content fetching with profile-specific wait strategy and selectors, and content extraction with profile-specific filters and cleanup. Manages browser lifecycle and ensures cleanup.

### extract_single_content()

Converts single HTML string to markdown with URL header. Passes profile to filter_content and cleanup_tags to to_markdown for profile-specific processing.

### init_browser()

Initializes headless Chromium browser instance using Playwright. Returns browser object for page scraping.

### fetch_url_content()

Fetches HTML content from URL using Playwright with stealth browser context. Uses profile-configured wait_until strategy (domcontentloaded or networkidle), content_selectors, and selector_timeout. Creates isolated browser context with realistic user agent and viewport. Returns raw HTML string or exception on failure.

### cleanup_browser()

Releases browser resources by closing the browser instance. Ensures proper cleanup even on errors.

### truncate_content()

Truncates content if exceeding maximum length. Attempts to break at paragraph boundary for clean truncation. Appends truncation notice when content is cut.

## html_parser.py

**Purpose:** Parses raw HTML into structured node representation with whitespace metadata preservation.
**Input:** HTML string.
**Output:** Dictionary with structured nodes array and tag stack state.

### parse_html()

Main orchestrator. Parses HTML string into structured representation using HTMLContentParser. Returns dictionary with nodes array and tag stack state.

### HTMLContentParser

Custom HTMLParser subclass that builds structured representation of HTML document. Tracks tag hierarchy, extracts text content with parent tag context, and preserves whitespace metadata. Handles pre-block depth tracking to preserve literal whitespace in code blocks. Text nodes inside pre blocks get in_pre flag and preserve all whitespace including standalone newlines. Text nodes outside pre blocks get has_leading_space and has_trailing_space metadata for intelligent spacing in markdown conversion.

## content_filter.py

**Purpose:** Filters parsed HTML nodes to extract main content while removing navigation, scripts, and other non-content elements. Uses profile configuration for site-specific filtering.
**Input:** Parsed nodes dictionary from html_parser and profile configuration dict.
**Output:** Filtered list of nodes containing only main content.

### filter_content()

Main orchestrator. Takes parsed content and profile dict. Applies universal skip-tag removal, main content extraction, then profile-configured nav_patterns, skip_table_classes, noise_url_patterns, and noise_text_patterns. Filter functions only execute when their corresponding profile list is non-empty.

### remove_skip_tags()

Removes all nodes belonging to universal skip tags (aside, script, style, noscript, iframe, svg, nav, footer, header, title). Always applied regardless of profile. Tracks nesting depth to handle nested skip tags correctly.

### remove_navigation_attributes()

Removes navigation elements by analyzing HTML attributes against profile-provided nav_patterns list. Filters div, section, aside, ul, ol, li, span, label, button, input, form elements with matching class, id, or role attributes.

### extract_main_content()

Extracts content from main, article, or section tags when present. Returns all nodes if no main content container found. Prioritizes main tag, then article tag, then section tags with content-related class or id attributes.

### find_content_tag_start()

Finds index of first content tag with improved priority detection.

### find_matching_end()

Finds index of matching end tag for given start tag. Tracks nesting depth to handle nested same-name tags correctly.

### remove_noise_links()

Removes anchor tags matching profile-provided noise URL patterns. Takes nodes list and patterns list as parameters.

### remove_noise_text()

Removes text nodes matching profile-provided noise text patterns. Takes nodes list and patterns list. Also removes hardcoded exact matches ('--', 'Share', 'Listen').

### remove_skip_tables()

Removes tables matching profile-provided skip class patterns. Generalized replacement for the former remove_wikipedia_tables function. Takes nodes list and skip_classes list as parameters.

## markdown_converter.py

**Purpose:** Converts filtered HTML nodes to clean markdown with profile-selective cleanup, proper whitespace boundaries, and code block preservation.
**Input:** Filtered nodes list from content_filter, maximum content length, and cleanup_tags list from profile.
**Output:** Clean markdown string with normalized whitespace.

### to_markdown()

Main orchestrator. Converts filtered nodes to markdown string. Executes three steps: converts HTML nodes to raw markdown, runs profile-selected cleanup functions followed by generic cleanup, normalizes whitespace while preserving code blocks.

### clean_markdown_artifacts()

Dispatcher function. Takes markdown string and cleanup_tags list. Runs each tag's cleanup function from cleanup_map, then always runs clean_generic_artifacts. Available cleanup tags: wiki_citations, wiki_links, sphinx_source, german_url_decode.

### clean_wiki_citations()

Removes Wikipedia citation references. Handles [[N]](#cite_note) patterns, [[N]](cite...) patterns, and standalone [N] number brackets.

### clean_wiki_links()

Removes Wikipedia internal /wiki/ links while preserving link text. Handles parenthesized wiki links, empty wiki links, and standard wiki links with trailing punctuation.

### clean_sphinx_source()

Removes Sphinx documentation artifacts: [[source]](url) buttons, standalone [source] text, paragraph markers [¶], and back-to-top arrows [↑].

### clean_german_url_decode()

Decodes German URL-encoded characters (umlauts and parentheses) commonly found in German Wikipedia URLs.

### clean_generic_artifacts()

Removes generic markdown artifacts that apply to all profiles regardless of cleanup_tags. Handles zero-width space anchors, hash self-reference anchors, double-bracket link patterns [[X]](url), anchor-only parenthetical links (#section), empty image/link brackets, broken image extensions, and malformed parentheses.

### strip_tracking_params()

Removes tracking query parameters from URLs. Preserves scheme, host, path, and fragment.

### sanitize_image_alt()

Sanitizes image alt text for markdown compatibility. Removes file extensions, strips markdown-breaking characters, truncates to 100 characters.

### extract_image_markdown()

Extracts image markdown with lazy loading support and size filtering. Filters out small and avatar-sized images.

### handle_start_tag()

Processes opening HTML tags and appends markdown equivalent to result buffer.

### handle_end_tag()

Processes closing HTML tags and appends markdown equivalent to result buffer.

### handle_text_node()

Processes text content nodes with whitespace normalization.

### handle_self_closing_tag()

Processes self-closing HTML tags (br, img, hr).

### convert_nodes_to_markdown()

Orchestrates node-to-markdown conversion by delegating to specialized handlers.

### should_add_space_before()

Checks if space should be added before inline tag marker.

### find_next_node()

Finds next node in list. Returns None if current node is last.

### should_add_space_after()

Checks if space should be added after inline tag marker.

### clean_whitespace()

Normalizes whitespace patterns in markdown text while preserving code blocks.

### clean_whitespace_chunk()

Cleans non-code-block chunk of whitespace issues.
