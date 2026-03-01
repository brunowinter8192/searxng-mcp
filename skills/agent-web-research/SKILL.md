---
name: agent-web-research
description: SearXNG MCP tool reference for web research agents
---

# SearXNG MCP Tools — Reference

## Tools

| Tool | Purpose |
|------|---------|
| search_web | Search the web via SearXNG. Returns up to 20 results with title, URL, snippet |
| scrape_url | Fetch full page content as clean markdown. Handles JavaScript-rendered pages |

## Parameter Reference

### search_web

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | required | Search query (e.g., "machine learning python tutorial") |
| category | Literal | "general" | Content category: general, news, it, science |

**Output:** Plain text numbered list with title, URL, and 200-char snippet per result. Max 20 results.

### scrape_url

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | required | Single URL to fetch and convert to markdown |
| max_content_length | int | 15000 | Character limit for returned content. Truncates at paragraph boundary |

**Output:** Markdown content with `# Content from: <url>` header. Includes headings, paragraphs, links, images, code blocks, tables.

## Search Categories

| Category | Best for |
|----------|----------|
| general | Broad web search (default) |
| news | Current events, recent articles |
| it | Technical topics, programming, tools |
| science | Academic, research, scientific papers |

## Typical Workflow

```
1. search_web("topic keywords", category="general") → Get URLs
2. Review results: identify top 3-5 by relevance
3. scrape_url(url, max_content_length=15000) → Read each page
4. Synthesize findings across scraped pages
```

## Known Limitations

- **SearXNG instance required** — must be running on localhost:8080
- **Max 20 results** per search query — use precise keywords
- **No pagination** — single query returns all results at once
- **Scraper optimized for content sites** — articles, docs, wikis work best
- **Complex SPAs** may not render fully (JavaScript-heavy single-page apps)
- **Login-protected pages** will return login forms, not content
- **Truncation** at max_content_length preserves paragraph boundaries
- **Images** included as markdown, but small/avatar images are filtered out
