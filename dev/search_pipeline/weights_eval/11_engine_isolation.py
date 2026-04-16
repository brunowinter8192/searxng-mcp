#!/usr/bin/env python3

# INFRASTRUCTURE
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.search.search_web import _select_engines, _query_engines_concurrent
from src.search.browser import close_browser
from _isolation_report import save_reports  # noqa: E402 — local dev module

DELAY_BETWEEN_ENGINES = 5
DELAY_BETWEEN_QUERIES = 10
TOP_N = 10

ENGINES = [
    "google",
    "bing",
    "google scholar",
    "crossref",
]

TEST_QUERIES = [
    # Tech/Code (EN)
    "python asyncio best practices",
    "rust ownership borrow checker explained",
    "fastapi websocket reconnect handler",
    "docker compose health check restart policy",
    "git rebase vs merge workflow",
    "PostgreSQL query optimization composite index",
    "react server components vs client components",
    "nginx reverse proxy websocket configuration",
    # Science (EN)
    "transformer attention mechanism explained",
    "RLHF reinforcement learning human feedback",
    "vector database approximate nearest neighbor",
    "RAG retrieval augmented generation benchmark",
    "climate change carbon capture technology 2025",
    "epidemiology cohort study design methodology",
    # German (Alltag + Tech)
    "Bewerbung Lebenslauf Format Deutschland",
    "Mietvertrag Kündigungsfrist gesetzliche Regelung",
    "GmbH Gründung Kosten Schritte",
    "Krankenversicherung Vergleich gesetzlich privat",
    "Python Programmierung Anfänger Tutorial deutsch",
    "Datenschutz DSGVO Website Impressum",
    # Niche/Specific
    "crawl4ai stealth browser detection bypass",
    "pydoll chromium CDP automation",
    "tmux session management scripting",
    "trafilatura vs readability content extraction",
    "SPLADE sparse retrieval model implementation",
    # Broad/General
    "best programming language 2025",
    "how does DNS work",
    "quantum computing error correction",
    "kubernetes vs docker swarm comparison",
    "open source alternative to notion",
]


# ORCHESTRATOR

# Run all queries × engines in one event loop to avoid browser singleton / dead-loop bug
async def run_isolation_eval_async():
    engine_results: dict[str, dict[int, list[dict]]] = {e: {} for e in ENGINES}

    try:
        for qi, query in enumerate(TEST_QUERIES):
            print(f"[Query {qi + 1}/{len(TEST_QUERIES)}] {query}", file=sys.stderr)
            for ei, engine in enumerate(ENGINES):
                print(f"  [{ei + 1}/{len(ENGINES)}] {engine}", file=sys.stderr)
                single_engine = _select_engines(engine)
                try:
                    results = await _query_engines_concurrent(query, "en", 10, single_engine)
                    items = [
                        {"url": r.url, "title": r.title or "", "position": pos}
                        for pos, r in enumerate(results[:TOP_N], 1)
                        if r.url
                    ]
                    result_count = len(items)
                    if result_count == 0:
                        print(f"    WARNING: 0 results for {engine} — possible rate-limit or CAPTCHA", file=sys.stderr)
                    else:
                        print(f"    {result_count} results", file=sys.stderr)
                except Exception as e:
                    print(f"    SKIP: {e}", file=sys.stderr)
                    items = []
                engine_results[engine][qi] = items
                if ei < len(ENGINES) - 1:
                    await asyncio.sleep(DELAY_BETWEEN_ENGINES)
            if qi < len(TEST_QUERIES) - 1:
                await asyncio.sleep(DELAY_BETWEEN_QUERIES)
    finally:
        await close_browser()

    _check_engine_coverage(engine_results)
    summary = compute_per_engine_summary(engine_results)
    jaccard = compute_jaccard_matrix(engine_results)
    save_reports(engine_results, summary, jaccard, ENGINES, TEST_QUERIES, TOP_N)


def run_isolation_eval():
    asyncio.run(run_isolation_eval_async())


# FUNCTIONS

# Warn if any engine returned 0 results for more than 50% of queries (likely blocked)
def _check_engine_coverage(engine_results: dict) -> None:
    query_count = len(TEST_QUERIES)
    for engine in ENGINES:
        zero_count = sum(
            1 for qi in range(query_count)
            if len(engine_results[engine].get(qi, [])) == 0
        )
        if zero_count > query_count * 0.5:
            print(
                f"STOP: Engine '{engine}' returned 0 results for {zero_count}/{query_count} queries. "
                "Likely rate-limited or CAPTCHA-blocked. Investigate before using data.",
                file=sys.stderr,
            )


# Compute per-engine metrics: avg URLs/query, total unique, consensus rate, avg position
def compute_per_engine_summary(engine_results: dict) -> dict:
    summary = {}
    query_count = len(TEST_QUERIES)

    for engine in ENGINES:
        total_urls = 0
        consensus_count = 0
        unique_count = 0
        position_sum = 0
        position_total = 0

        for qi in range(query_count):
            items = engine_results[engine].get(qi, [])
            urls = [d["url"] for d in items]
            url_set = set(urls)
            total_urls += len(url_set)

            for item in items:
                position_sum += item["position"]
                position_total += 1

            other_urls: set = set()
            for other_engine in ENGINES:
                if other_engine != engine:
                    other_urls |= {d["url"] for d in engine_results[other_engine].get(qi, [])}

            for url in url_set:
                if url in other_urls:
                    consensus_count += 1
                else:
                    unique_count += 1

        summary[engine] = {
            "total_urls": total_urls,
            "avg_urls_per_query": total_urls / query_count if query_count > 0 else 0,
            "unique_urls": unique_count,
            "consensus_count": consensus_count,
            "consensus_rate": consensus_count / total_urls if total_urls > 0 else 0,
            "avg_position": position_sum / position_total if position_total > 0 else 0,
        }

    return summary


# Compute pairwise Jaccard similarity using global URL sets across all queries
def compute_jaccard_matrix(engine_results: dict) -> dict:
    global_sets: dict[str, set] = {}
    for engine in ENGINES:
        all_urls: set = set()
        for qi in range(len(TEST_QUERIES)):
            all_urls |= {d["url"] for d in engine_results[engine].get(qi, [])}
        global_sets[engine] = all_urls

    jaccard: dict[str, dict[str, float]] = {}
    for a in ENGINES:
        jaccard[a] = {}
        for b in ENGINES:
            set_a = global_sets[a]
            set_b = global_sets[b]
            union = set_a | set_b
            jaccard[a][b] = 0.0 if not union else len(set_a & set_b) / len(union)

    return jaccard


if __name__ == "__main__":
    run_isolation_eval()
