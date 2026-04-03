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

JA3_SERVICES = [
    ("tls.browserleaks.com", "https://tls.browserleaks.com/json"),
    ("ja3er.com", "https://ja3er.com/json"),
]

UA_TEMPLATE = "Mozilla/5.0 ({os}; rv:{version}) Gecko/20100101 Firefox/{version}"
UA_OS = ["Windows NT 10.0; Win64; x64", "X11; Linux x86_64"]
UA_VERSIONS = ["148.0", "147.0"]


# ORCHESTRATOR
def run_tls_fingerprint():
    results = []
    for service_name, url in JA3_SERVICES:
        print(f"[*] Trying {service_name}...", file=sys.stderr)
        result = asyncio.run(probe_ja3_service(url, service_name))
        results.append(result)
        if result["success"]:
            print(f"    OK: JA3={result.get('ja3_hash', 'N/A')}", file=sys.stderr)
        else:
            print(f"    FAIL: {result.get('error', 'unknown')}", file=sys.stderr)
        time.sleep(2)

    report = build_report(results)
    save_report(report)


# FUNCTIONS

# Shuffle ciphers like SearXNG: keep first 3, shuffle rest
def shuffle_ciphers(ssl_context: ssl.SSLContext) -> None:
    c_list = [cipher["name"] for cipher in ssl_context.get_ciphers()]
    sc_list, c_list = c_list[:3], c_list[3:]
    random.shuffle(c_list)
    ssl_context.set_ciphers(":".join(sc_list + c_list))


# Build an httpx SSLContext with SearXNG cipher shuffling applied
def build_ssl_context() -> ssl.SSLContext:
    ctx = httpx.create_ssl_context()
    shuffle_ciphers(ctx)
    return ctx


# Generate a random Firefox User-Agent matching SearXNG's gen_useragent()
def gen_useragent() -> str:
    os_string = random.choice(UA_OS)
    version = random.choice(UA_VERSIONS)
    return UA_TEMPLATE.format(os=os_string, version=version)


# Probe a JA3 fingerprint service and return parsed result dict
async def probe_ja3_service(url: str, service_name: str) -> dict:
    ua = gen_useragent()
    ssl_ctx = build_ssl_context()
    cipher_list = [c["name"] for c in ssl_ctx.get_ciphers()]

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
                return {
                    "service": service_name,
                    "url": url,
                    "success": True,
                    "status_code": response.status_code,
                    "http_version": response.http_version,
                    "http2_used": http2_enabled,
                    "ja3_hash": data.get("ja3_hash") or data.get("ja3") or data.get("hash"),
                    "ja3_text": data.get("ja3_text") or data.get("ja3_string"),
                    "tls_version": data.get("tls_version") or data.get("tls"),
                    "user_agent": ua,
                    "cipher_count": len(cipher_list),
                    "first_3_ciphers": cipher_list[:3],
                    "raw": data,
                }
        except Exception as e:
            last_error = str(e)
            if not http2_enabled:
                return {
                    "service": service_name,
                    "url": url,
                    "success": False,
                    "error": last_error,
                    "user_agent": ua,
                    "cipher_count": len(ssl_ctx.get_ciphers()),
                }
    return {"service": service_name, "url": url, "success": False, "error": "unreachable"}


# Build markdown report from probe results
def build_report(results: list) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# TLS Fingerprint Report",
        f"Date: {timestamp}",
        "",
        "## JA3 Service Results",
        "",
        "| Service | Status | HTTP Version | JA3 Hash | TLS Version |",
        "|---------|--------|-------------|----------|-------------|",
    ]

    for r in results:
        status = "OK" if r["success"] else f"FAIL: {r.get('error', '')[:60]}"
        ja3 = r.get("ja3_hash") or "N/A"
        tls = r.get("tls_version") or "N/A"
        http_ver = r.get("http_version") or "N/A"
        lines.append(f"| {r['service']} | {status} | {http_ver} | {ja3} | {tls} |")

    lines += ["", "## Request Configuration", ""]
    for r in results:
        if r["success"]:
            lines += [
                f"### {r['service']}",
                f"- User-Agent: `{r.get('user_agent', 'N/A')}`",
                f"- Cipher count: {r.get('cipher_count', 'N/A')}",
                f"- First 3 ciphers (fixed): {r.get('first_3_ciphers', [])}",
                f"- JA3 text: `{r.get('ja3_text') or 'N/A'}`",
                f"- Raw response: `{r.get('raw', {})}`",
                "",
            ]

    lines += [
        "## Method",
        "",
        "Requests made via `httpx` with HTTP/2, mimicking SearXNG's `get_sslcontexts()`:",
        "- `shuffle_ciphers()`: keep first 3 ciphers fixed, shuffle remainder randomly",
        "- User-Agent: random Firefox 147/148 on Windows or Linux",
        "- Headers: Accept-Encoding, Cache-Control: no-cache, DNT: 1, Connection: keep-alive",
    ]

    return "\n".join(lines)


# Save report to 20_reports directory
def save_report(report: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"tls_fingerprint_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    run_tls_fingerprint()
