# INFRASTRUCTURE
from collections import defaultdict
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, ContentTypeFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

MAX_DEPTH = 10
DEFAULT_MAX_PAGES = 200


# ORCHESTRATOR
async def explore_site_workflow(url: str, max_pages: int = DEFAULT_MAX_PAGES) -> dict:
    domain = urlparse(url).netloc
    results = await crawl_for_discovery(url, domain, max_pages)
    return build_site_map(url, domain, results)


# FUNCTIONS

# BFS crawl to discover site structure
async def crawl_for_discovery(url: str, domain: str, max_pages: int) -> list:
    filter_chain = FilterChain([
        DomainFilter(allowed_domains=[domain]),
        ContentTypeFilter(allowed_types=["text/html"]),
    ])

    strategy = BFSDeepCrawlStrategy(
        max_depth=MAX_DEPTH,
        include_external=False,
        filter_chain=filter_chain,
        max_pages=max_pages,
    )

    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        markdown_generator=DefaultMarkdownGenerator(),
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun(url=url, config=run_config)

    if not isinstance(results, list):
        results = [results]

    return results


# Aggregate crawl results into site map with depth distribution
def build_site_map(seed_url: str, domain: str, results: list) -> dict:
    seen = set()
    urls = []
    depth_stats = defaultdict(lambda: {"count": 0, "chars": 0})

    for r in results:
        url = r.url.rstrip('/') if hasattr(r, 'url') and r.url else None
        if not url or url in seen:
            continue
        seen.add(url)

        chars = len(r.markdown.raw_markdown) if r.markdown and r.markdown.raw_markdown else 0
        depth = r.metadata.get("depth", -1) if r.metadata else -1

        urls.append({"url": url, "depth": depth, "chars": chars})
        depth_stats[depth]["count"] += 1
        depth_stats[depth]["chars"] += chars

    total_chars = sum(u["chars"] for u in urls)
    depth_distribution = {str(k): v for k, v in sorted(depth_stats.items())}

    return {
        "seed_url": seed_url,
        "domain": domain,
        "total_pages": len(urls),
        "total_chars": total_chars,
        "depth_distribution": depth_distribution,
        "urls": sorted(urls, key=lambda u: (u["depth"], u["url"])),
    }
