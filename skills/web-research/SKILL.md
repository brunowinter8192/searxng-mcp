---
name: web-research
description: SearXNG web research — CLI tool reference (search_web, search_batch, search_more, scrape_url, scrape_url_raw, explore_site, download_pdf)
---

# SearXNG Web Research — Skill

Web research CLI plugin with 8 active search engines (Google, DuckDuckGo, Mojeek, Lobsters, Google Scholar, CrossRef, OpenAlex, Stack Exchange), Crawl4AI-based scraping, and site exploration. Each `search_web` invocation is a fresh CLI process — fire calls in parallel for maximum throughput. Use `search_batch` when running multiple queries in one process to amortize Chrome startup cost.

## CLI Invocation

All tools are invoked via the `searxng-cli` wrapper (installed at `~/.local/bin/searxng-cli`, in PATH):

```
searxng-cli <cmd> [args]
```

### Output Handling (CRITICAL)

`search_web` / `search_batch` / `search_more` / `explore_site` produce **signal output** — every result is data you have to evaluate as a whole. Run them in the **foreground**, no `&`, no `> /tmp/...` redirect. The full result lands in the tool result and is immediately available in context.

```bash
# RIGHT — direct foreground call
searxng-cli search_batch "query 1" "query 2" "query 3"
```

Up to 4 queries × 20 URLs = 80 results, ~20 KB / ~5K tokens. Comfortably fits in one tool result. Wall time is bounded by engine roundtrips + preview fetches (~5–10s steady-state, longer on first call due to pydoll cold-engine warmup).

**Do NOT redirect to /tmp + chunk-read.** That's the pattern for noisy outputs (build, test, dev scripts) where you grep for one signal. Search output IS the signal — chunking it just spends N tool calls to reconstruct what one direct call would have given you in a single result.

`scrape_url_raw` is the exception: it writes to a `.md` file by design (for RAG indexing). The other scrape/explore commands print to stdout for direct context use.

### Quick Reference — All 7 Tools

```bash
# Search (8 engines: Google, DDG, Mojeek, Lobsters, Scholar, CrossRef, OpenAlex, StackExchange)
searxng-cli search_web "machine learning retrieval"
searxng-cli search_web "SPLADE sparse retrieval" --engines "google scholar,openalex,crossref"
searxng-cli search_web "RAG pipeline python" --language de --time-range month

# Search multiple queries in one warm-Chrome session
searxng-cli search_batch "SPLADE retrieval" "sparse vector search" "learned sparse retrieval"

# Paginate beyond first 20 results (within 1h cache TTL)
searxng-cli search_more "machine learning retrieval"
searxng-cli search_more "machine learning retrieval" --count 20

# Scrape
searxng-cli scrape_url "https://example.com/article"
searxng-cli scrape_url "https://docs.example.com/api" --max-content-length 30000

# Scrape to file (RAG indexing)
searxng-cli scrape_url_raw "https://example.com/article" /tmp/rag_output/

# Explore site structure
searxng-cli explore_site "https://docs.example.com" --max-pages 50
searxng-cli explore_site "https://example.com" --url-pattern ".*\/blog\/.*"

# Download PDF
searxng-cli download_pdf "https://arxiv.org/pdf/2310.01526" --output-dir /tmp/papers/
```

On error (import failure, missing dependency, engine timeout): the CLI prints to stderr and exits non-zero.

## Tools

| Tool | Purpose |
|------|---------|
| search_web | Search across 8 engines in parallel. Returns 20 slot-allocated results with title, URL, snippet |
| search_batch | Search multiple queries in one warm-Chrome session. Same output per query as search_web |
| search_more | Fetch next batch of URLs from cached search results (results 21+, 1h TTL) |
| scrape_url | Fetch page content as filtered markdown (PruningContentFilter). For in-conversation reading |
| scrape_url_raw | Fetch page content as raw markdown and save as .md file. For RAG indexing |
| explore_site | Discover URLs via sitemap + BFS prefetch. Returns structured URL list |
| download_pdf | Download PDF file from URL to local disk |

## Parameter Reference

### search_web

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | required | Search query (2–5 keywords) |
| --language | str | en | ISO language code (e.g. "de") |
| --time-range | day/month/year | None | Restrict results by recency |
| --engines | str | None | Comma-separated engine list (e.g. "google,duckduckgo" or "google scholar,openalex,crossref") |
| --general | flag | off | Restrict output to GENERAL class slots only |
| --academic | flag | off | Restrict output to ACADEMIC class slots only |
| --qa | flag | off | Restrict output to QA class slots only |

**Output:** Numbered list 1–20 — title, URL, snippet. Hard slot-allocated from the full ranked pool (~60–80 candidates): 12 GENERAL / 6 ACADEMIC / 2 QA. Underflow = fewer than 20 results when a class has insufficient supply. No overflow fill. Snippet source per URL is the highest-scoring candidate by `clean_len × lexical_density` across all engine snippets, og:description, and meta description (MIN_FLOOR=40 chars; best-of-worst fallback when all candidates are short). OpenAlex results with >50 citations append `(Cited N×)` to the snippet. CrossRef synthesizes `Author, I. (year), Container` when no abstract is available.

**Engine set (8 active):**

| Class | Engines | Output slots |
|-------|---------|-------------|
| GENERAL | Google, DuckDuckGo, Mojeek | 12 |
| ACADEMIC | Google Scholar, OpenAlex, CrossRef | 6 |
| QA | Stack Exchange, Lobsters | 2 |

Use `--engines` to restrict to specific engines (e.g. `--engines "google scholar,openalex,crossref"` for academic-only searches).

#### Class filter flags

`--general`, `--academic`, `--qa` control which slot classes are allocated. Can be combined:

| Flags | Allocation |
|-------|-----------|
| (none) | Hard 12 / 6 / 2 — all classes |
| `--academic` | 20 slots to ACADEMIC only |
| `--general` | 20 slots to GENERAL only |
| `--qa` | 20 slots to QA only |
| `--general --academic` | 18 slots (12 GENERAL + 6 ACADEMIC), QA=0 |
| `--general --qa` | 14 slots (12 GENERAL + 2 QA), ACADEMIC=0 |
| `--academic --qa` | 8 slots (6 ACADEMIC + 2 QA), GENERAL=0 |

Class filter is part of the cache key. `search_more` must use the same flags as the original `search_web` call to get a cache hit.

### search_batch

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| queries | str+ | required | One or more search queries (positional — each query as a separate quoted argument) |
| --language | str | en | ISO language code (e.g. "de") |
| --time-range | day/month/year | None | Restrict results by recency |
| --engines | str | None | Comma-separated engine list |
| --general | flag | off | Restrict output to GENERAL class slots only |
| --academic | flag | off | Restrict output to ACADEMIC class slots only |
| --qa | flag | off | Restrict output to QA class slots only |

**Output:** Results for each query in the same format as `search_web`, separated by `---`.

**Use case:** Run 3–5 query variations on the same topic in a single process. Chrome starts once (~5s), then each query runs in ~1s — amortized startup cost vs. one ~5s cold-start per separate `search_web` invocation. Prefer `search_batch` over parallel `search_web` calls when queries are topically related and sequential execution is acceptable.

### search_more

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | required | Must match a prior search_web query exactly |
| --count | int | 10 | Additional URLs to return |
| --language | str | en | Must match the original search_web call |
| --time-range | day/month/year | None | Must match the original search_web call |
| --engines | str | None | Must match the original search_web call |
| --general | flag | off | Must match the original search_web call (part of cache key) |
| --academic | flag | off | Must match the original search_web call (part of cache key) |
| --qa | flag | off | Must match the original search_web call (part of cache key) |

**Output:** Next batch of URLs from the cached ranked pool (results 21+), numbered from 21 onward.

**Cache:** `search_web` writes the full ranked pool (~60–80 URLs) to disk after every call (`~/.cache/searxng/<key>.json`, 1h TTL). `search_more` slices from index 20.

| Cache state | Behavior |
|-------------|----------|
| Hit + fresh (≤1h) | Returns `urls[20:20+count]`, numbered from 21 |
| Hit + fresh but pool exhausted | Exits with `# search_more: no further URLs in cached pool` |
| Miss or expired (>1h) | Re-runs search_web, returns first `count` results |

**Key rule:** `--language`, `--engines`, `--time-range`, and all class-filter flags are part of the cache key — they must match the original `search_web` call exactly. Any mismatch triggers a fresh search.

### scrape_url

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | required | URL to fetch and convert to markdown |
| --max-content-length | int | 15000 | Character limit for returned content |

**Output:** Filtered markdown with `# Content from: <url>` header.

**Plugin routing:** arxiv.org, github.com, reddit.com URLs are automatically rejected with a routing message — use the dedicated plugins instead.

### scrape_url_raw

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | required | URL to scrape and save as markdown file |
| output_dir | str | required | Directory to save the .md file (created if not exists) |

**Output:** Confirmation with file path and char count. File saved with `<!-- source: URL -->` header.

**Plugin routing:** Same blocking as scrape_url — routed domains return a message, no file is saved.

### explore_site

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | required | Root URL to explore |
| --max-pages | int | 200 | Max pages to discover |
| --url-pattern | str | None | Regex filter for discovered URLs |

**Output:** Structured URL list discovered via sitemap → BFS cascade. MAX_DEPTH=10, TIMEOUT=120s.

### download_pdf

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | required | URL of the PDF to download |
| --output-dir | str | /tmp | Directory to save the downloaded PDF |

**Output:** Confirmation with file path and file size.

## Search Strategy

### Parallel queries

Fire multiple `searxng-cli search_web` calls in parallel, each with a query variation. Each call already fans out to 8 engines internally — 4 parallel `search_web` calls = 32 engine calls total. Less aggressive parallelization is needed than a single-engine pipeline. 2–4 parallel calls is a good default for deep-research tasks.

```bash
# Example: 4 parallel calls for a deep research task
searxng-cli search_web "SPLADE sparse retrieval"
searxng-cli search_web "sparse vector retrieval benchmark"
searxng-cli search_web "SPLADE vs BM25 performance"
searxng-cli search_web "learned sparse retrieval neural"
```

**Query tips:**
- Keep queries short and keyword-focused (2–5 words)
- Try different angles: "X tutorial", "X implementation", "X benchmark", "X vs Y"
- "X best practices 2025" for recent content

### Warm-Chrome batch (search_batch)

For 3–5 variations on the same topic in one process, prefer `search_batch` — Chrome boots once and stays warm across all queries:

```bash
searxng-cli search_batch "SPLADE sparse retrieval" "sparse vector search" "learned sparse retrieval" "SPLADE vs BM25"
```

Use parallel `search_web` invocations when topics are independent and you want results in parallel processes. Use `search_batch` when queries are topically related and sequential execution is acceptable.

### Academic / paper topics

Academic engines (Google Scholar, OpenAlex, CrossRef) run in every `search_web` call in the ACADEMIC slots. For topics where you want to target academics-only:

```bash
searxng-cli search_web "SPLADE retrieval NDCG" --engines "google scholar,openalex,crossref"
```

### Language

For German-language research, add `--language de` to all queries. This filters results to German-language content.

### Workflow

1. **Search broadly:** Fire 2–4 parallel `search_web` queries with variations (or `search_batch` for topically-related queries)
2. **Paginate if needed:** Call `search_more` with the same query + flags to fetch results 21+ from the cached pool (within 1h)
3. **Filter results:** Categorize as scrape targets vs. plugin-routed (see Plugin Routing below)
4. **Scrape aggressively:** Call `searxng-cli scrape_url` on all relevant non-plugin URLs
5. **Report everything:** Return all findings using the Report Format below

For multi-topic tasks: before moving to the next topic, verify ≥5 unique URLs scraped for the current topic and ≥2 HIGH quality sources. Fire 2–3 additional topic-specific queries if below minimum.

For single-topic tasks: target 10+ scraped URLs. Fire additional queries if below 10 after initial batch.

**Cookie wall detection:** If scrape output contains only consent/GDPR text, mark as `[cookie wall]` — do NOT rate as HIGH quality. Use the search snippet as fallback, labeled "Source: search snippet (scrape blocked by cookie wall)".

**PDF URLs:** If a result URL ends in `.pdf`, call `download_pdf` instead of `scrape_url`. Report as `[PDF downloaded: /tmp/filename.pdf]`.

## Plugin Routing (CRITICAL)

**Do NOT scrape these domains — report them for plugin-based access:**

| Domain | Action |
|--------|--------|
| arxiv.org | Report: "Use RAG plugin (mcp__rag__search_hybrid) or /rag:pdf-convert" |
| github.com | Report: "Use GitHub Research plugin (github__get_file_content)" |
| reddit.com | Report: "Use Reddit plugin (reddit__search_posts)" |
| youtube.com | Skip entirely. Video content cannot be scraped. |

`scrape_url` and `scrape_url_raw` enforce this routing at the CLI level — they will return a routing message and exit without scraping. No need to pre-filter manually; scrape calls on routed domains are safe (they fail gracefully).

## Report Format

```
## Scraped Content

### 1. <Title>
**URL:** <url>
**Domain:** <domain>
**Content Quality:** [high/medium/low]
**Key Content:**
[2-5 sentences: What does this page actually contain? Concrete takeaways, code examples, benchmark numbers, methodologies.]

### 2. <Title>
...

[ALL scraped URLs, not limited to 10]

## Plugin-Routed URLs

These URLs require dedicated plugins for proper access:

### arxiv.org (Use RAG plugin)
- <url> — <title>

### github.com (Use GitHub Research plugin)
- <url> — <title>

### reddit.com (Use Reddit plugin)
- <url> — <title>

## Search Metadata
**Queries Used:** query1, query2, query3, ...
**Total Results Reviewed:** N
**URLs Scraped:** N
**Plugin-Routed:** N
**Skipped (garbage/thin):** N
```

## Content Assessment

**HIGH quality:** Tutorials with code, benchmarks with numbers, API docs with examples, research papers with methodology
**MEDIUM quality:** Blog posts with some substance, overviews with useful links, discussion with concrete answers
**LOW quality:** Thin wrapper around other content, mostly links, surface-level overview without depth

## Scraping Tips

- **Default `--max-content-length` is 15000** — sufficient for most articles/docs. Increase for long documentation pages.
- **JavaScript-rendered content** is supported — Playwright renders the page before extraction.
- **Content-focused sites** (articles, docs, wikis) produce the best results. The scraper is optimized for semantic HTML.
- **Truncation** preserves paragraph boundaries — content is cut at the nearest double newline.
- **Images** are included as markdown references (small/avatar images are filtered out).
- **Scrape before summarizing:** Never summarize from search snippets alone. If a page has content, scrape it.
- **Quantity over perfection:** 20 scraped URLs with quick assessments > 5 carefully curated summaries.

## Known Limitations

- **20 results per search_web call** — slot-allocated from ~60–80 ranked candidates. Use `search_more` for next batch (1h cache TTL)
- **Scraper optimized for content sites** — articles, docs, wikis work best
- **scrape_url uses PruningContentFilter** — may damage code blocks. Use `scrape_url_raw` for full fidelity
- **Login-protected pages** will return login forms, not content
- **PDF URLs (.pdf)** — use `download_pdf` to save the file locally. Do NOT use `scrape_url` on PDFs.

## When to Stop

Stop when ALL of:
- Exhausted 4+ query variations
- Called `search_more` to check cached pool for additional URLs
- Scraped all non-plugin URLs from top results
- Additional queries return mostly duplicates
