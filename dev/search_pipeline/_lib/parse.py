"""Smoke report parser for dev/search_pipeline analysis scripts."""

# INFRASTRUCTURE
import ast
import re
from collections import defaultdict
from pathlib import Path

# Canonical set of 8 active search engine names — single source of truth for dev scripts
KNOWN_ENGINES = {
    "google", "duckduckgo", "mojeek", "lobsters",
    "google_scholar", "openalex", "crossref", "stack_exchange",
}


# FUNCTIONS

# Parse Python repr-quoted string; fallback to stripping outer quote chars
def _repr_unquote(s: str) -> str:
    s = s.strip()
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
            return s[1:-1]
        return s


# Parse new pipeline_smoke MD format into URL records with snippets and previews
def parse_smoke_report(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict]       = []
    current_query: str | None = None
    current_record: dict | None = None
    query_counter   = 0
    query_seen: dict[str, int] = {}
    pos_per_query: dict[str, int] = defaultdict(int)

    for line in lines:
        # Query header: ## Q1: python asyncio best practices
        m = re.match(r'^## Q\d+: (.+)$', line)
        if m:
            current_query = m.group(1).strip()
            if current_query not in query_seen:
                query_counter += 1
                query_seen[current_query] = query_counter
            continue

        # URL entry: N. **[CLASS]** Title
        m = re.match(r'^\d+\. \*\*\[([A-Z]+)\]\*\* (.+)$', line)
        if m:
            if current_record is not None:
                records.append(current_record)
            cls   = m.group(1)
            title = m.group(2).strip()
            qi    = query_seen.get(current_query, 0)
            pos_per_query[current_query] += 1
            pos   = pos_per_query[current_query]
            current_record = {
                "query":    current_query,
                "class":    cls,
                "title":    title,
                "url":      None,
                "engines":  [],
                "source":   "",
                "display":  "",
                "og":       None,
                "meta":     None,
                "snippets": {},
                "_qi":      qi,
                "_pos":     pos,
            }
            continue

        if current_record is None:
            continue

        # URL field
        m = re.match(r'^\s+URL: (https?://\S+)', line)
        if m:
            current_record["url"] = m.group(1)
            continue

        # Engines field
        m = re.match(r'^\s+Engines: (.+)$', line)
        if m:
            current_record["engines"] = [e.strip() for e in m.group(1).split(",")]
            continue

        # source | display line
        m = re.match(r'^\s+source: (\S+) \| display: (.+)$', line)
        if m:
            current_record["source"]  = m.group(1)
            current_record["display"] = _repr_unquote(m.group(2))
            continue

        # og | meta line — checked before generic engine pattern ("og" not in KNOWN_ENGINES)
        m = re.match(r'^\s+og: (.*)', line)
        if m:
            rest = m.group(1)
            if ' | meta: ' in rest:
                og_part, meta_part = rest.split(' | meta: ', 1)
            else:
                og_part, meta_part = rest, "—"
            current_record["og"]   = None if og_part.strip()   == "—" else og_part.strip()
            current_record["meta"] = None if meta_part.strip() == "—" else meta_part.strip()
            continue

        # Per-engine snippet line: engine_name: 'repr-quoted text'
        m = re.match(r'^\s+(\w+): (.+)$', line)
        if m:
            eng = m.group(1).lower()
            if eng in KNOWN_ENGINES:
                current_record["snippets"][eng] = _repr_unquote(m.group(2))
            continue

    if current_record is not None:
        records.append(current_record)
    return records
