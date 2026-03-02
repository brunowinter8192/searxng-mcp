# INFRASTRUCTURE
from playwright.async_api import async_playwright, Browser
from mcp.types import TextContent

from src.scraper.html_parser import parse_html
from src.scraper.content_filter import filter_content
from src.scraper.markdown_converter import to_markdown
from src.scraper.routing import resolve_profile

TIMEOUT_MS = 30000
DEFAULT_MAX_CONTENT_LENGTH = 100000


# ORCHESTRATOR
async def scrape_url_workflow(url: str, max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH) -> list[TextContent]:
    profile = resolve_profile(url)
    browser = await init_browser()
    raw_html = await fetch_url_content(url, browser, profile)
    await cleanup_browser(browser)

    if isinstance(raw_html, Exception):
        error_msg = f"Error scraping {url}: {str(raw_html)}"
        return [TextContent(type="text", text=error_msg)]

    extracted_content = extract_single_content(url, raw_html, max_content_length, profile)
    return [TextContent(type="text", text=extracted_content)]


# Parse and convert single HTML to markdown with header
def extract_single_content(url: str, html: str, max_content_length: int, profile: dict) -> str:
    parsed = parse_html(html)
    filtered = filter_content(parsed, profile)
    cleanup_tags = profile.get("markdown_cleanup", [])
    markdown = to_markdown(filtered, max_content_length, cleanup_tags)
    truncated = truncate_content(markdown, max_content_length)
    return f"# Content from: {url}\n\n{truncated}"


# FUNCTIONS

# Initialize headless Chromium browser instance with stealth mode
async def init_browser() -> Browser:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"]
    )
    return browser


# Fetch HTML content from URL using profile-based config
async def fetch_url_content(url: str, browser: Browser, profile: dict) -> str | Exception:
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        wait_until = profile.get("wait_until", "domcontentloaded")
        await page.goto(url, timeout=TIMEOUT_MS, wait_until=wait_until)

        content_selectors = profile.get("content_selectors", ["main", "article", "[class*='content']", "h1"])
        selector_timeout = profile.get("selector_timeout", 5000)
        try:
            await page.wait_for_selector(", ".join(content_selectors), state="visible", timeout=selector_timeout)
        except Exception:
            pass

        content = await page.content()
        await context.close()
        return content
    except Exception as e:
        return e


# Release browser resources
async def cleanup_browser(browser: Browser) -> None:
    await browser.close()


# Truncate content if too long
def truncate_content(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_newline = truncated.rfind('\n\n')
    if last_newline > max_length * 0.8:
        truncated = truncated[:last_newline]
    return truncated + "\n\n[Content truncated...]"
