"""Tests for query_logger + per-engine stats capture in search_web_workflow.

Runs without network: mock engines return fixed results immediately.
Uses tmp_path to redirect LOG_PATH so production log is never touched.
"""
import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_engine(name: str, results: list, delay: float = 0.0):
    """Mock engine with .name and async .search()."""
    eng = MagicMock()
    eng.name = name

    async def _search(query, language, max_results):
        if delay:
            await asyncio.sleep(delay)
        return results

    eng.search = _search
    return eng


def _fake_result(url: str = "https://example.com", title: str = "T", snippet: str = "S", engine: str = "mock"):
    from src.search.result import SearchResult
    return SearchResult(url=url, title=title, snippet=snippet, engine=engine, position=1)


# ---------------------------------------------------------------------------
# test_log_query_writes_jsonl
# ---------------------------------------------------------------------------

def test_log_query_writes_jsonl(tmp_path):
    """log_query appends exactly one JSONL line with the provided record."""
    log_file = tmp_path / "query_log.jsonl"

    import src.search.query_logger as ql
    with patch.object(ql, "LOG_PATH", log_file):
        ql.log_query({"ts": "2026-01-01T00:00:00.000Z", "query": "hello", "total_wall_ms": 42})

    lines = log_file.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["query"] == "hello"
    assert record["total_wall_ms"] == 42


def test_log_query_appends(tmp_path):
    """Two log_query calls produce two JSONL lines."""
    log_file = tmp_path / "query_log.jsonl"

    import src.search.query_logger as ql
    with patch.object(ql, "LOG_PATH", log_file):
        ql.log_query({"query": "a"})
        ql.log_query({"query": "b"})

    lines = log_file.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["query"] == "a"
    assert json.loads(lines[1])["query"] == "b"


def test_log_query_fail_soft(tmp_path, caplog):
    """log_query does NOT raise when write fails — logs a warning instead."""
    import src.search.query_logger as ql

    # Create a FILE where the parent dir should be, so mkdir fails
    blocker = tmp_path / "blocked"
    blocker.write_text("i am a file")
    bad_path = blocker / "nested" / "query_log.jsonl"

    with patch.object(ql, "LOG_PATH", bad_path):
        with caplog.at_level(logging.WARNING, logger="src.search.query_logger"):
            ql.log_query({"query": "should not crash"})

    assert any("query_log write failed" in m for m in caplog.messages)


# ---------------------------------------------------------------------------
# test_engine_with_timing (unit tests, no workflow)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_with_timing_ok():
    """_engine_with_timing returns (results, rate_wait_ms, search_ms, OK, None) on success."""
    from src.search.search_web import _engine_with_timing

    r = _fake_result("https://x.com", engine="fast")
    fast = _make_mock_engine("fast", [r])

    results, rate_wait_ms, search_ms, status, drop_reason = await _engine_with_timing(
        fast, "query", "en", 10, timeout=3.6
    )

    assert len(results) == 1
    assert status == "OK"
    assert drop_reason is None
    assert isinstance(rate_wait_ms, int) and rate_wait_ms >= 0
    assert isinstance(search_ms, int) and search_ms >= 0


@pytest.mark.asyncio
async def test_engine_with_timing_timeout():
    """_engine_with_timing returns TIMEOUT + drop_reason when engine exceeds watchdog."""
    from src.search.search_web import _engine_with_timing

    slow = _make_mock_engine("slow_eng", [], delay=5.0)

    results, rate_wait_ms, search_ms, status, drop_reason = await _engine_with_timing(
        slow, "query", "en", 10, timeout=0.05
    )

    assert results == []
    assert status == "TIMEOUT"
    assert drop_reason is not None and "watchdog" in drop_reason
    assert isinstance(rate_wait_ms, int)
    assert isinstance(search_ms, int)


@pytest.mark.asyncio
async def test_engine_with_timing_empty():
    """_engine_with_timing returns EMPTY status when engine returns []."""
    from src.search.search_web import _engine_with_timing

    empty = _make_mock_engine("empty_eng", [])

    results, _, _, status, drop_reason = await _engine_with_timing(
        empty, "query", "en", 10, timeout=3.6
    )

    assert results == []
    assert status == "EMPTY"
    assert drop_reason is None


# ---------------------------------------------------------------------------
# test_search_web_workflow_writes_log (integration, no network)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_web_workflow_writes_log(tmp_path):
    """search_web_workflow writes exactly one JSONL record with correct fields."""
    import src.search.query_logger as ql
    from src.search import search_web
    log_file = tmp_path / "query_log.jsonl"

    result_a = _fake_result("https://a.com", engine="google")
    result_b = _fake_result("https://b.com", engine="duckduckgo")

    mock_engines = {
        "google": _make_mock_engine("google", [result_a]),
        "duckduckgo": _make_mock_engine("duckduckgo", [result_b]),
    }

    async def _mock_preview(results, top_n=20):
        stats = {"urls_attempted": len(results[:top_n]), "urls_succeeded": 0, "url_timeouts": 0, "total_ms": 1}
        return results[:top_n], stats

    with (
        patch.object(search_web, "ENGINES", mock_engines),
        patch.object(search_web, "fetch_previews", _mock_preview),
        patch.object(search_web, "cache_write"),
        patch.object(search_web, "cache_key", return_value="testkey"),
        patch.object(search_web, "_merge_and_rank", return_value=([result_a, result_b], {"general": 1, "academic": 0, "qa": 1})),
        patch.object(ql, "LOG_PATH", log_file),
    ):
        await search_web.search_web_workflow("test query", language="en")

    lines = log_file.read_text().splitlines()
    assert len(lines) == 1, f"Expected 1 log line, got {len(lines)}: {lines}"

    rec = json.loads(lines[0])
    assert rec["query"] == "test query"
    assert rec["language"] == "en"
    assert "ts" in rec and rec["ts"].endswith("Z")
    assert rec["total_wall_ms"] >= 0
    assert set(rec["engines_requested"]) == {"google", "duckduckgo"}
    assert "google" in rec["engines"]
    assert "duckduckgo" in rec["engines"]

    for eng_name, stats in rec["engines"].items():
        assert "rate_wait_ms" in stats, f"{eng_name} missing rate_wait_ms"
        assert "search_ms" in stats, f"{eng_name} missing search_ms"
        assert stats["status"] in ("OK", "EMPTY", "TIMEOUT", "ERROR"), f"{eng_name} bad status"
        assert "result_count" in stats, f"{eng_name} missing result_count"
        assert "drop_reason" in stats, f"{eng_name} missing drop_reason"

    pv = rec["preview"]
    assert "urls_attempted" in pv
    assert "urls_succeeded" in pv
    assert "url_timeouts" in pv
    assert "total_ms" in pv
    assert rec["bottleneck_engine"] in ("google", "duckduckgo")
