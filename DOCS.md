# SearXNG MCP Server

Privacy-focused web search via local SearXNG metasearch engine instance.

## Project Structure

```
searxng/
├── server.py              # MCP server orchestrator
├── search_web.py          # SearXNG API wrapper module
├── docker-compose.yml     # SearXNG container config
├── searxng/
│   └── settings.yml       # SearXNG configuration (JSON format enabled)
├── README.md              # Quick start guide
├── DOCS.md                # Module documentation
├── CLAUDE.md              # Engineering standards
└── .gitignore             # Excludes debug/, logs/
```

## server.py

**Purpose:** MCP server orchestrator defining tool interfaces.

### search_web()

Exposes web search functionality to LLM clients. Accepts query string and category parameter. Delegates execution to search_web_workflow. Returns structured results with title, url, and content snippet for each result.

## search_web.py

**Purpose:** Wrapper for SearXNG JSON API.
**Input:** Query string and category name.
**Output:** Dictionary containing query, category, and list of result objects.

### search_web_workflow()

Main orchestrator function. Coordinates fetching raw results from SearXNG API and formatting them into clean output structure. Called directly by server.py tool definition.

### fetch_search_results()

Performs HTTP GET request to SearXNG search endpoint. Constructs query parameters including format=json and category filter. Raises exception on HTTP errors. Extracts results array from response and limits to MAX_RESULTS (20).

### format_results()

Transforms raw SearXNG response into standardized output. Iterates over raw results and extracts title, url, and content fields. Returns dictionary with query metadata and cleaned results list.

## docker-compose.yml

**Purpose:** Container configuration for SearXNG instance.

Defines SearXNG service with port mapping 8080:8080. Mounts local searxng/ directory for custom configuration. Sets base URL and restart policy.

## searxng/settings.yml

**Purpose:** SearXNG instance configuration.

Enables JSON output format required for API access. Disables rate limiting for local use. Sets English as default language. Configures 3 second request timeout.
