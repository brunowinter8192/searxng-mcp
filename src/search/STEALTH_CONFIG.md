# Pydoll Stealth Configuration — All Levers

## 1. Browser Launch Options (ChromiumOptions)

Set in `browser.py` → `build_options()`. Applied at Chrome startup.

| Lever | Current Value | What it does |
|-------|--------------|--------------|
| `--user-agent=...` | Chrome 146 Mac UA | Sets UA string in HTTP headers |
| `--disable-blink-features=AutomationControlled` | ON | Removes `navigator.webdriver=true` flag |
| `--window-size=1920,1080` | ON | Sets viewport, affects fingerprint |
| `webrtc_leak_protection` | ON | Blocks WebRTC IP leak via `disable_non_proxied_udp` |
| `headless` | ON (env override) | Headless vs headed. Headless has detection vectors |
| `--user-data-dir=...` | `~/.searxng-mcp/browser-session` | Persistent session (cookies, localStorage) |
| `block_popups` | ON | Blocks popup windows |
| `block_notifications` | ON | Blocks notification prompts |
| `--proxy-server=...` | NOT SET | Proxy with optional credential auth |
| `--disable-gpu` | NOT SET | Can help with headless stability |
| `--no-sandbox` | NOT SET | Linux only, not needed on Mac |
| `page_load_state` | COMPLETE | When to consider page loaded: COMPLETE, DOM_CONTENT_LOADED, INTERACTIVE |
| `set_accept_languages("en-US,en;q=0.9")` | NOT SET | Accept-Language preference |
| `browser_preferences` | profile, safebrowsing, autofill, search, credentials | Make Chrome profile look like real user |

## 2. JS Fingerprint Patches (injected per tab)

Set in `browser.py` → `JS_FINGERPRINT_PATCHES`. Injected via `Page.addScriptToEvaluateOnNewDocument`.

| Lever | Current Value | What it does |
|-------|--------------|--------------|
| `screen.width/height` | 1920×1080 | Override screen dimensions |
| `screen.colorDepth/pixelDepth` | 30 | Mac Retina values |
| `window.devicePixelRatio` | 2 | Retina Mac |
| `window.outerWidth/outerHeight` | innerWidth / innerHeight+85 | Simulates browser chrome |
| `getComputedStyle` patch | Proxy on color | Fixes headless CSS color detection |

### Missing patches (should add):
- `navigator.languages` — should match Accept-Language
- `navigator.platform` — should be "MacIntel"
- `navigator.hardwareConcurrency` — default 8-16
- `navigator.deviceMemory` — default 8
- `Permissions.query` override — notifications permission
- `WebGL vendor/renderer` — headless has different values
- `Canvas fingerprint` noise — add subtle randomization

## 3. CDP Network Commands (per tab, runtime)

Available via `tab._execute_command(NetworkCommands.xxx())`. Applied after tab creation.

| Lever | Current Usage | What it does |
|-------|--------------|--------------|
| `set_useragent_override(ua, accept_language, platform, user_agent_metadata)` | **NOT USED** | CDP-level UA + Client Hints. **CRITICAL** — Google checks Sec-CH-UA consistency |
| `set_extra_http_headers(headers)` | **NOT USED** | Set Accept, Accept-Language, Accept-Encoding, etc. |
| `set_cookie(name, value, domain)` | **NOT USED** | Manage cookies per engine |
| `get_cookies()` | **NOT USED** | Read cookies (for debugging) |
| `clear_browser_cookies()` | **NOT USED** | Reset cookie state |
| `set_cache_disabled(bool)` | **NOT USED** | Disable caching (cleaner requests) |
| `emulate_network_conditions(latency, download, upload)` | **NOT USED** | Simulate connection speed |
| `set_blocked_urls(urls)` | **NOT USED** | Block tracking/analytics scripts |

## 4. CDP Emulation Commands (per tab, runtime)

Available via `tab._execute_command(EmulationCommands.xxx())`.

| Lever | Current Usage | What it does |
|-------|--------------|--------------|
| `set_user_agent_override(ua, accept_language, platform, ua_metadata)` | **NOT USED** | Same as Network version but via Emulation domain. Sets `navigator.userAgent` + Client Hints |

## 5. Rate Limiter (per engine)

Set in `rate_limiter.py` → `get_limiter(engine, max_requests, window_seconds)`.

| Lever | Current Value | What it does |
|-------|--------------|--------------|
| `max_requests` | 10 (default) | Requests allowed per window |
| `window_seconds` | 60.0 | Window duration |
| `JITTER_MIN/MAX` | 1.0-3.0s | Random delay between requests |
| `BACKOFF_BASE` | 30.0s | Initial backoff on 429/403 |
| Backoff formula | `base * 2^attempt + random(1,10)` | Exponential backoff |

## 6. Per-Engine Config (in engine files)

| Lever | Where | What it does |
|-------|-------|--------------|
| Search URL construction | `engines/*.py` | Query params, language, result count |
| CSS selectors | `engines/*.py` | DOM parsing for title/URL/snippet |
| Wait timeout | `tab.go_to(url, timeout=20)` | How long to wait for page load |
| Selector wait | `execute_script` polling | How long to wait for results to appear |

## 7. Humanized Interactions (pydoll built-in)

| Interaction | Method | What it does |
|-------------|--------|-------------|
| Click | `element.click(humanize=True)` | Bezier curve path, Fitts's Law timing, tremor, overshoot |
| Type | `element.type_text(text, humanize=True)` | Variable delays 30-120ms, ~2% typos, thinking pauses |
| Scroll | `scroll.by(distance, humanize=True)` | Easing curves, jitter ±3px, overshoot correction |

## 8. Context Isolation

| Feature | Method | Use case |
|---------|--------|----------|
| New Context | `context = await browser.new_context()` | Isolated cookies, cache, localStorage |
| Context Tab | `tab = await context.new_tab(url)` | Tab with context-specific isolation |
| Cookie Isolation | Automatic per context | Avoid tracking linkage across engines |

## 9. Request Interception (Fetch Domain)

| Method | What it does |
|--------|-------------|
| `tab.enable_fetch_events(handle_auth=True)` | Enable request interception |
| `tab.continue_request(request_id, headers, url)` | Forward with modified headers |
| `tab.abort_request(request_id, error_reason)` | Block request (tracking scripts) |
| `tab.fulfill_request(request_id, response_code, headers, body)` | Custom response |

## Key Finding: Pydoll Auto-Syncs Client Hints

**Pydoll automatically syncs UA + Client Hints when `--user-agent=` is set:**
1. Parses `--user-agent` arg to extract OS, browser, version
2. Calls CDP `Emulation.setUserAgentOverride()` with full metadata
3. Generates proper `Sec-CH-UA*` Client Hints matching UA
4. Injects JS property overrides for `navigator.vendor`, `navigator.appVersion`
5. Applies to initial tab AND all new tabs

**→ Client Hints are NOT the reason Google/Bing return 0.**

## Priority Fixes

### P0: Diagnose Google/Bing 0-results (root cause unknown)

Client Hints are auto-synced by pydoll. Possible causes:
1. **CSS selectors wrong** — Google changes DOM structure, selectors from training data may be stale
2. **IP still banned** from earlier SearXNG 270-request run
3. **Consent banner** blocking results page
4. **Headless detection** — use `--headless=new` (modern headless, harder to detect)

**Debug approach:** Run headed (`SEARXNG_HEADED=1`), screenshot what Google shows.

### P1: Missing Launch Options (add to browser.py)
```python
options.add_argument('--lang=en-US')
options.add_argument('--no-first-run')
options.add_argument('--no-default-browser-check')
# Modern headless (Chrome 109+, harder to detect):
# options.headless = False; options.add_argument('--headless=new')
```

### P2: Browser Preferences (add to browser.py)
```python
options.browser_preferences = {
    'profile': {
        'created_by_version': '146.0.7680.154',
        'creation_time': str(int(time.time()) - 60*86400),  # 60 days ago
        'exit_type': 'Normal',
        'exited_cleanly': True,
    },
    'safebrowsing': {'enabled': True},
    'autofill': {'enabled': True},
    'search': {'suggest_enabled': True},
    'enable_do_not_track': False,
    'credentials_enable_service': True,
    'intl': {'accept_languages': 'en-US,en'},
}
```

### P3: Additional JS Patches
- `navigator.languages = ["en-US", "en"]`
- `navigator.platform = "MacIntel"`
- `navigator.hardwareConcurrency = 10`
- `navigator.deviceMemory = 8`

### P4: Per-Engine Context Isolation
Use `browser.new_context()` instead of `browser.new_tab()` to get isolated cookie jars per engine. Prevents cross-engine tracking.
