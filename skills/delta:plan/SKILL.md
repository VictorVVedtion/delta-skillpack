---
name: delta:plan
description: Generate implementation plans using Claude Opus 4.5 with deep reasoning. Produces 5 variant plans for comparison.
---

# delta:plan - Architecture Planning Skill

## When to Use

Use this skill when:
- Starting a new feature implementation
- Need multiple implementation approaches to compare
- Refactoring requires architectural decisions
- Task complexity warrants detailed planning

## What It Does

1. Analyzes the task requirements
2. Explores the codebase for relevant context
3. Generates 5 variant implementation plans
4. Outputs plans to `.skillpack/runs/<id>/plans/`

## Invocation

```bash
# Via CLI
skill plan "Implement user authentication with JWT"

# With options
skill plan "Task description" --variants 3 --repo /path/to/repo
```

## Execution Instructions

When this skill is invoked, execute the following:

```bash
cd "{{REPO_PATH}}"
skill plan "{{TASK_DESCRIPTION}}" --variants {{VARIANTS:-5}}
```

## Output

Plans are saved to:
- `.skillpack/runs/<run_id>/plans/plan_1.md`
- `.skillpack/runs/<run_id>/plans/plan_2.md`
- ... up to plan_5.md

## Integration

After planning, typically followed by:
1. User reviews and selects a plan
2. `delta:implement` executes the chosen plan
3. `delta:review` validates the implementation
