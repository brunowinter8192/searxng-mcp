---
description: Crawl a website and save pages as Markdown files
argument-hint: [url]
---

## Input

URL: $ARGUMENTS

---

## Pipeline Flow

```
URL (from search_web or user)
 ↓ crawl_site.py (Crawl4AI BFS)
 ↓ deduplicate + clean permalinks
output-dir/*.md
 ↓ tmux worker (claude --model haiku)
 ↓ /rag:web-md-index (cleanup + chunk + embed)
indexed in RAG
```

---

## Step Indicator Rule

**MANDATORY:** Every response MUST start with: `Phase X, Step Y: [Name]`

---

## STOP Point Rule

**CRITICAL:** After each phase, there is a `**STOP**` marker.

- **STOP = END OF RESPONSE.** Do not continue to next phase.
- Wait for user to say "weiter", "proceed", "go", etc.
- NEVER batch multiple phases in one response

---

## Phase 1: Confirm Parameters

### Step 1: Resolve URL

If `$ARGUMENTS` contains a URL, use it. Otherwise ask user for the URL to crawl.

### Step 2: Ask for Output Directory

Ask user: "Where should the Markdown files be saved?"

Provide context: This is the first half of a crawl-to-RAG pipeline. The output directory should be wherever the RAG tool expects its input documents.

### Step 3: Confirm Crawl Settings

Present parameters and ask for confirmation:

```
URL:        [url]
Output Dir: [path]
Depth:      3 (default)
Max Pages:  100 (default)
```

Ask: "Start crawl with these settings? Adjust depth/max-pages if needed."

---

**STOP** - Wait for user confirmation before crawling.

---

## Phase 2: Crawl

### Step 1: Run Crawler

```bash
${CLAUDE_PLUGIN_ROOT}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/crawl_site.py \
  --url "$URL" \
  --output-dir "$OUTPUT_DIR" \
  --depth $DEPTH \
  --max-pages $MAX_PAGES
```

**Note:** Crawling can take several minutes depending on site size and depth.

### Step 2: Verify Output

```bash
ls -la "$OUTPUT_DIR"
wc -l "$OUTPUT_DIR"/*.md | tail -1
```

### Phase 2 Report

```
PHASE 2: Crawl
==============
URL:     [url]
OUTPUT:  [output-dir]
FILES:   [N] markdown files
STATUS:  [Success/Failed]
```

---

**STOP** - Report results. Ask: "Spawn a worker to index these MD files into RAG? (requires RAG plugin with `web-md-index` command)"

---

## Phase 3: RAG Indexing (tmux Worker)

**Prerequisite:** RAG plugin must be installed with the `web-md-index` command available.

### Step 1: Spawn Worker

```bash
tmux new-window -n "rag-index"
tmux send-keys -t "rag-index" 'claude --model haiku "/rag:web-md-index $OUTPUT_DIR"' Enter
```

### Step 2: Report

```
PHASE 3: RAG Worker
====================
TMUX WINDOW: rag-index
MODEL:       haiku
COMMAND:     /rag:web-md-index $OUTPUT_DIR
STATUS:      Spawned
```

Inform user: "Worker is running in tmux window 'rag-index'. Switch to it to monitor progress."

---

**STOP** - Pipeline complete. Crawl finished, RAG indexing worker spawned.
