---
name: scrape-cleanup
description: Clean raw scraped markdown (output of `searxng-cli scrape_url_raw` or equivalent) into RAG-indexable content. Diagnose-first workflow, shape-based dispatch, explicit stop-criteria to prevent over-engineering.
---

# Scrape Cleanup — Skill

You're cleaning raw markdown from a web scrape (typically `<!-- source: <URL> -->` followed by `raw_markdown` from Crawl4AI or similar). Goal: indexable content for RAG. Not perfect content. Indexable content.

The pipeline is: **scrape → clean (you) → LLM cleanup pass (downstream) → embedding/index**. Your output feeds an LLM cleanup that handles small residual noise. You handle the structural, high-volume chrome that the LLM shouldn't have to see.

---

## Core Principle: Diagnose First, Code Second

DO NOT start by writing cleanup regex. That path leads to whack-a-mole — you patch one file, regress another, change a threshold, regress two more, end with a fragile heuristic that fits nothing well.

The right order:

1. **Diagnose pass** — scan ALL raw inputs, extract structural fingerprints (h1/h2 counts, prose density, table presence, source domain). 50 LOC, 5s runtime.
2. **Shape classification** — group inputs into 4-5 page shapes by fingerprint pattern.
3. **Per-shape cleaner** — write one small function per shape, ~20-30 LOC each. NOT one big function with N patterns.
4. **Spot-check** — open 1-2 outputs per shape, read them, judge. NOT strip-percentage tables.
5. **Stop** — at the "good enough" line (see below). Don't write a 10th script for marginal gain.

`strip%` is a useless metric. It tells you bytes-out vs bytes-in, not "is this indexable". Use it for sanity-checking (suspicious 80% strip = check for over-strip), not for declaring done.

---

## The Five Shapes

Real scraped pages cluster into these shapes. Identify the shape, apply the matching cleaner.

### 1. Blog-Shape

**Fingerprint:** one `# ` h1 in the first ~20% of the doc; substantial prose under it; `## ` h2 sections; explicit footer markers (Continue reading, Comments, Copyright, breadcrumb).

**Examples:** seirdy.one, adrien.barbaresi.eu individual posts, justtothepoint.com, contextractor.com, chuniversiteit.nl.

**Cleanup:** strip everything between `<!-- source -->` and the title h1. Strip from earliest tail-marker to EOF. Done.

**KEEP:** `<!-- source -->`, h1 title, posted/updated metadata directly under title, ToC if present, all body content (paragraphs, code, tables, lists, images), abbreviation definitions (`*[XXX]: Yyy`).

**STRIP:** Top-nav bullet-lists, skip-to-content links, footer (Continue reading / Related posts / Comments / Copyright / breadcrumb / social-badge images).

### 2. Paper-Landing-Shape

**Fingerprint:** title h1 OR h2 oriented around academic title; author list directly under; abstract paragraph; metadata table (Subjects, DOI, etc.); short doc overall.

**Examples:** arxiv.org/abs/, doi.org/* (redirects to ACL Anthology, ACM DL, Qeios, SemEval).

**Cleanup:** strip top-of-page nav (logo, menu links). Keep title + authors + abstract + metadata table. Strip "View PDF / HTML / Disable MathJax" link clusters at the end. Strip footer (About / Help / Subscribe / Privacy / Web Accessibility).

**KEEP:** title, authors with their links, abstract paragraph, subject classification table, DOI/license metadata.

**STRIP:** site-wide nav, sidebar form (e.g. ACL Anthology's "Correct Metadata" form is sidebar, not content), copyright/license footer.

**Variant — h2-as-title:** Some paper landings (ACL Anthology) use `## [Title]` instead of `# Title`. The no-h1 fallback handles this — anchor on first `## ` h2 that's a title.

### 3. Forum-Thread-Shape

**Fingerprint:** heavy markdown-table layout (rows of `| ... | ... |`); top-nav row with site name + section links; story/comment row with vote-link; nested comment threads as nested tables.

**Examples:** news.ycombinator.com.

**Cleanup:** site-specific. For HN: detect `news.ycombinator.com` source, find first `vote?id=` link as content-start anchor, strip everything before. Keep story title row + comment thread.

**KEEP:** Story title, points, author, submission time, all comments with their authors and timestamps.

**STRIP:** top global nav (logo + new/past/comments/ask/show/jobs/submit/login row).

**Tolerable noise:** the markdown-table syntax itself adds verbosity (~30% of bytes are `| --- |` separators). Don't try to convert to flat prose — that breaks comment threading. Embedding handles markdown-table syntax fine.

### 4. Repo-Heavy-Chrome-Shape

**Fingerprint:** very long pre-content chrome (>100 lines); MANY `# ` h1 lines that are chrome (search box, feedback prompts, sponsor sections, repo headers); real content title appears late.

**Examples:** github.com/*/issues/N, github.com/*/pull/N, github.com/<org>/<repo>.

**Cleanup:** site-specific. For github issue/PR: extract issue number `<N>` from URL, find `^# .+ #<N>` line, strip everything before. For github repo home: anchor on README's first h1 or the file-tree end-marker.

**KEEP:** issue/PR title, opened-on metadata, `## Description` body, `## Activity`, all comments.

**STRIP:** all pre-title chrome (search, feedback, saved searches, sponsor section, repo nav, branch/file browser).

**Tolerable noise:** title-bar action buttons (`Copy link`, `New issue`, `Subscribe`) directly under the title. ~5 lines of low-signal text. LLM-cleanup-tauglich (the downstream LLM cleanup pass handles them).

**WARNING:** the "first h1 = title" heuristic FAILS on github. Github has a chrome-h1 cluster (Search, Provide feedback, Saved searches, Sponsor X) before the real title. Don't rely on `re.search('^# ', text)` — use the URL-based anchor.

### 5. Index/Aggregator-Shape

**Fingerprint:** no clear single page-title h1; multiple `## ` h2s as item-list (each h2 = one indexed item with teaser + "more..." link).

**Examples:** adrien.barbaresi.eu/blog/tag/X.html, libhunt.com/r/X.

**Cleanup:** strip top-nav (Toggle navigation, menu bullets), keep all `## [Item](url)` blocks with their teaser paragraphs.

**KEEP:** every h2 item + its description.

**STRIP:** site-nav, footer, pagination chrome.

**Note:** these pages have lower per-item content density. They're useful for discovery (linking to other URLs) more than for content indexing itself.

---

## Anti-Pattern Catalog (Chrome You'll See)

Comprehensive list — not exhaustive, but covers ~95% of what Crawl4AI raw_markdown emits as chrome:

**Head chrome:**
- `[Skip to content](#anchor)` / `[Skip to main content](...)` — accessibility chrome, anywhere
- Top-nav menu — bullet-list of internal links between source comment and h1
- `Toggle navigation` / `Menu` / `Search this site` — generic nav phrases
- Cookie consent banners — usually pre-stripped by `excluded_selector` in scrape config but check
- Sphinx/Furo permalink-anchors next to headings: `[#](url "Link to this heading")` and `[¶](url "Permalink to ...")`
- Site logos as image-in-link composites: `[![SiteLogo](logo.svg) SiteName ](url)` — fingerprint of head chrome on sites without h1

**Mid-content chrome:**
- Site-search forms / boxes
- "{{ message }}" leftover Mustache/Vue template placeholders
- Login/signup prompts that leaked through (especially github)
- Sponsor sections, ad blocks (`.ethical-ad`, generic CTA blocks)
- "You signed in with another tab..." session-state messages (github)
- Action buttons near titles: Copy link / Subscribe / Star / Watch / Fork

**Tail chrome:**
- `## Continue reading` / `## Related posts` / `## Related articles`
- `## Comments` / `## Webmentions` / `## Replies` (NOTE: gray area — see "Gray Areas" below)
- Breadcrumbs: `You are here:` followed by numbered list
- Copyright lines: `^Copyright \d{4}` followed by license/source/privacy/Tor link block
- Social-media badge images: `[ ![88x31](badge.png) ](social-link)`
- Acronym/abbreviation definition lists: `*[XXX]: Yyy` — KEEP these, they're content
- "Was this page helpful?" / "Thanks for your feedback!" feedback widgets

---

## Workflow

### Step 1 — Diagnose

Write or reuse a small script that emits one row per raw input file:

```
| file | source-domain | h1-count | h1-first-line | h2-count | byte-size | first-prose-line-pos | shape-guess |
```

Helpers to write:
- `count_h1(text)` — count `^# +\S` matches (note: `# ` and `#  ` both valid, regex `# +`)
- `find_first_h1(text)` — position of first h1
- `count_h2(text)` — count `^## +\S`
- `first_substantive_pos(text)` — first line with > 60 chars of visible-text (after stripping markdown-link/image wrappers AND bare URLs)
- `source_domain(text)` — extract from `<!-- source: <url> -->` header

Read the table. Group files by shape-guess. You now know what cleaners you need.

### Step 2 — Per-Shape Cleaners

One function per shape. Each function:
- Receives raw text
- Returns cleaned text
- Has 20-30 LOC
- Is independent of other shape cleaners
- Has 2-3 inline test inputs for fast verification

Dispatch by source-domain pattern OR by fingerprint:

```python
def cleanup(text: str) -> str:
    domain = source_domain(text)
    if "github.com" in domain:
        return clean_github(text)
    if "news.ycombinator.com" in domain:
        return clean_hn(text)
    shape = classify_shape(text)
    return CLEANERS[shape](text)
```

### Step 3 — Spot-Check

Open 1-2 cleaned outputs per shape. Read them. Specifically check:
- Does the title appear in the first ~10% / 1KB?
- Is the body structure intact (tables, code blocks, lists)?
- Did the footer get stripped?
- Are there obvious chrome remnants in the body?

If yes to first three and no to fourth → done with that shape.

### Step 4 — Stop

See "good enough" criteria below.

---

## "Good Enough" Line — Stop Criteria

You're done when ALL of these hold:

1. **Title is in the first 10% of file size or first 1KB**, whichever comes first.
2. **Body structural integrity preserved** — no broken tables, no severed code blocks, no orphan list items.
3. **Footer chrome (Copyright/Continue-reading/Breadcrumb/Privacy) is gone.**
4. **No gigantic top-chrome block remains** — pre-title content is < 500 bytes (allows a few link-line residuals, but not a full nav-stack).
5. **No scrape-failure outputs in the indexing set** (see "Scrape-Failure Detection" below).

You stop when the next pattern improvement would require a NEW function or a NEW special-case AND would only measurably affect ONE file out of N. That's diminishing returns. The downstream LLM cleanup pass handles the residual.

**Specific don'ts (over-engineering pitfalls):**

- Don't write a per-URL micro-pattern. If it's one URL out of 18, leave it for the LLM downstream.
- Don't tune a threshold by trial-and-error across 4+ iterations. If a heuristic doesn't converge in 2 iterations with clear evidence, switch strategy (heuristic → site-specific dispatch).
- Don't chase "Copy link" / "Subscribe" / "Star" button labels under titles. Tolerable noise.
- Don't try to convert HN markdown tables to prose. Breaks comment threading.
- Don't strip Comments/Webmentions sections before checking with the user (gray area, may be valued).

---

## Gray Areas (Surface to User Before Deciding)

These have legitimate-content interpretations. Don't strip silently.

| Pattern | Argument for KEEP | Argument for STRIP |
|---|---|---|
| `## Comments` (article comments) | Reader-perspective signal, can be high-quality | Pollutes the article's chunk; not the article itself |
| `## Webmentions` (Mastodon/IndieWeb replies) | Same as Comments | Same as Comments |
| Author bio at end | Provenance / context | Repeated boilerplate per article |
| ToC (Table of Contents) | Helps semantic chunking | Duplicates section headers below |
| Acronym definitions (`*[XXX]: Yyy`) | Indexable glossary | Disconnected from prose body |

Default: KEEP comments + bio + ToC + acronyms unless the user says strip.

---

## Scrape-Failure Detection (Critical)

Some "ok"-status raw outputs are functionally empty or garbage at the SCRAPE level, not the cleanup level. No cleaning fixes them. You detect, exclude from indexing, and ideally feed back to the scrape pipeline as a known-bad URL.

**Detection signals:**

- **Whitespace-only content:** raw file is < 500 bytes after the `<!-- source -->` header (typical for PDFs that returned binary noise that markdown-converted to whitespace).
- **Placeholder-content fingerprint:** `# example domain` as h1 (iana.org placeholder), or `<title>Default Web Site Page</title>` style text. Crawl4AI returned the placeholder served by the site instead of real content.
- **Login-wall remnants:** body is mostly "Sign in to continue", "Subscribe to read", or similar prompts with no article body.
- **Tiny content with PDF-extension URL:** URL ends in `.pdf` AND content < 200 bytes → handled by separate `download_pdf` flow, not scrape cleanup.

When detected: emit a status line, do NOT write a cleaned output, exclude from the indexing set.

---

## Pitfalls Observed (Lessons from Real Iteration)

**Pitfall 1 — "Smart h1-detection" with line-count gap heuristics breaks on short pages.**

Tried: "title h1 = first h1 with >= N lines until next h1". Worked for github (chrome-h1 cluster), broke for arxiv (footer h1 within N lines of real title → wrong h1 picked → 84% over-strip).

Lesson: line-count gap is the wrong signal. Either use prose-content-density (chars of substantive non-link prose in gap) OR ditch the heuristic and use URL-pattern dispatch.

**Pitfall 2 — Markdown-link length inflates false-positive prose detection.**

`[![SiteLogo](url) SiteName ](url2)` looks like 100+ char prose to a naive `len(line) > 60` check. After stripping markdown wrappers and bare URLs, it's 8 chars (`SiteName`). Always strip markdown wrappers AND URLs before length-checking.

**Pitfall 3 — Single growing function with N patterns can't be tested.**

I wrote one `clean_markdown(text)` function and added patterns to it across 6 iterations. Changing one pattern (MIN_TITLE_GAP=30 → 60) silently regressed another (arxiv 15% → 84%). Should have been: separate functions per pattern, each with 2-3 inline test fixtures, fast regression detection on every change.

**Pitfall 4 — Aspirational "URL-spanning" patterns fit no URL well.**

Wrote heuristics labeled "generic" that turned out to fit zero of 18 perfectly. Reality: a few page SHAPES exist; cleanup is per-shape, not per-pattern. Dispatch by shape, not by pattern.

**Pitfall 5 — Strip-percentage as success metric.**

Tracked "X% stripped" across iterations. Useless number. Says nothing about indexability. The metric that matters is "title in first 10% + body intact + footer gone + no scrape-failure". Read 1-2 outputs per shape, judge qualitatively.

---

## Reference Implementation

`dev/scrape_pipeline/03_cleanup/clean.py` is the iterative-discovery artifact from the session that produced this skill. **It's the messy version**, kept as reference for which patterns work on which shapes. Do NOT copy-paste it into prod. A fresh worker should follow the workflow above (diagnose → shape → per-shape cleaner) and produce a cleaner architecture.

Reference outputs at `dev/scrape_pipeline/02_raw_outputs/<latest>/` (raw input set) and `dev/scrape_pipeline/03_cleanup/cleaned_outputs/<latest>/` (cleaned). Use these as your test set when validating new cleanup work.

---

## Worker Workflow Summary

1. Read this skill.
2. Inventory the raw set (1 diagnose script, 50 LOC).
3. Classify shapes (read the diagnose table).
4. For each shape: write a 20-30 LOC cleaner with 2-3 inline tests.
5. Run on full set, spot-check 1-2 per shape.
6. Detect and exclude scrape-failures (separate output).
7. Stop at "good enough" — don't chase the last 5% of polish.
8. Hand off cleaned outputs to downstream LLM cleanup + indexing.
