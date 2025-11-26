---
description: Iterative feature implementation with exploration, planning, and approval gates
argument-hint: [feature-description]
---

## Feature Request

User wants to implement: $ARGUMENTS

---

# Workflow

## Phase 0: Clarify Feature Requirements

**CRITICAL:** Before launching any subagent, you MUST understand exactly what the user wants.

**Analyze $ARGUMENTS for ambiguities:**
- What exactly should this feature do? (Clear functionality description?)
- Where should it be used? (Which tool? Which module?)
- What are the inputs/outputs? (Data flow clear?)
- How should it interact with existing code? (Integration points?)
- Are there any constraints or requirements? (Performance, format, compatibility?)

**For EVERY ambiguity: IMMEDIATELY use `AskUserQuestion`**

Ask 1-4 multiple choice questions to clarify:

**Example questions:**

**If functionality unclear:**
```
Question: "What should this feature do exactly?"
Options:
- Process data and return results
- Fetch external data via API
- Transform/convert existing data
- Add new MCP tool
```

**If integration unclear:**
```
Question: "Where should this feature be integrated?"
Options:
- New @mcp.tool in server.py
- Extend existing tool's module in src/
- New module in existing domain (src/domain/)
- New domain folder entirely
```

**If scope unclear:**
```
Question: "What is the scope of this feature?"
Options:
- Minimal - Single focused function
- Moderate - Small module with 3-5 functions
- Extensive - Full domain with multiple modules
- Just exploring - Not sure yet, need suggestions
```

**Only when 100% crystal clear → proceed to Phase 1: Exploration**

**Why this matters:**
- Subagent will be prompted based on YOUR understanding
- Wrong understanding = wrong exploration = wrong implementation
- One question NOW saves rebuilding entire feature LATER

---

## Phase 1: Exploration

**CRITICAL:**
- Use explore-specialist to understand the codebase broadly
- Focus on finding: existing patterns, relevant modules, similar features, architectural conventions

Launch the Task tool with explore-specialist:

```json
{
  "tool": "Task",
  "parameters": {
    "description": "explore codebase for feature context",
    "subagent_type": "explore-specialist",
    "model": "haiku",
    "prompt": "## Feature to Implement\n$ARGUMENTS\n\n## Exploration Goals\n1. Find existing modules that handle similar functionality\n2. Identify architectural patterns used in the codebase\n3. Locate where this feature would logically fit (new module vs extend existing)\n4. Check for relevant dependencies or cross-module interactions\n5. Review CLAUDE.md and src/domain/DOCS.md for project structure\n\n## Output Required\n- Relevant files with File:Line references\n- Similar patterns already in use\n- Recommended location for implementation\n- Architectural considerations"
  }
}
```

---

## Phase 2: Location & Architecture Proposal

After receiving the exploration report:

### 2.1 Analyze Findings
Based on exploration results, determine:
- Should this be a new module in src/domain/ or extend existing module?
- Which existing modules will be affected?
- What cross-module dependencies are needed?
- Does server.py need a new @mcp.tool?

### 2.2 Present Proposal to User

**Location Recommendation:**
```
IMPLEMENTATION LOCATION
=======================

Recommended Approach: [New Module | Extend Existing | New Tool]

[If New Tool:]
- server.py: Add @mcp.tool definition
- Module: src/[domain]/[tool_name].py
- Reason: [Why new tool is needed]

[If New Module:]
- File: src/[domain]/[module_name].py
- Reason: [Why new module is justified]
- Integrates with: [List affected modules with File:Line]

[If Extend Existing:]
- File: src/[domain]/[existing_module].py
- Functions to add: [List new function signatures]
- Reason: [Why extending is better than new module]

Affected Files:
- server.py:[line] - [what changes if new tool]
- src/[domain]/[file1].py:[line] - [what changes]
- src/[domain]/[file2].py:[line] - [what changes]
```

**Architectural Approach:**
- Follows existing patterns: [describe patterns from exploration]
- CLAUDE.md compliance: [3-section structure, tool parameter design, etc.]
- Cross-module interaction: [how modules will call each other]

### 2.3 Wait for User Approval

**CRITICAL:** WAIT for explicit user confirmation before proceeding.

Ask: "Should I proceed with this location and approach?"

User might want to:
- Choose different location
- Adjust architectural approach
- Ask questions about the proposal

---

## Phase 3: Implementation Planning

**Only after Phase 2 approval.**

### 3.1 Create Detailed Implementation Plan

Break down the feature into specific tasks following CLAUDE.md structure:

```
IMPLEMENTATION PLAN
===================

[If New Tool in server.py:]

@mcp.tool definition:
- Function name: [tool_name]
- Parameters: [list with Annotated + Field descriptions]
- Docstring: [when to use this tool]
- Delegates to: src/[domain]/[module].py

[If New Module: src/[domain]/[module_name].py]

INFRASTRUCTURE Section:
- Import statements: [list required imports]
- Constants: [list any constants needed]

ORCHESTRATOR Section:
- Function: [tool_name]_workflow([parameters])
- Calls in sequence:
  1. [function_1]() - [purpose]
  2. [function_2]() - [purpose]
  3. [function_3]() - [purpose]

FUNCTIONS Section:
1. [function_1_name]([params]) -> [return_type]
   Purpose: [what it does]
   Logic: [brief description]

2. [function_2_name]([params]) -> [return_type]
   Purpose: [what it does]
   Logic: [brief description]

3. [function_3_name]([params]) -> [return_type]
   Purpose: [what it does]
   Logic: [brief description]

[If Extending Existing Module:]

Modifications to src/[domain]/[existing_module].py:

INFRASTRUCTURE Updates:
- Add imports: [list new imports]
- Add constants: [list new constants]

ORCHESTRATOR Updates:
- [Modify existing orchestrator OR keep unchanged]

FUNCTIONS to Add:
[Same function breakdown as above]

---

Cross-Module Changes:
- server.py:[line] - [add tool definition if needed]
- src/[domain]/[module1].py:[line] - [change description]

---

CLAUDE.md Compliance Checklist:
- All code in src/domain/ directory
- 3-section structure (INFRASTRUCTURE, ORCHESTRATOR, FUNCTIONS)
- No emojis in production code
- Function header comments (1 line, WHAT not HOW)
- No inline comments inside function bodies
- Tool parameters use Annotated + Field with descriptions
- Tool docstring describes when/why to use the tool
```

### 3.2 Wait for User Approval

**CRITICAL:** WAIT for explicit user confirmation before implementing.

Present the plan and ask: "Should I implement this feature according to the plan?"

User might want to:
- Adjust function breakdown
- Change implementation details
- Add/remove functionality
- Modify cross-module interactions

---

## Phase 4: Implementation

**Only after Phase 3 approval.**

### 4.1 Execute Implementation

Follow the approved plan step-by-step:

1. **Create/Modify Module File(s)**
   - Write INFRASTRUCTURE section first
   - Write ORCHESTRATOR section (calls only, no logic)
   - Write FUNCTIONS section (ordered by call sequence)
   - Include function header comments (1 line each)

2. **Update server.py (if new tool)**
   - Add import from src/domain/module
   - Add @mcp.tool definition with Annotated + Field parameters
   - Write docstring for when to use tool

3. **Update Cross-Module Dependencies**
   - Modify affected files
   - Add imports where needed

4. **Create Debug/Test Script**
   - File: debug/test_[feature_name].py
   - Include test cases from plan
   - Test against real data

5. **Test the Implementation**
   - Run debug script to verify functionality
   - Check that feature works as expected
   - Fix any issues found

### 4.2 Report Implementation Status

After implementation:

```
IMPLEMENTATION COMPLETE
=======================

Files Created/Modified:
- server.py:[line] - [added tool definition]
- src/[domain]/[new_module].py - [brief description]
- src/[domain]/[changed_module].py:[lines] - [what changed]

Testing:
- debug/test_[feature_name].py - [test results]

Next Steps:
- Update src/[domain]/DOCS.md if contract changed
- Update README.md if new tool added
```

---

**IMPORTANT NOTES:**

1. **Approval Gates:** This command has 2 explicit approval gates:
   - After Phase 2 (location/approach)
   - After Phase 3 (implementation plan)

2. **Iterative Process:** User can request changes at any approval gate. Be flexible.

3. **CLAUDE.md Compliance:** Every implementation MUST follow MCP server standards strictly.

4. **Cross-Module Awareness:** Always consider how new feature integrates with existing modules.

5. **Documentation Sync:** Run /check-docs after implementation to verify documentation needs.
