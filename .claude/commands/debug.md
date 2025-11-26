---
description: Systematic debugging with context gathering, debug-specialist subagent and bug documentation
argument-hint: [observation/error-description]
---

## Problem Observation

User observes: $ARGUMENTS

---

## Phase 1: Context Gathering + Agent Strategy

### Step 1: Clarification (if needed)

**BEFORE analyzing:** Is the problem 100% clear?
- WHERE does it occur?
- WHAT exactly is the symptom?
- WHEN does it happen?

**If unclear:** Use `AskUserQuestion` immediately.

### Step 2: Context Gathering

1. Identify affected modules based on observation
2. Check `bug_fixes/` for similar past issues
3. Check `not_working/` for fixes that not worked out in the past
4. Find relevant files (max 3-4, focused)
5. Gather: Error messages, stack traces, File:Line references

### Step 3: Decide Agent Strategy

**YOU (Main Agent) are the ORCHESTRATOR. Analyze problem complexity:**

**1 Agent - Single Lane:**
- One clear problem with one investigation path
- Small, focused bug

**2 Agents - Parallel Lanes:**
- Two independent problems → Agent 1: Problem A, Agent 2: Problem B
- One complex problem with multiple possible causes → Agent 1: Road 1, Agent 2: Road 2

**CRITICAL:** Each agent stays on their assigned lane. No cross-assessment, no reassignment mid-debug.

---

## Phase 2: Launch Debug Agents

**Workspaces:**
- Agent 1 → `debug/Agent_1/`
- Agent 2 → `debug/Agent_2/` (if used)

**MANDATORY:** Launch agents with clear lane assignment.

**Agent Prompt Template:**

```
## Your Lane: [LANE DESCRIPTION]

You are Agent [X]. Your ONLY focus is: [specific problem/road to investigate]

## Problem Description
[Precise description of what is failing, expected vs actual]

## Investigation Results
[Findings from Phase 1: errors, stack traces, File:Line refs]

## Relevant Production Files
[Absolute paths]:
- /path/to/file1.py
- /path/to/file2.py

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

AGENT [X] CHECKPOINT REPORT
===========================
LANE: [Your assigned lane]

ROOT CAUSE:
- File: [module.py:line]
- Issue: [What you found]
- Why: [Explanation]

REPRODUCTION:
- Success: YES/NO
- Script: debug/Agent_[X]/reproduce_[issue].py
- Findings: [What reproduction revealed]

PLANNED FIX:
- Approach: [How you plan to fix it]
- Files to modify: [List]

AWAITING: GO/REDIRECT instruction
===========================

## CRITICAL Rules
- Stay on YOUR lane only
- NO mocks - copy production code 1:1
- Test against real data
- Your workspace: debug/Agent_[X]/
```

**If 2 agents:** Launch BOTH in a single message (parallel execution).

---

## Phase 3: Checkpoint Assessment

**After agents return with Checkpoint Reports:**

### Quick Assessment per Agent

For each agent, check:

1. **Lane Check:** Is agent still on assigned problem?
   - YES → Continue
   - NO → Redirect back to lane

2. **Reproduce Check:** Did agent reproduce the bug?
   - YES → Continue
   - NO → Investigate why (wrong lane? wrong assumption?)

### Decision Format

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

PROCEEDING: Resuming [X] agent(s)
=====================
```

---

## Phase 4: Resume Agents for Fix

**Resume each agent with GO or REDIRECT:**

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

AGENT [X] FINAL REPORT
======================
LANE: [Your lane]

ROOT CAUSE CONFIRMED:
- File: [module.py:line]
- Issue: [Final diagnosis]

FIX IMPLEMENTED:
- Solution script: debug/Agent_[X]/solution_[issue].py
- What was changed: [Specific code changes]
- Validation: [How you confirmed it works]

PRODUCTION FIX:
- Files to modify: [List with line numbers]
- Exact changes needed: [Code diff or description]

CONFIDENCE: [HIGH/MEDIUM/LOW]
- Why: [What makes you confident or uncertain]
======================
```

---

## Phase 5: Synthesis + Honest Assessment

**After all agents complete, synthesize results:**

```
HONEST ASSESSMENT & SYNTHESIS
=============================

CONFIDENCE LEVEL: [X%] - [High 80-95% / Medium 60-80% / Low 40-60%]

Why this confidence level:
[Honest explanation based on agent findings]

---

AGENT FINDINGS:

Agent 1 ([Lane]):
- Root Cause: [What they found]
- Fix: [Their solution]
- Validation: [How they tested]
- Confidence: [Their self-assessment]

Agent 2 ([Lane]) - if used:
- Root Cause: [What they found]
- Fix: [Their solution]
- Validation: [How they tested]
- Confidence: [Their self-assessment]

---

SYNTHESIS:

[If 2 agents on same problem]:
- Agreement: [Do they agree on root cause?]
- Best approach: [Which fix looks more robust and why]

[If 2 agents on different problems]:
- Problem A: [Agent 1's findings and fix]
- Problem B: [Agent 2's findings and fix]

---

RECOMMENDED FIX(ES):
[Concrete recommendation based on agent findings]

WHAT COULD BE WRONG:
- [Uncertainty 1]
- [Uncertainty 2]

PROBABILITY FIX WORKS: [X%]
Reasoning: [Why this probability]

=============================
USER DECISION
=============================

Proceed with implementation?
- Yes, implement fix(es)
- No, investigate further: [what]
- Different approach: [specify]
```

**WAIT for user confirmation before implementing.**

---

## Phase 6: Implementation (After Approval)

### 6.1 Implement Fix
- Apply the fix to production code
- Follow agent's recommended changes

### 6.2 MANDATORY STOP

**CRITICAL: After implementing the fix, STOP IMMEDIATELY.**

- DO NOT run tests yourself
- DO NOT validate the fix yourself
- DO NOT iterate on the fix if you "notice" something
- DO NOT run baseline scripts or any validation

**Your job ends at implementation. User validates.**

If you test and find issues, you have already violated the workflow. The user decides what happens next, not you.

---

## Phase 7: User Testing

**After implementation, user validates fix in production environment.**

### 7.1 Handoff to User

```
FIX IMPLEMENTED
===============

Files modified:
- [List of changed files with line numbers]

Changes made:
- [Summary of what was changed]

Ready for user testing.
===============
```

### 7.2 User Tests
- User runs production code with real scenarios
- User confirms fix works / reports issues

### 7.3 After User Confirmation
- If fix works → Run `/document-fix` to document in `bug_fixes/`
- If fix fails → Return to Phase 1 with new findings, document in `not_working/`

---

