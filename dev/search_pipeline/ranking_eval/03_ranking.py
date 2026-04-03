#!/usr/bin/env python3

# INFRASTRUCTURE
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

REPORTS_DIR = Path(__file__).parent.parent / "engines_eval" / "01_reports"
COMPARE_DIR = Path(__file__).parent / "03_reports"


# ORCHESTRATOR
def compare_reports():
    report_a, report_b = resolve_report_paths()
    queries_a = parse_report(report_a)
    queries_b = parse_report(report_b)
    comparison = build_comparison(queries_a, queries_b, report_a.name, report_b.name)
    save_comparison(comparison)


# FUNCTIONS

# Resolve two report paths from CLI args or latest two
def resolve_report_paths() -> tuple[Path, Path]:
    if len(sys.argv) >= 3:
        a, b = Path(sys.argv[1]), Path(sys.argv[2])
        if not a.exists():
            raise FileNotFoundError(f"Report not found: {a}")
        if not b.exists():
            raise FileNotFoundError(f"Report not found: {b}")
        return a, b

    reports = sorted(REPORTS_DIR.glob("search_report_*.md"))
    if len(reports) < 2:
        raise FileNotFoundError(f"Need at least 2 reports in {REPORTS_DIR}, found {len(reports)}")
    return reports[-2], reports[-1]


# Parse report into dict of query -> results
def parse_report(report_path: Path) -> dict:
    content = report_path.read_text()
    queries = {}

    # Extract config hash
    hash_match = re.search(r'Config hash: (\w+)', content)
    config_hash = hash_match.group(1) if hash_match else "unknown"

    # Split by query sections
    query_blocks = re.split(r'^## Query: "(.+?)"', content, flags=re.MULTILINE)

    for i in range(1, len(query_blocks), 2):
        query_text = query_blocks[i]
        block = query_blocks[i + 1] if i + 1 < len(query_blocks) else ""

        # Extract profile
        profile_match = re.search(r'Profile: (\w+)', block)
        profile = profile_match.group(1) if profile_match else "general"

        urls = []
        for line in block.strip().split("\n"):
            if not line.startswith("|") or line.startswith("|--") or line.startswith("| #"):
                continue
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]
            if len(cells) >= 6:
                try:
                    score = float(cells[1])
                except ValueError:
                    continue
                url = cells[5]
                domain = urlparse(url).netloc if url.startswith("http") else cells[3]
                engines = cells[2]
                if url.startswith("http"):
                    urls.append({"url": url, "score": score, "domain": domain, "engines": engines})

        key = f"{query_text}|{profile}"
        queries[key] = {
            "query": query_text,
            "profile": profile,
            "results": urls,
            "config_hash": config_hash,
        }

    return queries


# Build comparison report between two parsed reports
def build_comparison(queries_a: dict, queries_b: dict, name_a: str, name_b: str) -> str:
    lines = []
    lines.append("# Search Config Comparison")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Report A: {name_a}")
    lines.append(f"Report B: {name_b}")
    lines.append("")

    # Find common queries
    keys_a = set(queries_a.keys())
    keys_b = set(queries_b.keys())
    common = keys_a & keys_b
    only_a = keys_a - keys_b
    only_b = keys_b - keys_a

    lines.append("## Overview")
    lines.append(f"- Common queries: {len(common)}")
    lines.append(f"- Only in A: {len(only_a)}")
    lines.append(f"- Only in B: {len(only_b)}")
    lines.append("")

    # Summary table
    lines.append("## Per-Query Comparison")
    lines.append("")
    lines.append("| Query | Profile | Results A | Results B | Avg Score A | Avg Score B | Domain Overlap | Winner |")
    lines.append("|-------|---------|-----------|-----------|-------------|-------------|----------------|--------|")

    for key in sorted(common):
        qa = queries_a[key]
        qb = queries_b[key]
        ra = qa["results"]
        rb = qb["results"]

        avg_a = sum(r["score"] for r in ra) / len(ra) if ra else 0
        avg_b = sum(r["score"] for r in rb) / len(rb) if rb else 0

        domains_a = set(r["domain"] for r in ra)
        domains_b = set(r["domain"] for r in rb)
        overlap = len(domains_a & domains_b)
        total = len(domains_a | domains_b)

        winner = "A" if avg_a > avg_b else "B" if avg_b > avg_a else "="
        query_short = qa["query"][:50]

        lines.append(f"| {query_short} | {qa['profile']} | {len(ra)} | {len(rb)} | {avg_a:.1f} | {avg_b:.1f} | {overlap}/{total} | {winner} |")

    lines.append("")

    # Detail sections for queries with significant differences
    lines.append("## Details (queries with different results)")
    lines.append("")

    for key in sorted(common):
        qa = queries_a[key]
        qb = queries_b[key]
        urls_a = set(r["url"] for r in qa["results"])
        urls_b = set(r["url"] for r in qb["results"])

        new_in_b = urls_b - urls_a
        lost_in_b = urls_a - urls_b

        if not new_in_b and not lost_in_b:
            continue

        lines.append(f'### "{qa["query"]}" ({qa["profile"]})')
        lines.append("")

        if new_in_b:
            lines.append("**New in B:**")
            for url in sorted(new_in_b):
                domain = urlparse(url).netloc
                lines.append(f"- {domain}: {url}")
            lines.append("")

        if lost_in_b:
            lines.append("**Lost from A:**")
            for url in sorted(lost_in_b):
                domain = urlparse(url).netloc
                lines.append(f"- {domain}: {url}")
            lines.append("")

    return "\n".join(lines)


# Save comparison report
def save_comparison(report: str) -> None:
    COMPARE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = COMPARE_DIR / f"comparison_{timestamp}.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Comparison saved: {report_path}")


if __name__ == "__main__":
    compare_reports()
