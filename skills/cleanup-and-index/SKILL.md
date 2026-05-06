---
name: cleanup-and-index
description: Worker-side methodology — cleanup raw scraped/crawled markdown OR convert+cleanup PDFs, then index into RAG collection. Two modes (web-md / pdf). Activated by a worker after the main session has made acquisition decisions (URL filtering, PDF selection, collection naming).
---

# Cleanup-and-Index Skill (Worker)

This skill is loaded by a worker after main session has made acquisition decisions. Worker calls `Skill(skill="cleanup-and-index")` at start, then follows this protocol with the inputs provided in its spawn prompt.

## DEV State

This skill consolidates three existing artifacts that will be deleted after end-to-end verification:
- `MCP/searxng/skills/scrape-cleanup/SKILL.md` (290 LOC) — 5-shape diagnose-first methodology for web markdown
- `MCP/RAG/skills/web-md-index/SKILL.md` (214 LOC) — block-level chrome detection (Sphinx specifics) + index-dir call
- `MCP/RAG/skills/pdf-convert/SKILL.md` (245 LOC) — MinerU convert + OCR/LaTeX cleanup + index-dir call

Originals stay in place until this skill is verified end-to-end against one example domain (web-md mode) and one example PDF (pdf mode).

---

## Modes

The worker picks the mode based on its inputs.

### Mode 1: web-md
Input: absolute path to a URL list `.txt` (one URL per line) OR a directory of pre-crawled `*.md` files.
- If URL list: Phase 0 crawls all URLs via Crawl4AI.
- If pre-crawled directory: skip Phase 0.

Pipeline: [optional crawl] → block-level chrome cleanup (5-shape + Sphinx-specifics) → index.

### Mode 2: pdf
Input: absolute path to a single PDF file OR a directory of `*.pdf` files.

Pipeline: MinerU convert → OCR/LaTeX cleanup → index.

---

## Common Inputs

Every worker spawn provides:

| Var | Meaning | Example |
|---|---|---|
| `MODE` | `web-md` or `pdf` | `web-md` |
| `INPUT` | Source path | `/tmp/searxng_urls.txt` or `/path/to/paper.pdf` |
| `COLLECTION` | RAG collection name — `<project>_reference` (lowercase, underscore). One reference collection per project, all indexed material lands here. | `searxng_reference` |
| `OUTPUT_DIR` | Where cleaned `.md` files land — folder name MUST match `COLLECTION` exactly | `~/Documents/ai/Meta/ClaudeCode/MCP/RAG/data/documents/searxng_reference/` |

---

## Phase 0 — Acquisition

### Mode 1 (web-md)

If INPUT is a URL list `.txt`:

```bash
mkdir -p $OUTPUT_DIR
cd /Users/brunowinter2000/Documents/ai/Meta/ClaudeCode/MCP/searxng && \
./venv/bin/python -m src.crawler.crawl_site \
    --url-file $INPUT \
    --output-dir $OUTPUT_DIR \
    --concurrency 10
```

Report: `N URLs crawled, M succeeded, K failed`. List failed URLs.

If `>50%` failed → STOP, report to Opus, do not proceed.

If INPUT is a directory of `.md` files: skip Phase 0, set `OUTPUT_DIR=INPUT`.

### Mode 2 (pdf)

If INPUT is a single PDF file:

```bash
mkdir -p $OUTPUT_DIR
STEM="<derive descriptive PascalCase name from filename or first page>"
cd /Users/brunowinter2000/Documents/ai/Mineru && \
./venv/bin/python workflow.py convert \
    --input "$INPUT" \
    --output "$OUTPUT_DIR/$STEM.md"
```

If INPUT is a directory: loop over `*.pdf`, derive STEM per file (read first page or arxiv abstract if filename is cryptic), run convert per file. Report progress: `[N/M] <STEM>: phase 0 done`.

If MinerU fails for any PDF: log + skip + continue. Report failed PDFs at end.

---

## Phase 1 — Cleanup

### Mode 1: Web-MD Cleanup

Diagnose first. Don't write cleanup regex before classifying shape.

#### Diagnose Pass

Build a small script that scans ALL `.md` files in OUTPUT_DIR, extracts per-file fingerprints (h1 count, h2 count, prose density, table presence, source domain from `<!-- source: URL -->` comment, total LOC). Cluster by fingerprint similarity to identify 4-5 shape groups. ~50 LOC, ~5s runtime.

#### The Five Shapes

1. **Blog-Shape** — one h1 in first 20%, prose-heavy, h2 sections, footer markers (Continue reading / Comments / Copyright / breadcrumb).
   - Strip pre-h1 chrome + footer from earliest tail-marker.
   - Keep: source comment, h1 title, posted/updated metadata, ToC, body content.

2. **Paper-Landing-Shape** — academic title h1/h2, author list, abstract, metadata table (Subjects, DOI). Short overall.
   - Strip site nav, sidebar forms, "View PDF/HTML" link clusters, license footer.
   - Keep title, authors, abstract, subject table, DOI.
   - Variant: ACL Anthology uses `## [Title]` not `# Title` — anchor on first `## ` h2 if no h1.

3. **Forum-Thread-Shape** — markdown-table layout, top-nav row, story/comment rows.
   - Site-specific (HN: anchor on first `vote?id=` link, strip everything before).
   - Keep story title row + comment threads. Markdown-table syntax stays (embedding handles it).

4. **Repo-Heavy-Chrome-Shape** — very long pre-content chrome (>100 lines), many h1 chrome lines (search box, feedback, sponsor, repo headers), real title appears late.
   - GitHub issue/PR: extract `#<N>` from URL, find `^# .+ #<N>` line, strip everything before.
   - GitHub repo home: anchor on README's first h1 or file-tree end-marker.

5. **Index-Aggregator-Shape** — page is mostly link list, no real prose. Wikipedia category pages, blog index pages, doc TOC pages.
   - Flag as low-content. Optionally exclude from indexing (skip the file).

#### Web-Specific: Sphinx Documentation

Sphinx-generated docs (SearXNG, ReadTheDocs, many Python project docs) have a distinctive pattern. Header avg 10.7 lines, footer avg 52.6 lines, total noise ~37% of chars (verified on 278 files).

Header (top of file, before first `# ` heading):
- `### Navigation` block with index/modules/next/previous links
- Breadcrumb trail with `»` separators
- Strip: everything between `<!-- source:` line and first `# ` heading

Footer (after last content line):
- Logo image line: `[ ![Logo of ...](...) ](...)` — RELIABLE content-end marker
- `### [Table of Contents]`, `### Project Links`, second `### Navigation`, `### Quick search`, `### This Page`, `© Copyright`
- Strip: everything from `^\[ !\[Logo of ` to EOF

Inline noise (`_modules_*` files only): `[docs][](URL)` markers before class/function defs. Regex: `\[docs\]\[]\(https://[^)]*\)`.

#### Per-Shape Cleaner Pattern

For each detected shape, write ONE small script in `/tmp/clean_<shape>_<COLLECTION_lower>.py` (~20-30 LOC each). NOT one big function with N patterns.

#### Script Safety Rules (CRITICAL — previous runs failed here)

- Every `while` loop MUST increment in ALL code paths (skip/continue/break/normal — all)
- Test on 1 file FIRST, then run on all
- ALWAYS `python3` (not `python`)
- Use `Path(__file__).parent` — NEVER hardcode absolute paths like `/Users/...`
- Preserve `<!-- source: URL -->` comments in every file (they are crawl metadata)
- Overwrite originals in-place

#### Edge Cases

- Files with no `# ` heading (auto-generated redirect pages) → keep content between source comment and logo line
- Files nearly empty after cleanup (<5 lines) → still output, don't delete
- `user_None.md` / `user_{}.md` files = crawled error pages, minimal content expected

### Mode 2: PDF Cleanup

PDFs come from MinerU as Markdown. Cleanup focuses on inline OCR artifacts, not block chrome.

#### Pre-cleanup: Backup + Word Count Baseline

```bash
cp "$OUTPUT_DIR/$STEM.md" "/tmp/backup_$STEM.md"
wc -w "$OUTPUT_DIR/$STEM.md"
```

#### Artifacts to Detect and Fix

- **LaTeX spaced** — `\ f r a c`, `\ s u m`, `\ m a t h r m` → `\frac`, `\sum`, `\mathrm`
- **Broken images** — `! [ ] ( ... )` with spaces between chars → `![](...)`
- **Split words** — "mod els", "alg orithm" — fix conservatively via dictionary check (`/usr/share/dict/words` or in-document vocabulary)
- **HTML entities** — `&amp;`, `&#39;` → unescape
- **Encoding artifacts** — UTF-8 mojibake (Ã©, Ã¤) → re-encode
- **Hyphenated line-end splits** — `comput-\ner` → `computer` (only when both halves are dictionary words)
- **Run-on duplicate headers** — Line N is garbage run-on, Line N+1 is correct → DELETE the garbage line

#### Per-Issue Script Pattern

For each issue type, create `/tmp/fix_<issue>_<STEM>.py`. Run, verify count reaches 0 for that issue, move to next. NOT one mega-script.

#### Validation (MANDATORY after each fix)

- Word count must be stable (+/- 1%)
- Check for run-on words (iscentral, tothe, ofthe) — must remain 0
- If word count drops >2% OR run-on words appear: ABORT, restore from backup, report

#### Stop Criteria — "Good Enough"

The pipeline downstream is: convert → clean (this phase) → embedding/index. Embedding handles small residual noise. Don't over-engineer.

Stop when:
- All known issue categories have 0 remaining matches in the file
- Word count is stable
- Spot-check 10-15 lines from the middle reads as natural text

---

## Phase 2 — Index

Identical for both modes. Run as background job with `PYTHONUNBUFFERED=1` so the worker stays responsive (foreground would block on the long-running embed phase) and the log fills line-by-line for post-mortem if needed.

```bash
cd ~/Documents/ai/Meta/ClaudeCode/MCP/RAG && \
PYTHONUNBUFFERED=1 ./venv/bin/python workflow.py index-dir \
    --input "$OUTPUT_DIR" --collection "$COLLECTION" \
    > /tmp/${COLLECTION}_index.log 2>&1 &
```

This handles: server health check → start if needed → chunk → index → summary.

### Status check (during indexing)

Single signal — chunk count in the DB. Grows during indexing, stable when done.

```bash
cd ~/Documents/ai/Meta/ClaudeCode/MCP/RAG && \
./venv/bin/python cli.py list_collections | grep "$COLLECTION"
# → "  $COLLECTION (N chunks)"
```

### Failure check (after indexing done)

```bash
tail -20 /tmp/${COLLECTION}_index.log
```

Confirm `M chunks chunked, M chunks indexed` — numbers must match. If a `⚠️  WARNING: ... chunks skipped due to NULL embeddings` block is present, investigate via the indexer log before treating the collection as complete.

### Verify

```bash
cd ~/Documents/ai/Meta/ClaudeCode/MCP/RAG && \
./venv/bin/python workflow.py search \
    --query "<topic from collection content>" \
    --top-k 3
```

Top result should be a chunk from the just-indexed collection.

---

## Completion Report

Output back to Opus when done:

```
CLEANUP-AND-INDEX REPORT
=========================
Mode:             [web-md | pdf]
Collection:       <COLLECTION>
Input:            <INPUT path> (N items)
Phase 0:          [crawl: M ok, K failed | convert: M ok, K failed]
Cleanup shapes:   [shape: file_count, ...]  (web-md only)
Cleanup issues:   [issue: count, ...]       (pdf only)
Char reduction:   X% total                  (web-md)
Word stability:   ±Y%                       (pdf)
Indexed:          N chunks across M documents
Verification:     query "<q>" → top result snippet (~50 chars)
Status:           [Success | Issues — describe]
```

End with this report. STOP. No commit needed (output is data files, not code).

---

## Anti-Patterns (both modes)

- One mega-script with N regex patterns instead of per-shape/per-issue small scripts
- Treating `strip%` (web-md) or `% removed` (pdf) as a quality metric — bytes-out vs bytes-in says nothing about indexability
- Hardcoded absolute paths in cleanup scripts
- Infinite loops — every `while` MUST increment in all paths
- Skipping the backup step (pdf mode) — restore is impossible without it
- Skipping spot-check after cleanup — strip% can lie, eyeballing 2-3 files catches over-strip
