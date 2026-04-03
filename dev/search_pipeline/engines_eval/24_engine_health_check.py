#!/usr/bin/env python3
# Phase-1-only health check for previously-suspended engines after SearXNG update

# INFRASTRUCTURE
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "20_reports"
SEARXNG_URL = "http://localhost:8080/search"

ENGINES = [
    "brave",
    "mojeek",
    "startpage",
    "google scholar",
    "semantic scholar",
    "crossref",
]

QUERIES = [
    "python asyncio best practices",
    "machine learning evaluation metrics",
    "climate change carbon capture",
    "rust ownership borrow checker",
    "docker kubernetes container orchestration",
    "transformer architecture attention",
]

PHASE_INTERVAL = 10
PHASE_COUNT = 6
COOLDOWN = 30

_counter = 0


# ORCHESTRATOR
def run_engine_health_check():
    results: dict = {}
    for i, engine in enumerate(ENGINES):
        print(f"\n[{i+1}/{len(ENGINES)}] {engine}", file=sys.stderr)
        rows = test_engine_phase1(engine)
        results[engine] = rows
        if i < len(ENGINES) - 1:
            print(f"  Cooldown {COOLDOWN}s...", file=sys.stderr)
            time.sleep(COOLDOWN)

    report = build_report(results)
    save_report(report)


# FUNCTIONS

# Run Phase 1 (10s × 6 queries) for one engine
def test_engine_phase1(engine: str) -> list:
    rows = []
    for idx in range(PHASE_COUNT):
        query = QUERIES[idx % len(QUERIES)]
        row = single_query(engine, query)
        rows.append(row)
        flag = row.get("suspension_flag") or "—"
        print(
            f"  [{row['req_num']}] HTTP={row['status_code']} results={row['result_count']} {flag}",
            file=sys.stderr,
        )
        time.sleep(PHASE_INTERVAL)
    return rows


# Execute one SearXNG query and return result dict
def single_query(engine: str, query: str) -> dict:
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
            "engines": engine,
        }
        response = requests.get(SEARXNG_URL, params=params, timeout=20)
        elapsed = round(time.time() - start, 2)
        data = response.json()
        results = data.get("results", [])
        unresponsive = data.get("unresponsive_engines", [])

        engine_entry = next(
            (e for e in unresponsive if
             (isinstance(e, list) and e[0] == engine) or
             (isinstance(e, dict) and e.get("name") == engine)),
            None,
        )
        suspension_flag = None
        if engine_entry:
            reason = engine_entry[1] if isinstance(engine_entry, list) else engine_entry.get("error", "")
            suspension_flag = f"{reason}"

        return {
            "req_num": req_num,
            "engine": engine,
            "status_code": response.status_code,
            "result_count": len(results),
            "response_time": elapsed,
            "suspension_flag": suspension_flag,
        }
    except Exception as e:
        return {
            "req_num": req_num,
            "engine": engine,
            "status_code": 0,
            "result_count": 0,
            "response_time": round(time.time() - start, 2),
            "suspension_flag": f"ERROR:{str(e)[:60]}",
        }


# Build markdown report from per-engine rows
def build_report(results: dict) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Engine Health Check (Phase 1 Only)",
        f"Date: {timestamp}",
        f"Config: Phase 1 only — {PHASE_INTERVAL}s interval × {PHASE_COUNT} queries, {COOLDOWN}s cooldown",
        "",
        "## Summary",
        "",
        "| Engine | Clean | Flagged | Total | Avg Results | Status |",
        "|--------|-------|---------|-------|-------------|--------|",
    ]

    for engine, rows in results.items():
        clean = sum(1 for r in rows if not r.get("suspension_flag") and r["result_count"] > 0)
        flagged = sum(1 for r in rows if r.get("suspension_flag"))
        total = len(rows)
        avg = sum(r["result_count"] for r in rows) / total if total else 0
        flags = list({r["suspension_flag"] for r in rows if r.get("suspension_flag")})
        status = "OK" if flagged == 0 else (f"PARTIAL ({flags[0][:30]})" if clean > 0 else f"FAIL ({flags[0][:30]})")
        lines.append(f"| {engine} | {clean} | {flagged} | {total} | {avg:.0f} | {status} |")

    lines += ["", "## Per-Engine Detail", ""]
    for engine, rows in results.items():
        lines += [
            f"### {engine}",
            "",
            "| Req# | HTTP | Results | Time(s) | Flag |",
            "|------|------|---------|---------|------|",
        ]
        for r in rows:
            flag = r.get("suspension_flag") or "—"
            lines.append(f"| {r['req_num']} | {r['status_code']} | {r['result_count']} | {r['response_time']} | {flag} |")
        lines.append("")

    return "\n".join(lines)


# Save report to 20_reports directory
def save_report(report: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"engine_health_check_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    run_engine_health_check()
