#!/usr/bin/env python3
"""One-shot DOM inspector — navigate Google, dump result container structure."""

# INFRASTRUCTURE
import asyncio
import json
import sys
from urllib.parse import quote_plus

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.commands import PageCommands
from pydoll.commands.network_commands import NetworkCommands
from pydoll.protocol.network.types import CookieSameSite

from stealth_config import DEFAULT_CONFIG, build_chrome_args, build_js_patches

SESSION_DIR = str(__import__("pathlib").Path.home() / ".searxng-mcp" / "stealth-dom-inspect")

_INSPECT_JS = """
return JSON.stringify({
    div_g: document.querySelectorAll('div.g').length,
    search_exists: !!document.querySelector('#search'),
    rso_exists: !!document.querySelector('#rso'),
    rso_children: Array.from(document.querySelectorAll('#rso > div')).slice(0, 5).map(function(el) {
        var firstA = el.querySelector('a[href^="http"]');
        var firstH3 = el.querySelector('h3');
        return {
            classes: el.className,
            dataKeys: Object.keys(el.dataset),
            hasA: !!firstA,
            href: firstA ? firstA.href : null,
            h3: firstH3 ? firstH3.textContent.slice(0, 60) : null,
            childDivClasses: Array.from(el.querySelectorAll('div')).slice(0, 5).map(function(d) { return d.className; }).filter(Boolean)
        };
    }),
    all_h3s: document.querySelectorAll('h3').length,
    links_with_h3: Array.from(document.querySelectorAll('h3')).slice(0, 5).map(function(h3) {
        var a = h3.closest('a') || h3.parentElement.querySelector('a[href^="http"]') || h3.parentElement.parentElement.querySelector('a[href^="http"]');
        return { text: h3.textContent.slice(0, 60), href: a ? a.href : null };
    })
});
"""


# ORCHESTRATOR
async def inspect_dom(query: str) -> None:
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
    await tab._execute_command(NetworkCommands.set_cookie(
        name="SOCS",
        value="CAISHAgCEhJnd3NfMjAyNjA0MDctMCAgIBgEIAEaBgiA_fC8Bg",
        domain=".google.com",
        path="/",
        secure=True,
        same_site=CookieSameSite.LAX,
    ))

    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en&num=10"
    await tab.go_to(url, timeout=30)
    await asyncio.sleep(4.0)

    raw = await tab.execute_script(_INSPECT_JS)
    try:
        value = raw["result"]["result"]["value"]
        data = json.loads(value)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        print(repr(raw), file=sys.stderr)

    await browser.stop()


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "python asyncio best practices"
    asyncio.run(inspect_dom(q))
