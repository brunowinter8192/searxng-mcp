#!/usr/bin/env python3

# INFRASTRUCTURE
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.search.search_web import fetch_search_results

REPORTS_DIR = Path(__file__).parent / "14_reports"
DELAY_BETWEEN_ENGINES = 3
TOP_N_PER_ENGINE = 10
TIER1_SIZE = 20

ENGINES = [
    "google", "bing", "google scholar", "crossref",
]


# ORCHESTRATOR
def run_tiered_ranking(query: str) -> None:
    per_engine = collect_results(query)
    url_data = aggregate_url_data(per_engine)
    tier1, tier2, tier3 = compute_tiers(url_data)
    report = build_report(query, tier1, tier2, tier3)
    save_report(query, report)


# FUNCTIONS

# Fetch results from all engines, collect per-engine position-keyed items
def collect_results(query: str) -> dict[str, list[dict]]:
    per_engine: dict[str, list[dict]] = {}
    for i, engine in enumerate(ENGINES):
        print(f"[{i + 1}/{len(ENGINES)}] {engine}", file=sys.stderr)
        try:
            results = fetch_search_results(query, "", "en", None, engine, 1)
        except Exception as e:
            print(f"  SKIP: {e}", file=sys.stderr)
            results = []
        items = []
        for pos, result in enumerate(results[:TOP_N_PER_ENGINE], 1):
            url = result.get("url", "")
            if url:
                items.append({"url": url, "title": result.get("title", "") or "", "position": pos})
        per_engine[engine] = items
        if i < len(ENGINES) - 1:
            time.sleep(DELAY_BETWEEN_ENGINES)
    return per_engine


# Aggregate per-engine results into url_data with RRF scores
def aggregate_url_data(per_engine: dict[str, list[dict]]) -> dict[str, dict]:
    url_data: dict[str, dict] = {}
    for engine, items in per_engine.items():
        for item in items:
            url = item["url"]
            if url not in url_data:
                url_data[url] = {"engine_positions": [], "title": ""}
            url_data[url]["engine_positions"].append((engine, item["position"]))
            if not url_data[url]["title"] and item["title"]:
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


# Build markdown report with 3 tier tables and RRF scores
def build_report(query: str, tier1: list, tier2: list, tier3: list) -> str:
    lines = [
        f'# Query: "{query}"',
        "",
        f"**Tier 1:** {len(tier1)} results | "
        f"**Tier 2:** {len(tier2)} more (≥2 engines) | "
        f"**Tier 3:** {len(tier3)} unique (1 engine)",
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


# Save report to 14_reports/<sanitized_query>.md
def save_report(query: str, report: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", query)[:80].strip("_")
    path = REPORTS_DIR / f"{safe_name}.md"
    path.write_text(report, encoding="utf-8")
    print(f"Report saved: {path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: 14_tiered_ranking.py <query>", file=sys.stderr)
        sys.exit(1)
    run_tiered_ranking(sys.argv[1])
