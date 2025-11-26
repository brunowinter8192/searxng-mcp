# Scraper Cleanup Batch (6 Problems) - PARTIAL FAILURE

**Date:** 2025-11-26 19:15

## Problem
Six scraping issues: (1) Whitespace after bold/italic, (2) UI artifacts `[#]`, `[source]`, (3) Ghost punctuation from wiki links, (4) Image filename fragments `.jpg)`, (5) Empty list bullets, (6) Wikipedia infoboxes.

## Attempted Fix

**content_filter.py:**
- Line 6: Added `SKIP_TABLE_CLASSES` constant
- Line 15: Added `remove_wikipedia_tables()` call to orchestrator
- Lines 175-196: New `remove_wikipedia_tables()` function

**markdown_converter.py:**
- Lines 306-348: Expanded `clean_markdown_artifacts()` with new regex patterns
- Lines 368-369, 382-383: Added list bullet fix in `clean_whitespace()`

**Theory:** Additional regex patterns in cleanup function would remove artifacts; new table filter would remove infoboxes; list regex would fix empty bullets.

## Why It Failed

**What we observed when tested:**
- Partially fixed (some improvement but new issues appeared)

**Specific symptoms:**
- Text-Mashing: `geschützt.Er unterliegt`, `GattungCastor`, `**n_estimators**int` - missing spaces between sentences and after tags
- Broken image links: `[![Nagespuren ...](/wiki/Datei:Biber_nagte_an_Eiche` - unclosed markdown
- New artifacts: `(#cite_ref-1)` visible instead of removed
- Header artifacts: `# engines:(#engines)` - anchor IDs in headers

**Comparison to before:**
- Lists: IMPROVED (dangling bullets fixed)
- UI artifacts: PARTIALLY IMPROVED (`[¶]`, `[↑]` removed)
- Readability: WORSE (text mashing is critical regression)
- Images: WORSE (broken markdown syntax)

**Side effects:**
- Critical: Whitespace removal too aggressive, breaks readability

**Our best hypothesis for why it failed:**
The `clean_whitespace()` function removes spaces between elements that should preserve spacing. The regex `\)\*\s+` and bracket cleanup patterns are too aggressive and remove necessary whitespace. The problem is NOT in artifact removal but in how whitespace is handled around HTML tag boundaries.

**Confidence in this analysis:** 75% - Medium
Root cause is clear (whitespace handling), but exact regex responsible needs investigation.

**What we're still uncertain about:**
- Which specific regex in `clean_markdown_artifacts()` causes text mashing
- Whether problem is in `clean_whitespace()` or `clean_markdown_artifacts()`
- Why `(#cite_ref-*)` patterns not caught by existing regex

## Next Steps

1. **Whitespace-Logik umkehren:** Ensure space is added AFTER closing inline tags (`</b>`, `</a>`) unless followed by punctuation
2. **Header anchor cleanup:** Add regex `\(#[^)]+\)\s*$` to remove anchor IDs from headings
3. **Cite ref cleanup:** Add regex `\(#cite_ref-[^)]*\)` to remove citation anchors
4. **Image handling:** Either fix markdown closure or remove images entirely from Wikipedia

## Successful Parts (For Reference)

These fixes DID work and should be preserved:
- `SKIP_TABLE_CLASSES` and `remove_wikipedia_tables()` - infoboxes removed
- `[¶]`, `[↑]`, `[[source]]` removal patterns
- List bullet fix regex in `clean_whitespace()`
