---
description: Workflow for documenting a previous bug fix
---

## Fix observations:

User observes: $ARGUMENTS

---

## Workflow

### Step 1: Detailed Failure Analysis (ONLY for failed fixes)

**CRITICAL:** If fix failed, gather detailed information about HOW it failed using AskUserQuestion.

**Ask 3-4 multiple choice questions:**

**Question 1: What happened when you tested the fix?**
```
Options:
- Same problem persists (no change at all)
- Problem got worse (new issues appeared)
- Partially fixed (some improvement but not complete)
- Different problem now (original fixed, new issue)
```

**Question 2: Describe the new/persisting behavior:**
```
Options:
- Nothing displays/renders anymore
- Error messages or crashes appear
- Feature works but with side effects
- Exactly same symptoms as before fix
```

**Question 3: Compared to BEFORE the fix:**
```
Options:
- Exactly the same (no difference)
- Worse than before (regression)
- Slightly better but still broken
- Different symptoms entirely
```

**Question 4: Did you observe any side effects?**
```
Options:
- Yes, critical side effects (blocks other functionality)
- Yes, minor side effects (cosmetic/performance)
- No side effects observed
- Not tested for side effects yet
```

**Use answers to populate "Why It Failed" section with precise details.**

### Step 2: Gather Information

Collect from conversation history and ask user if needed:
1. **Problem Description** - What was the bug/issue?
2. **Root Cause** - What caused it? (from debug agent analysis)
3. **Fix Applied** - What changes were made? (File:Line references)
4. **Testing Results** - What happened when tested?
5. **Why Failed?** (only for failed fixes) - What went wrong?

### Step 3: Generate Documentation

**For SUCCESS → `bug_fixes/[descriptive-name]_YYYYMMDD_HHMMSS.md`:**

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

**For FAILED → `not_working/[descriptive-name]_YYYYMMDD_HHMMSS_failed.md`:**

```markdown
# [Short Bug Title] - FAILED FIX ATTEMPT

**Date:** YYYY-MM-DD HH:MM

## Problem
[How the problem manifested - 2-3 sentences max]

## Attempted Fix
[What was tried - File:Line references]

**Theory:** [Why this approach was expected to work]

## Why It Failed

**What we observed when tested:**
[Outcome from Step 1 Question 1: what happened]

**Specific symptoms:**
- [New/persisting symptoms from Step 1 Question 2]
- [Comparison to before fix from Step 1 Question 3]
- [Side effects from Step 1 Question 4]

**Our best hypothesis for why it failed:**
[Technical explanation of what went wrong]

**Confidence in this analysis:** [X%] - [High/Medium/Low]
[Why we think this / What creates uncertainty]

**What we're still uncertain about:**
- [Unknown factor 1]
- [Alternative explanation 2]
- [What we'd need to investigate to be more certain]

## Next Steps
[Other approaches to try - from other agent analyses or new ideas]
```

### Step 4: Write File

- Generate timestamp: `YYYYMMDD_HHMMSS`
- Create descriptive filename (lowercase, underscores, no spaces)
- Write to appropriate folder
- Confirm to user

---

## Important

- **CONCISE:** Documentation must be short - no prose, only facts
- **ACCURATE:** Use exact File:Line references from implementation
- **COMPLETE:** Include all relevant information for future debugging
- **TIMESTAMPED:** Always use current timestamp in filename
