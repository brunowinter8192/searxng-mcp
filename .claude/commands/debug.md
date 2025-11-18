---
description: Systematic debugging with context gathering, debug-specialist subagent and bug documentation
argument-hint: [observation/error-description]
---

## Problem Observation

User observes: $ARGUMENTS

---

## Phase 1: Context Gathering

**CRITICAL:**
- Read the codebase BROADLY to understand the user's problem and effectively prompt the subagent
- If unclear what the user means, ask clarifying questions before prompting the subagent

1. Identify affected modules based on the observation
2. Check bug_fixes/ in root to see if such an issue existed before, it's possible the issue was previously fixed but reappeared due to a new feature
3. Find relevant files in the codebase (max 3-4, focused)
4. Check `logs/` folder if present
5. Determine debug/ location: root-level (simple MCP) or src/[module]/debug/ (complex MCP)
6. Gather: Error messages, stack traces, affected functions with File:Line references

---

## Phase 2: Parallel Multi-Agent Debug

**CRITICAL:** Launch 3 debug-specialist agents in parallel to get multiple perspectives.

**MANDATORY:** Each agent gets its own isolated workspace:
- Agent 1 → `debug/Agent_1/`
- Agent 2 → `debug/Agent_2/`
- Agent 3 → `debug/Agent_3/`

Call 3 Task tools **in a single message** (parallel execution):

```json
{
  "tool": "Task",
  "parameters": {
    "description": "debug issue (Agent 1)",
    "subagent_type": "debug-specialist",
    "prompt": "## Problem Description\n<Precise description of what is failing, expected vs actual behavior>\n\n## Investigation Results\n<Findings from Phase 1: error messages, stack traces, affected functions with File:Line references>\n\n## Recommended Starting Points\n<Specific folders and files the subagent should examine first, ordered by relevance>\n\n## CRITICAL: Workspace\nYou MUST create all debug scripts and test files in: debug/Agent_1/\nThis is YOUR isolated workspace. Other agents work in Agent_2/ and Agent_3/."
  }
}
```

Repeat for Agent 2 and Agent 3 with their respective workspace paths.

---

## Phase 2.4: Assess Agent Debug Plans & Get User Approval

**CRITICAL:** Agents deliver their debug plans BEFORE executing Step 2 (Reproduce).

After Phase 2 agents return with their initial reports, assess their planned approaches and WAIT for user decision.

### Collect Agent Plans

Each agent provides:
1. **Root Cause Analysis** - What they identified as the problem source
2. **Debug Plan** - What they intend to test/reproduce
3. **Planned Scripts** - Which debug scripts they will create
4. **Solution Hypothesis** - Their proposed fix approach

### Assessment Analysis

Analyze and present to yourself first:

**Root Cause Consensus:**
- Agent 1: [root cause identified]
- Agent 2: [root cause identified]
- Agent 3: [root cause identified]
- Consensus: YES/NO - [explanation]

**Approach Overlap Analysis:**
- Agent 1 vs Agent 2: HIGH/MEDIUM/LOW overlap - [explain]
- Agent 1 vs Agent 3: HIGH/MEDIUM/LOW overlap - [explain]
- Agent 2 vs Agent 3: HIGH/MEDIUM/LOW overlap - [explain]

**Coverage Gaps:**
- Untested approaches: [list alternative strategies not covered by any agent]
- Diversity rating: EXCELLENT/GOOD/POOR - [explanation]

### Present Assessment to User

Show user complete analysis with recommendations:

```
AGENT PLAN ASSESSMENT
=====================

AGENT 1 PLAN:
Root Cause: [identified cause]
Approach: [brief summary of planned testing strategy]
Planned Scripts:
- reproduce_[issue].py
- test_[solution].py
- validate_[solution]_*.py
Solution Hypothesis: [what they think will work]

AGENT 2 PLAN:
Root Cause: [identified cause]
Approach: [brief summary of planned testing strategy]
Planned Scripts: [list]
Solution Hypothesis: [what they think will work]

AGENT 3 PLAN:
Root Cause: [identified cause]
Approach: [brief summary of planned testing strategy]
Planned Scripts: [list]
Solution Hypothesis: [what they think will work]

---

OVERLAP ANALYSIS:
- Agent 1 vs 2: [HIGH/MEDIUM/LOW] - [why]
- Agent 1 vs 3: [HIGH/MEDIUM/LOW] - [why]
- Agent 2 vs 3: [HIGH/MEDIUM/LOW] - [why]

COVERAGE GAPS:
- Untested Approaches: [list what's not covered]
- Diversity: [EXCELLENT/GOOD/POOR]

---

MY RECOMMENDATION:
- Agent 1: GO (proceed as planned) / REDIRECT to [alternative approach]
- Agent 2: GO / REDIRECT to [alternative approach]
- Agent 3: GO / REDIRECT to [alternative approach]

REASONING: [Why these recommendations ensure diverse coverage]
```

**WAIT for user decision.**

Ask: "Should I proceed with these agent assignments, or would you like to redirect any agents to different approaches?"

### User Decision Options

User can:
1. **Approve all**: All agents GO with their planned approaches
2. **Approve with modifications**: Specific agents get REDIRECT instructions
3. **Request changes**: User specifies different approach assignments

### Send Continuation Instructions to Agents

After user approval, resume each agent with specific instructions:

**If GO:**
"Proceed with your planned approach. Execute Step 2 (Reproduce) as described in your plan."

**If REDIRECT:**
"Focus on [specific alternative approach] instead. Modify your planned scripts to test [new strategy] because [reason]. Proceed to Step 2 with this adjusted approach."

Agents continue from Step 2 with clear direction.

---

## Phase 2.6: Agent Results Aggregation

After all 3 agents complete, analyze their solutions:

### Comparison Criteria
1. **Consensus Check**: Do all 3 agents identify the same root cause?
2. **Solution Diversity**: How different are the proposed fixes?
3. **Test Quality**: Which agent wrote the most comprehensive debug scripts?
4. **Root Cause Analysis**: Which agent went deepest in identifying the issue?
5. **CLAUDE.md Compliance**: Which solution follows standards best?

### Assessment Output
Present to yourself (before showing user):

```
AGENT COMPARISON REPORT
=======================

Root Cause Consensus:
- Agent 1: [brief summary]
- Agent 2: [brief summary]
- Agent 3: [brief summary]
- Consensus: [YES/NO - explain]

Proposed Solutions:
- Agent 1: [approach summary]
- Agent 2: [approach summary]
- Agent 3: [approach summary]

Test Coverage:
- Agent 1: [files created, test comprehensiveness]
- Agent 2: [files created, test comprehensiveness]
- Agent 3: [files created, test comprehensiveness]

RECOMMENDED SOLUTION: Agent [X]
REASONING: [Why this solution is best - consider all criteria above]

REJECTED SOLUTIONS:
- Agent [Y]: [Why rejected or inferior]
- Agent [Z]: [Why rejected or inferior]
```

---

## Phase 3: Present Multi-Agent Analysis to User

After completing Phase 2.6 aggregation:

1. **Show the Agent Comparison Report** (from Phase 2.6)
2. **Present your recommended solution** with clear reasoning
3. **Highlight key differences** between the 3 approaches
4. **Show consensus areas** (if all agents agreed on root cause)
5. **WAIT for explicit user confirmation** before proceeding
6. Ask: "Should I implement the recommended fix from Agent [X]?"

**IMPORTANT:** User might choose a different agent's solution than your recommendation. Be prepared to implement their choice.

---

## Phase 4: Implementation and Documentation (after Approval)

### 4.1 Implement Fix
- Apply the proposed fix
- Test the changes

### 4.15 Validate Scraper Quality (If Scraper Modified)

**CRITICAL:** If the fix modified `src/scraper/scrape_url.py`, validate quality impact.

**Detection:**
- Check if `src/scraper/scrape_url.py` was changed in the fix
- If YES: Proceed with validation
- If NO: Skip to Phase 4.2

**Launch tester-specialist agent:**

Use the Task tool to run quality validation:

```json
{
  "tool": "Task",
  "parameters": {
    "description": "validate scraper quality after fix",
    "subagent_type": "tester-specialist",
    "model": "haiku",
    "prompt": "## Context\nBug fix applied to src/scraper/scrape_url.py.\n\n## Fix Description\n[Brief description of what was fixed]\n\n## Task\nRun the scraping suite baseline and comparison to validate the fix maintains or improves content extraction quality across all test domains.\n\n## Required Analysis\n1. Execute baseline suite\n2. Compare with previous iteration\n3. Analyze character/word count changes\n4. Review content diffs for regressions\n5. Assess: PASS (no regressions) / REVIEW (changes need review) / FAIL (regressions detected)\n\n## Required Output\n- Domain-by-domain analysis with concrete evidence\n- Overall assessment (PASS/REVIEW/FAIL)\n- Clear recommendation"
  }
}
```

**Wait for validation report.**

**Decision Gates:**
- **PASS**: Quality maintained or improved → Proceed to Phase 4.2
- **REVIEW**: Moderate changes detected → Present findings to user, wait for approval before Phase 4.2
- **FAIL**: Regressions detected → Return to Phase 4.1, refine the fix based on tester-specialist findings

**If FAIL:**
1. Review tester-specialist report to understand regressions
2. Refine fix in the selected agent's workspace (Agent_1/2/3/)
3. Re-apply fix
4. Re-run Phase 4.15 validation
5. Iterate until PASS or REVIEW

### 4.2 Document Bug Fix
**Location:** `bug_fixes/` (in project root)

**Filename:** `[descriptive-name]_YYYYMMDD_HHMMSS.md`

**Format (CONCISE):**
```markdown
# [Short Bug Title]

**Date:** YYYY-MM-DD HH:MM

## Problem
[How the problem manifested - 2-3 sentences max]

## Root Cause
[What was the root cause - 2-3 sentences max]

## Fix
[How it was fixed - File:Line references]
```

**IMPORTANT:** Documentation must be short and concise - no prose, only facts.
