# INFRASTRUCTURE
import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path

from src.search.result import SearchResult

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".cache" / "searxng"
DEFAULT_TTL = 3600  # 1 hour


# FUNCTIONS

# SHA-256 hex of canonical input string, first 16 chars
# modifier_id is appended when set (e.g. 'books' for --books, future 'pdf' for --pdf/x4f).
# modifier_id=None is backward-compatible — produces identical hash to pre-modifier callers.
def cache_key(
    query: str,
    language: str,
    engines: str | None,
    time_range: str | None,
    class_filter: frozenset[str] | None = None,
    modifier_id: str | None = None,
) -> str:
    cf = "|".join(sorted(class_filter)) if class_filter else ""
    mid = f"|{modifier_id}" if modifier_id else ""
    canonical = f"{query.lower().strip()}|{language}|{engines or ''}|{time_range or ''}|{cf}{mid}"
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ~/.cache/searxng/<key>.json
def cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


# Atomic write via temp file + rename
def cache_write(
    key: str,
    ranked: list[SearchResult],
    query: str,
    language: str,
    engines: str | None,
    time_range: str | None,
    snippet_sources: dict[str, str] | None = None,
    slot_counts: dict | None = None,
    snippet_texts: dict[str, str] | None = None,
    og_meta: dict[str, dict] | None = None,
) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "query": query,
        "language": language,
        "engines": engines,
        "time_range": time_range,
        "timestamp": int(time.time()),
        "returned_count": len(ranked),
        "slot_counts": slot_counts,
        "urls": [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "engines": r.engines,
                "snippets": r.snippets,
                "snippet_source": snippet_sources.get(r.url) if snippet_sources else None,
                "snippet_display": snippet_texts.get(r.url) if snippet_texts else None,
                "og":   (og_meta.get(r.url) or {}).get("og")   if og_meta else None,
                "meta": (og_meta.get(r.url) or {}).get("meta") if og_meta else None,
            }
            for r in ranked
        ],
    }
    target = cache_path(key)
    fd, tmp = tempfile.mkstemp(dir=CACHE_DIR, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, target)
        logger.debug("Cache written: %s (%d urls)", target, len(ranked))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# Read cache if exists and not expired (mtime-based). Returns dict or None on miss/expiry.
def cache_read(key: str, ttl_seconds: int = DEFAULT_TTL) -> dict | None:
    path = cache_path(key)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > ttl_seconds:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Cache read error %s: %s", path, e)
        return None


# Format a slice of cached url-dicts as a numbered plain-text list
def format_cached_slice(urls: list[dict], start_index: int) -> str:
    lines = []
    for i, entry in enumerate(urls, start_index + 1):
        lines.append(f"{i}. {entry['title']}")
        lines.append(f"   URL: {entry['url']}")
        snippet = entry.get("snippet", "")
        if snippet:
            lines.append(f"   Snippet: {snippet[:5000]}")
        lines.append("")
    return "\n".join(lines)
