# INFRASTRUCTURE
import argparse
import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, AsyncUrlSeeder, BrowserConfig, CrawlerRunConfig, CacheMode, SeedingConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, URLPatternFilter, ContentTypeFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_dispatcher import SemaphoreDispatcher

PERMALINK_PATTERN = re.compile(r'\[¶\]\([^)]+\)')
TRAILING_SLASH = re.compile(r'/$')
DEFAULT_CONCURRENCY = 10


# ORCHESTRATOR
async def crawl_site_workflow(url: str, output_dir: str, depth: int, max_pages: int,
                              exclude_patterns: str = None, include_patterns: str = None,
                              no_prefetch: bool = False, strategy: str = "auto",
                              url_file: str = None):
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    domain = urlparse(url).netloc

    if url_file:
        print(f"Reading URLs from {url_file}")
        urls = read_url_file(url_file)
        print(f"Loaded {len(urls)} URLs")
        results = await crawl_urls(urls)
    elif strategy == "bfs":
        print(f"Strategy: BFS full rendering (depth={depth}, max_pages={max_pages})")
        results = await crawl_bfs(url, domain, depth, max_pages, exclude_patterns, include_patterns)
    elif strategy == "sitemap":
        print(f"Strategy: Sitemap discovery")
        urls = await discover_urls_sitemap(domain, include_patterns)
        if not urls:
            print("No sitemap found. Aborting.")
            return
        print(f"Sitemap: {len(urls)} URLs")
        results = await crawl_urls(urls)
    elif strategy == "prefetch":
        print(f"Strategy: Prefetch BFS (depth={depth}, max_pages={max_pages})")
        urls = await discover_urls(url, domain, depth, max_pages, exclude_patterns, include_patterns)
        print(f"Prefetch: {len(urls)} URLs")
        results = await crawl_urls(urls)
    elif strategy == "auto":
        print("Auto-detection: trying sitemap...")
        urls = await discover_urls_sitemap(domain, include_patterns)
        if urls:
            print(f"Sitemap: {len(urls)} URLs")
            results = await crawl_urls(urls)
        else:
            print("No sitemap. Trying prefetch BFS...")
            urls = await discover_urls(url, domain, depth, max_pages, exclude_patterns, include_patterns)
            if len(urls) > 1:
                print(f"Prefetch: {len(urls)} URLs")
                results = await crawl_urls(urls)
            else:
                print(f"SPA detected (prefetch found {len(urls)} URLs). Falling back to BFS full rendering.")
                results = await crawl_bfs(url, domain, depth, max_pages, exclude_patterns, include_patterns)
    else:
        print(f"Crawling {url} via BFS with full rendering (depth={depth}, max_pages={max_pages})")
        results = await crawl_bfs(url, domain, depth, max_pages, exclude_patterns, include_patterns)

    print(f"Crawled {len(results)} pages")
    unique = deduplicate(results)
    saved = save_markdown(unique, url, target)

    print(f"\nDone: {saved} files saved to {target}")


# FUNCTIONS

# Discover URLs via sitemap (fastest strategy, no rendering needed)
async def discover_urls_sitemap(domain: str, include_patterns: str = None) -> list[str]:
    config = SeedingConfig(source="sitemap")
    if include_patterns:
        config.pattern = include_patterns.split(",")[0]
    try:
        async with AsyncUrlSeeder() as seeder:
            results = await seeder.urls(f"https://{domain}", config=config)
            return [r["url"] for r in results if "url" in r]
    except Exception:
        return []


# Read URL list from text file (one URL per line)
def read_url_file(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# Phase 1: Fast URL discovery via prefetch BFS
async def discover_urls(url: str, domain: str, depth: int, max_pages: int,
                        exclude_patterns: str = None, include_patterns: str = None) -> list[str]:
    # Resolve redirects to use final domain for DomainFilter
    try:
        import requests as _req
        resp = _req.head(url, allow_redirects=True, timeout=10)
        final_domain = urlparse(resp.url).netloc
        if final_domain != domain:
            domain = final_domain
            url = resp.url
    except Exception:
        pass

    filters = [
        DomainFilter(allowed_domains=[domain]),
        ContentTypeFilter(allowed_types=["text/html"]),
    ]
    if exclude_patterns:
        filters.append(URLPatternFilter(patterns=exclude_patterns.split(","), reverse=True))
    if include_patterns:
        filters.append(URLPatternFilter(patterns=include_patterns.split(","), reverse=False))
    filter_chain = FilterChain(filters)

    strategy = BFSDeepCrawlStrategy(
        max_depth=depth,
        include_external=False,
        filter_chain=filter_chain,
        max_pages=max_pages
    )

    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        prefetch=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun(url=url, config=run_config)

    if not isinstance(results, list):
        results = [results]

    seen = set()
    urls = []
    for r in results:
        normalized = TRAILING_SLASH.sub('', r.url) if hasattr(r, 'url') and r.url else None
        if normalized and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)

    return urls


# BFS crawl with full rendering (for JS-heavy/SPA sites)
async def crawl_bfs(url: str, domain: str, depth: int, max_pages: int,
                    exclude_patterns: str = None, include_patterns: str = None) -> list:
    filters = [
        DomainFilter(allowed_domains=[domain]),
        ContentTypeFilter(allowed_types=["text/html"]),
    ]
    if exclude_patterns:
        filters.append(URLPatternFilter(patterns=exclude_patterns.split(","), reverse=True))
    if include_patterns:
        filters.append(URLPatternFilter(patterns=include_patterns.split(","), reverse=False))
    filter_chain = FilterChain(filters)

    strategy = BFSDeepCrawlStrategy(
        max_depth=depth,
        include_external=False,
        filter_chain=filter_chain,
        max_pages=max_pages
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


# Phase 2: Parallel crawl of discovered URLs
async def crawl_urls(urls: list[str]) -> list:
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        markdown_generator=DefaultMarkdownGenerator(),
    )

    dispatcher = SemaphoreDispatcher(max_session_permit=DEFAULT_CONCURRENCY)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(urls=urls, config=run_config, dispatcher=dispatcher)

    return results if isinstance(results, list) else list(results)


# Remove duplicate URLs (trailing slash normalization)
def deduplicate(results: list) -> list:
    seen = set()
    unique = []
    for r in results:
        normalized = TRAILING_SLASH.sub('', r.url) if hasattr(r, 'url') else None
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(r)
    print(f"Unique after dedup: {len(unique)}")
    return unique


# Save crawled pages as markdown files
def save_markdown(results: list, seed_url: str, output_dir: Path) -> int:
    saved = 0
    for r in results:
        url = TRAILING_SLASH.sub('', r.url) if hasattr(r, 'url') else None
        raw_md = r.markdown.raw_markdown if r.markdown else ""
        if not url or not raw_md:
            continue

        clean_md = PERMALINK_PATTERN.sub('', raw_md)
        clean_md = re.sub(r'\n{3,}', '\n\n', clean_md).strip()

        filename = url_to_filename(url, seed_url)
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"<!-- source: {url} -->\n\n{clean_md}")

        saved += 1
        print(f"  [{saved}] {filename} ({len(clean_md)} chars)")

    return saved


# Domain to filename prefix mapping
DOMAIN_PREFIX = {
    "docs.searxng.org": "searxng",
    "docs.crawl4ai.com": "crawl4ai",
    "playwright.dev": "playwright",
    "support.torproject.org": "tor",
    "www.cookieyes.com": "cookieyes",
    "developer.onetrust.com": "onetrust",
    "www.sitemaps.org": "sitemaps",
    "trafilatura.readthedocs.io": "trafilatura",
    "platform.claude.com": "anthropic",
    "www.cookiebot.com": "cookiebot",
}


# Convert URL to safe filename with domain prefix
def url_to_filename(url: str, seed_url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc
    prefix = DOMAIN_PREFIX.get(domain, domain.replace(".", "_"))

    path = parsed.path.strip("/")
    if not path:
        path = "index"

    path = path.replace(".html", "").replace(".htm", "")
    path = path.replace("/", "__")

    return f"{prefix}__{path}.md"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl a website and save as Markdown")
    parser.add_argument("--url", required=True, help="Seed URL to crawl")
    parser.add_argument("--output-dir", required=True, help="Directory to save markdown files")
    parser.add_argument("--depth", type=int, default=3, help="Max crawl depth")
    parser.add_argument("--max-pages", type=int, default=100, help="Max pages to crawl")
    parser.add_argument("--exclude-patterns", type=str, default=None,
                        help="Comma-separated URL patterns to exclude (e.g. '/genindex*,/search*')")
    parser.add_argument("--include-patterns", type=str, default=None,
                        help="Comma-separated URL patterns to include (e.g. '/docs/*,/api/*')")
    parser.add_argument("--no-prefetch", action="store_true",
                        help="Use serial BFS with full rendering (for JS-heavy/SPA sites where prefetch finds no links)")
    parser.add_argument("--strategy", choices=["auto", "sitemap", "prefetch", "bfs"], default="auto",
                        help="Force discovery strategy: auto (cascade: sitemap→prefetch→bfs), sitemap, prefetch, bfs")
    parser.add_argument("--url-file", type=str, default=None,
                        help="Path to text file with URLs (one per line) — skips discovery entirely")
    args = parser.parse_args()

    asyncio.run(crawl_site_workflow(args.url, args.output_dir, args.depth, args.max_pages,
                                    args.exclude_patterns, args.include_patterns, args.no_prefetch,
                                    args.strategy, args.url_file))
