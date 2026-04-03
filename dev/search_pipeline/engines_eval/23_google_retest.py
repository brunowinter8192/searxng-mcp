#!/usr/bin/env python3
# One-shot retest: Google only, after suspension disabled in settings.yml

# INFRASTRUCTURE
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "20_reports"
SEARXNG_URL = "http://localhost:8080/search"

PHASES = [
    ("Phase 1 (10s interval)", 10, 6),
    ("Phase 2 (5s interval)", 5, 6),
    ("Phase 3 (2s interval)", 2, 6),
    ("Phase 4 (1s interval)", 1, 6),
]

QUERIES = [
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
]

_counter = 0


# ORCHESTRATOR
def run_google_retest():
    print("[*] Google retest — suspension_times=0, ban_time_on_fail=0", file=sys.stderr)
    rows = test_google()
    report = build_report(rows)
    save_report(report)


# FUNCTIONS

# Run all 4 phases against Google and return result rows
def test_google() -> list:
    rows = []
    query_idx = 0

    for phase_name, interval, count in PHASES:
        print(f"  {phase_name}...", file=sys.stderr)
        for _ in range(count):
            query = QUERIES[query_idx % len(QUERIES)]
            query_idx += 1
            row = single_query(query, phase_name, interval)
            rows.append(row)
            flag = row.get("suspension_flag") or "—"
            print(
                f"    [{row['req_num']}] HTTP={row['status_code']} "
                f"results={row['result_count']} unresponsive={row['unresponsive_raw']} {flag}",
                file=sys.stderr,
            )
            time.sleep(interval)

    return rows


# Execute one SearXNG query for Google and return result dict with raw unresponsive field
def single_query(query: str, phase_name: str, interval: int) -> dict:
    global _counter
    _counter += 1
    req_num = _counter

    start = time.time()
    try:
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "language": "en",
            "pageno": 1,
            "engines": "google",
        }
        response = requests.get(SEARXNG_URL, params=params, timeout=20)
        elapsed = round(time.time() - start, 2)
        data = response.json()
        results = data.get("results", [])
        unresponsive = data.get("unresponsive_engines", [])

        google_entry = next(
            (e for e in unresponsive if
             (isinstance(e, list) and e[0] == "google") or
             (isinstance(e, dict) and e.get("name") == "google")),
            None,
        )
        suspension_flag = None
        if google_entry:
            reason = google_entry[1] if isinstance(google_entry, list) else google_entry.get("error", "")
            suspension_flag = f"UNRESPONSIVE:{reason}"

        return {
            "req_num": req_num,
            "phase": phase_name,
            "interval": interval,
            "query": query,
            "status_code": response.status_code,
            "result_count": len(results),
            "response_time": elapsed,
            "suspension_flag": suspension_flag,
            "unresponsive_raw": str(unresponsive) if unresponsive else "[]",
        }
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return {
            "req_num": req_num,
            "phase": phase_name,
            "interval": interval,
            "query": query,
            "status_code": 0,
            "result_count": 0,
            "response_time": elapsed,
            "suspension_flag": f"ERROR:{str(e)[:80]}",
            "unresponsive_raw": "N/A",
        }


# Build markdown report from Google retest rows
def build_report(rows: list) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    flagged = [r for r in rows if r.get("suspension_flag")]
    clean = [r for r in rows if not r.get("suspension_flag") and r["result_count"] > 0]

    lines = [
        "# Google Retest Report (Suspension Disabled)",
        f"Date: {timestamp}",
        f"Engine: google only | suspension_times=0, ban_time_on_fail=0",
        f"Requests: {len(rows)} | Flagged (unresponsive): {len(flagged)} | Clean (results>0): {len(clean)}",
        "",
        "## Verdict",
        "",
    ]
    if not flagged:
        lines.append("**Suspension flag: GONE** — SearXNG no longer marks Google as unresponsive")
    else:
        reasons = list({r["suspension_flag"] for r in flagged})
        if all("access denied" in r.lower() or "403" in r for r in reasons):
            lines.append(
                "**Suspension flag still present — but cause is GOOGLE-SIDE (403/access denied), "
                "NOT SearXNG ban.** SearXNG retries Google on every request (no pre-emptive block)."
            )
        else:
            lines.append(f"**Suspension flag present:** {reasons}")

    lines += [
        "",
        "## Per-Request Results",
        "",
        "| Req# | Phase | Interval | HTTP | Results | Time(s) | Unresponsive Flag |",
        "|------|-------|----------|------|---------|---------|-------------------|",
    ]
    for r in rows:
        flag = r.get("suspension_flag") or "—"
        lines.append(
            f"| {r['req_num']} | {r['phase']} | {r['interval']}s "
            f"| {r['status_code']} | {r['result_count']} | {r['response_time']} | {flag} |"
        )

    lines += [
        "",
        "## Phase Summary",
        "",
        "| Phase | Flagged | Clean | Avg Results |",
        "|-------|---------|-------|-------------|",
    ]
    for phase_name, _, _ in PHASES:
        phase_rows = [r for r in rows if r["phase"] == phase_name]
        phase_flagged = sum(1 for r in phase_rows if r.get("suspension_flag"))
        phase_clean = sum(1 for r in phase_rows if not r.get("suspension_flag") and r["result_count"] > 0)
        avg = sum(r["result_count"] for r in phase_rows) / len(phase_rows) if phase_rows else 0
        lines.append(f"| {phase_name} | {phase_flagged} | {phase_clean} | {avg:.0f} |")

    return "\n".join(lines)


# Save report to 20_reports directory with label
def save_report(report: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"google_retest_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    run_google_retest()
