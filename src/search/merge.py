# INFRASTRUCTURE
from src.search.result import SearchResult

GENERAL  = {"google", "duckduckgo", "mojeek"}
ACADEMIC = {"google_scholar", "openalex", "crossref"}  # "google_scholar" matches ScholarEngine.name
QA       = {"stack_exchange", "lobsters"}

ACADEMIC_PRIORITY = {"openalex": 1, "google_scholar": 2, "crossref": 3}
QA_PRIORITY       = {"stack_exchange": 1, "lobsters": 2}

TARGET_GENERAL  = 12
TARGET_ACADEMIC = 6
TARGET_QA       = 2


# FUNCTIONS

# Count engines in merged result belonging to GENERAL class
def _n_general(m: dict) -> int:
    return sum(1 for e in m["engines"] if e in GENERAL)


# Count engines in merged result belonging to ACADEMIC class
def _n_academic(m: dict) -> int:
    return sum(1 for e in m["engines"] if e in ACADEMIC)


# Count engines in merged result belonging to QA class
def _n_qa(m: dict) -> int:
    return sum(1 for e in m["engines"] if e in QA)


# Lowest academic priority among m's engines; 99 if none
def _best_academic_pri(m: dict) -> int:
    return min((ACADEMIC_PRIORITY.get(e, 99) for e in m["engines"] if e in ACADEMIC), default=99)


# Lowest QA priority among m's engines; 99 if none
def _best_qa_pri(m: dict) -> int:
    return min((QA_PRIORITY.get(e, 99) for e in m["engines"] if e in QA), default=99)


# Fill up to target slots from pool; dedupes via placed_urls (caller-owned set, mutated in-place)
def _fill_slots(pool: list, target: int, placed_urls: set) -> list:
    slots = []
    for m in pool:
        if len(slots) == target:
            break
        if m["url"] in placed_urls:
            continue
        slots.append(m)
        placed_urls.add(m["url"])
    return slots


# Merge by URL, classify into engine-class pools, allocate slots, return ranked results + slot fill counts
def _merge_and_rank(results: list[SearchResult], target_count: int = 20, class_filter: frozenset[str] | None = None) -> tuple[list[SearchResult], dict]:
    # Step 1 — Merge by URL: aggregate engine list, snippets dict, min position, prefer non-empty title
    merged: dict[str, dict] = {}
    for r in results:
        if r.url not in merged:
            merged[r.url] = {
                "url":          r.url,
                "title":        r.title or "",
                "snippet":      r.snippet,
                "engines":      [r.engine],
                "snippets":     {r.engine: r.snippet} if r.snippet else {},
                "min_position": r.position,
            }
        else:
            m = merged[r.url]
            if r.engine not in m["engines"]:
                m["engines"].append(r.engine)
            if r.snippet:
                m["snippets"][r.engine] = r.snippet
            m["min_position"] = min(m["min_position"], r.position)
            if not m["title"] and r.title:
                m["title"] = r.title
    pool = list(merged.values())

    # Step 2 — Classify and rank within each class
    general_pool  = sorted([m for m in pool if _n_general(m)  > 0], key=lambda m: (-_n_general(m),  m["min_position"]))
    academic_pool = sorted([m for m in pool if _n_academic(m) > 0], key=lambda m: (m["min_position"], _best_academic_pri(m)))
    qa_pool       = sorted([m for m in pool if _n_qa(m)       > 0], key=lambda m: (m["min_position"], _best_qa_pri(m)))

    # Step 3 — Resolve per-class targets based on class_filter
    active = class_filter if class_filter else {"general", "academic", "qa"}
    if len(active) == 1:
        cls = next(iter(active))
        tg = 20 if cls == "general"  else 0
        ta = 20 if cls == "academic" else 0
        tq = 20 if cls == "qa"       else 0
    elif len(active) == 2:
        tg = TARGET_GENERAL  if "general"  in active else 0
        ta = TARGET_ACADEMIC if "academic" in active else 0
        tq = TARGET_QA       if "qa"       in active else 0
    else:
        tg, ta, tq = TARGET_GENERAL, TARGET_ACADEMIC, TARGET_QA

    # Step 4 — Fill slots, assemble ordered list and leftover candidates
    placed_urls    = set()
    general_slots  = _fill_slots(general_pool,  tg, placed_urls)
    academic_slots = _fill_slots(academic_pool, ta, placed_urls)
    qa_slots       = _fill_slots(qa_pool,       tq, placed_urls)
    leftover = [m for m in pool if m["url"] not in placed_urls]
    leftover.sort(key=lambda m: (-len(m["engines"]), m["min_position"]))
    ordered  = general_slots + academic_slots + qa_slots
    extended = ordered + leftover
    slot_counts = {
        "general":  len(general_slots),
        "academic": len(academic_slots),
        "qa":       len(qa_slots),
    }
    return [
        SearchResult(
            url=m["url"],
            title=m["title"],
            snippet=m["snippet"],
            engine=m["engines"][0],
            position=m["min_position"],
            engines=m["engines"],
            snippets=m["snippets"],
        )
        for m in extended
    ], slot_counts
