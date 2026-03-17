# Search Pipeline Step 2: Routing & Proxy

## Status Quo

**Code:** `src/searxng/settings.yml` — `outgoing` + per-Engine `proxies`/`using_tor_proxy`
**Method:** Split-Routing: Default Tor, Ausnahmen direkt für Engines die Tor-Exit-Nodes blockieren

### Globaler Tor-Default

```yaml
outgoing:
  request_timeout: 5.0
  max_request_timeout: 15.0
  proxies:
    all://:
      - socks5h://tor:9150
  using_tor_proxy: true
  extra_proxy_timeout: 10
```

### Per-Engine Routing

**DIREKT (Tor-Bypass via `proxies: {}` + `using_tor_proxy: false`):**

| Engine | Kategorie | Grund |
|--------|-----------|-------|
| Google | general | Blockiert Tor-Exit-Nodes (CAPTCHA/403) |
| Bing | general | Blockiert Tor-Exit-Nodes wie Google |
| DuckDuckGo | general | Blockiert Tor-Exit-Nodes (Bing-Backend) |
| Mojeek | general | Kleinere Engine, Tor-Exit-Nodes vermutlich geblockt |

**TOR (erbt globalen Default — kein Override nötig):**

| Engine | Kategorie | Grund |
|--------|-----------|-------|
| Brave | general | Toleriert Tor, profitiert von IP-Rotation |
| Startpage | general | Google-Proxy über Tor, IP-Rotation |
| Google Scholar | general | API-Endpunkt, seltener Tor-Blocking als Consumer-Google |
| Semantic Scholar | general | API-basiert, kein Tor-Blocking bekannt |
| CrossRef | general | API-basiert, kein Tor-Blocking |
| ArXiv | plugin | API-basiert, kein Tor-Blocking |
| GitHub | plugin | API-basiert |
| Reddit | plugin | Scraper, Tor-Kompatibilität ungetestet |

### Suspension Times

| Fehlertyp | Sperrzeit |
|-----------|-----------|
| SearxEngineAccessDenied | 600s (10 min) |
| SearxEngineCaptcha | 600s (10 min) |
| SearxEngineTooManyRequests | 300s (5 min) |
| cf_SearxEngineCaptcha (Cloudflare) | 1800s (30 min) |
| cf_SearxEngineAccessDenied | 600s (10 min) |
| recaptcha_SearxEngineCaptcha | 3600s (60 min) |

### Timeout-Kaskade

- `request_timeout: 5.0` — normaler Engine-Timeout
- `max_request_timeout: 15.0` — absolutes Maximum
- `extra_proxy_timeout: 10` — zusätzlicher Buffer für Tor-Latenz
- `timeout: 10` auf Google Scholar — Scholar-spezifischer Override

## Evidenz

### Tor-Exit-Nodes — Aggressive Blockierung
Google, Bing, DuckDuckGo und wahrscheinlich Mojeek blockieren bekannte Tor-Exit-Nodes zuverlässig mit CAPTCHA oder sofortigem 403. Direktverbindung ist die einzige funktionierende Option. Per-Engine `proxies: {}` und `using_tor_proxy: false` überschreiben den globalen Tor-Default.

**CRITICAL:** Beide Felder müssen gesetzt werden. `using_tor_proxy: false` allein deaktiviert nur die Tor-Verification, nicht den Proxy. `proxies` wird unabhängig von `using_tor_proxy` aus `outgoing.proxies` geerbt (SearXNG network.py initialize function).

### Brave + Startpage — Tor-Benefit
Brave und Startpage blockieren keine Tor-Exit-Nodes. Tor-Routing bietet IP-Rotation bei Rate-Limiting und verhindert Session-Tracking über Queries hinweg.

### API-Engines — Tor unproblematisch
Semantic Scholar, CrossRef, ArXiv und GitHub nutzen offizielle APIs. Diese blockieren in der Regel keine Tor-Exit-Nodes, da sie für programmatischen Zugriff ausgelegt sind. Tor bietet hier zusätzlichen Anonymitäts-Schutz ohne Nachteil.

### Reddit — Ungetestet
Reddit Engine ist ein Scraper (nicht API). Tor-Kompatibilität muss empirisch getestet werden. Fallback: `proxies: {}` + `using_tor_proxy: false` wenn Tor-Blocking auftritt.

### extra_proxy_timeout
Tor-Routing fügt ~1-3s Latenz pro Hop hinzu. `extra_proxy_timeout: 10` erweitert das effektive Timeout für Tor-Engines, ohne den normalen `request_timeout` zu erhöhen.

### Suspension Times — Cloudflare-Sonderbehandlung
Cloudflare-geschützte Sites haben aggressiveres Rate-Limiting. 1800s (30 min) für `cf_SearxEngineCaptcha` verhindert wiederholtes Triggern. recaptcha = härtester Blocker → 3600s.

## Entscheidung

Split-Routing-Architektur: **Default Tor, Ausnahmen direkt.** Rationale:
- Globaler Tor-Default schützt alle Engines mit IP-Rotation ohne Einzelkonfiguration
- Gezielter Bypass für 4 Engines (Google, Bing, DDG, Mojeek) die Tor blockieren
- API-basierte Engines (Scholar, Semantic Scholar, CrossRef, ArXiv, GitHub) profitieren von Tor ohne Nachteile
- Reddit-Engine als Scraper noch ungetestet — bei Problemen auf DIREKT umstellen
- Tor-Container läuft als Docker-Service (`tor:9150`), keine externe Abhängigkeit

## Offene Fragen

- Reddit via Tor: Empirisch testen ob Reddit-Scraper über Tor funktioniert
- Google Scholar via Tor: Nicht explizit getestet ob Scholar Tor-Exit-Nodes blockiert
- Startpage via Tor: Startpage ist ein Google-Proxy — unklar ob Google-Sperren durchschlagen
- Mojeek Tor: ANNAHME dass Tor geblockt wird (nicht verifiziert). Bei Bedarf testen.
- Tor-Container Failover: Kein Fallback wenn Tor-Container down — alle Tor-Engines fallen gleichzeitig aus

## Quellen

- `src/searxng/settings.yml` — Routing-Konfiguration
- `searxng/searxng` GitHub Repo (`searx/network.py`) — Proxy-Inheritance-Logik
- SearXNG Docs (RAG Collection: searxng) — outgoing, proxy, suspended_times Parameter
- search01_engines.md — Engine-Auswahl und Kategorie-Zuordnung
