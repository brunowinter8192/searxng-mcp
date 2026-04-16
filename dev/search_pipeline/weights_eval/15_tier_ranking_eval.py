#!/usr/bin/env python3

# INFRASTRUCTURE
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

RAW_DATA_PATH = Path(__file__).parent / "11_reports" / "raw_data.json"
REPORTS_DIR = Path(__file__).parent / "15_reports" / "per_query"
TIER1_SIZE = 20

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
def run_tier_eval() -> None:
    raw = load_raw_data(RAW_DATA_PATH)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for qi, query in enumerate(TEST_QUERIES):
        print(f"[{qi + 1}/{len(TEST_QUERIES)}] {query}", file=sys.stderr)
        engine_data = extract_query_data(raw, qi)
        url_data = aggregate_url_data(engine_data)
        tier1, tier2, tier3 = compute_tiers(url_data)
        report = build_per_query_report(query, tier1, tier2, tier3)
        save_per_query_report(query, report)
    print(f"Done. Reports in {REPORTS_DIR}", file=sys.stderr)


# FUNCTIONS

# Load raw_data.json produced by 11_engine_isolation.py
def load_raw_data(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: {path} not found. Run 11_engine_isolation.py first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


# Extract per-engine result lists for a single query index (JSON key is string)
def extract_query_data(raw: dict, query_index: int) -> dict[str, list[dict]]:
    key = str(query_index)
    return {
        engine: query_map.get(key, [])
        for engine, query_map in raw.items()
    }


# Aggregate per-engine results into url_data with RRF scores
def aggregate_url_data(engine_data: dict[str, list[dict]]) -> dict[str, dict]:
    url_data: dict[str, dict] = {}
    for engine, items in engine_data.items():
        for item in items:
            url = item.get("url", "")
            if not url:
                continue
            if url not in url_data:
                url_data[url] = {"engine_positions": [], "title": ""}
            url_data[url]["engine_positions"].append((engine, item["position"]))
            if not url_data[url]["title"] and item.get("title"):
                url_data[url]["title"] = item["title"]
    for d in url_data.values():
        d["count"] = len(d["engine_positions"])
        d["rrf"] = sum(1.0 / pos for _, pos in d["engine_positions"])
    return url_data


# Split url_data into 3 tiers: top TIER1_SIZE by (count DESC, rrf DESC), then remainder by count
def compute_tiers(url_data: dict) -> tuple[list, list, list]:
    sorted_urls = sorted(
        url_data.items(),
        key=lambda x: (-x[1]["count"], -x[1]["rrf"]),
    )
    tier1 = sorted_urls[:TIER1_SIZE]
    remainder = sorted_urls[TIER1_SIZE:]
    tier2 = [(u, d) for u, d in remainder if d["count"] >= 2]
    tier3 = [(u, d) for u, d in remainder if d["count"] == 1]
    return tier1, tier2, tier3


# Build per-query markdown report with 3 tier tables
def build_per_query_report(query: str, tier1: list, tier2: list, tier3: list) -> str:
    lines = [
        f'# Query: "{query}"',
        "",
        "## Tier 1 (Top 20)",
        "",
        "| # | URL | Engines | Count | RRF-Score | Title |",
        "|---|-----|---------|-------|-----------|-------|",
    ]
    for rank, (url, d) in enumerate(tier1, 1):
        engines_str = ", ".join(e for e, _ in d["engine_positions"])
        title = d["title"].replace("|", "\\|")[:80]
        lines.append(f"| {rank} | {url} | {engines_str} | {d['count']} | {d['rrf']:.3f} | {title} |")

    lines += [
        "",
        "## Tier 2 (≥2 Engines, not in Tier 1)",
        "",
        "| # | URL | Engines | Count | RRF-Score | Title |",
        "|---|-----|---------|-------|-----------|-------|",
    ]
    for rank, (url, d) in enumerate(tier2, 1):
        engines_str = ", ".join(e for e, _ in d["engine_positions"])
        title = d["title"].replace("|", "\\|")[:80]
        lines.append(f"| {rank} | {url} | {engines_str} | {d['count']} | {d['rrf']:.3f} | {title} |")

    lines += [
        "",
        "## Tier 3 (1 Engine)",
        "",
        "| # | URL | Engine | Position | Title |",
        "|---|-----|--------|----------|-------|",
    ]
    for rank, (url, d) in enumerate(tier3, 1):
        engine, pos = d["engine_positions"][0]
        title = d["title"].replace("|", "\\|")[:80]
        lines.append(f"| {rank} | {url} | {engine} | {pos} | {title} |")

    return "\n".join(lines)


# Save per-query report to 15_reports/per_query/<sanitized_query>.md
def save_per_query_report(query: str, report: str) -> None:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", query)[:80].strip("_")
    path = REPORTS_DIR / f"{safe_name}.md"
    path.write_text(report, encoding="utf-8")
    print(f"  Saved: {path.name}", file=sys.stderr)


if __name__ == "__main__":
    run_tier_eval()
