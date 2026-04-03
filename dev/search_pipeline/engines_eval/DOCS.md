# engines_eval/

Engine evaluation and fingerprint investigation scripts for the search pipeline.

Maps to: `decisions/search01_engines.md` (engine status) and `decisions/search02_routing.md` (fingerprint/suspension investigation).

All scripts write reports to `20_reports/` (scripts 20–24 share this output directory).

## 01_engines.py → decisions/search01_engines

**Purpose:** Run all test queries against SearXNG API with profile-based parameters and generate markdown report.
**Input:** `queries.txt` + `profiles.yml` (in pipeline root).
**Output:** Markdown report in `01_reports/` with timestamp.

```bash
# Standard run
./venv/bin/python dev/search_pipeline/engines_eval/01_engines.py

# A/B compare mode
./venv/bin/python dev/search_pipeline/engines_eval/01_engines.py --compare
```

## 20_tls_fingerprint.py → decisions/search02_routing

**Purpose:** Probe external JA3 fingerprint services to measure the TLS fingerprint of SearXNG-style httpx requests. Mimics `get_sslcontexts()` + `shuffle_ciphers()` to determine the JA3 hash that search engines see.
**Input:** No CLI args. Queries tls.browserleaks.com and ja3er.com.
**Output:** Markdown report in `20_reports/` with JA3 hash, TLS version, cipher count, User-Agent per service.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/20_tls_fingerprint.py
```

## 21_cipher_shuffle_verify.py → decisions/search02_routing

**Purpose:** Verify that SearXNG's `shuffle_ciphers()` produces distinct JA3 hashes across requests — confirms TLS fingerprint diversification is active. Sends 12 requests with fresh SSL context per request.
**Input:** No CLI args. Uses tls.browserleaks.com.
**Output:** Markdown report in `20_reports/` with per-request JA3 table, unique hash count, and verdict.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/21_cipher_shuffle_verify.py
```

**Key metric:** Unique JA3 hashes observed / total requests. Expected: 12/12 unique (shuffle works).

## 22_header_inspection.py → decisions/search02_routing

**Purpose:** Inspect which HTTP headers SearXNG-style requests send, as seen by the receiving server. Identifies header gaps vs. real browser fingerprint (e.g., missing `Accept: */*`).
**Input:** No CLI args. Sends 3 requests to httpbin.org/headers.
**Output:** Markdown report in `20_reports/` with per-request header tables and consistency analysis.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/22_header_inspection.py
```

## 23_suspension_threshold.py → decisions/search02_routing

**Purpose:** Measure at which query rate each engine gets suspended by SearXNG's internal suspension mechanism. Tests 8 engines across 4 escalating-frequency phases.
**Input:** No CLI args. Queries local SearXNG at `http://localhost:8080`.
**Output:** Markdown report in `20_reports/` with suspension threshold per engine and per-phase detail tables.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/23_suspension_threshold.py
```

**Phases:** 10s×6, 5s×6, 2s×6, 1s×6 per engine. 60s cooldown between engines.

## 23_google_retest.py → decisions/search02_routing

**Purpose:** One-shot retest of Google after `suspension_times=0` and `ban_time_on_fail=0` were set in `settings.yml`. Verifies SearXNG no longer pre-emptively marks Google as unresponsive.
**Input:** No CLI args. Runs same 4-phase protocol, Google only.
**Output:** Markdown report in `20_reports/` with verdict (suspension flag present/absent) and per-request + phase summary tables.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/23_google_retest.py
```

## 24_engine_health_check.py → decisions/search01_engines

**Purpose:** Phase-1-only (conservative 10s interval) health check for engines that were previously suspended, run after SearXNG 2026.4.3 update. Confirms recovery without full 4-phase stress test.
**Input:** No CLI args. Tests: Brave, Mojeek, Startpage, Google Scholar, Semantic Scholar, CrossRef.
**Output:** Markdown report in `20_reports/` with summary table (clean/flagged/status) and per-engine detail.

```bash
./venv/bin/python dev/search_pipeline/engines_eval/24_engine_health_check.py
```

**Phase config:** 10s × 6 queries per engine, 30s cooldown between engines.
