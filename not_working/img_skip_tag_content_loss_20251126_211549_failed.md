# Adding img to SKIP_TAGS - CATASTROPHIC CONTENT LOSS

**Date:** 2025-11-26 21:15

## Problem
Text-mashing, broken image syntax, footnote noise in scraped content. Goal was to remove images completely and filter citation links.

## Attempted Fix

**File:** `content_filter.py`
- Line 2: Added `'img'` to `SKIP_TAGS`
- Line 5: Added `'#cite_ref'`, `'#cite_note'` to `NOISE_URL_PATTERNS`

**File:** `markdown_converter.py`
- Lines 89-105: Extended `should_add_space_after()` with `first_char in '([{'`

**Theory:** Adding `img` to SKIP_TAGS would filter out image tags. `remove_skip_tags()` already handles tag removal correctly.

## Why It Failed

**What we observed when tested:**
- Problem got catastrophically worse - total content loss on 4/6 test sites

**Specific symptoms:**
- Wikipedia: Empty except "Zum Inhalt springen"
- Scikit-learn: Empty except "Back to top"
- Binance: Empty except header
- Medium: Empty except "Sign up / Search"
- Only SearXNG and Chroma survived

**Comparison to before fix:**
- MUCH WORSE - regression from "text-mashing" to "no text at all"

**Side effects:**
- Critical: Primary article content completely missing

**Our best hypothesis for why it failed:**
The `remove_skip_tags()` function uses stack-based tracking that may break when `img` is added. Unlike block tags (aside, script, etc.), `img` is typically self-closing or has no matching end tag. The stack logic expects `</img>` which never comes, causing the skip_stack to never pop, filtering ALL subsequent content.

Alternative hypothesis: The `img` tags on these sites may be inside the main content container. If `remove_skip_tags()` runs BEFORE `extract_main_content()`, it may be removing content prematurely.

**Confidence in this analysis:** 70% - Medium
The stack-based logic is designed for paired tags, not self-closing tags.

**What we're still uncertain about:**
- Exact interaction between `remove_skip_tags()` and self-closing img tags
- Whether issue is in tag-pairing logic or execution order
- Why SearXNG and Chroma survived (maybe fewer/no img tags in main content?)

## Next Steps

1. **IMMEDIATE ROLLBACK:** Remove `'img'` from SKIP_TAGS
2. **Alternative approach for images:** Instead of SKIP_TAGS, handle img removal in markdown_converter.py by returning empty string from `extract_image_markdown()` and `handle_self_closing_tag()`
3. **Test citation filter separately:** The `#cite_ref`/`#cite_note` patterns may be fine, test independently
4. **Investigate stack logic:** Check if `remove_skip_tags()` handles self-closing tags correctly

## Rollback Required

```python
# content_filter.py Line 2 - REVERT TO:
SKIP_TAGS = {'aside', 'script', 'style', 'noscript', 'iframe', 'svg', 'nav', 'footer', 'header'}

# content_filter.py Line 5 - KEEP (citations probably fine):
NOISE_URL_PATTERNS = ['/m/signin', 'actionUrl=', 'operation=register', 'clap_footer', 'bookmark_footer', '#cite_ref', '#cite_note']
```
