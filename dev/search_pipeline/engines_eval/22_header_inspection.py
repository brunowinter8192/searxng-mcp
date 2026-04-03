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
NUM_REQUESTS = 3
DELAY_BETWEEN_REQUESTS = 2

HTTPBIN_URL = "https://httpbin.org/headers"

UA_TEMPLATE = "Mozilla/5.0 ({os}; rv:{version}) Gecko/20100101 Firefox/{version}"
UA_OS = ["Windows NT 10.0; Win64; x64", "X11; Linux x86_64"]
UA_VERSIONS = ["148.0", "147.0"]


# ORCHESTRATOR
def run_header_inspection():
    rows = []
    for i in range(1, NUM_REQUESTS + 1):
        print(f"[{i}/{NUM_REQUESTS}] Probing {HTTPBIN_URL}...", file=sys.stderr)
        row = asyncio.run(inspect_headers(i))
        rows.append(row)
        if row["success"]:
            print(f"    UA: {row.get('sent_user_agent', 'N/A')}", file=sys.stderr)
        else:
            print(f"    FAIL: {row.get('error', 'unknown')}", file=sys.stderr)
        if i < NUM_REQUESTS:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    report = build_report(rows)
    save_report(report)


# FUNCTIONS

# Shuffle ciphers like SearXNG: keep first 3, shuffle rest
def shuffle_ciphers(ssl_context: ssl.SSLContext) -> None:
    c_list = [cipher["name"] for cipher in ssl_context.get_ciphers()]
    sc_list, c_list = c_list[:3], c_list[3:]
    random.shuffle(c_list)
    ssl_context.set_ciphers(":".join(sc_list + c_list))


# Build a fresh SSL context with cipher shuffling applied
def build_ssl_context() -> ssl.SSLContext:
    ctx = httpx.create_ssl_context()
    shuffle_ciphers(ctx)
    return ctx


# Generate a random Firefox User-Agent matching SearXNG's gen_useragent()
def gen_useragent() -> str:
    os_str = random.choice(UA_OS)
    version = random.choice(UA_VERSIONS)
    return UA_TEMPLATE.format(os=os_str, version=version)


# Make one request to httpbin/headers and return all headers as seen by server
async def inspect_headers(req_num: int) -> dict:
    ua = gen_useragent()
    ssl_ctx = build_ssl_context()

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
                response = await client.get(HTTPBIN_URL)
                response.raise_for_status()
                data = response.json()
                server_headers = data.get("headers", {})
                return {
                    "req_num": req_num,
                    "success": True,
                    "http_version": response.http_version,
                    "http2_used": http2_enabled,
                    "status_code": response.status_code,
                    "sent_user_agent": ua,
                    "server_headers": server_headers,
                }
        except Exception as e:
            last_error = str(e)
            if not http2_enabled:
                return {
                    "req_num": req_num,
                    "success": False,
                    "error": last_error,
                    "sent_user_agent": ua,
                }
    return {"req_num": req_num, "success": False, "error": "unreachable", "sent_user_agent": ua}


# Check if a header value is consistent across all successful requests
def is_consistent(rows: list, header: str) -> str:
    vals = {r["server_headers"].get(header) for r in rows if r.get("success") and r.get("server_headers")}
    vals.discard(None)
    if not vals:
        return "absent"
    if len(vals) == 1:
        return f"constant: `{list(vals)[0]}`"
    return f"varies: {vals}"


# Build markdown report from header inspection rows
def build_report(rows: list) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    successful = [r for r in rows if r.get("success")]

    lines = [
        "# Header Inspection Report",
        f"Date: {timestamp}",
        f"Target: {HTTPBIN_URL}",
        f"Requests: {len(rows)} (successful: {len(successful)})",
        "",
        "## Headers As Seen By Server (Per Request)",
        "",
    ]

    for r in rows:
        lines.append(f"### Request {r['req_num']}")
        if r.get("success"):
            lines += [
                f"- HTTP Version: `{r.get('http_version')}`",
                f"- Status: {r.get('status_code')}",
                f"- Sent User-Agent: `{r.get('sent_user_agent')}`",
                "",
                "| Header | Value |",
                "|--------|-------|",
            ]
            for k, v in sorted(r.get("server_headers", {}).items()):
                lines.append(f"| `{k}` | `{v}` |")
        else:
            lines.append(f"FAILED: {r.get('error', 'unknown')}")
        lines.append("")

    if successful:
        lines += [
            "## Consistency Analysis",
            "",
            "| Header | Consistency |",
            "|--------|-------------|",
        ]
        all_keys: set = set()
        for r in successful:
            all_keys |= set(r.get("server_headers", {}).keys())
        for key in sorted(all_keys):
            consistency = is_consistent(successful, key)
            lines.append(f"| `{key}` | {consistency} |")

        lines += [
            "",
            "## Notable Findings",
            "",
            f"- HTTP/2 used: {'Yes' if successful[0].get('http_version') == 'HTTP/2' else 'No/Unknown'}",
            f"- User-Agent varies: {len({r.get('sent_user_agent') for r in successful}) > 1}",
            f"- DNT header present: {is_consistent(successful, 'Dnt')}",
            f"- Accept-Encoding: {is_consistent(successful, 'Accept-Encoding')}",
            f"- Cache-Control: {is_consistent(successful, 'Cache-Control')}",
        ]

    return "\n".join(lines)


# Save report to 20_reports directory
def save_report(report: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"header_inspection_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    run_header_inspection()
