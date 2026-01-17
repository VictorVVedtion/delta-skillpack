---
name: delta:review
description: Perform thorough code review using Claude Opus 4.5 with extended thinking for deep analysis.
---

# delta:review - Code Review Skill

## When to Use

Use this skill when:
- Implementation is complete
- Before merging code changes
- Need quality assurance
- Want detailed code analysis

## What It Does

1. Analyzes recent code changes (git diff)
2. Reviews against best practices
3. Checks for bugs, security issues, performance problems
4. Generates detailed review report

## Invocation

```bash
# Review recent changes
skill run review

# Review specific files
skill run review --files "src/auth.py,src/models.py"

# With custom scope
skill run review --scope "last 3 commits"
```

## Execution Instructions

When this skill is invoked, execute the following:

```bash
cd "{{REPO_PATH}}"
skill run review {{OPTIONS}}
```

## Output

Review saved to: `.skillpack/runs/<run_id>/review/review.md`

## Review Checklist

The review covers:
- [ ] Code correctness
- [ ] Error handling
- [ ] Security vulnerabilities
- [ ] Performance implications
- [ ] Code style and readability
- [ ] Test coverage
- [ ] Documentation

## Integration

Typically used after:
1. `delta:implement` execution
2. Manual code changes

May lead to:
1. Additional implementation iterations
2. Bug fixes
3. Merge approval
