#!/usr/bin/env python3

# INFRASTRUCTURE
import asyncio
import random
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

REPORTS_DIR = Path(__file__).parent / "20_reports"
NUM_REQUESTS = 12
DELAY_BETWEEN_REQUESTS = 2

JA3_SERVICE_NAME = "tls.browserleaks.com"
JA3_SERVICE_URL = "https://tls.browserleaks.com/json"

UA_TEMPLATE = "Mozilla/5.0 ({os}; rv:{version}) Gecko/20100101 Firefox/{version}"
UA_OS = ["Windows NT 10.0; Win64; x64", "X11; Linux x86_64"]
UA_VERSIONS = ["148.0", "147.0"]


# ORCHESTRATOR
def run_cipher_shuffle_verify():
    service_name, service_url = JA3_SERVICE_NAME, JA3_SERVICE_URL
    print(f"[*] Using service: {service_name}", file=sys.stderr)

    rows = []
    for i in range(1, NUM_REQUESTS + 1):
        print(f"[{i}/{NUM_REQUESTS}] Sending request with fresh cipher shuffle...", file=sys.stderr)
        row = asyncio.run(single_request(i, service_url))
        rows.append(row)
        status = row.get("ja3_hash") or row.get("error", "FAIL")
        print(f"    JA3: {status}", file=sys.stderr)
        if i < NUM_REQUESTS:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    report = build_report(rows, service_name)
    save_report(report)


# FUNCTIONS

# Shuffle ciphers like SearXNG: keep first 3, shuffle rest
def shuffle_ciphers(ssl_context: ssl.SSLContext) -> None:
    c_list = [cipher["name"] for cipher in ssl_context.get_ciphers()]
    sc_list, c_list = c_list[:3], c_list[3:]
    random.shuffle(c_list)
    ssl_context.set_ciphers(":".join(sc_list + c_list))


# Build a fresh SSL context with cipher shuffling applied (new per request)
def build_ssl_context() -> ssl.SSLContext:
    ctx = httpx.create_ssl_context()
    shuffle_ciphers(ctx)
    return ctx


# Return cipher names list from an SSL context
def get_cipher_names(ctx: ssl.SSLContext) -> list[str]:
    return [c["name"] for c in ctx.get_ciphers()]


# Generate a random Firefox User-Agent matching SearXNG's gen_useragent()
def gen_useragent() -> str:
    os_str = random.choice(UA_OS)
    version = random.choice(UA_VERSIONS)
    return UA_TEMPLATE.format(os=os_str, version=version)


# Make a single request with a freshly-created httpx client and SSL context
async def single_request(req_num: int, url: str) -> dict:
    ssl_ctx = build_ssl_context()
    cipher_order = get_cipher_names(ssl_ctx)
    ua = gen_useragent()

    headers = {
        "User-Agent": ua,
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "DNT": "1",
        "Connection": "keep-alive",
    }

    for http2_enabled in (True, False):
        try:
            async with httpx.AsyncClient(
                http2=http2_enabled,
                verify=ssl_ctx,
                headers=headers,
                timeout=15.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                ja3 = data.get("ja3_hash") or data.get("ja3") or data.get("hash") or "N/A"
                return {
                    "req_num": req_num,
                    "ja3_hash": ja3,
                    "ja3_text": data.get("ja3_text") or data.get("ja3_string") or "N/A",
                    "cipher_order_first5": cipher_order[:5],
                    "http2_used": http2_enabled,
                    "success": True,
                }
        except Exception as e:
            last_error = str(e)
            if not http2_enabled:
                return {
                    "req_num": req_num,
                    "error": last_error,
                    "cipher_order_first5": cipher_order[:5],
                    "success": False,
                }
    return {"req_num": req_num, "error": "unreachable", "cipher_order_first5": cipher_order[:5], "success": False}


# Count unique JA3 hashes in result rows
def count_unique_hashes(rows: list) -> int:
    return len({r["ja3_hash"] for r in rows if r.get("success")})


# Determine if cipher shuffling changes JA3 fingerprint
def assess_verdict(rows: list, unique_count: int) -> str:
    successful = [r for r in rows if r.get("success")]
    if not successful:
        return "INCONCLUSIVE — all requests failed"
    if unique_count > 1:
        return f"YES — cipher shuffling produces {unique_count} distinct JA3 hashes across {len(successful)} requests"
    return "NO — all requests produced the same JA3 hash (cipher order does not affect JA3)"


# Build markdown report from request rows
def build_report(rows: list, service_name: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    successful = [r for r in rows if r.get("success")]
    unique_hashes = count_unique_hashes(rows)
    verdict = assess_verdict(rows, unique_hashes)

    lines = [
        "# Cipher Shuffle Verification Report",
        f"Date: {timestamp}",
        f"Service: {service_name}",
        f"Requests: {len(rows)} (successful: {len(successful)})",
        "",
        "## Verdict",
        "",
        f"**Does cipher shuffling change the JA3 hash?** {verdict}",
        "",
        "## Per-Request Results",
        "",
        "| Req# | JA3 Hash | First 5 Ciphers (shuffled order) |",
        "|------|----------|----------------------------------|",
    ]

    for r in rows:
        if r.get("success"):
            ciphers = ", ".join(r.get("cipher_order_first5", []))
            lines.append(f"| {r['req_num']} | `{r['ja3_hash']}` | {ciphers} |")
        else:
            lines.append(f"| {r['req_num']} | FAIL: {r.get('error', '')[:60]} | — |")

    lines += [
        "",
        "## JA3 Hash Summary",
        "",
        f"- Unique JA3 hashes observed: **{unique_hashes}**",
        f"- Total successful requests: **{len(successful)}**",
    ]

    if successful:
        hash_counts: dict = {}
        for r in successful:
            h = r["ja3_hash"]
            hash_counts[h] = hash_counts.get(h, 0) + 1
        lines += ["", "| JA3 Hash | Count |", "|----------|-------|"]
        for h, cnt in sorted(hash_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| `{h}` | {cnt} |")

    lines += [
        "",
        "## Method",
        "",
        "Each request creates a NEW `httpx.AsyncClient` with a freshly shuffled SSL context.",
        "SearXNG's `shuffle_ciphers()`: keeps first 3 ciphers fixed, shuffles remaining randomly.",
        "JA3 hash is determined by: TLS version + cipher list order + extensions + elliptic curves + EC point formats.",
    ]

    return "\n".join(lines)


# Save report to 20_reports directory
def save_report(report: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"cipher_shuffle_verify_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    run_cipher_shuffle_verify()
