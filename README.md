# SearXNG

Web search, URL scraping, and site crawling for Claude Code — powered by a pydoll-based stealth browser engine.

## Features

- **Multi-Engine Web Search** — 8 search engines (Google, DuckDuckGo, Mojeek, Lobsters, Google Scholar, CrossRef, OpenAlex, Stack Exchange) with overlap-ranked, slot-allocated 20-URL output and disk-cached pagination via `search_more`
- **JavaScript-Aware Scraping** — full page rendering via Crawl4AI with stealth fallback, cookie consent removal, and garbage detection
- **Site Exploration** — sitemap and BFS-based URL discovery for crawl planning
- **Autonomous Research Agent** — Haiku-powered agent that searches broadly, scrapes aggressively, and routes domain-specific results to specialized plugins (arXiv→RAG, GitHub→GitHub, Reddit→Reddit)

## Quick Start

```
/plugin marketplace add brunowinter8192/claude-plugins
/plugin install searxng
# Restart session — mcp-start.sh bootstraps the Python venv automatically
```

## Prerequisites

- Python 3.10+
- Playwright Chromium (auto-installed by `mcp-start.sh`)

`mcp-start.sh` bootstraps the Python venv and sets up Playwright Chromium on first run. No Docker required.

## Setup

**1. Clone + venv**

```bash
git clone https://github.com/brunowinter8192/SearXNG.git
cd SearXNG
python -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium
```

## Usage

### MCP Tools

| Tool | What it does | When to use |
|------|-------------|-------------|
| `search_web` | Search the web with language and time-range filters, returns top 20 URLs ranked across 8 engines (overlap + slot-allocation) | Any web search |
| `search_more` | Get the next batch of URLs from the cached search (sha256-keyed disk cache, 1h TTL) | Pagination beyond the first 20 |
| `scrape_url` | Fetch a page as filtered markdown with JS rendering | Read full content of a search result |
| `scrape_url_raw` | Fetch a page as raw markdown, saved to file | Prepare content for RAG indexing |
| `explore_site` | Discover all URLs on a site via sitemap/BFS | Plan a crawl before committing to it |
| `download_pdf` | Download a PDF file to local disk | When a result URL ends in `.pdf` |

### Skills & Commands

- `/searxng:crawl-site` — Crawl an entire website to markdown files. 6-phase pipeline: explore → assess → crawl → cleanup → index. Optionally spawns a RAG indexing worker (requires the RAG plugin with `/rag:web-md-index`).

### Agents

- **web-research** — Autonomous web research specialist. Searches with 5+ query variations, paginates through results, scrapes 10-15+ URLs per batch, and routes plugin-domain results (arXiv, GitHub, Reddit) to their respective MCP plugins. Dispatched automatically when deep web research is needed.

## Workflows

**Search → Scrape**

1. `search_web` with broad query → top 20 URLs ranked across 8 engines (overlap-counted across general engines, plus reserved slots for academic and Q&A engines), with `search_more` for the next batch from the disk cache
2. Pick relevant URLs → `scrape_url` for full page content as markdown
3. Plugin-domain URLs (arXiv, GitHub, Reddit) get routed to specialized plugins instead

**Crawl → RAG**

1. `/searxng:crawl-site https://docs.example.com` — explore site structure
2. Filter URL patterns (exclude noise like login pages, language variants)
3. Crawl selected URLs → markdown files with garbage detection
4. Optional: LLM cleanup (web-md-cleanup agent) → chunk + index into RAG

## Troubleshooting

<details>
<summary>Scraping returns empty content</summary>

Some sites block headless browsers. The scraper tries normal mode first, then stealth mode with an undetected adapter. If both fail, the site likely has aggressive bot detection — try `scrape_url_raw` as an alternative.

</details>

<details>
<summary>Playwright/Chromium not installed</summary>

`mcp-start.sh` installs Chromium automatically. For manual installation:

```bash
./venv/bin/playwright install chromium
```

</details>

## License

MIT
