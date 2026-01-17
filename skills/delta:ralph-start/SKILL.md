---
name: delta:ralph-start
description: Start Ralph autonomous development loop. Executes PRD stories through multi-engine pipeline until completion.
---

# delta:ralph-start - Ralph Autonomous Loop

## When to Use

Use this skill when:
- PRD has been initialized
- Ready for automated development
- Want end-to-end execution without manual intervention
- Complex multi-story implementation

## What It Does

1. Reads PRD from `.skillpack/ralph/prd.json`
2. Selects next story by priority and dependencies
3. Executes story pipeline based on type:
   - **feature**: plan → implement → review → verify
   - **ui**: ui → implement → review → browser
   - **refactor**: plan → implement → review → verify
   - **test**: implement → review → verify
   - **docs**: plan → implement → review
4. Commits successful stories
5. Continues until all stories pass or max iterations

## Invocation

```bash
# Start the loop
skill ralph start

# Preview without execution
skill ralph start --dry-run

# Limit iterations
skill ralph start --max-iterations 50
```

## Execution Instructions

When this skill is invoked, execute the following:

```bash
cd "{{REPO_PATH}}"
skill ralph start
```

## Completion Signal

When all stories are complete, outputs:
```
<promise>COMPLETE</promise>
```

## Memory Channels

Ralph maintains 4 memory channels:
1. **PRD State**: `.skillpack/ralph/prd.json`
2. **Progress Log**: `.skillpack/ralph/progress.txt`
3. **Knowledge Base**: `.skillpack/ralph/AGENTS.md`
4. **Git History**: `git log`

## Integration

Prerequisites:
- `delta:ralph-init` must be run first
- PRD must exist in `.skillpack/ralph/prd.json`

Outputs:
- Completed code changes
- Git commits per story
- Progress documentation
