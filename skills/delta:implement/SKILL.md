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
2. **Queries NotebookLM for API docs and implementation patterns** (if configured)
3. Executes code changes using Codex GPT-5.2
4. Creates/modifies files as needed
5. Outputs summary to `.skillpack/runs/<id>/implement/`

## Invocation

```bash
# Execute from a plan file
skill implement -f .skillpack/runs/<id>/plans/plan_1.md

# Direct task description
skill implement "Add error handling to API endpoints"

# With options
skill implement "Task" --full-auto --sandbox workspace-write

# With NotebookLM knowledge integration
skill implement "Task" --notebook <notebook_id>

# Disable knowledge queries
skill implement "Task" --no-knowledge
```

## Knowledge Integration

When `--notebook` is provided, the skill automatically queries NotebookLM for:
- API documentation and interface specs for the task
- Code examples and implementation patterns for similar features

This ensures implementations follow established patterns and use correct APIs.

### Supported Notebook Types
- `api` - API documentation, interface specs
- `patterns` - Implementation patterns, code examples

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
