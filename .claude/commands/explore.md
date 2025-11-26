---
description: Explore codebase with search specialist agent (Haiku)
argument-hint: [question] | [reason why you need this]
---

# Codebase Exploration

You have received an exploration request from the user.

**Full Input:** $ARGUMENTS

---

# Workflow

## Step 1: Parse User Input

The user provides:
- **Question**: What they want to find/understand (before the `|`)
- **Reason**: Why they need this information (after the `|`)

**Format:** `[question] | [reason]`

**If no `|` separator:** Treat entire input as question and infer reason from context.

**Example:**
```
Input: "Where is session discovery logic? | Need to debug filtering issue"
→ Question: "Where is session discovery logic?"
→ Reason: "Need to debug filtering issue"
```

## Step 2: Launch Explore Specialist Agent

Use the Task tool to launch the explore-specialist subagent:

**Parameters:**
```
Tool: Task
Parameters:
  description: "Explore codebase"
  subagent_type: "explore-specialist"
  model: "haiku"
  prompt: |
    EXPLORATION REQUEST

    Question: [extracted question]

    Reason/Goal: [extracted reason]

    Please search the codebase systematically and provide a structured report with:
    - Direct answer to the question
    - Relevant file paths with line numbers (file:line format)
    - Key code patterns found
    - Context specific to the stated goal
```

**Why Haiku:** Fast, efficient searches for codebase exploration.

## Step 3: Wait for Agent Report

The explore-specialist agent will:
- Search codebase systematically (Glob, Grep, Read)
- Analyze relevant files
- Generate structured report with file:line references

**Do not proceed until agent completes its search.**

## Step 4: Present Findings to User

Present the agent's findings in clear, actionable format:

**Structure:**
1. **Direct Answer** - Answer the user's question concisely
2. **Key Discoveries** - Summarize most important findings
3. **Relevant Files** - List files with clickable file:line paths
4. **Code Patterns** - Highlight key patterns/implementations found
5. **Next Steps** - Actionable recommendations based on their reason

**Example format:**
```
The session discovery logic is in src/session_finder.py:34

Key Discoveries:
- find_active_sessions() is the main orchestrator
- Filtering happens in matches_project_filter() at line 84
- Project path encoding in encode_project_path() at line 90

Relevant Files:
- src/session_finder.py:34 (main orchestrator)
- src/session_finder.py:84 (filtering logic)
- src/monitor.py:115 (calls finder with filter)

For your debugging goal (filtering issue):
1. Check src/session_finder.py:84 - matches_project_filter()
2. Verify encoded path format matches expectations
3. Review logs/03_session_discovery.log for filter results
```

---

# Important

- **Fast exploration:** Haiku model keeps exploration quick
- **File:line references:** Enable direct navigation to code
- **Context-aware:** Report addresses user's specific reason/goal
- **No assumptions:** Agent searches systematically, reports what it finds
