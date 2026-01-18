# Delta SkillPack + Obra Superpowers Integration

This document describes how Delta SkillPack's NotebookLM knowledge engine integrates with Obra Superpowers skills.

## Integration Overview

Delta SkillPack enhances Obra Superpowers with external knowledge from NotebookLM:

| Superpower | Knowledge Enhancement |
|------------|----------------------|
| `brainstorming` | Queries for prior art, constraints, and domain context |
| `systematic-debugging` | Searches for known solutions and troubleshooting patterns |
| `test-driven-development` | References testing patterns and examples |
| `verification-before-completion` | Validates against specifications and standards |

## Usage

### With Brainstorming

When using `superpowers-brainstorming`, first run a research workflow:

```bash
# 1. Gather knowledge before brainstorming
skill run research "Implement feature X" --notebook <notebook_id>

# 2. The research output will inform the brainstorming session
```

### With Systematic Debugging

When debugging issues:

```bash
# 1. Query troubleshooting knowledge
skill run research "Debug: <error_message>" --notebook <notebook_id>

# 2. Use the knowledge in debugging process
```

### With TDD

When writing tests:

```bash
# 1. Get testing patterns from knowledge base
skill run research "Testing patterns for <component>" --notebook <notebook_id>

# 2. Apply patterns in TDD workflow
```

## Automatic Integration

When Ralph is configured with NotebookLM:

1. **Self-Healing**: Automatically queries troubleshooting notebook on errors
2. **Learning**: Extracts patterns and suggests notebook uploads
3. **Plan/Review**: Queries relevant notebooks for context

## Configuration

Add to `.skillpackrc`:

```json
{
  "ralph": {
    "use_notebooklm": true,
    "knowledge_query_before_plan": true,
    "knowledge_query_before_review": true,
    "knowledge_query_on_error": true,
    "notebooklm": {
      "enabled": true,
      "default_notebook_id": "<your-notebook-id>",
      "notebooks": [
        {
          "id": "<architecture-notebook>",
          "type": "architecture",
          "keywords": ["ADR", "design", "architecture"]
        },
        {
          "id": "<troubleshooting-notebook>",
          "type": "troubleshoot",
          "keywords": ["error", "fix", "solution"]
        }
      ]
    }
  }
}
```

## Workflow Recommendations

### For New Features

1. `skill run research` → Gather context
2. `superpowers-brainstorming` → Explore approaches
3. `skill plan` → Create implementation plan
4. `skill implement` → Execute plan
5. `skill run review` → Review implementation

### For Bug Fixes

1. `superpowers-systematic-debugging` → Diagnose issue
2. `skill run research` → Find known solutions
3. `superpowers-test-driven-development` → Write failing test
4. `skill implement` → Fix the bug
5. `skill run verify-spec` → Verify fix

### For Code Quality

1. `skill run learn` → Extract patterns from codebase
2. Upload valuable patterns to NotebookLM
3. Reference patterns in future development
