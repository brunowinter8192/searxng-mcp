#!/usr/bin/env python3

# INFRASTRUCTURE
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

REPORTS_DIR = Path(__file__).parent / "20_reports"
SEARXNG_URL = "http://localhost:8080/search"

ENGINES = [
    "google",
    "bing",
    "brave",
    "mojeek",
    "startpage",
    "google scholar",
    "semantic scholar",
    "crossref",
]

PHASES = [
    ("Phase 1 (10s interval)", 10, 6),
    ("Phase 2 (5s interval)", 5, 6),
    ("Phase 3 (2s interval)", 2, 6),
    ("Phase 4 (1s interval)", 1, 6),
]

COOLDOWN_BETWEEN_ENGINES = 60

VARIED_QUERIES = [
    "python asyncio best practices",
    "machine learning evaluation metrics",
    "climate change carbon capture",
    "rust ownership borrow checker",
    "docker kubernetes container orchestration",
    "transformer architecture attention",
    "postgresql query optimization index",
    "quantum computing error correction",
    "react hooks state management",
    "epidemiology study design cohort",
    "fastapi async database pool",
    "neural network backpropagation",
    "distributed systems consensus raft",
    "computer vision object detection",
    "natural language processing bert",
    "graph neural network applications",
    "reinforcement learning policy gradient",
    "cryptography elliptic curve",
    "microservices API gateway pattern",
    "database sharding horizontal scaling",
    "time series forecasting LSTM",
    "generative adversarial network training",
    "kubernetes helm chart deployment",
    "elasticsearch full text search",
    "apache kafka stream processing",
]


# ORCHESTRATOR
def run_suspension_threshold():
    engine_results: dict = {}

    for engine_idx, engine in enumerate(ENGINES):
        print(f"\n[ENGINE {engine_idx+1}/{len(ENGINES)}] Testing: {engine}", file=sys.stderr)
        rows = test_engine(engine)
        engine_results[engine] = rows

        if engine_idx < len(ENGINES) - 1:
            print(f"  Cooldown {COOLDOWN_BETWEEN_ENGINES}s before next engine...", file=sys.stderr)
            time.sleep(COOLDOWN_BETWEEN_ENGINES)

    report = build_report(engine_results)
    save_report(report)


# FUNCTIONS

# Run all phases for one engine and return list of per-request result rows
def test_engine(engine: str) -> list:
    rows = []
    query_idx = 0
    query_pool = VARIED_QUERIES.copy()

    for phase_name, interval, count in PHASES:
        print(f"  {phase_name}...", file=sys.stderr)
        phase_suspended = False

        for _ in range(count):
            query = query_pool[query_idx % len(query_pool)]
            query_idx += 1

            row = single_query(engine, query)
            rows.append({**row, "phase": phase_name, "interval": interval})

            status_str = f"HTTP={row['status_code']} results={row['result_count']} {row.get('suspension', '')}"
            print(f"    [{row['req_num']}] {status_str}", file=sys.stderr)

            if row.get("suspended"):
                phase_suspended = True

            time.sleep(interval)

        if phase_suspended:
            print(f"  SUSPENSION detected in {phase_name}, continuing to next phase...", file=sys.stderr)

    return rows


# Execute one SearXNG query for a single engine and return result dict
def single_query(engine: str, query: str) -> dict:
    req_num = getattr(single_query, "_counter", 0) + 1
    single_query._counter = req_num  # type: ignore[attr-defined]

    start = time.time()
    try:
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "language": "en",
            "pageno": 1,
            "engines": engine,
        }
        response = requests.get(SEARXNG_URL, params=params, timeout=20)
        elapsed = time.time() - start
        status_code = response.status_code

        if status_code != 200:
            return {
                "req_num": req_num,
                "engine": engine,
                "query": query,
                "status_code": status_code,
                "result_count": 0,
                "response_time": round(elapsed, 2),
                "suspended": True,
                "suspension": f"HTTP {status_code}",
            }

        data = response.json()
        results = data.get("results", [])
        unresponsive = data.get("unresponsive_engines", [])

        engine_suspended = any(
            (isinstance(e, list) and e[0] == engine) or
            (isinstance(e, dict) and e.get("name") == engine)
            for e in unresponsive
        )

        suspension_note = ""
        if engine_suspended:
            suspension_note = "ENGINE_SUSPENDED"
        elif len(results) == 0:
            suspension_note = "ZERO_RESULTS"

        return {
            "req_num": req_num,
            "engine": engine,
            "query": query,
            "status_code": status_code,
            "result_count": len(results),
            "response_time": round(elapsed, 2),
            "suspended": engine_suspended,
            "suspension": suspension_note,
            "unresponsive": [str(e) for e in unresponsive],
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "req_num": req_num,
            "engine": engine,
            "query": query,
            "status_code": 0,
            "result_count": 0,
            "response_time": round(elapsed, 2),
            "suspended": True,
            "suspension": f"ERROR: {str(e)[:80]}",
        }


# Determine the first phase where suspension was detected for one engine
def find_threshold(rows: list) -> str:
    for row in rows:
        if row.get("suspended") or row.get("suspension") in ("ENGINE_SUSPENDED",):
            return f"{row['phase']} (interval={row['interval']}s, req#{row['req_num']})"
    return "No suspension detected"


# Compute success rate for a list of rows
def success_rate(rows: list) -> str:
    if not rows:
        return "N/A"
    ok = sum(1 for r in rows if r["status_code"] == 200 and r["result_count"] > 0 and not r.get("suspended"))
    return f"{ok}/{len(rows)} ({ok*100//len(rows)}%)"


# Build markdown report from per-engine result rows
def build_report(engine_results: dict) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Suspension Threshold Report",
        f"Date: {timestamp}",
        f"Engines tested: {len(engine_results)}",
        "",
        "## Threshold Summary",
        "",
        "| Engine | Threshold | Success Rate | Notes |",
        "|--------|-----------|-------------|-------|",
    ]

    for engine, rows in engine_results.items():
        threshold = find_threshold(rows)
        rate = success_rate(rows)
        suspension_types = list({r["suspension"] for r in rows if r.get("suspension")})
        notes = ", ".join(suspension_types) if suspension_types else "—"
        lines.append(f"| {engine} | {threshold} | {rate} | {notes} |")

    lines += ["", "## Per-Engine Detail", ""]

    for engine, rows in engine_results.items():
        lines += [
            f"### {engine}",
            "",
            "| Phase | Interval | Req# | HTTP | Results | Time(s) | Suspension |",
            "|-------|----------|------|------|---------|---------|------------|",
        ]
        for r in rows:
            susp = r.get("suspension") or "—"
            lines.append(
                f"| {r['phase']} | {r['interval']}s | {r['req_num']} "
                f"| {r['status_code']} | {r['result_count']} "
                f"| {r['response_time']} | {susp} |"
            )
        lines.append("")

    lines += [
        "## Method",
        "",
        "Queries sent to local SearXNG instance (`http://localhost:8080/search`) with `engines=<name>`.",
        "Each engine tested independently. 4 phases with increasing frequency:",
        "- Phase 1: 1 query / 10s (6 queries)",
        "- Phase 2: 1 query / 5s (6 queries)",
        "- Phase 3: 1 query / 2s (6 queries)",
        "- Phase 4: 1 query / 1s (6 queries)",
        f"60-second cooldown between engines to prevent cross-contamination.",
        "Suspension detected via: `unresponsive_engines` field in JSON response.",
    ]

    return "\n".join(lines)


# Save report to 20_reports directory
def save_report(report: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"suspension_threshold_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    run_suspension_threshold()
