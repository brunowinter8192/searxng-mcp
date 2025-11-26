---
description: Check if README.md and module DOCS.md files need updates after MCP server code changes
---

# MCP DOCUMENTATION UPDATE CHECK

Systematic review workflow for README.md and module-level DOCS.md updates following CLAUDE.md MCP server standards.

**Execute this command after making code changes to determine if documentation updates are required.**

---

## Phase 1: Change Analysis

### Step 1: Identify Modified Files

List all files modified in this session:
- server.py changes?
- src/domain/*.py changes?
- .mcp.json changes?
- .env or environment changes?

THEN ↓

### Step 2: Categorize Changes (WHAT vs HOW)

For each modified file, determine:

**WHAT changed** = Contract, interface, behavior visible to users
- New tool added
- Parameter changed
- Output format changed
- Function responsibility changed

**HOW changed** = Internal implementation only
- Bug fix
- Refactoring
- Performance improvement
- Algorithm change (same result)

**OUTPUT:** List of changes with WHAT/HOW classification

---

## Phase 2: README Impact Assessment

**Purpose:** README documents installation, quick start, environment variables, and tool usage.

### Step 1: Check Tool Interface Changes

**README update required when:**
- New @mcp.tool added to server.py
- Tool parameter added/removed/renamed
- Default values changed
- Tool docstring changed (use case guidance)
- Output format changed

**README update NOT required when:**
- Bug fixes in src/ modules
- Internal refactoring
- Performance improvements
- Code reorganization without interface change

THEN ↓

### Step 2: Check Configuration Changes

**README update required when:**
- New environment variable required
- .env structure changed
- .mcp.json env section changed
- New dependencies required
- venv setup changed
- .mcp.json paths changed

THEN ↓

### Step 3: Decision

Based on Steps 1-2, determine:

```
README ASSESSMENT
=================
Tool Interface Changes: YES / NO
Configuration Changes: YES / NO

DECISION: UPDATE REQUIRED / NO UPDATE / UNCERTAIN
CONFIDENCE: [X%]
REASON: [Brief explanation]
```

**If UNCERTAIN:** Note specific uncertainty for Phase 4

---

## Phase 3: Module DOCS Impact Assessment

**Purpose:** Each domain folder in src/ has its own DOCS.md documenting its modules.

**Location:** src/domain_name/DOCS.md

### Step 1: Identify Affected Domains

Which src/domain/ folders contain changes?
- List each affected domain
- Note which modules within domain changed

THEN ↓

### Step 2: Check Function Contract Changes

For each affected domain, check:

**DOCS update required when:**
- New module added to domain folder
- New function added to existing module
- Function responsibility (WHAT) changed
- Function parameters changed
- Return structure changed
- Orchestrator call sequence changed
- New domain folder created (needs new DOCS.md)

**DOCS update NOT required when:**
- Bug fixes in function implementation (HOW)
- Internal refactoring within function body
- Performance improvements
- Variable renaming (internal only)
- Algorithm changes that don't affect contract

THEN ↓

### Step 3: Decision

For each affected domain:

```
DOMAIN: src/[domain_name]/
========================
Modules Changed: [list]
Contract Changes: YES / NO
Call Sequence Changed: YES / NO

DECISION: UPDATE REQUIRED / NO UPDATE / UNCERTAIN
CONFIDENCE: [X%]
REASON: [Brief explanation]
SECTION TO UPDATE: [If update required, which section]
```

---

## Phase 4: Honest Assessment & User Decision

### Step 1: Consolidate All Decisions

Gather decisions from Phase 2 and Phase 3.

THEN ↓

### Step 2: Present Assessment

```
HONEST ASSESSMENT
=================

OVERALL CONFIDENCE: [X%] - [High 80-95% / Medium 60-80% / Low 40-60%]

Why this confidence level:
[Explanation: What makes us confident? What creates uncertainty?]

---

README.md:
- Decision: UPDATE REQUIRED / NO UPDATE / UNCERTAIN
- Confidence: [X%]
- Reason: [What changed or why no change needed]
- Sections affected: [If update, which sections]

src/[domain]/DOCS.md: (repeat for each affected domain)
- Decision: UPDATE REQUIRED / NO UPDATE / UNCERTAIN
- Confidence: [X%]
- Reason: [What changed or why no change needed]
- Sections affected: [If update, which sections]

---

WHAT COULD BE WRONG:
- [Uncertainty 1: What we might have missed]
- [Uncertainty 2: Edge case not considered]

=================
```

THEN ↓

### Step 3: Get User Approval

**CRITICAL:** Present assessment and wait for user confirmation.

Use `AskUserQuestion` if decisions are UNCERTAIN:

```
Question: "Should we update [file] based on [change]?"
Options:
- Yes, update documentation
- No, change is internal only
- Need more context: [specify]
```

**If all decisions are confident (>80%):** Present recommendation and ask for confirmation.

THEN ↓

### Step 4: Execute Updates (After Approval)

**Only after user confirms:**

1. Update approved files following CLAUDE.md prose style
2. Keep updates minimal - only document what changed
3. Maintain existing structure and formatting

**If user rejects:** Document user's decision and reasoning for future reference.
