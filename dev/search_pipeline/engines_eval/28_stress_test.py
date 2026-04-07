#!/usr/bin/env python3

# INFRASTRUCTURE
import argparse
import asyncio
import dataclasses
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.commands import PageCommands
from pydoll.commands.network_commands import NetworkCommands
from pydoll.protocol.network.types import CookieSameSite

from stealth_config import DEFAULT_CONFIG, StealthConfig, build_chrome_args, build_js_patches
from engine_selectors import ENGINE_SELECTORS

QUERIES_FILE = Path(__file__).parent.parent / "queries.txt"
REPORTS_DIR = Path(__file__).parent / "28_reports"
SESSION_DIR = str(Path.home() / ".searxng-mcp" / "stress-test-session")
PYDOLL_ENGINES = ["google", "bing", "brave", "startpage", "mojeek", "google scholar"]
MAX_WAIT_CYCLES = 15
WAIT_INTERVAL = 1.0
SLEEP_WAIT = 3.0


@dataclass
class QueryResult:
    query: str
    engine: str
    result_count: int
    response_time: float
    error: Optional[str]
    first_title: str


# ORCHESTRATOR

# Fire all queries at all 6 pydoll engines, collect results, write summary report
async def run_stress_test(config: StealthConfig, limit: Optional[int]) -> None:
    queries = _load_queries(limit)
    total = len(queries) * len(PYDOLL_ENGINES)
    print(f"Loaded {len(queries)} queries | Engines: {len(PYDOLL_ENGINES)} | Total: {total}", file=sys.stderr)

    results: list[QueryResult] = []
    browser = None
    browser_restarted = False

    try:
        browser = await _start_browser(config)

        for q_idx, query in enumerate(queries, 1):
            print(f"\n[{q_idx}/{len(queries)}] {query!r}", file=sys.stderr)

            for engine in PYDOLL_ENGINES:
                try:
                    result = await _run_one(browser, query, engine, config)
                except Exception as e:
                    err_str = str(e)
                    print(f"  {engine}: browser-level error — {err_str[:80]}", file=sys.stderr)

                    if not browser_restarted:
                        print("  Attempting browser restart...", file=sys.stderr)
                        try:
                            await browser.stop()
                        except Exception:
                            pass
                        try:
                            browser = await _start_browser(config)
                            browser_restarted = True
                            result = await _run_one(browser, query, engine, config)
                        except Exception as e2:
                            result = QueryResult(query, engine, 0, 0.0, f"restart_failed: {str(e2)[:80]}", "")
                    else:
                        result = QueryResult(query, engine, 0, 0.0, f"browser_dead: {err_str[:80]}", "")

                results.append(result)
                status = f"  {engine}: {result.result_count} results ({result.response_time:.1f}s)"
                if result.error:
                    status += f" | {result.error[:50]}"
                print(status, file=sys.stderr)

    finally:
        if browser:
            try:
                await browser.stop()
            except Exception:
                pass

    report = _build_report(results, len(queries))
    path = _save_report(report)
    print(f"\nReport: {path}")


# FUNCTIONS

# Parse queries.txt and return only @profile: general queries (non-empty, non-comment)
def _load_queries(limit: Optional[int]) -> list[str]:
    text = QUERIES_FILE.read_text(encoding="utf-8")
    queries = []
    in_general = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "@profile: general":
            in_general = True
            continue
        if stripped.startswith("@profile:"):
            in_general = False
            continue
        if in_general and stripped and not stripped.startswith("#"):
            queries.append(stripped)

    return queries[:limit] if limit else queries


# Build browser with stealth config, inject consent cookies once into shared cookie store
async def _start_browser(config: StealthConfig):
    options = ChromiumOptions()
    options.headless = config.headless
    options.add_argument(f"--user-data-dir={SESSION_DIR}")
    options.block_popups = True
    options.block_notifications = True
    options.webrtc_leak_protection = config.webrtc_leak_protection
    options.browser_preferences = config.browser_preferences

    for arg in build_chrome_args(config):
        options.add_argument(arg)

    browser = Chrome(options)
    tab = await browser.start()
    await _inject_consent_cookies(tab)
    return browser


# Set Google/Scholar SOCS consent cookie in browser-wide cookie store via CDP
async def _inject_consent_cookies(tab) -> None:
    cookie = ENGINE_SELECTORS["google"]["consent_cookie"]
    await tab._execute_command(NetworkCommands.set_cookie(
        name=cookie["name"],
        value=cookie["value"],
        domain=cookie["domain"],
        path=cookie["path"],
        secure=cookie["secure"],
        same_site=CookieSameSite.LAX,
    ))


# Open new tab, apply JS patches, navigate, wait, parse, close tab — return QueryResult
async def _run_one(browser, query: str, engine: str, config: StealthConfig) -> QueryResult:
    cfg = ENGINE_SELECTORS[engine]
    start = time.monotonic()
    tab = None

    try:
        tab = await browser.new_tab()

        js = build_js_patches(config)
        await tab._execute_command(
            PageCommands.add_script_to_evaluate_on_new_document(
                source=js,
                run_immediately=True,
            )
        )

        url = cfg["url_fn"](query)
        await tab.go_to(url, timeout=30)
        current = await tab.current_url

        if cfg.get("captcha_path") and cfg["captcha_path"] in current:
            elapsed = time.monotonic() - start
            return QueryResult(query, engine, 0, elapsed, "CAPTCHA", "")

        if cfg.get("consent_domain") and cfg["consent_domain"] in current:
            elapsed = time.monotonic() - start
            return QueryResult(query, engine, 0, elapsed, "consent_redirect", "")

        await _wait_for_results(tab, cfg)
        results = await _parse_results(tab, cfg)
        elapsed = time.monotonic() - start
        first_title = results[0].get("title", "")[:60] if results else ""

        return QueryResult(query, engine, len(results), elapsed, None, first_title)

    except Exception as e:
        elapsed = time.monotonic() - start
        return QueryResult(query, engine, 0, elapsed, str(e)[:120], "")

    finally:
        if tab:
            try:
                await tab.close()
            except Exception:
                pass


# Wait for results using engine's strategy: JS poll or fixed sleep
async def _wait_for_results(tab, cfg: dict) -> bool:
    if cfg["wait"] == "sleep":
        await asyncio.sleep(SLEEP_WAIT)
        return True

    for _ in range(MAX_WAIT_CYCLES):
        raw = await tab.execute_script(cfg["wait_js"])
        count = _extract_nested(raw)
        if count and int(count) > 0:
            return True
        await asyncio.sleep(WAIT_INTERVAL)
    return False


# Execute parse_js and return list of result dicts
async def _parse_results(tab, cfg: dict) -> list[dict]:
    raw = await tab.execute_script(cfg["parse_js"])
    value = _extract_nested(raw)
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


# Extract value from nested CDP result structure
def _extract_nested(result):
    try:
        return result["result"]["result"]["value"]
    except (KeyError, TypeError):
        return None


# Build full markdown stress test report with summary, failure timeline, full matrix
def _build_report(results: list[QueryResult], total_queries: int) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    engines = PYDOLL_ENGINES

    by_engine: dict[str, list[QueryResult]] = {e: [] for e in engines}
    for r in results:
        by_engine[r.engine].append(r)

    queries_ordered: list[str] = []
    seen: set[str] = set()
    for r in results:
        if r.query not in seen:
            seen.add(r.query)
            queries_ordered.append(r.query)

    lines = [
        "# Stress Test Report",
        f"Date: {timestamp}",
        f"Queries: {total_queries} | Engines: {len(engines)} | Total: {total_queries * len(engines)}",
        "",
        "## Summary per Engine",
        "",
        "| Engine | Success | Zero Results | Errors | Avg Time | Total URLs |",
        "|--------|---------|--------------|--------|----------|------------|",
    ]

    for engine in engines:
        ers = by_engine[engine]
        success = sum(1 for r in ers if r.result_count > 0)
        zero = sum(1 for r in ers if r.result_count == 0 and not r.error)
        errors = sum(1 for r in ers if r.error)
        avg_time = sum(r.response_time for r in ers) / len(ers) if ers else 0.0
        total_urls = sum(r.result_count for r in ers)
        lines.append(f"| {engine} | {success} | {zero} | {errors} | {avg_time:.1f}s | {total_urls} |")

    lines += [
        "",
        "## Failure Timeline",
        "",
        "| Engine | First Failure Query | Query # | Status |",
        "|--------|---------------------|---------|--------|",
    ]

    for engine in engines:
        ers = by_engine[engine]
        first_fail = None
        for idx, r in enumerate(ers, 1):
            if r.error or r.result_count == 0:
                first_fail = (idx, r)
                break
        if first_fail:
            idx, r = first_fail
            status = r.error if r.error else "zero_results"
            q_short = r.query[:40].replace("|", "\\|")
            lines.append(f"| {engine} | {q_short} | {idx} | {status[:60]} |")
        else:
            lines.append(f"| {engine} | — | — | — |")

    lines += [
        "",
        "## Full Matrix",
        "",
        "| # | Query | " + " | ".join(engines) + " |",
        "|---|-------|" + "|".join(["-------"] * len(engines)) + "|",
    ]

    lookup: dict[tuple, QueryResult] = {(r.query, r.engine): r for r in results}

    for q_idx, query in enumerate(queries_ordered, 1):
        cells = []
        for engine in engines:
            r = lookup.get((query, engine))
            if not r:
                cells.append("—")
            elif r.error:
                short_err = r.error[:20].replace("|", "\\|")
                cells.append(f"❌ {short_err}")
            else:
                cells.append(str(r.result_count))
        short_q = query[:35].replace("|", "\\|")
        lines.append(f"| {q_idx} | {short_q} | " + " | ".join(cells) + " |")

    return "\n".join(lines)


# Save report to 28_reports/stress_<timestamp>.md, return path string
def _save_report(report: str) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"stress_{timestamp}.md"
    path.write_text(report, encoding="utf-8")
    return str(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stress test — all general queries × 6 pydoll engines")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--limit", type=int, default=None, help="Only first N queries")
    args = parser.parse_args()

    config = dataclasses.replace(DEFAULT_CONFIG, headless=not args.headed)
    asyncio.run(run_stress_test(config, args.limit))
