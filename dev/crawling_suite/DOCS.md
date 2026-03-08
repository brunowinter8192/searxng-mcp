# Crawling Suite

URL discovery and traversal testing for Crawl4AI's BFS deep crawl strategy.

## 01_run_crawl.py

**Purpose:** Crawls a website using BFS strategy with domain filtering. Reports URL discovery metrics: total fetched, unique URLs, duplicates removed, content presence, character counts.
**Output:** `01_reports/<label>_<timestamp>.json`

`--all` crawls all domains from `domains.txt` in parallel (asyncio.gather, no semaphore — each domain gets its own browser context with independent BFS state).

```bash
python dev/crawling_suite/01_run_crawl.py https://docs.searxng.org --depth 2 --max-pages 50
python dev/crawling_suite/01_run_crawl.py --all
```

## domains.txt

Seed URLs for batch crawling. Format: `label|url|depth|max_pages`

Each domain represents a different HTML generator and content type for broad test coverage.

## Report Format

JSON with summary (total fetched, unique URLs, duplicates, content/empty counts, total chars) and URL list with per-URL content status and character counts. Reports are consumed by the scraping suite's `05_compare_content_source.py`.
