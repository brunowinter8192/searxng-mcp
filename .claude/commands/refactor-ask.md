---
description: Systematic refactoring analysis after feature implementation to assess module complexity and suggest improvements
argument-hint: [optional: module-path or "auto" to detect recent changes]
---

## Refactoring Analysis

Target: $ARGUMENTS

---

# Workflow

## Phase 1: Collect Metrics

Read all Python files in the specified path. For each module, analyze:

### Core Metrics

| Metric | OK | Warning | Critical |
|--------|-------|-----------|-------------|
| Module LOC | < 400 | 400-600 | > 600 |
| Functions | < 15 | 15-20 | > 20 |
| Function LOC | < 30 | 30-50 | > 50 |
| Cross-Module Imports | < 5 | 5-8 | > 8 |

### Additional Indicators

- **Single Responsibility**: Multiple unrelated concerns in one module?
- **Code Duplication**: Repeated logic across functions?
- **Deep Nesting**: > 4 indentation levels?
- **Naming Clarity**: Unclear function/variable names?

---

## Phase 2: Identify Refactoring Opportunities

Based on metrics, categorize findings into opportunity types:

### Opportunity Types

**1. Extract Module**
- Trigger: > 400 LOC with distinct functional groups
- Example: "HTML parsing + Markdown conversion" → 2 modules

**2. Extract Function**
- Trigger: Functions > 50 LOC
- Example: Large orchestrator → extract sub-tasks

**3. Consolidate Duplication**
- Trigger: Similar code in multiple places
- Example: Common validation → shared helper function

**4. Simplify Dependencies**
- Trigger: > 5 cross-module imports
- Example: 8 imports → refactor to 3 via abstraction

**5. Improve Clarity**
- Trigger: Unclear naming, missing structure
- Example: Rename functions, add section separators

### Output Format

For each module with issues:

```
MODULE: src/[domain]/[path].py
LOC: [X] | Functions: [Y] | Imports: [Z]
Issues: [list threshold violations]

Opportunities:
- [Type]: [specific suggestion]
- [Type]: [specific suggestion]
```

---

## Phase 3: Clarifying Questions

**CRITICAL:** Before creating the refactoring plan, use `AskUserQuestion` to clarify focus.

Based on the opportunities found, ask the user which areas to prioritize:

**Example questions:**

```
Question: "Which refactoring opportunities should be prioritized?"
Options:
- Extract Module: [specific modules identified]
- Extract Function: [specific functions identified]
- Consolidate Duplication: [specific patterns identified]
- Simplify Dependencies: [specific coupling issues identified]
```

```
Question: "How extensive should the refactoring be?"
Options:
- Minimal: Only fix critical threshold violations
- Moderate: Fix warnings + critical
- Extensive: Full cleanup following best practices
```

**Only when focus is 100% clear → proceed to Phase 4**

---

## Phase 4: Create Refactoring Plan

Create a detailed, executable plan following CLAUDE.md structure:

```
REFACTORING PLAN
================

Scope: [What will be refactored]
Focus: [User's chosen priorities from Phase 3]

---

Step 1: [Concrete action]
File: src/[domain]/[path].py:[lines]
Action: [Extract/Move/Rename/Split]
Details:
- [Specific change 1]
- [Specific change 2]

Step 2: [Concrete action]
File: src/[domain]/[path].py:[lines]
Action: [Extract/Move/Rename/Split]
Details:
- [Specific change 1]
- [Specific change 2]

[... continue for all steps ...]

---

Cross-Module Updates:
- server.py:[line] - Update import if module renamed
- src/[domain]/[file1].py:[line] - Update import
- src/[domain]/[file2].py:[line] - Update function call

---

CLAUDE.md Compliance:
- 3-section structure (INFRASTRUCTURE, ORCHESTRATOR, FUNCTIONS)
- Function header comments (1 line, WHAT not HOW)
- No emojis in production code
- Tool parameters use Annotated + Field
- Docstrings describe when to use tool
```

### Wait for User Approval

**CRITICAL:** WAIT for explicit user confirmation before implementing.

Ask: "Should I implement this refactoring plan?"

User might want to:
- Adjust steps
- Remove certain changes
- Add additional refactoring

---

## Phase 5: Execute

**Only after Phase 4 approval.**

Follow the approved plan step-by-step:

1. **Execute each step in order**
   - Make changes as specified in plan
   - Maintain CLAUDE.md structure in all modified files
   - Update cross-module imports

2. **Verify functionality unchanged**
   - Run existing tests if available
   - Quick smoke test of affected functionality

3. **Update Documentation**
   - Run /check-docs to assess if src/[domain]/DOCS.md needs update
   - Update if module responsibilities changed

4. **Report completion**

```
REFACTORING COMPLETE
====================

Files Modified:
- src/[domain]/[file1].py - [what changed]
- src/[domain]/[file2].py - [what changed]

Metrics After:
- [Module]: LOC [before] → [after]
- [Module]: Functions [before] → [after]

Next Steps: [if any follow-up recommended]
```

---

**IMPORTANT NOTES:**

1. **Approval Gates:** This command has 2 explicit approval gates:
   - After Phase 3 (focus clarification)
   - After Phase 4 (refactoring plan)

2. **No Over-Engineering:** Only refactor what's in the approved plan. No additional "improvements".

3. **Preserve Behavior:** Refactoring = same functionality, better structure. Never change behavior without explicit approval.
