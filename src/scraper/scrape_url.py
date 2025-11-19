# INFRASTRUCTURE
import re
from html.parser import HTMLParser
from html import unescape
from playwright.async_api import async_playwright, Browser
from mcp.types import TextContent

TIMEOUT_MS = 30000
DEFAULT_MAX_CONTENT_LENGTH = 15000

SKIP_TAGS = {'aside', 'script', 'style', 'noscript', 'iframe', 'svg', 'nav', 'footer'}
CONTENT_TAGS = {'main', 'article', 'section', 'div', 'body'}
INLINE_TAGS = {'a', 'strong', 'b', 'em', 'i', 'code', 'span', 'img'}
BLOCK_TAGS = {'p', 'div', 'section', 'article', 'main', 'blockquote'}
HEADING_TAGS = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### ', 'h5': '##### ', 'h6': '###### '}
LIST_TAGS = {'ul', 'ol'}


# ORCHESTRATOR
async def scrape_url_workflow(url: str, max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH) -> list[TextContent]:
    browser = await init_browser()
    raw_html = await fetch_url_content(url, browser)
    await cleanup_browser(browser)

    if isinstance(raw_html, Exception):
        error_msg = f"Error scraping {url}: {str(raw_html)}"
        return [TextContent(type="text", text=error_msg)]

    extracted_content = extract_single_content(raw_html, max_content_length)
    return [TextContent(type="text", text=extracted_content)]


# FUNCTIONS

# Initialize headless Chromium browser instance
async def init_browser() -> Browser:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    return browser


# Fetch HTML content from URL using Playwright with networkidle wait
async def fetch_url_content(url: str, browser: Browser) -> str | Exception:
    try:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, timeout=TIMEOUT_MS, wait_until="networkidle")
        content = await page.content()
        await context.close()
        return content
    except Exception as e:
        return e


# Release browser resources
async def cleanup_browser(browser: Browser) -> None:
    await browser.close()


# Parse and convert single HTML to markdown
def extract_single_content(html: str, max_content_length: int) -> str:
    parsed = parse_html(html)
    filtered = filter_content(parsed)
    markdown = to_markdown(filtered, max_content_length)
    return markdown


# Parse HTML into structured representation
def parse_html(html: str) -> dict:
    parser = HTMLContentParser()
    parser.feed(html)
    return parser.get_result()


# Filter parsed content to extract main content
def filter_content(parsed: dict) -> list:
    nodes = parsed.get("nodes", [])
    filtered = remove_skip_tags(nodes)
    main_content = extract_main_content(filtered)
    clean_content = remove_navigation_attributes(main_content)
    return clean_content


# Remove navigation elements by attributes
def remove_navigation_attributes(nodes: list) -> list:
    result = []
    skip_depth = 0
    current_skip_tag = None
    filterable_tags = {'div', 'section', 'aside', 'ul', 'ol', 'li', 'span', 'label', 'button', 'input', 'form'}

    for node in nodes:
        if node["type"] == "start" and node["tag"] in filterable_tags:
            attrs = node.get("attrs", {})
            class_attr = attrs.get("class", "").lower()
            id_attr = attrs.get("id", "").lower()
            role_attr = attrs.get("role", "").lower()

            nav_patterns = ['vector-', 'mw-portlet', 'mw-panel', 'navigation', 'noprint', 'toc', 'sidebar', 'menu', 'tools', 'p-lang', 'p-tb', 'p-navigation', 'p-interaction', 'wmde-banner', 'cn-fundraising', 'frb']

            should_skip = (
                role_attr in ['navigation', 'complementary', 'banner'] or
                any(pattern in class_attr for pattern in nav_patterns) or
                any(pattern in id_attr for pattern in nav_patterns)
            )

            if should_skip:
                if skip_depth == 0:
                    current_skip_tag = node["tag"]
                skip_depth += 1
                continue

        if node["type"] == "end" and skip_depth > 0:
            if node["tag"] == current_skip_tag:
                skip_depth -= 1
                if skip_depth == 0:
                    current_skip_tag = None
            continue

        if skip_depth == 0:
            result.append(node)

    return result


# Convert filtered nodes to markdown string
def to_markdown(nodes: list, max_content_length: int) -> str:
    raw_markdown = convert_nodes_to_markdown(nodes)
    cleaned = clean_whitespace(raw_markdown)
    truncated = truncate_content(cleaned, max_content_length)
    return truncated


# HTMLParser subclass that builds structured representation
class HTMLContentParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.result = []
        self.tag_stack = []
        self.current_attrs = {}

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        self.current_attrs[tag] = dict(attrs)
        self.result.append({
            "type": "start",
            "tag": tag,
            "attrs": dict(attrs)
        })

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        self.result.append({
            "type": "end",
            "tag": tag
        })

    def handle_data(self, data):
        text = unescape(data.strip())
        if text:
            self.result.append({
                "type": "text",
                "content": text,
                "parent_tags": list(self.tag_stack)
            })

    def handle_startendtag(self, tag, attrs):
        self.result.append({
            "type": "self_closing",
            "tag": tag,
            "attrs": dict(attrs)
        })

    def get_result(self) -> dict:
        return {
            "nodes": self.result,
            "tag_stack": self.tag_stack
        }


# Remove nodes that belong to skip tags
def remove_skip_tags(nodes: list) -> list:
    result = []
    skip_depth = 0
    current_skip_tag = None

    for node in nodes:
        if node["type"] == "start" and node["tag"] in SKIP_TAGS:
            if skip_depth == 0:
                current_skip_tag = node["tag"]
            skip_depth += 1
            continue

        if node["type"] == "end" and skip_depth > 0:
            if node["tag"] == current_skip_tag:
                skip_depth -= 1
                if skip_depth == 0:
                    current_skip_tag = None
            continue

        if skip_depth == 0:
            result.append(node)

    return result


# Extract content from main/article tags or return all
def extract_main_content(nodes: list) -> list:
    main_start = find_content_tag_start(nodes)
    if main_start == -1:
        return nodes

    main_end = find_matching_end(nodes, main_start)
    if main_end == -1:
        return nodes

    return nodes[main_start:main_end + 1]


# Find index of first content tag with improved priority
def find_content_tag_start(nodes: list) -> int:
    for priority_tag in ['main', 'article', 'section']:
        for i, node in enumerate(nodes):
            if node["type"] == "start" and node["tag"] == priority_tag:
                attrs = node.get("attrs", {})
                class_attr = attrs.get("class", "").lower()
                id_attr = attrs.get("id", "").lower()

                if priority_tag in ['main', 'article']:
                    return i

                if 'content' in class_attr or 'content' in id_attr or 'main' in class_attr or 'article' in class_attr:
                    return i
    return -1


# Find matching end tag index
def find_matching_end(nodes: list, start_idx: int) -> int:
    if start_idx == -1:
        return -1

    tag = nodes[start_idx]["tag"]
    depth = 1

    for i in range(start_idx + 1, len(nodes)):
        node = nodes[i]
        if node["type"] == "start" and node["tag"] == tag:
            depth += 1
        elif node["type"] == "end" and node["tag"] == tag:
            depth -= 1
            if depth == 0:
                return i

    return -1


# Convert parsed nodes to markdown string
def convert_nodes_to_markdown(nodes: list) -> str:
    result = []
    list_stack = []
    link_href = None

    for node in nodes:
        if node["type"] == "start":
            tag = node["tag"]
            attrs = node.get("attrs", {})

            if tag in HEADING_TAGS:
                result.append("\n\n" + HEADING_TAGS[tag])
            elif tag == "p":
                result.append("\n\n")
            elif tag == "br":
                result.append("\n")
            elif tag == "strong" or tag == "b":
                result.append("**")
            elif tag == "em" or tag == "i":
                result.append("*")
            elif tag == "code":
                result.append("`")
            elif tag == "pre":
                result.append("\n\n```\n")
            elif tag == "a":
                link_href = attrs.get("href", "")
                result.append("[")
            elif tag == "img":
                alt = attrs.get("alt", "image")
                src = attrs.get("src", "")
                result.append(f"![{alt}]({src})")
            elif tag == "ul":
                list_stack.append("ul")
                result.append("\n")
            elif tag == "ol":
                list_stack.append("ol")
                result.append("\n")
            elif tag == "li":
                indent = "  " * (len(list_stack) - 1)
                if list_stack and list_stack[-1] == "ol":
                    result.append(f"{indent}1. ")
                else:
                    result.append(f"{indent}- ")
            elif tag == "blockquote":
                result.append("\n\n> ")
            elif tag in BLOCK_TAGS:
                result.append("\n\n")

        elif node["type"] == "end":
            tag = node["tag"]

            if tag in HEADING_TAGS:
                result.append("\n")
            elif tag == "strong" or tag == "b":
                result.append("**")
            elif tag == "em" or tag == "i":
                result.append("*")
            elif tag == "code":
                result.append("`")
            elif tag == "pre":
                result.append("\n```\n\n")
            elif tag == "a":
                result.append(f"]({link_href})")
                link_href = None
            elif tag == "li":
                result.append("\n")
            elif tag == "ul" or tag == "ol":
                if list_stack:
                    list_stack.pop()
                result.append("\n")
            elif tag in BLOCK_TAGS:
                result.append("\n")

        elif node["type"] == "text":
            result.append(node["content"])

        elif node["type"] == "self_closing":
            tag = node["tag"]
            attrs = node.get("attrs", {})

            if tag == "br":
                result.append("\n")
            elif tag == "img":
                alt = attrs.get("alt", "image")
                src = attrs.get("src", "")
                result.append(f"![{alt}]({src})")
            elif tag == "hr":
                result.append("\n\n---\n\n")

    return "".join(result)


# Remove excessive whitespace
def clean_whitespace(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n +', '\n', text)
    text = text.strip()
    return text


# Truncate content if too long
def truncate_content(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_newline = truncated.rfind('\n\n')
    if last_newline > max_length * 0.8:
        truncated = truncated[:last_newline]
    return truncated + "\n\n[Content truncated...]"
