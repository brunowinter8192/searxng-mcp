# INFRASTRUCTURE
import asyncio
import nest_asyncio
from typing import Annotated, Literal
from fastmcp import FastMCP
from pydantic import Field

nest_asyncio.apply()

from src.searxng.search_web import search_web_workflow
from src.scraper.scrape_url import scrape_url_workflow

mcp = FastMCP("SearXNG")


# TOOLS

@mcp.tool
def search_web(
    query: Annotated[str, Field(description="Search query (e.g., 'fastapi async tutorial', 'python memory profiling')")],
    category: Annotated[
        Literal["general", "news", "it", "science"],
        Field(description="Search category: general (web/books), news (articles), it (code/packages/Q&A), science (publications)")
    ] = "general"
) -> dict:
    """Use when user needs to search the web for information. Good for finding documentation, tutorials, code examples, news articles, or scientific papers."""
    return search_web_workflow(query, category)


@mcp.tool
def scrape_url(
    url: Annotated[str, Field(description="Single URL to scrape (e.g., 'https://example.com', 'https://docs.python.org/3/library/asyncio.html')")],
    max_content_length: Annotated[int, Field(description="Maximum content length in characters (default: 15000, increase for longer articles)")] = 15000
) -> dict:
    """Use when user needs to fetch full page content from a URL. Handles JavaScript-rendered pages with networkidle wait strategy. Good for extracting documentation, articles, or any web content after getting URLs from search_web."""
    return asyncio.run(scrape_url_workflow(url, max_content_length))


if __name__ == "__main__":
    mcp.run()
