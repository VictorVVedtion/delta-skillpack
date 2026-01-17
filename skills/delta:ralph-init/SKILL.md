---
name: delta:ralph-init
description: Initialize a PRD (Product Requirements Document) from a task description for Ralph autonomous development.
---

# delta:ralph-init - Ralph PRD Initialization

## When to Use

Use this skill when:
- Starting a complex development task
- Need to break down a large feature into stories
- Want automated end-to-end development
- PRD-driven development workflow

## What It Does

1. Analyzes the task description
2. Generates a structured PRD with user stories
3. Assigns story types (feature, ui, refactor, test, docs)
4. Sets priorities and dependencies
5. Saves PRD for Ralph execution

## Invocation

```bash
# Initialize from task description
skill ralph init "Build a complete user management system with CRUD operations"

# Load existing PRD
skill ralph init -f existing_prd.json
```

## Execution Instructions

When this skill is invoked, execute the following:

```bash
cd "{{REPO_PATH}}"
skill ralph init "{{TASK_DESCRIPTION}}"
```

## Output

PRD saved to: `.skillpack/ralph/prd.json`

## PRD Structure

```json
{
  "id": "PRD-<timestamp>",
  "title": "Task title",
  "stories": [
    {
      "id": "STORY-001",
      "type": "feature|ui|refactor|test|docs",
      "priority": "p0|p1|p2|p3",
      "description": "Story description",
      "acceptance_criteria": ["..."]
    }
  ]
}
```

## Integration

After initialization:
1. Review the generated PRD
2. Optionally edit stories
3. Run `delta:ralph-start` to begin execution
