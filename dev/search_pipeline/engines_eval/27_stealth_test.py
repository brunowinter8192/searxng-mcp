#!/usr/bin/env python3

# INFRASTRUCTURE
import argparse
import asyncio
import dataclasses
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.commands import PageCommands

from stealth_config import DEFAULT_CONFIG, StealthConfig, build_chrome_args, build_js_patches

REPORTS_DIR = Path(__file__).parent / "27_reports"
SESSION_DIR = str(Path.home() / ".searxng-mcp" / "stealth-test-session")
MAX_WAIT_CYCLES = 15
WAIT_INTERVAL = 1.0
SLEEP_WAIT = 3.0

# Engines that use httpx — cannot be stealth-tested with a browser
HTTPX_ENGINES = {"duckduckgo", "semantic scholar", "crossref"}

# --- Engine-specific JS strings (copied verbatim from src/search/engines/) ---

_GOOGLE_JS_WAIT = "return document.querySelectorAll('div.g').length"

_GOOGLE_JS_PARSE = """
return JSON.stringify((function() {
    var nodes = document.querySelectorAll('div.g');
    var out = [];
    for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        var a = el.querySelector('a[href^="http"], a[href^="//"]');
        var h3 = el.querySelector('h3');
        if (!a || !h3) continue;
        var snip = el.querySelector('.VwiC3b') ||
                   el.querySelector('[data-sncf]') ||
                   el.querySelector('.lEBKkf') ||
                   el.querySelector('[data-content-feature]');
        out.push({
            url: a.href,
            title: h3.textContent.trim(),
            snippet: snip ? snip.textContent.trim() : ''
        });
    }
    return out;
})());
"""

_GOOGLE_JS_CONSENT = """
var btn = document.querySelector('button[jsname="b3VHJd"]') ||
           document.querySelector('.lssxud') ||
           document.querySelector('form[action*="consent"] button[type="submit"]') ||
           document.querySelector('button[aria-label*="Accept"]');
if (btn) { btn.click(); return true; }
return false;
"""

_SCHOLAR_JS_WAIT = "return document.querySelectorAll('div.gs_r.gs_or.gs_scl').length"

_SCHOLAR_JS_PARSE = """
return JSON.stringify((function() {
    var nodes = document.querySelectorAll('div.gs_r.gs_or.gs_scl');
    var out = [];
    for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        var a = el.querySelector('h3.gs_rt a');
        var snip = el.querySelector('div.gs_rs');
        if (!a) continue;
        out.push({
            url: a.href,
            title: a.textContent.trim(),
            snippet: snip ? snip.textContent.trim() : ''
        });
    }
    return out;
})());
"""

_BING_JS_PARSE = """
JSON.stringify(
  Array.from(document.querySelectorAll('li.b_algo')).map(function(el) {
    var a = el.querySelector('h2 a');
    var snip = el.querySelector('p.b_lineclamp2') || el.querySelector('.b_caption p');
    return {
      title: a ? a.innerText.trim() : '',
      url: a ? a.href : '',
      snippet: snip ? snip.innerText.trim() : ''
    };
  }).filter(function(r) { return r.url; })
)
"""

_BRAVE_JS_PARSE = """
JSON.stringify(
  Array.from(document.querySelectorAll('div.snippet')).map(function(el) {
    var a = el.querySelector('a.result-header');
    var snip = el.querySelector('p.snippet-description');
    return {
      title: a ? a.innerText.trim() : '',
      url: a ? a.href : '',
      snippet: snip ? snip.innerText.trim() : ''
    };
  }).filter(function(r) { return r.url; })
)
"""

_STARTPAGE_JS_PARSE = """
JSON.stringify(
  Array.from(document.querySelectorAll('div.w-gl__result')).map(function(el) {
    var a = el.querySelector('a.w-gl__result-title');
    var snip = el.querySelector('p.w-gl__description');
    return {
      title: a ? a.innerText.trim() : '',
      url: a ? a.href : '',
      snippet: snip ? snip.innerText.trim() : ''
    };
  }).filter(function(r) { return r.url; })
)
"""

_MOJEEK_JS_PARSE = """
JSON.stringify(
  Array.from(document.querySelectorAll('ul.results-standard li')).map(function(li) {
    var urlEl = li.querySelector('a.ob');
    var titleEl = li.querySelector('h2 a');
    var snippetEl = li.querySelector('p.s');
    return {
      title: titleEl ? titleEl.innerText.trim() : '',
      url: urlEl ? urlEl.href : '',
      snippet: snippetEl ? snippetEl.innerText.trim() : ''
    };
  }).filter(function(r) { return r.url; })
)
"""

# Engine configuration table
ENGINE_CONFIGS = {
    "google": {
        "url_fn": lambda q: f"https://www.google.com/search?q={quote_plus(q)}&hl=en&num=10",
        "wait": "poll",
        "wait_js": _GOOGLE_JS_WAIT,
        "parse_js": _GOOGLE_JS_PARSE,
        "extract": "nested",
        "consent_domain": "consent.google.com",
        "captcha_path": "/sorry/",
        "consent_js": _GOOGLE_JS_CONSENT,
    },
    "google scholar": {
        "url_fn": lambda q: f"https://scholar.google.com/scholar?q={quote_plus(q)}&hl=en&num=10",
        "wait": "poll",
        "wait_js": _SCHOLAR_JS_WAIT,
        "parse_js": _SCHOLAR_JS_PARSE,
        "extract": "nested",
        "consent_domain": "consent.google.com",
        "captcha_path": "/sorry/",
        "consent_js": _GOOGLE_JS_CONSENT,
    },
    "bing": {
        "url_fn": lambda q: f"https://www.bing.com/search?q={quote_plus(q)}&setlang=en&count=10",
        "wait": "sleep",
        "parse_js": _BING_JS_PARSE,
        "extract": "return_by_value",
    },
    "brave": {
        "url_fn": lambda q: f"https://search.brave.com/search?q={quote_plus(q)}&source=web",
        "wait": "sleep",
        "parse_js": _BRAVE_JS_PARSE,
        "extract": "return_by_value",
    },
    "startpage": {
        "url_fn": lambda q: f"https://www.startpage.com/sp/search?query={quote_plus(q)}&language=en",
        "wait": "sleep",
        "parse_js": _STARTPAGE_JS_PARSE,
        "extract": "return_by_value",
    },
    "mojeek": {
        "url_fn": lambda q: f"https://www.mojeek.com/search?q={quote_plus(q)}&arc=none",
        "wait": "sleep",
        "parse_js": _MOJEEK_JS_PARSE,
        "extract": "return_by_value",
    },
}


# ORCHESTRATOR

# Run stealth test for one engine/query with given config, save report, optional screenshot
async def run_stealth_test(engine: str, query: str, config: StealthConfig, screenshot: bool) -> None:
    print(f"Engine: {engine} | Query: {query!r}", file=sys.stderr)
    print(f"Mode: {'headed' if not config.headless else 'headless'}", file=sys.stderr)

    browser, tab = await _start_browser(config)
    screenshot_path = None
    detection = {"consent": False, "captcha": False, "zero_results": False, "error": None}
    results = []

    try:
        results, detection = await _run_engine(tab, engine, query, detection)
        if screenshot:
            screenshot_path = await _save_screenshot(tab, engine)
    except Exception as e:
        detection["error"] = str(e)
        print(f"ERROR: {e}", file=sys.stderr)
    finally:
        await browser.stop()

    _print_summary(engine, query, results, detection)
    report = _build_report(engine, query, config, detection, results, screenshot_path, screenshot)
    report_path = _save_report(engine, report)
    print(f"Report: {report_path}")


# FUNCTIONS

# Build ChromiumOptions from config and start browser, return (browser, tab)
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
    await _apply_js_patches(tab, config)
    return browser, tab


# Inject fingerprint patch script via Page.addScriptToEvaluateOnNewDocument
async def _apply_js_patches(tab, config: StealthConfig) -> None:
    js = build_js_patches(config)
    await tab._execute_command(
        PageCommands.add_script_to_evaluate_on_new_document(
            source=js,
            run_immediately=True,
        )
    )


# Navigate engine, handle consent, wait for results, parse
async def _run_engine(tab, engine: str, query: str, detection: dict) -> tuple[list, dict]:
    cfg = ENGINE_CONFIGS[engine]
    url = cfg["url_fn"](query)

    await tab.go_to(url, timeout=30)
    current = await tab.current_url

    # Consent page handling (Google/Scholar)
    if cfg.get("consent_domain") and cfg["consent_domain"] in current:
        detection["consent"] = True
        print(f"CONSENT PAGE detected — clicking accept", file=sys.stderr)
        await tab.execute_script(cfg["consent_js"])
        await asyncio.sleep(2.0)
        await tab.go_to(url, timeout=30)
        current = await tab.current_url

    # CAPTCHA detection
    if cfg.get("captcha_path") and cfg["captcha_path"] in current:
        detection["captcha"] = True
        print(f"CAPTCHA detected", file=sys.stderr)
        return [], detection

    # Wait for results
    found = await _wait_for_results(tab, cfg)
    if not found:
        print(f"Timeout — no results loaded", file=sys.stderr)

    # Parse results
    results = await _parse_results(tab, cfg)
    if not results:
        detection["zero_results"] = True

    return results, detection


# Wait for results using engine's strategy (JS poll or fixed sleep)
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


# Run parse JS and return list of result dicts
async def _parse_results(tab, cfg: dict) -> list[dict]:
    if cfg["extract"] == "nested":
        raw = await tab.execute_script(cfg["parse_js"])
        value = _extract_nested(raw)
    else:
        raw = await tab.execute_script(cfg["parse_js"], return_by_value=True)
        value = _extract_return_by_value(raw)

    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


# Take screenshot and save to 27_reports, return path string
async def _save_screenshot(tab, engine: str) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_engine = engine.replace(" ", "_")
    path = REPORTS_DIR / f"{safe_engine}_{timestamp}.png"
    await tab.take_screenshot(path=str(path))
    print(f"Screenshot: {path}", file=sys.stderr)
    return str(path)


# Extract value from nested CDP result structure (google.py pattern)
def _extract_nested(result):
    try:
        return result["result"]["result"]["value"]
    except (KeyError, TypeError):
        return None


# Extract value from return_by_value CDP result (bing.py pattern)
def _extract_return_by_value(result) -> str:
    if isinstance(result, dict):
        v = result.get("value")
        if v is not None:
            return v
        level1 = result.get("result", {})
        if isinstance(level1, dict):
            v = level1.get("value")
            if v is not None:
                return v
            level2 = level1.get("result", {})
            if isinstance(level2, dict):
                v = level2.get("value")
                if v is not None:
                    return v
    return "[]"


# Print compact summary to stdout
def _print_summary(engine: str, query: str, results: list, detection: dict) -> None:
    print(f"\n=== {engine} | {query!r} ===")
    print(f"Results: {len(results)}")
    for k, v in detection.items():
        if v:
            print(f"  {k}: {v}")
    for i, r in enumerate(results[:3], 1):
        print(f"  {i}. {r.get('title', '')[:60]}")
        print(f"     {r.get('url', '')}")


# Build full markdown report
def _build_report(
    engine: str,
    query: str,
    config: StealthConfig,
    detection: dict,
    results: list,
    screenshot_path: str | None,
    screenshot_requested: bool,
) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    mode = "headed" if not config.headless else "headless"
    screenshot_label = "yes" if screenshot_path else ("requested but failed" if screenshot_requested else "no")

    lines = [
        "# Stealth Test Report",
        f"Date: {timestamp}",
        f'Engine: {engine} | Query: "{query}"',
        f"Mode: {mode} | Screenshot: {screenshot_label}",
        "",
        "## Config Used",
        "",
        "| Setting | Value |",
        "|---------|-------|",
    ]

    cfg_dict = dataclasses.asdict(config)
    for key, value in cfg_dict.items():
        if isinstance(value, (dict, list)) and len(str(value)) > 80:
            display = str(value)[:80] + "…"
        else:
            display = str(value)
        display = display.replace("|", "\\|")
        lines.append(f"| {key} | {display} |")

    consent_label = "Yes" if detection["consent"] else "No"
    captcha_label = "Yes" if detection["captcha"] else "No"
    zero_label = "Yes" if detection["zero_results"] else "No"
    error_label = detection["error"] or "None"

    lines += [
        "",
        "## Detection",
        "",
        "| Check | Result |",
        "|-------|--------|",
        f"| Consent Page | {consent_label} |",
        f"| CAPTCHA | {captcha_label} |",
        f"| Zero Results | {zero_label} |",
        f"| Error | {error_label} |",
        "",
        f"## Results ({len(results)} URLs)",
        "",
        "| # | Title | URL |",
        "|---|-------|-----|",
    ]

    for idx, r in enumerate(results, 1):
        title = r.get("title", "")[:80].replace("|", "\\|")
        url = r.get("url", "").replace("|", "\\|")
        lines.append(f"| {idx} | {title} | {url} |")

    if not results:
        lines.append("| — | — | — |")

    return "\n".join(lines)


# Save report to 27_reports/<engine>_<timestamp>.md, return path
def _save_report(engine: str, report: str) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_engine = engine.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"{safe_engine}_{timestamp}.md"
    path.write_text(report, encoding="utf-8")
    return str(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stealth config test — one engine, one query")
    parser.add_argument("engine", help="Engine name: google, bing, brave, startpage, mojeek, 'google scholar'")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--screenshot", action="store_true", help="Save screenshot to 27_reports/")
    args = parser.parse_args()

    engine = args.engine.lower()

    if engine in HTTPX_ENGINES:
        print(f"'{engine}' uses httpx — no browser involved, cannot stealth-test.", file=sys.stderr)
        print(f"Stealth-testable engines: {', '.join(ENGINE_CONFIGS)}", file=sys.stderr)
        sys.exit(1)

    if engine not in ENGINE_CONFIGS:
        print(f"Unknown engine: {engine!r}", file=sys.stderr)
        print(f"Available: {', '.join(ENGINE_CONFIGS)}", file=sys.stderr)
        sys.exit(1)

    config = dataclasses.replace(DEFAULT_CONFIG, headless=not args.headed)
    asyncio.run(run_stealth_test(engine, args.query, config, args.screenshot))
