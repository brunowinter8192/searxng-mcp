# Scraper Module

URL scraping tool with JavaScript rendering for SearXNG MCP server.

## scrape_url.py

**Purpose:** Main orchestrator for single URL scraping with JavaScript rendering. Coordinates HTML parsing, content filtering, and markdown conversion.
**Input:** Single URL string and optional maximum content length.
**Output:** Plain markdown content string wrapped in TextContent, or error message string on failure.

### scrape_url_workflow()

Main orchestrator function. Coordinates browser initialization, URL content fetching, and content extraction. Manages browser lifecycle and ensures cleanup. Returns plain markdown directly in TextContent on success, or error message on failure. Called directly by server.py tool definition. Uses domcontentloaded wait strategy for fast page loading without waiting for all network activity.

### extract_single_content()

Converts single HTML string to markdown with URL header. Takes URL, HTML string, and maximum content length. Orchestrates parsing (html_parser), filtering (content_filter), and markdown conversion (markdown_converter) pipeline. Prepends source URL header to output for clear provenance.

### init_browser()

Initializes headless Chromium browser instance using Playwright. Returns browser object for page scraping.

### fetch_url_content()

Fetches HTML content from URL using Playwright with stealth browser context. Creates isolated browser context with realistic user agent and viewport, navigates to URL with domcontentloaded wait strategy, then waits for content selectors (main, article, content class, h1) to become visible before extracting HTML. This two-phase approach handles both traditional server-rendered pages and SPAs that render content via JavaScript after initial DOM load. Returns raw HTML string or exception on failure.

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

**Purpose:** Filters parsed HTML nodes to extract main content while removing navigation, scripts, and other non-content elements.
**Input:** Parsed nodes dictionary from html_parser.
**Output:** Filtered list of nodes containing only main content.

### filter_content()

Main orchestrator. Filters parsed content to extract main content. Removes navigation, footer, script, header, and other non-content elements. Extracts content from main or article tags when present. Applies noise filtering to remove UI elements like signin links, share buttons, and standalone numbers.

### remove_skip_tags()

Removes all nodes belonging to skip tags like aside, script, style, noscript, iframe, svg, nav, footer. Tracks nesting depth to handle nested skip tags correctly.

### remove_navigation_attributes()

Removes navigation elements by analyzing HTML attributes. Filters div, section, aside, ul, ol, li, span, label, button, input, form elements with navigation-related class, id, or role attributes. Uses pattern matching against common navigation identifiers like vector-, mw-portlet, navigation, sidebar, menu.

### extract_main_content()

Extracts content from main, article, or section tags when present. Returns all nodes if no main content container found. Prioritizes main tag, then article tag, then section tags with content-related class or id attributes.

### find_content_tag_start()

Finds index of first content tag with improved priority detection. Searches for main, article, or section tags. For section tags, checks class and id attributes for content-related keywords like content, main, or article.

### find_matching_end()

Finds index of matching end tag for given start tag. Tracks nesting depth to handle nested same-name tags correctly.

### remove_noise_links()

Removes anchor tags that match noise URL patterns. Filters out signin links, clap buttons, bookmark buttons, and other UI action links that disrupt content flow. Skips entire link including inner content when href matches patterns like /m/signin, actionUrl=, clap_footer, or bookmark_footer.

### remove_noise_text()

Removes text nodes matching noise patterns. Filters out UI text like "Member-only story", "Share", "Listen", "Press enter or click to view", and specific noise strings like "--". Preserves numeric values to maintain data integrity in technical documentation, code examples, and JSON content.

## markdown_converter.py

**Purpose:** Converts filtered HTML nodes to clean markdown with proper whitespace boundaries and code block preservation.
**Input:** Filtered nodes list from content_filter and maximum content length.
**Output:** Clean markdown string with normalized whitespace.

### to_markdown()

Main orchestrator. Converts filtered nodes to markdown string with configurable maximum length. Orchestrates node conversion, artifact cleaning, and whitespace normalization. The workflow executes three steps: converts HTML nodes to raw markdown, removes Wikipedia-specific artifacts like citations and broken links, and normalizes whitespace patterns while preserving code blocks.

### strip_tracking_params()

Removes tracking query parameters from URLs. Takes URL string and returns clean URL without query string. Preserves scheme, host, path, and fragment while stripping all query parameters. Used to clean links from tracking suffixes like ?source=post_page or ?utm_source.

### sanitize_image_alt()

Sanitizes image alt text for markdown compatibility. Removes file extensions (.jpg, .png, .gif, .webp, .svg, .bmp), strips markdown-breaking characters (brackets, parentheses), and truncates to 100 characters with ellipsis if exceeding limit. Returns cleaned alt text suitable for markdown image syntax.

### extract_image_markdown()

Extracts image markdown with lazy loading support and size filtering. Checks src attribute first, falls back to data-src, data-lazy-src, or srcset for lazy-loaded images. Returns empty string if no valid source found (prevents ghost exclamation marks). Filters out small images (width or height below 100px) and avatar-sized images (Medium resize:fill patterns). Returns properly formatted markdown image syntax with alt text.

### handle_start_tag()

Processes opening HTML tags and appends markdown equivalent to result buffer. Handles headings, paragraphs, line breaks, bold, italic, code, pre blocks, links, images, lists, blockquotes, and tables. For tables, tracks state including header row detection and cell counting for separator row generation. Returns updated link_href and pre_depth state. Mutates result list, list_stack, and table_state in place.

### handle_end_tag()

Processes closing HTML tags and appends markdown equivalent to result buffer. Handles heading newlines, bold/italic/code closing markers with trailing space detection, pre block closing fences, link closing with href, list stack management, and table elements. For table rows, generates markdown separator row after header row using tracked cell count. Returns updated link_href and pre_depth state.

### handle_text_node()

Processes text content nodes with whitespace normalization. Preserves literal whitespace for text inside pre blocks (in_pre flag). For regular text, detects leading and trailing space metadata to insert boundary spaces when adjacent to alphanumeric characters. Mutates result list in place.

### handle_self_closing_tag()

Processes self-closing HTML tags (br, img, hr). Appends line break for br, image markdown for img (using extract_image_markdown), and horizontal rule for hr. Mutates result list in place.

### convert_nodes_to_markdown()

Orchestrates node-to-markdown conversion by delegating to specialized handlers. Iterates through nodes and dispatches to handle_start_tag, handle_end_tag, handle_text_node, or handle_self_closing_tag based on node type. Maintains conversion state including result buffer, list stack for nesting, link href for anchors, pre depth for code blocks, last text node for whitespace tracking, and table state for GitHub-flavored markdown table generation.

### should_add_space_before()

Helper function to check if space should be added before inline tag marker. Examines result buffer for trailing alphanumeric characters, checks parser whitespace flags, and applies smart spacing for inline formatting tags (strong, b, em, i, code). Adds space when previous text ends with alphanumeric character and current tag is inline formatting, even when parser flags indicate no explicit whitespace.

### find_next_node()

Helper function to find next node in list. Returns None if current node is last.

### should_add_space_after()

Helper function to check if space should be added after inline tag marker. Examines next text node's has_leading_space metadata and content start character. Adds space after inline formatting closing markers when next text starts with alphanumeric character, improving readability when HTML source lacks explicit whitespace.

### clean_markdown_artifacts()

Removes documentation artifacts from markdown output to improve readability and LLM processing quality. Handles both general documentation patterns (zero-width space anchors, hash self-reference anchors, empty bracket anchors) and Wikipedia-specific patterns (citation references, wiki links). Also decodes URL-encoded characters common in German Wikipedia. Applied after node-to-markdown conversion and before whitespace normalization.

### clean_whitespace()

Normalizes whitespace patterns in markdown text while preserving code blocks. Detects code fence markers and applies different rules inside vs outside code blocks. Outside code blocks collapses multiple consecutive spaces to single space, limits newlines to maximum of two, removes leading and trailing spaces around newlines. Inside code blocks preserves all whitespace literally including indentation.
