# Custom Search Engine: Stealth & Detection Layers

Applies to: `src/search/` (pydoll-based custom engine) + `dev/search_pipeline/engines_eval/` (test suite)

## Status Quo (IST)

**Code:** `dev/search_pipeline/engines_eval/stealth_config.py` (global patches), `dev/search_pipeline/engines_eval/engine_selectors.py` (per-engine config)

### Detection Layers

Bot-Detection operiert auf mehreren Ebenen. Jede Suchmaschine nutzt eine andere Kombination.

| # | Ebene | Was geprüft wird | Unsere Stellschrauben | Status |
|---|-------|-------------------|----------------------|--------|
| 1 | **Browser-Fingerprint** | webdriver-Flag, WebGL vendor/renderer, Canvas Hash, navigator.plugins (leer in headless), chrome.runtime (fehlt in headless), Screen-Dimensionen, Permissions API, CSS media queries | `patch_webgl`, `patch_canvas_noise`, `patch_permissions`, `patch_computed_style`, Screen/Navigator-Overrides, `disable_blink_features=AutomationControlled`, `headless_new=True` | 2/5 Patches ON. chrome.runtime + navigator.plugins nicht implementiert |
| 2 | **Behavioral** | Request-Timing (zu schnell, zu regelmäßig), fehlende Mausbewegung/Scrolling, Klick-Muster | `humanize_click`, `humanize_type`, `humanize_scroll` | Alle OFF |
| 3 | **Session-Tracking** | Gleicher Browser/Cookies über Queries → Tracking, Cookie-Walls | `use_context` (frischer Browser-Context pro Query), `consent_cookie` Injection via CDP | use_context OFF bei allen Engines |
| 4 | **IP-Reputation** | Datacenter-IPs, VPN/Tor Exit-Nodes, bekannte Proxy-Listen | `proxy` per Engine (Tor socks5, direct, custom) | Nur Tor oder direct verfügbar. Keine residential Proxies. |
| 5 | **Rate-Limiting** | X Requests/Zeitfenster pro IP | `between_query_delay`, `settle_seconds` | Kein Delay = provoziert Blocking (gewollt für Tests) |
| 6 | **TLS/HTTP-Fingerprint** | JA3 Hash, HTTP/2 Frame-Order, Header-Order | Nicht steuerbar — Chrome ist Chrome. httpx-Engines haben anderen Fingerprint. | OK (Chrome TLS ist real) |
| 7 | **CAPTCHA** | PoW (Brave Svelte Slider), reCAPTCHA, hCaptcha als letzte Verteidigung | `captcha_detect_js` (erkennt, löst nicht), `captcha_path` (URL-basierte Erkennung) | Detect-only, kein Solving |

### Stellschrauben-Inventar

#### Global (stealth_config.py DEFAULT_CONFIG)

| Stellschraube | Ebene | Default | Effekt |
|---------------|-------|---------|--------|
| `headless_new` | Fingerprint | True ✅ | `--headless=new` — schwerer zu detecten als altes headless |
| `disable_blink_features` | Fingerprint | AutomationControlled ✅ | Entfernt `navigator.webdriver=true` Flag |
| `patch_computed_style` | Fingerprint | True ✅ | Fixt headless CSS color detection |
| `patch_webgl` | Fingerprint | False ❌ | WebGL vendor/renderer Override (Apple M1 Pro) |
| `patch_canvas_noise` | Fingerprint | False ❌ | Subtile Canvas-Fingerprint-Randomisierung |
| `patch_permissions` | Fingerprint | False ❌ | Permissions.query Override für Notifications |
| chrome.runtime masking | Fingerprint | NICHT IMPLEMENTIERT | chrome.runtime Object Spoofing |
| navigator.plugins spoofing | Fingerprint | NICHT IMPLEMENTIERT | Fake Plugin-Liste für headless |
| `humanize_click` | Behavioral | False ❌ | Menschenähnliche Klick-Muster |
| `humanize_type` | Behavioral | False ❌ | Menschenähnliches Tippen |
| `humanize_scroll` | Behavioral | False ❌ | Scroll mit Easing/Jitter |
| `set_useragent_override` | Fingerprint | False ❌ | CDP UA Override |
| `block_urls` | Behavioral | None | Tracking/Analytics blockieren |

#### Per-Engine (engine_selectors.py config dict)

| Stellschraube | Ebene | Effekt |
|---------------|-------|--------|
| `proxy` | IP-Reputation | None (direkt), socks5 (Tor), oder custom Proxy URL |
| `settle_seconds` | Behavioral | DOM-Wartezeit nach Navigation (gibt JS Zeit zum Rendern) |
| `use_context` | Session | Frischer Browser-Context pro Query (Cookie-Isolation) |
| `captcha_detect_js` | CAPTCHA | JS das truthy returned wenn CAPTCHA präsent |
| `between_query_delay` | Rate-Limiting | Pause zwischen Queries (Sekunden) |
| `consent_cookie` | Session | Cookie-Injection via CDP vor Navigation |

### Engine-Status (Stresstest 2026-04-07)

| Engine | Score | Hauptproblem | Erkennungsebene | Routing |
|--------|-------|-------------|-----------------|---------|
| Google | 30/30 ✅ | — | — | direct, consent_cookie |
| Bing | 30/30 ✅ | — | — | direct |
| CrossRef | 30/30 ✅ | — | — | httpx API |
| Mojeek | 15/30 ⚠️ | Block ab Query 16 | Rate-Limiting (IP) | direct |
| DuckDuckGo | 6/30 ⚠️ | Bing-Redirect | Package-Bug (ddgs) | httpx |
| Brave | 1/30 ❌ | PoW CAPTCHA ab Query 2 | Fingerprint + Rate-Limiting | direct (Tor = 0/30) |
| Startpage | 0/30 ❌ | Zero results, kein Error | Unklar | direct |
| Google Scholar | 0/0 ❌ | Engine-Crash | Unklar | direct |
| Semantic Scholar | 3/30 ❌ | 429 Rate-Limit | Rate-Limiting (API) | httpx API |

### Google vs Brave — Warum gleiche Config, unterschiedliches Ergebnis

Google 30/30 und Brave 1/30 nutzen identische Stealth-Config (DEFAULT_CONFIG). Unterschied:
- Google: Consent-Cookie löst Cookie-Wall → kein Blocker. Minimale Stealth reicht. Google setzt auf reCAPTCHA (/sorry/) erst bei hohem Traffic.
- Brave: Kein Consent-Problem, aber aggressivere Fingerprint-Detection. PoW CAPTCHA ab Query 2 trotz headless_new + AutomationControlled. Brave prüft vermutlich tiefere Fingerprint-Signale (WebGL, Canvas, chrome.runtime, navigator.plugins).

## Evidenz

### Brave PoW CAPTCHA (2026-04-07)
- Screenshot: "Confirm you're a human being / I'm not a robot" Dialog mit "Learn more about Proof of Work Captcha"
- Svelte-basierter Slider CAPTCHA — kein einfacher Button-Click
- Tritt ab Query 2 auf (Query 1 liefert 23 Results)
- Mit Tor-Proxy: 0/30 (Tor Exit-Nodes auf Blocklist)
- captcha_detect_js Selektor (`dialog .captcha-card`) matcht nicht das tatsächliche DOM

### puppeteer-extra-plugin-stealth Vergleich (2026-04-07)
- Fehlende Patches vs. puppeteer-extra: chrome.runtime Masking, navigator.plugins Spoofing
- Quelle: GitHub puppeteer-extra-plugin-stealth Source

### Mojeek Rate-Limit (2026-04-09)
- Exakt 15 Requests pro ~60s Sliding Window
- Ab Request 16: 403 "automated queries"
- Unabhängig von Sprache (Deutsch war Red Herring)
- IP-basiert (use_context + Browser-Rotation helfen nicht)

## Recommendation (SOLL)

### Brave — Stealth-Patch-Evaluation ausstehend

Pending — folgende Patches müssen einzeln getestet werden (eine Variable pro 30-Query-Run):
1. patch_webgl=True
2. patch_canvas_noise=True
3. patch_permissions=True
4. chrome.runtime Masking (implementieren + testen)
5. navigator.plugins Spoofing (implementieren + testen)

Ziel: Messen welche Patches die CAPTCHA-Schwelle hochsetzen (von 1/30 auf X/30).

### Andere Engines

Pending — Evaluation nicht abgeschlossen.

## Offene Fragen

- Brave: Ist das Problem rein Fingerprint-basiert, oder Fingerprint + IP-Rate-Limit Kombination? (Stealth-Patches könnten den Fingerprint-Score verbessern → höhere Rate-Limit-Schwelle)
- Brave captcha_detect_js: Falscher Selektor — muss aus DOM-Dump korrigiert werden
- Startpage: Root Cause komplett unklar (0/30, kein Error)
- Google Scholar: Engine-Crash Root Cause unklar
- Residential Proxies als Alternative zu Tor: Nicht verfügbar, aber wäre optimale IP-Rotation

## Quellen

- `dev/search_pipeline/engines_eval/stealth_config.py` — Patch-Implementierung
- `dev/search_pipeline/engines_eval/engine_selectors.py` — Per-Engine Config
- `dev/search_pipeline/engines_eval/28_reports/stress_20260407_184152.md` — Stresstest Baseline
- puppeteer-extra-plugin-stealth (GitHub) — Fehlende Patch-Analyse
- pydoll GitHub Source + Docs — Stealth-Capabilities
