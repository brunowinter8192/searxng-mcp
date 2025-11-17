# INFRASTRUCTURE
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext

from scraper.html_parser import parse_html
from scraper.content_filter import filter_content
from scraper.markdown_formatter import to_markdown

DEFAULT_CONCURRENCY = 5
TIMEOUT_MS = 30000


# ORCHESTRATOR
async def scrape_urls_workflow(urls: list[str], concurrency: int = DEFAULT_CONCURRENCY) -> list[dict]:
    browser = await init_browser()
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [scrape_single_url(url, browser, semaphore) for url in urls]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    await cleanup_browser(browser)
    extracted_results = extract_all_content(raw_results)
    return format_results(urls, extracted_results)


# FUNCTIONS

# Initialize headless Chromium browser instance
async def init_browser() -> Browser:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    return browser


# Scrape single URL with semaphore-controlled concurrency
async def scrape_single_url(url: str, browser: Browser, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, timeout=TIMEOUT_MS, wait_until="domcontentloaded")
        content = await page.content()
        await context.close()
        return content


# Release browser resources
async def cleanup_browser(browser: Browser) -> None:
    await browser.close()


# Extract content from all raw HTML results
def extract_all_content(raw_results: list) -> list:
    extracted = []
    for result in raw_results:
        if isinstance(result, Exception):
            extracted.append(result)
        else:
            extracted.append(extract_single_content(result))
    return extracted


# Parse and convert single HTML to markdown
def extract_single_content(html: str) -> str:
    parsed = parse_html(html)
    filtered = filter_content(parsed)
    markdown = to_markdown(filtered)
    return markdown


# Transform raw results into structured output
def format_results(urls: list[str], results: list) -> list[dict]:
    formatted = []
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            formatted.append({
                "url": url,
                "content": "",
                "success": False,
                "error": str(result)
            })
        else:
            formatted.append({
                "url": url,
                "content": result,
                "success": True,
                "error": None
            })
    return formatted
