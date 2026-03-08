# INFRASTRUCTURE
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from mcp.types import TextContent

DEFAULT_MAX_CONTENT_LENGTH = 15000


# ORCHESTRATOR
async def scrape_url_workflow(url: str, max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH) -> list[TextContent]:
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.48,
                threshold_type="fixed",
                min_word_threshold=0
            )
        ),
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

    content = result.markdown.fit_markdown if result.markdown else ""

    if not content:
        return [TextContent(type="text", text=f"Error scraping {url}: No content extracted")]

    truncated = truncate_content(content, max_content_length)
    return [TextContent(type="text", text=f"# Content from: {url}\n\n{truncated}")]


# FUNCTIONS

# Truncate content at paragraph boundary if too long
def truncate_content(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_newline = truncated.rfind('\n\n')
    if last_newline > max_length * 0.8:
        truncated = truncated[:last_newline]
    return truncated + "\n\n[Content truncated...]"
