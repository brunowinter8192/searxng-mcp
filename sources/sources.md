# Sources

**searxng** — Single RAG collection with all indexed sources. Search with `mcp__rag__search_hybrid(collection="searxng")`.

| Source | Type | Pipeline Steps | Status |
|--------|------|---------------|--------|
| searxng | RAG Collection | search01, search02, search03, scrape01, scrape02, scrape03, explore01 | Indexed |
| docs.searxng.org | Web Domain | search01, search02, search03, agent01 | Indexed |
| docs.crawl4ai.com | Web Domain | scrape01, scrape02, scrape03, explore01 | Indexed |
| docs.anthropic.com | Web Domain | agent01 | Indexed |
| playwright.dev | Web Domain | scrape01 | Indexed |
| trafilatura.readthedocs.io | Web Domain | scrape02 | Indexed |
| cookieyes.com | Web Domain | scrape02, scrape03 | Indexed |
| cookiebot.com | Web Domain | scrape03 | Indexed |
| developer.onetrust.com | Web Domain | scrape03 | Indexed |
| sitemaps.org | Web Domain | explore01 | Indexed |
| support.torproject.org | Web Domain | search02 | Indexed |
| github.com | Web Domain | search01, search02, search03, scrape01, scrape02, scrape03, explore01 | Not indexed |
| api.search.brave.com | Web Domain | search01 | Not indexed |
| huggingface.co | Web Domain | agent02 | Not indexed |
| info.arxiv.org | Web Domain | agent02 | Not indexed |
| lobste.rs | Web Domain | search05 | Indexed |
| developers.openalex.org | Web Domain | search05 | Indexed |
| api.stackexchange.com | Web Domain | search05 | Indexed |
| www.crossref.org | Web Domain | search05 | Indexed |
| www.mojeek.com | Web Domain | search05 | Indexed |
| blog.mojeek.com | Web Domain | search05 | Indexed |
| duckduckgo.com (help-pages) | Web Domain | search05 | Indexed |
| scholar.google.com | Web Domain | search05 | Indexed |
| support.google.com (websearch operators) | Web Domain | search05 | Indexed |
| blog.cloudflare.com (markdown-for-agents) | Web Domain | scrape04 | Indexed |
| seirdy.one (search-engines-with-own-indexes) | Web Domain | search05 | Referenced |
| morphllm.com (ai-web-scraping benchmarks) | Web Domain | scrape00 | Referenced |
| chuniversiteit.nl (extraction-comparison) | Web Domain | scrape02 | Referenced |
| vercel.com/docs (independent markdown-edge) | Web Domain | scrape04 | Referenced |

| GitHub Issue #5286 | github.com | Issue | search02_routing | Referenced |
| GitHub Issue #5922 | github.com | Issue | search02_routing | Referenced |
| GitHub PR #5644 | github.com | PR | search01_engines | Referenced |

| daijro/camoufox | Repo | stealth01 | Referenced |
| saifyxpro/HeadlessX | Repo | stealth01 | Referenced |
| nichochar/stealth-browser-mcp | Repo | stealth01 | Referenced |
| Kaliiiiiiiiii-Vinyzu/patchright-python | Repo | stealth01 | Referenced |
| debug-it/brave-captcha-solver | Repo | stealth01 | Referenced |
| nullpt-rs/blog (reversing-botid.mdx) | Web | stealth01 | Referenced |
| FriendlyCaptcha/friendly-challenge | Repo | stealth01 | Referenced |
| BotBrowser CHANGELOG | Repo | stealth01 | Referenced |
| autoscrape-labs/pydoll | Repo | stealth00, stealth01, stealth03 | Referenced |
| opsdisk/yagooglesearch | Repo | stealth05 | Referenced |
| karust/openserp | Repo | stealth05, stealth07 | Referenced |
| 2captcha/2captcha-go | Repo | stealth07 | Referenced |
| github.com/StractOrg/stract | Repo | search05 | Referenced |
| github.com/MarginaliaSearch/MarginaliaSearch | Repo | search05 | Referenced |
| github.com/MarginaliaSearch/docs.marginalia.nu | Repo | search05 | Referenced |
| github.com/cyanheads/hn-mcp-server | Repo | search05 | Referenced |
| github.com/voska/hn-cli | Repo | search05 | Referenced |
| github.com/lucjon/Py-StackExchange | Repo | search05 | Referenced |
| github.com/searxng/searxng | Repo | search05 | Referenced |
| github.com/searxng/searxng (searx/engines/duckduckgo.py) | Repo | search05 | Referenced |
| github.com/searxng/searxng (searx/engines/mojeek.py) | Repo | search05 | Referenced |
| github.com/searxng/searxng (searx/engines/lobsters.py) | Repo | search05 | Referenced |
| github.com/hffmnnj/kagi-skill | Repo | search05 | Referenced |
| github.com/encode/httpx | Repo | search06 | Referenced |
| github.com/lxml/lxml | Repo | search06 | Referenced |
| Cormack et al. 2009 — Reciprocal Rank Fusion outperforms Condorcet | Paper | g82 | Indexed (RAG: searxng_reference) |
| Benham 2017 — Risk-Reward Trade-offs in Rank Fusion | Paper | g82 | Indexed (RAG: searxng_reference) |
| MMMORRF 2025 — Multimodal Multilingual RRF | Paper | g82 | Indexed (RAG: searxng_reference) |
| Mourao — Learning to Rank / Rank Combination Slides | Slides | g82 | Indexed (RAG: searxng_reference) |
| Zheng — A Comparative Study of Search Result Diversification Methods | Paper | g82 | Indexed (RAG: searxng_reference) |
| He 2011 — Result Diversification Based on Query-Specific Cluster | Paper | g82 | Indexed (RAG: searxng_reference) |
| Minack — Current Approaches to Search Result Diversification | Paper | g82 | Indexed (RAG: searxng_reference) |
| Santos 2010 — Exploiting Query Reformulations for Diversification (xQuAD) | Paper | g82 | Indexed (RAG: searxng_reference) |
| Zhu/Guo 2014 — Learning for Search Result Diversification | Paper | g82 | Indexed (RAG: searxng_reference) |
| Hu 2015 — Search Result Diversification Based on Query Facets | Paper | g82 | Indexed (RAG: searxng_reference) |
| Mordo 2025 — Diversification in Competitive Search | Paper | g82 | Indexed (RAG: searxng_reference) |
| Rollings — TREC 2022 Multi-Faceted Question Fusion | Paper | g82 | Indexed (RAG: searxng_reference) |
| UWaterloo TREC 21 — Logistic Regression + RRF | Paper | g82 | Indexed (RAG: searxng_reference) |
| Kafi — Weighted Reciprocal Rank Fusion RAG | Paper | g82 | Indexed (RAG: searxng_reference) |
| Santosh 2024 — arxiv 2404.00590 (rank-fusion-related) | Paper | g82 | Indexed (RAG: searxng_reference) |
| Ruizhang ICDE 2023 — Personalized Diversification for Neural Re-ranking | Paper | g82 | Referenced (recommendation system, less relevant) |
| api.semanticscholar.org / semanticscholar.org/product/api | Web | 10y | Verified (browser-engine landed; API tier 429s without business-email key) |
| Manning/Raghavan/Schütze — Introduction to Information Retrieval (2008) | Book | g82 | Referenced (canonical IR textbook, not yet indexed) |
| Croft/Metzler/Strohman — Search Engines: IR in Practice (2009) | Book | g82 | Referenced (web-search architecture textbook, not yet indexed) |
| Baeza-Yates/Ribeiro-Neto — Modern Information Retrieval (2nd Ed 2011) | Book | g82 | Referenced (broad IR textbook, not yet indexed) |
| Liu — Learning to Rank for Information Retrieval (2011) | Book | g82 | Referenced (LtR monograph, not yet indexed) |

Consult via RAG search before making assumptions. Pipeline step references match `decisions/` files.
