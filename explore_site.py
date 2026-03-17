# INFRASTRUCTURE
import argparse
import asyncio
import time
from urllib.parse import urlparse

import requests
from crawl_site import discover_urls, discover_urls_sitemap

DEFAULT_MAX_PAGES = 200
SITEMAP_MIN_THRESHOLD = 5


# ORCHESTRATOR
async def explore_site_workflow(url: str, strategy: str, max_pages: int, output: str,
                                depth: int, include_patterns: str, exclude_patterns: str,
                                append: bool = False):
    domain = urlparse(url).netloc
    effective_max = max_pages

    if output is None:
        output = f"/tmp/explore_{domain}_urls.txt"

    # Resolve redirects to get final URL and domain
    resolved_url, resolved_domain = resolve_redirect(url)
    if resolved_domain != domain:
        print(f"Redirect detected: {url} → {resolved_url} (domain: {domain} → {resolved_domain})")
        url = resolved_url
        domain = resolved_domain

    print(f"Exploring {url} (strategy: {strategy})")

    start = time.time()
    seed_path = urlparse(url).path

    if strategy == "sitemap":
        urls = await discover_urls_sitemap(domain, include_patterns)
        urls = filter_sitemap_by_seed_path(urls, seed_path)
        strategy_used = "sitemap"
        duration = time.time() - start
        print(f"Sitemap: {len(urls)} URLs found in {duration:.1f}s")
    elif strategy == "prefetch":
        urls = await discover_urls(url, domain, depth, effective_max, exclude_patterns, include_patterns)
        strategy_used = "prefetch"
        duration = time.time() - start
        print(f"Prefetch: {len(urls)} URLs found in {duration:.1f}s")
    else:
        sitemap_urls = await discover_urls_sitemap(domain, include_patterns)
        sitemap_urls = filter_sitemap_by_seed_path(sitemap_urls, seed_path)

        if len(sitemap_urls) >= SITEMAP_MIN_THRESHOLD:
            urls = sitemap_urls
            strategy_used = "sitemap"
            duration = time.time() - start
            print(f"Sitemap: {len(urls)} URLs found in {duration:.1f}s")
        else:
            if sitemap_urls:
                print(f"Sitemap too shallow ({len(sitemap_urls)} URLs). Trying prefetch BFS...")
            else:
                print("No sitemap found. Trying prefetch BFS...")
            prefetch_urls = await discover_urls(url, domain, depth, effective_max, exclude_patterns, include_patterns)
            if len(prefetch_urls) > len(sitemap_urls):
                urls = prefetch_urls
                strategy_used = "prefetch"
            else:
                urls = sitemap_urls
                strategy_used = "sitemap (shallow, prefetch found fewer)"
            duration = time.time() - start
            print(f"{strategy_used}: {len(urls)} URLs found in {duration:.1f}s")

    # Deduplicate against existing URLs if appending
    if append:
        existing = load_existing_urls(output)
        new_urls = [u for u in urls if u not in existing]
        print(f"New URLs: {len(new_urls)} (filtered {len(urls) - len(new_urls)} duplicates)")
        urls = new_urls

    print_url_samples(urls)
    save_url_list(urls, output, append=append)
    print(f"Saved {len(urls)} URLs to {output}")

    if len(urls) >= effective_max:
        print(f"\n⚠ Hit max_pages limit ({effective_max}). Run again with --max-pages {effective_max * 2} --append to discover more.")


# FUNCTIONS

# Resolve HTTP redirects to get final URL and domain
def resolve_redirect(url: str) -> tuple[str, str]:
    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        final_url = resp.url
        final_domain = urlparse(final_url).netloc
        return final_url, final_domain
    except Exception:
        return url, urlparse(url).netloc


# Filter sitemap URLs to match seed URL path prefix
def filter_sitemap_by_seed_path(urls: list[str], seed_path: str) -> list[str]:
    if not seed_path or seed_path == "/":
        return urls
    return [u for u in urls if seed_path in urlparse(u).path]


# Print URL samples for noise pattern identification
def print_url_samples(urls: list[str], max_samples: int = 15) -> None:
    if not urls:
        return
    total = len(urls)
    indices = set()
    for i in range(min(5, total)):
        indices.add(i)
    for i in range(max(0, total - 5), total):
        indices.add(i)
    if total > 10:
        step = total // 5
        for i in range(5):
            indices.add(min(i * step, total - 1))
    sorted_indices = sorted(indices)[:max_samples]
    print(f"\n=== URL Samples ({len(sorted_indices)} of {total}) ===")
    for i in sorted_indices:
        print(f"[{i+1:>4}] {urls[i]}")
    print()


# Load existing URLs from file (for dedup on append)
def load_existing_urls(path: str) -> set[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


# Save URL list to text file (one URL per line)
def save_url_list(urls: list[str], output_path: str, append: bool = False) -> None:
    mode = "a" if append else "w"
    with open(output_path, mode, encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover all URLs of a website and save to a file")
    parser.add_argument("--url", required=True, help="Seed URL to explore")
    parser.add_argument("--strategy", choices=["auto", "sitemap", "prefetch"], default="auto",
                        help="Discovery strategy: auto (sitemap→prefetch), sitemap, prefetch")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                        help=f"Max pages to discover (default: {DEFAULT_MAX_PAGES})")
    parser.add_argument("--append", action="store_true",
                        help="Append to output file instead of overwrite (for continuation runs)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file path (default: /tmp/explore_<domain>_urls.txt)")
    parser.add_argument("--depth", type=int, default=10,
                        help="Max crawl depth for prefetch BFS")
    parser.add_argument("--include-patterns", type=str, default=None,
                        help="Comma-separated URL patterns to include (e.g. '/docs/*,/api/*')")
    parser.add_argument("--exclude-patterns", type=str, default=None,
                        help="Comma-separated URL patterns to exclude (e.g. '/genindex*,/search*')")
    args = parser.parse_args()

    asyncio.run(explore_site_workflow(args.url, args.strategy, args.max_pages, args.output,
                                     args.depth, args.include_patterns, args.exclude_patterns,
                                     args.append))
