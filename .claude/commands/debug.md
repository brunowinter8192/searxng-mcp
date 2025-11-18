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
5. Debug workspaces: `debug/Agent_1/`, `debug/Agent_2/`, `debug/Agent_3/` (isolated per agent)
6. Shared testing infrastructure: `debug/scraping_suite/`
   - `domains.txt` - Test URLs for agents to pick from
   - `run_baseline.py` - Reference for environment validation approach
7. Gather: Error messages, stack traces, affected functions with File:Line references

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
    "prompt": "## Problem Description\n<Precise description of what is failing, expected vs actual behavior>\n\n## Investigation Results\n<Findings from Phase 1: error messages, stack traces, affected functions with File:Line references>\n\n## Recommended Starting Points\n<Specific folders and files the subagent should examine first, ordered by relevance>\n\n## CRITICAL: Workspace\nYou MUST create all debug scripts and test files in: debug/Agent_1/\nThis is YOUR isolated workspace. Other agents work in Agent_2/ and Agent_3/.\n\n## CRITICAL: Testing Infrastructure\nFor URL selection and validation:\n- Pick ONE URL from debug/scraping_suite/domains.txt for your tests\n- Reference debug/scraping_suite/run_baseline.py for environment validation approach\n- Your validation must use REAL scraper output, not just isolated function tests"
  }
}
```

Repeat for Agent 2 and Agent 3 with their respective workspace paths.

---

## Phase 2.3: Extract Agent IDs

**CRITICAL:** After launching the 3 agents in parallel, extract their Agent IDs for later resumption.

**Implementation:**
```python
import glob
from pathlib import Path
import time

# Wait briefly for JSONL files to be written
time.sleep(0.5)

# Find Claude projects directory
claude_projects_dir = Path.home() / ".claude" / "projects"
all_agent_files = list(claude_projects_dir.glob("*/agent-*.jsonl"))

# Sort by modification time (newest first)
sorted_agents = sorted(all_agent_files, key=lambda f: f.stat().st_mtime, reverse=True)

# Take the 3 newest (our just-launched agents)
latest_3 = sorted_agents[:3]

# Extract Agent IDs (e.g., "agent-abc123" from "agent-abc123.jsonl")
agent_1_id = latest_3[0].stem  # agent-abc123
agent_2_id = latest_3[1].stem  # agent-def456
agent_3_id = latest_3[2].stem  # agent-ghi789

# Log for reference
print(f"Agent IDs extracted: {agent_1_id}, {agent_2_id}, {agent_3_id}")
```

**Note:** These IDs will be used in Phase 2.4 to resume agents with GO/REDIRECT instructions.

---

## Phase 2.4: Assess Agent Debug Plans & Get User Approval

**CRITICAL:** Agents deliver their debug plans BEFORE executing Step 2 (Reproduce).

After Phase 2 agents return with their initial reports, perform **DUAL ASSESSMENT** and WAIT for user decision.

### Collect Agent Plans

Each agent provides:
1. **Root Cause Analysis** - What they identified as the problem source
2. **Debug Plan** - What they intend to test/reproduce
3. **Planned Scripts** - Which debug scripts they will create in debug/Agent_X/
4. **Validation Strategy** - How they will validate using scraping_suite infrastructure

### Assessment Criteria (DUAL)

#### A. Root Cause Assessment

Analyze root cause findings:

1. **Consensus Check**
   - Do all 3 agents identify the same root cause?
   - If YES with identical solution approach: **Diversify methods**
     → Agent 1: Method X, Agent 2: Method Y, Agent 3: Method Z
   - If NO: Good diversity, let agents test different theories

2. **Sanity Check**
   - Is any root cause analysis "hirnrissig" (obviously wrong)?
   - If YES: **REDIRECT** with hints toward credible analysis
   - If plausible: Let agent test their theory

**Root Cause Consensus:**
- Agent 1: [root cause identified]
- Agent 2: [root cause identified]
- Agent 3: [root cause identified]
- Consensus: YES/NO - [explanation]
- **Action needed:** [None / Diversify solutions / Redirect incorrect analysis]

#### B. Test Strategy Assessment (CRITICAL)

**MANDATORY: All agents MUST use the scraping_suite infrastructure!**

**Required Test Coverage:**
```
✅ Phase 1: Isolated Function Test (debug/Agent_X/)
   - Test scraper functions with imports from src/scraper/
   - Use URL picked from debug/scraping_suite/domains.txt

✅ Phase 2: Real Environment Test (using scraping_suite)
   - Reference debug/scraping_suite/run_baseline.py approach
   - Scrape actual URL from domains.txt
   - Compare output before/after fix
   - Demonstrate concrete improvement with real examples
```

**RED FLAGS (Incomplete Test Strategy):**
```
❌ "Test with mock HTML strings only"
❌ "Validate regex patterns in isolation"
❌ "Test function logic without real scraping"
❌ NO mention of domains.txt
❌ NO mention of run_baseline.py or real scraper output
❌ NO comparison of actual scraping results
```

**Test Strategy Analysis:**
- Agent 1: Uses domains.txt? [YES/NO] | Uses real scraper output? [YES/NO]
- Agent 2: Uses domains.txt? [YES/NO] | Uses real scraper output? [YES/NO]
- Agent 3: Uses domains.txt? [YES/NO] | Uses real scraper output? [YES/NO]

**Approach Overlap Analysis:**
- Agent 1 vs Agent 2: HIGH/MEDIUM/LOW overlap - [explain]
- Agent 1 vs Agent 3: HIGH/MEDIUM/LOW overlap - [explain]
- Agent 2 vs Agent 3: HIGH/MEDIUM/LOW overlap - [explain]

**Coverage Quality:**
- Untested approaches: [list alternative strategies not covered by any agent]
- Diversity rating: EXCELLENT/GOOD/POOR - [explanation]

### Present Assessment to User

Show user complete analysis with recommendations:

```
PHASE 2.4: AGENT PLANS ASSESSMENT
==================================

AGENT 1 ASSESSMENT
------------------
Root Cause: [identified cause]
Planned Approach: [brief summary]
Planned Scripts: [list in debug/Agent_1/]

TEST STRATEGY:
✅/❌ Phase 1 (Isolated): [Tests functions with URL from domains.txt]
✅/❌ Phase 2 (Real Environment): [Uses run_baseline.py approach, compares actual output]
✅/❌ Scraping Suite Integration: [Picks URL from domains.txt, references baseline]

⚠️ ISSUES FOUND:
[Missing scraping_suite usage / isolated-only testing / no real URL testing / etc.]

OVERLAP:
- With Agent 2: [HIGH/MEDIUM/LOW - explain]
- With Agent 3: [HIGH/MEDIUM/LOW - explain]

QUALITY: [EXCELLENT/GOOD/NEEDS_IMPROVEMENT]
DECISION: GO / REDIRECT
REASONING: [Why]

---

AGENT 2 ASSESSMENT
------------------
[Same structure as Agent 1]

---

AGENT 3 ASSESSMENT
------------------
[Same structure as Agent 1]

---

OVERALL ASSESSMENT
==================

Root Cause Consensus: YES/NO
  [If YES: Are solutions identical? → Need diversification?]

Solution Diversity: EXCELLENT/GOOD/POOR
  [If all test same method: Redirect to diversify]

Test Strategy Quality:
  - Agent 1: COMPLETE/INCOMPLETE (uses scraping_suite: YES/NO)
  - Agent 2: COMPLETE/INCOMPLETE (uses scraping_suite: YES/NO)
  - Agent 3: COMPLETE/INCOMPLETE (uses scraping_suite: YES/NO)

---

MY RECOMMENDATIONS:
- Agent 1: [GO / REDIRECT - specific instructions]
- Agent 2: [GO / REDIRECT - specific instructions]
- Agent 3: [GO / REDIRECT - specific instructions]

REASONING: [Why these recommendations ensure complete and diverse testing]
```

**WAIT for user decision.**

Ask: "Should I proceed with these agent assignments, or would you like to redirect any agents to different approaches?"

### User Decision Options

User can:
1. **Approve all**: All agents GO with their planned approaches
2. **Approve with modifications**: Specific agents get REDIRECT instructions
3. **Request changes**: User specifies different approach assignments

### Send Continuation Instructions to Agents

After user approval, resume each agent using the Task tool with `resume` parameter and their extracted Agent IDs:

```python
# Example: Resume Agent 1 with GO instruction
Task(
    subagent_type="debug-specialist",
    description="continue debug (Agent 1)",
    resume=agent_1_id,  # Use extracted ID from Phase 2.3
    prompt="[GO or REDIRECT message below]"
)
```

Resume each agent with specific instructions:

**If GO:**
```
Proceed with your planned approach. Execute Step 2 (Reproduce) as described in your plan.
```

**If REDIRECT (incomplete test strategy):**
```
Your test plan is incomplete. You MUST add real environment validation:
- Pick ONE URL from debug/scraping_suite/domains.txt
- Reference debug/scraping_suite/run_baseline.py for validation approach
- Compare actual scraper output before/after your fix
- Show concrete examples from real scraping, not just isolated tests

Proceed to Step 2 with this enhanced validation strategy.
```

**If REDIRECT (solution diversification needed):**
```
All agents identified the same root cause with identical solution approaches.
To ensure thorough testing, focus on [specific alternative method] instead.

Test [alternative approach] because [reasoning].
Still use scraping_suite infrastructure (domains.txt + run_baseline.py approach).

Proceed to Step 2 with this adjusted approach.
```

**If REDIRECT (incorrect root cause):**
```
Your root cause analysis seems incorrect. Consider [hint toward correct direction].
Re-examine [specific file:line] and [specific behavior].

Still use scraping_suite infrastructure for validation.

Proceed to Step 2 with revised root cause analysis.
```

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
