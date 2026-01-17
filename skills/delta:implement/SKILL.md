---
name: delta:implement
description: Execute code implementation using Codex GPT-5.2 with full-auto mode and workspace write access.
---

# delta:implement - Code Implementation Skill

## When to Use

Use this skill when:
- Have an approved implementation plan
- Need to write code across multiple files
- Implementing features that require code generation
- Executing refactoring tasks

## What It Does

1. Reads the implementation plan (if provided)
2. Executes code changes using Codex GPT-5.2
3. Creates/modifies files as needed
4. Outputs summary to `.skillpack/runs/<id>/implement/`

## Invocation

```bash
# Execute from a plan file
skill implement -f .skillpack/runs/<id>/plans/plan_1.md

# Direct task description
skill implement "Add error handling to API endpoints"

# With options
skill implement "Task" --full-auto --sandbox workspace-write
```

## Execution Instructions

When this skill is invoked, execute the following:

```bash
cd "{{REPO_PATH}}"
skill implement {{PLAN_FILE:-"{{TASK_DESCRIPTION}}"}} --full-auto
```

## Output

- Implementation summary: `.skillpack/runs/<run_id>/implement/summary.md`
- Code changes are applied directly to the workspace
- Git checkpoint created automatically

## Safety Features

- Creates new git branch: `skill/implement/<run_id>`
- Auto-stashes uncommitted changes
- Sandbox mode: `workspace-write` (no system modifications)

## Integration

After implementation, typically followed by:
1. `delta:review` for code review
2. Test execution
3. Merge or further iterations
