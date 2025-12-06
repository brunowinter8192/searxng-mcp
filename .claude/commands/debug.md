---
description: Systematic debugging with context gathering, debug-specialist subagent and bug documentation
argument-hint: [observation/error-description]
---

## Problem Observation

User observes Probelm: $ARGUMENTS

---

## Step Indicator Rule

**MANDATORY:** Every response in this workflow MUST start with:
`Phase X, Step Y: [Name]`

Example: `Phase 1, Step 3: Find Files`

---

## Phase 1: Context Gathering

**Purpose A: Prepare Agent Prompts**
- What is the problem?
- Which files should agents look at?
- How should they approach the problem?

**Purpose B: Understand for Validation**
- You MUST understand the code
- Otherwise you cannot evaluate if Agent-Fix makes sense
- **Validation is the most important part**

### Step 1: Check Past Attempts

1. Check `bug_fixes/` for similar past issues
2. Check `not_working/` for fixes that failed

### Step 2: Find Relevant Files

- Find relevant files in which are causing the problem
- Narrow down on function level

### Step 3: Analyze Target

**Reference Files:**
- Domains: `debug/scraping_suite/domains.txt`
- Baselines: `debug/scraping_suite/baselines/{domain}/`

**DOM Analysis Workflow:**
1. Read `domains.txt` → Which domain relates to the problem?
2. Find newest baseline → In `baselines/{domain}/` find highest `iteration_XXX.md`
3. Analyze baseline output → How does scraper currently process the page?
4. Fetch raw HTML → Get live DOM structure of the URL
5. Compare → Where does scraper output differ from expected?

**Questions that must be answered:**
1. WHERE in the DOM is the problem? (Tag, class, id, structure)
2. HOW does the scraper process it? (Which module, which function)
3. WHY does it get through? (Which filter doesn't catch it?)

**No Overfitting:** Fixes must be general, not site-specific.

### Step 5: Localize the Problem

- Where exactly does the problem occur?
- Gather File:Line references

### Step 6: Context Summary

```
CONTEXT SUMMARY
===============

PROBLEM: [User's problem from arguments]

RELEVANT FILES:
- /path/to/file1.py - [why relevant]
- /path/to/file2.py - [why relevant]

PAST ATTEMPTS:
- bug_fixes/xyz.md - [what was tried]
- not_working/abc.md - [what failed and why]

PROPOSED LANES:
- Agent 1: [Lane description]
- Agent 2: [Lane description] (if needed)

===============
```

**🛑 STOP** - Ask the user if he wants to proceed to Phase 2 or if he has remarks based on the summary or if there are more things to clarify
     **CRITICAL** as long as the user dont explicitly states that he wants to proceed to phase 2, dont proceed

---

## Phase 2: Launch Debug Agents

### Step 1: Prepare Workspaces

- Agent 1 → `debug/Agent_1/`
- Agent 2 → `debug/Agent_2/` (if used)

### Step 2: Write Agent Prompts

Agent Prompt must contain:
1. **Problem** - What's broken, expected vs actual
2. **Relevant Files** - Absolute paths with line refs
3. **Proposed Lane** - Specific focus area to solve the problem

### Step 3: Launch Agents

**Agent Prompt Template:**

```
## Your Lane: [LANE DESCRIPTION]

You are Agent [X]. Your ONLY focus is: [specific road to investigate the problem]

## Problem Description
[Precise description of what is failing, expected vs actual]

## Relevant Production Files
[Absolute paths]:
- /path/to/file1.py
- /path/to/file2.py
- domains
- scraper output

## Your Task (Steps 1-2 only, then STOP and report)

**Step 1: Root Cause Analysis**
- Analyze the code
- Identify WHERE and WHY the bug occurs
- Document File:Line references

**Step 2: Reproduce**
- Create `debug/Agent_[X]/reproduce_[issue].py`
- Copy affected production function(s) 1:1
- Reproduce the bug with real data
- Document: Bug reproduced YES/NO + findings

**Step 2.5: STOP and Report**
After reproduce, provide this report and STOP:

## CRITICAL Rules
- Stay on YOUR lane only
- NO mocks - copy production code 1:1
- Test against real data
- Your workspace: debug/Agent_[X]/
```

**If 2 agents:** Launch BOTH in a single message (parallel execution).

---

## Phase 3: Checkpoint Assessment

### Step 1: Review Agent Reports

For each agent, check:
- Lane adherence: Is agent still on assigned solution pathway for the problem?
- Reproduction success: Did agent reproduce the bug?

### Step 2: Assessment Summary

```
CHECKPOINT ASSESSMENT
=====================

AGENT 1:
- Lane: [assigned] → [actual]: OK / DRIFTED
- Reproduced: YES / NO
- Decision: GO / REDIRECT
- Instruction: [If redirect, what to fix]

AGENT 2 (if used):
- Lane: [assigned] → [actual]: OK / DRIFTED
- Reproduced: YES / NO
- Decision: GO / REDIRECT
- Instruction: [If redirect, what to fix]

=====================
```

**🛑 STOP** - Ask the user if he wants to proceed to Phase 2 or if he has remarks based on the summary or if there are more things to clarify
     **CRITICAL** as long as the user dont explicitly states that he wants to proceed to phase 2, dont proceed

---

## Phase 4: Resume Agents for Fix

### Step 1: Send GO/REDIRECT

Resume each agent with GO or REDIRECT instruction:

```
## [GO/REDIRECT] - Continue to Fix

[If GO]: Your checkpoint report is good. Proceed with your planned fix.
[If REDIRECT]: [Specific correction needed]

## Your Task (Steps 3-4)

**Step 3: Implement Fix**
- Create `debug/Agent_[X]/solution_[issue].py`
- Apply fix to copied production code
- Validate fix works with real data

**Step 4: Final Report**

```

### Step 2: Wait for Agent Reports

Collect final reports from all agents.

---

## Phase 5: Synthesis

### Step 1: Combine Findings

```
SYNTHESIS
=========

AGENT FINDINGS:

Agent 1 ([Lane]):
- Root Cause: [What they found]
- Fix: [Their solution]
- Confidence: [Their self-assessment]

Agent 2 ([Lane]) - if used:
- Root Cause: [What they found]
- Fix: [Their solution]
- Confidence: [Their self-assessment]

RECOMMENDED FIX:
[Concrete recommendation based on agent findings]

WHAT COULD BE WRONG:
- [Uncertainty 1]
- [Uncertainty 2]

=========
```

### Step 2: Validate Against Own Understanding

- Does the fix make sense based on Phase 1 code understanding?
- Is the fix general (no overfitting)?

**🛑 STOP** - Ask the user if he wants to proceed to Phase 2 or if he has remarks based on the summary or if there are more things to clarify
     **CRITICAL** as long as the user dont explicitly states that he wants to proceed to phase 2, dont proceed
---

## Phase 6: Write Plan

### Step 1: Write to System Plan File

Write fix plan to system plan file (path from Plan Mode system message).

### Step 2: Exit Plan Mode

Call ExitPlanMode.

---

## Phase 7: Implementation

### Step 1: Implement Fix

Apply the fix to production code.

### Step 2: Commit

Commit changes.

---

## Phase 8: User Testing
