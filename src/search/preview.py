# INFRASTRUCTURE
import asyncio
import dataclasses
import html
import logging
import re
import time

import httpx
from lxml import html as lxml_html

from src.search.result import SearchResult

logger = logging.getLogger(__name__)

PREVIEW_TOP_N = 20
PREVIEW_CONCURRENCY = 8
PREVIEW_TIMEOUT = 3.6
PREVIEW_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.7727.101 Safari/537.36"
    )
}


# ORCHESTRATOR

# Fetch og:description / meta:description for top-N results, attach preview field, skip rest; return (results, stats)
async def fetch_previews(results: list[SearchResult], top_n: int = PREVIEW_TOP_N) -> tuple[list[SearchResult], dict]:
    t0 = time.perf_counter()
    targets = results[:top_n]
    rest = results[top_n:]
    sem = asyncio.Semaphore(PREVIEW_CONCURRENCY)
    async with httpx.AsyncClient(
        timeout=PREVIEW_TIMEOUT,
        follow_redirects=True,
        headers=PREVIEW_HEADERS,
    ) as client:
        raw = await asyncio.gather(
            *[asyncio.wait_for(_fetch_one(client, sem, r.url), timeout=PREVIEW_TIMEOUT) for r in targets],
            return_exceptions=True,
        )
    urls_succeeded = sum(1 for p in raw if isinstance(p, dict))
    url_timeouts = sum(1 for p in raw if isinstance(p, asyncio.TimeoutError))
    total_ms = round((time.perf_counter() - t0) * 1000)
    out = []
    for r, p in zip(targets, raw):
        if isinstance(p, Exception) or p is None:
            out.append(r)
        else:
            out.append(dataclasses.replace(r, preview=p))
    stats = {
        "urls_attempted": len(targets),
        "urls_succeeded": urls_succeeded,
        "url_timeouts": url_timeouts,
        "total_ms": total_ms,
    }
    return out + rest, stats


# FUNCTIONS

# Iteratively unescape HTML entities until idempotent — handles double/triple-encoded entities
def _deep_unescape(s: str | None) -> str | None:
    if not s:
        return s
    while True:
        new = html.unescape(s)
        if new == s:
            return new
        s = new


# Fetch one URL with semaphore guard, extract og:description + meta:description, return dict or None on any failure
async def _fetch_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
) -> dict | None:
    async with sem:
        try:
            resp = await client.get(url)
            _ct = resp.headers.get("content-type", "")
            _m = re.search(r"charset=([^\s;,]+)", _ct, re.I)
            _enc = _m.group(1) if _m else "utf-8"
            tree = lxml_html.fromstring(resp.content, parser=lxml_html.HTMLParser(encoding=_enc))
            og = tree.xpath("string(//meta[@property='og:description']/@content)") or None
            meta = tree.xpath("string(//meta[@name='description']/@content)") or None
            if not og and not meta:
                return None
            return {"og": _deep_unescape(og), "meta": _deep_unescape(meta)}
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug("Preview fetch skipped %s: %s", url, e)
            return None
