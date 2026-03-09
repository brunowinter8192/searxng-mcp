# INFRASTRUCTURE
import asyncio
import nest_asyncio
from typing import Literal
from fastmcp import FastMCP
from mcp.types import TextContent

nest_asyncio.apply()

from src.searxng.search_web import search_web_workflow
from src.scraper.scrape_url import scrape_url_workflow
from src.scraper.explore_site import explore_site_workflow

mcp = FastMCP("SearXNG")


# TOOLS

@mcp.tool
def search_web(
    query: str,
    category: Literal["general", "news", "it", "science"] = "general"
) -> list[TextContent]:
    """Search web."""
    return search_web_workflow(query, category)


@mcp.tool
def scrape_url(
    url: str,
    max_content_length: int = 15000
) -> list[TextContent]:
    """Scrape URL."""
    return asyncio.run(scrape_url_workflow(url, max_content_length))


@mcp.tool
def explore_site(
    url: str,
    max_pages: int = 200
) -> dict:
    """Use when user wants to understand a website's structure before crawling.
    Shows URL tree with depth levels, page counts, and estimated total size.
    Good for deciding crawl scope (depth, filters, max_pages) before running crawl_site."""
    return asyncio.run(explore_site_workflow(url, max_pages))


if __name__ == "__main__":
    mcp.run()
