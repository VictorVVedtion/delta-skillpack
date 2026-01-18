---
name: delta:ui
description: Generate UI/UX specifications using Gemini 3 Pro following Vercel Web Interface Guidelines.
---

# delta:ui - UI/UX Design Skill

## When to Use

Use this skill when:
- Designing user interfaces
- Creating visual specifications
- Frontend component design
- Need UI/UX recommendations

## What It Does

1. Analyzes UI requirements
2. **Queries NotebookLM for UI patterns and component guidelines** (if configured)
3. Considers existing design patterns in the codebase
4. Generates UI specification following Vercel guidelines
5. Outputs design document with component specs

## Invocation

```bash
# Generate UI spec
skill ui "Design a user settings page with profile, preferences, and security tabs"

# With framework context
skill ui "Create login form" --framework react --style tailwind

# With NotebookLM knowledge integration
skill ui "Design settings page" --notebook <notebook_id>

# Disable knowledge queries
skill ui "Design settings page" --no-knowledge
```

## Knowledge Integration

When `--notebook` is provided, the skill automatically queries NotebookLM for:
- UI design patterns and component guidelines for the project
- Existing UI components or design specs to follow

This ensures UI designs are consistent with project design system.

### Supported Notebook Types
- `patterns` - Design patterns, component guidelines

## Execution Instructions

When this skill is invoked, execute the following:

```bash
cd "{{REPO_PATH}}"
skill ui "{{TASK_DESCRIPTION}}"
```

## Output

UI specification saved to: `.skillpack/runs/<run_id>/ui/ui_spec.md`

## Design Principles Applied

- Vercel Web Interface Guidelines
- Responsive design
- Accessibility (WCAG 2.1)
- Dark/light mode support
- Component reusability

## Integration

Typically followed by:
1. `delta:implement` for frontend code
2. `delta:review` for UI code review
3. Browser testing (Ralph BROWSER step)
