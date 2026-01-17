---
name: delta:ralph-status
description: Check Ralph execution status, view PRD progress, and story completion rates.
---

# delta:ralph-status - Ralph Status Check

## When to Use

Use this skill when:
- Want to check Ralph progress
- Need to see which stories are complete
- Debugging failed stories
- Monitoring long-running execution

## What It Does

1. Reads current PRD state
2. Calculates completion statistics
3. Shows story statuses
4. Displays recent progress log entries

## Invocation

```bash
# Check status
skill ralph status

# JSON output for scripting
skill ralph status --json

# Check specific story
skill ralph story-status --story-id STORY-001
```

## Execution Instructions

When this skill is invoked, execute the following:

```bash
cd "{{REPO_PATH}}"
skill ralph status {{OPTIONS}}
```

## Output Format

```
PRD: PRD-20250115_143022
Title: User Management System

Stories: 5 total | 3 passed | 1 in-progress | 1 pending
Completion: 60%

| ID        | Type    | Status      | Attempts |
|-----------|---------|-------------|----------|
| STORY-001 | feature | ✅ passed   | 1        |
| STORY-002 | ui      | ✅ passed   | 2        |
| STORY-003 | feature | ✅ passed   | 1        |
| STORY-004 | test    | 🔄 running  | 1        |
| STORY-005 | docs    | ⏳ pending  | 0        |

Recent Progress:
[15:30:22] STORY-004: Starting IMPLEMENT step
[15:28:15] STORY-003: Completed successfully
```

## Integration

Use alongside:
- `delta:ralph-start` for execution
- `skill ralph cancel` to stop running loop
