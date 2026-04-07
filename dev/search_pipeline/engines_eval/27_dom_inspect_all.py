#!/usr/bin/env python3
"""Inspect DOM structure for all 5 pydoll engines in one Chrome session."""

# INFRASTRUCTURE
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import quote_plus

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.commands import PageCommands
from pydoll.commands.network_commands import NetworkCommands
from pydoll.protocol.network.types import CookieSameSite

from stealth_config import DEFAULT_CONFIG, build_chrome_args, build_js_patches

SESSION_DIR = str(Path.home() / ".searxng-mcp" / "stealth-dom-inspect-all")
REPORTS_DIR = Path(__file__).parent / "27_reports" / "dom"
QUERY = "python asyncio best practices"

ENGINES = {
    "bing":          f"https://www.bing.com/search?q={quote_plus(QUERY)}&setlang=en&count=10",
    "brave":         f"https://search.brave.com/search?q={quote_plus(QUERY)}&source=web",
    "startpage":     f"https://www.startpage.com/sp/search?query={quote_plus(QUERY)}&language=en",
    "mojeek":        f"https://www.mojeek.com/search?q={quote_plus(QUERY)}&arc=none",
    "google_scholar": f"https://scholar.google.com/scholar?q={quote_plus(QUERY)}&hl=en&num=10",
}

_INSPECT_JS = """
return JSON.stringify({
    url: window.location.href,
    title: document.title.slice(0, 80),
    known_containers: {
        li_b_algo: document.querySelectorAll('li.b_algo').length,
        div_snippet: document.querySelectorAll('div.snippet').length,
        div_w_gl_result: document.querySelectorAll('div.w-gl__result').length,
        ul_results_li: document.querySelectorAll('ul.results-standard li').length,
        div_gs_r: document.querySelectorAll('div.gs_r').length,
        div_gs_r_or: document.querySelectorAll('div.gs_r.gs_or.gs_scl').length,
        rso_h3: document.querySelectorAll('#rso h3').length,
        all_h3: document.querySelectorAll('h3').length
    },
    first_result_links: Array.from(document.querySelectorAll('a[href^="http"]'))
        .filter(function(a) {
            var text = a.textContent.trim();
            return text.length > 15 && text.length < 200 && !a.href.includes(window.location.hostname);
        })
        .slice(0, 5).map(function(a) {
            return {
                href: a.href.slice(0, 100),
                text: a.textContent.trim().slice(0, 70),
                parent_classes: (a.parentElement ? a.parentElement.className : '').slice(0, 80),
                grandparent_classes: (a.parentElement && a.parentElement.parentElement ? a.parentElement.parentElement.className : '').slice(0, 80)
            };
        }),
    first_3_divs_with_h3: Array.from(document.querySelectorAll('h3')).slice(0, 5).map(function(h3) {
        var p = h3.parentElement;
        var gp = p ? p.parentElement : null;
        var ggp = gp ? gp.parentElement : null;
        var a = h3.closest('a') || (p ? p.querySelector('a[href^="http"]') : null) || (gp ? gp.querySelector('a[href^="http"]') : null);
        return {
            text: h3.textContent.trim().slice(0, 60),
            parent_tag: p ? p.tagName : null,
            parent_class: p ? p.className.slice(0, 80) : null,
            grandparent_class: gp ? gp.className.slice(0, 80) : null,
            ggp_class: ggp ? ggp.className.slice(0, 80) : null,
            href: a ? a.href.slice(0, 100) : null
        };
    })
});
"""


# ORCHESTRATOR
async def inspect_all_engines() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    browser, tab = await _start_browser()

    try:
        await _set_google_consent_cookie(tab)

        for engine_name, url in ENGINES.items():
            print(f"\n--- {engine_name} ---", file=sys.stderr)
            data = await _inspect_engine(tab, engine_name, url)
            out_path = REPORTS_DIR / f"dom_{engine_name}.json"
            out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Saved: {out_path}")
            await asyncio.sleep(4)
    finally:
        await browser.stop()


# FUNCTIONS

# Start browser with stealth config
async def _start_browser():
    options = ChromiumOptions()
    options.headless = True
    options.add_argument(f"--user-data-dir={SESSION_DIR}")
    for arg in build_chrome_args(DEFAULT_CONFIG):
        options.add_argument(arg)
    browser = Chrome(options)
    tab = await browser.start()
    js = build_js_patches(DEFAULT_CONFIG)
    await tab._execute_command(
        PageCommands.add_script_to_evaluate_on_new_document(source=js, run_immediately=True)
    )
    return browser, tab


# Set Google SOCS consent cookie
async def _set_google_consent_cookie(tab) -> None:
    await tab._execute_command(NetworkCommands.set_cookie(
        name="SOCS",
        value="CAISHAgCEhJnd3NfMjAyNjA0MDctMCAgIBgEIAEaBgiA_fC8Bg",
        domain=".google.com",
        path="/",
        secure=True,
        same_site=CookieSameSite.LAX,
    ))


# Navigate to URL, wait, inspect DOM, return parsed dict
async def _inspect_engine(tab, name: str, url: str) -> dict:
    await tab.go_to(url, timeout=30)
    current = await tab.current_url
    print(f"  URL after nav: {current[:80]}", file=sys.stderr)

    # Handle Google consent redirect
    if "consent.google.com" in current:
        print(f"  Consent redirect — retrying after cookie", file=sys.stderr)
        await asyncio.sleep(1)
        await tab.go_to(url, timeout=30)
        current = await tab.current_url
        print(f"  URL after retry: {current[:80]}", file=sys.stderr)

    await asyncio.sleep(5)

    raw = await tab.execute_script(_INSPECT_JS)
    try:
        value = raw["result"]["result"]["value"]
        data = json.loads(value)
        print(f"  containers: {data['known_containers']}", file=sys.stderr)
        return data
    except Exception as e:
        return {"error": str(e), "raw": repr(raw)[:200]}


if __name__ == "__main__":
    asyncio.run(inspect_all_engines())
