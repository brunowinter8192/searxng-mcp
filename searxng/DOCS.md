# SearXNG Web Search Tool

Privacy-focused web search via SearXNG metasearch engine.

## Project Structure

```
searxng/
├── search_web.py      # Main module
├── settings.yml       # SearXNG container config
└── DOCS.md           # This file
```

## search_web.py

**Purpose:** Fetches search results from local SearXNG instance and formats them for LLM consumption.

**Input:** Query string and category filter

**Output:** Dictionary with query metadata and list of results (title, url, content snippet)

### search_web_workflow()

Orchestrates the search process by fetching raw results from SearXNG API and transforming them into a clean output structure. Returns a dictionary containing the original query, category used, and up to 20 formatted results.

### fetch_search_results()

Sends HTTP GET request to local SearXNG instance with query and category parameters. Expects JSON response format. Raises exception on HTTP errors. Returns raw result list truncated to MAX_RESULTS (20).

### format_results()

Transforms raw SearXNG API response into standardized output format. Extracts title, url, and content fields from each result item. Returns dictionary with query metadata and cleaned results array.

## Configuration

SearXNG runs in Docker container on port 8080. Settings in `settings.yml` enable JSON API format. MAX_RESULTS constant limits output to 20 items to manage context window size.

## Error Handling

Fail-fast approach. HTTP errors propagate up via raise_for_status(). No silent failures.
