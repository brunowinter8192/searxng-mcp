# Scrape Pipeline Step 2: Content Filtering

## Status Quo

**Code:** `src/scraper/scrape_url.py` — `scrape_url_workflow`, `scrape_url_raw_workflow`, `truncate_content`

**Method:** PruningContentFilter mit fit_markdown-Fallback auf raw_markdown

**Config:**
- `scrape_url_workflow`: `PruningContentFilter(threshold=0.48)` + `fit_markdown`
  - Fallback auf `raw_markdown` wenn `fit_markdown < MIN_CONTENT_THRESHOLD` (200 chars)
  - `DEFAULT_MAX_CONTENT_LENGTH = 15000` chars
  - Truncation an Absatzgrenze (`\n\n`) wenn `last_newline > max_length * 0.8`
- `scrape_url_raw_workflow`: `DefaultMarkdownGenerator()` ohne Filter + `raw_markdown`
  - Speichert mit `<!-- source: URL -->` Header in Datei
  - Kein Truncation (für Dev/Suite-Verwendung)
- `COOKIE_CONSENT_SELECTOR`: CSS-Selektor-Liste für DOM-Elemente vor dem Crawl entfernen
  - CookieYes: `cky-consent`, `cky-banner`, `cky-modal`
  - OneTrust: `onetrust-*`
  - Cookiebot: `CookiebotDialog`, `CookiebotWidget`
  - Generisch: `cc-banner`, `cc-window`, `gdpr`, `cookie-banner/consent/notice/law`

`PruningContentFilter` entfernt Blöcke mit niedrigem Informationsgehalt (Navigation, Footer, Werbung) anhand eines Scoring-Algorithmus. `fit_markdown` ist das gefilterte Ergebnis, `raw_markdown` der ungefilterte HTML-zu-Markdown-Output.

## Evidenz

### Session-Findings (2026-03)
- `cky-modal` fehlte initial in `COOKIE_CONSENT_SELECTOR` — führte zu ~12K chars CookieYes-Consent-Wall als Content
- TDS (Towards Data Science) Cookie-Wall wurde durch den Selector nicht vollständig eliminiert — `is_garbage_content()` hat als zweite Verteidigungslinie gegriffen
- `fit_markdown`-Fallback auf `raw_markdown` rettet Short-Pages (z.B. simple API-Docs, One-Pager)

### Crawl4AI Docs
- `PruningContentFilter(threshold=0.48)`: Blöcke unterhalb des Scores werden entfernt. Höherer Threshold = aggressivere Filterung
- Bekannte Limitation: PruningFilter kann Code-Blöcke zerstören, wenn sie als "low-density" eingestuft werden (wenig natürliche Sprache)
- `DefaultMarkdownGenerator()` ohne Filter: vollständiger HTML→Markdown, kein Scoring — für Dev-Suites sinnvoller als für Live-MCP
- `content_source`-Option in `CrawlerRunConfig`: alternative Quelle (z.B. `fit_html`, `cleaned_html`) statt Markdown-Pipeline

### Truncation-Logik
- 15000 chars entspricht ~3750 Wörtern — ausreichend für die meisten Artikel, vermeidet Context-Window-Overflow im MCP
- Absatzgrenze-Truncation (`\n\n` wenn > 80% der Grenze) verhindert mid-sentence cuts

### Empirical Sweep (2026-05)

`dev/scrape_pipeline/04_overview_sweep/` — 36 configs × 20 URLs (Q24 search-result set across 5 page shapes: Blog / Paper-Landing / Forum-Thread / Repo-Heavy-Chrome / Index-Aggregator). Diff against clean-raw baseline (raw scrape + dev-only cleanup script).

Asymmetric preference frame: chrome retention is much worse than content loss. Quality > quantity. Filter must strip noise even at cost of some content detail, as long as title + general message preserved.

Per-config median F1 across 17 analyzed URLs (PDF stubs + scrape-failures excluded):

| Filter / source | F1 | Note |
|---|---|---|
| `none + cleaned_html` | 0.98 | quasi identical to clean-raw, no size reduction |
| `prune_030 + cleaned_html` | 0.89 | lenient, residual chrome (Skip-link visible on some sites) |
| **`prune_048 + cleaned_html`** (current prod) | **0.75** | **empirically optimal for asymmetric preference** |
| `prune_060 + cleaned_html` | 0.60 | aggressive, drops title text on short-title pages (e.g. webscraping.fyi shows `# ` empty header) |
| `prune_075 + cleaned_html` | 0.47 | title text gone, only body prose remains |
| `bm25 + *` | 0.05 | unusable for general overview — query-snippet extractor only |
| `* + fit_html` | 0.44 (constant) | anomaly: `fit_html` source is always-pre-filtered regardless of additional filter, not a useful tuning knob |

Per-shape break: `none + cleaned_html` wins on Blog/Forum/Index, `prune_030+` wins on Paper-Landing + Repo-Heavy-Chrome. Single-config trade-off: prune_048 most consistent across shapes for the noise-removal preference.

Cookies vs cookies+sphinx selectors: no measurable difference on this URL set (≤ 0.01 F1 delta).

**Closes 3 of 5 open questions:**
- threshold validation: prune_048 confirmed empirically optimal (asymmetric metric: precision over recall)
- content_source="fit_html": NOT useful (always-pre-filtered anomaly)
- 0.48 vs alternatives: 0.30 retains chrome, 0.60+ damages titles → 0.48 is sweetspot

## Entscheidung

`PruningContentFilter(threshold=0.48)` als Standard: reduziert Boilerplate erheblich und hält Context klein. Threshold 0.48 ist empirisch — niedrig genug, um echten Content zu behalten, hoch genug, um Navigation/Footer zu entfernen.

`raw_markdown`-Fallback bei < 200 chars: sichert Short-Pages, wo der Filter zu aggressiv filtert.

`COOKIE_CONSENT_SELECTOR` als DOM-Intervention vor dem Crawl: entfernt Cookie-Walls auf DOM-Ebene, bevor Crawl4AI den Content verarbeitet — zuverlässiger als Post-Processing.

`scrape_url_raw` bewusst ohne Filter: Dev-Suites und Vergleiche brauchen den Roh-Output, keine Filterung.

## Offene Fragen

- ~~Threshold 0.48 nicht durch systematische Tests belegt~~ → DONE 2026-05: Sweep bestätigt empirisch optimal für asymmetrische Noise-Removal-Präferenz
- ~~`content_source="fit_html"` als Alternative~~ → RULED OUT 2026-05: always-pre-filtered Anomalie, nicht als tuning-knob nutzbar
- Code-Seiten (GitHub, Docs): PruningFilter destruktiv für Code-Blöcke — `scrape_url_raw` (Mode 1) als Alternative für Code-heavy Sites bestätigt; Mode 1 + cleanup-Skill ist der Indexing-Pfad
- Cookie-Consent via `excluded_selector` entfernt den DOM-Node, aber manchmal bleibt ein Overlay-Backdrop — JS-basierte Dismissal wäre robuster
- `MIN_CONTENT_THRESHOLD` (200 chars) ggf. zu niedrig — 200 chars kann auch ein valider Error-Text sein
- **15K cap removal pending (2026-05-06 user direction)** — `DEFAULT_MAX_CONTENT_LENGTH = 15000` strippt 95% von long-form articles (seirdy.one 226K → 14K), verzerrt empirische Vergleiche. Removal via Prod-Migration-Bead nach pfk (Paper Mode) sequenziert.
- **Per-shape filter dispatch?** — Sweep zeigte: Blog/Forum/Index profitieren von less filtering (none/prune_030), Paper-Landing/Repo profitieren von prune_048+. Single-config = Trade-off. Per-shape dispatch wäre konsistenter, würde aber eigene Shape-Detection-Logik vor dem Filter brauchen (Komplexität vs Crawl4AI's eingebauter Filter alone)

## Quellen

- `src/scraper/scrape_url.py` (Code-Inspektion)
- Crawl4AI Docs (RAG Collection: Crawl4AIDocs) — PruningContentFilter, DefaultMarkdownGenerator, content_source
- Session-Findings: CookieYes cky-modal Fix, TDS Cookie-Wall, Truncation-Logik

### Zum Indexieren (für systematische Verbesserung)

- Crawl4AI GitHub Issues "PruningContentFilter" — Threshold-Tuning, Code-Block-Destruction: https://github.com/unclecode/crawl4ai/issues?q=pruning+filter
- Crawl4AI Content Filter Source — PruningContentFilter Algorithmus: https://github.com/unclecode/crawl4ai/blob/main/crawl4ai/content_filter_strategy.py
- Trafilatura Docs — Alternative Content-Extraction (Benchmark-Vergleich): https://trafilatura.readthedocs.io/
- Mozilla Readability — Reference Content-Extraction-Algorithmus: https://github.com/mozilla/readability
- CookieYes Developer Docs — DOM-Struktur, Klassen-Konventionen: https://www.cookieyes.com/documentation/
