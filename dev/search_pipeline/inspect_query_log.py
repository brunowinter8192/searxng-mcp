"""Inspect src/logs/query_log.jsonl — summary stats over all logged queries.

Usage: python dev/search_pipeline/inspect_query_log.py [--tail N]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

LOG_PATH = Path("src/logs/query_log.jsonl")


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect query_log.jsonl")
    ap.add_argument("--tail", type=int, default=None, help="Only show last N records")
    args = ap.parse_args()

    if not LOG_PATH.exists():
        print(f"No log file at {LOG_PATH}", file=sys.stderr)
        sys.exit(1)

    records = [json.loads(l) for l in LOG_PATH.read_text().splitlines() if l.strip()]
    if args.tail:
        records = records[-args.tail:]

    if not records:
        print("Log is empty.")
        return

    total_wall = [r["total_wall_ms"] for r in records]
    bottlenecks = Counter(r.get("bottleneck_engine") for r in records if r.get("bottleneck_engine"))
    timeouts: Counter = Counter()
    for r in records:
        for eng, d in r.get("engines", {}).items():
            if d.get("status") == "TIMEOUT":
                timeouts[eng] += 1

    print(f"Records      : {len(records)}")
    print(f"Wall ms      : min={min(total_wall)}  mean={sum(total_wall)//len(total_wall)}  max={max(total_wall)}")
    print(f"Bottlenecks  : {dict(bottlenecks.most_common(5))}")
    print(f"TIMEOUT hits : {dict(timeouts.most_common(5))}")
    print(f"\nLast query   : {records[-1].get('query')}  ({records[-1].get('ts')})")

    prev = records[-1]
    for eng, d in prev.get("engines", {}).items():
        print(f"  {eng:20s}  rate_wait={d['rate_wait_ms']:5d}ms  search={d['search_ms']:5d}ms  {d['status']}")

    pv = prev.get("preview", {})
    print(f"  preview: {pv.get('urls_succeeded')}/{pv.get('urls_attempted')} ok, "
          f"{pv.get('url_timeouts')} timeouts, {pv.get('total_ms')}ms total")


if __name__ == "__main__":
    main()
