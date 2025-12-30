# Delta SkillPack v2

> Modern workflow orchestrator for terminal AI agents: **Codex**, **Gemini 3 Pro**, and **Claude Opus 4.5**.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/tests-163%20passed-brightgreen.svg" alt="163 tests passed">
</p>

## Why SkillPack?

Transform ad-hoc prompts into **repeatable, versioned, auditable workflows** with **multi-engine orchestration**:

```bash
# Before: Manual, single-engine, inconsistent
codex exec "implement this feature"

# After: Multi-engine, parallel plans, git-safe, tracked
skill plan "implement this feature"   # → Claude Opus 4.5 generates 5 plans
skill implement -f plan_3.md          # → Codex GPT-5.2 executes selected plan
skill run review "check the code"     # → Claude reviews the implementation
skill run ui "mobile layout"          # → Gemini 3 Pro designs UI
```

## Key Innovation: Multi-Engine Orchestration

```
┌─────────────────────────────────────────────────────────────────┐
│                    SkillPack Orchestrator                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│   │   Claude    │   │   Codex     │   │   Gemini    │          │
│   │  Opus 4.5   │   │  GPT-5.2    │   │   3 Pro     │          │
│   ├─────────────┤   ├─────────────┤   ├─────────────┤          │
│   │ • Planning  │   │ • Coding    │   │ • UI/UX     │          │
│   │ • Review    │   │ • Execute   │   │ • Vision    │          │
│   │ • Reasoning │   │ • Implement │   │ • Design    │          │
│   └─────────────┘   └─────────────┘   └─────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- 🚀 **Async Parallel Execution** - Generate 5 plans concurrently
- 🧠 **Best-in-Class Models** - Opus 4.5, GPT-5.2 Codex, Gemini 3 Pro
- 🔒 **Git Safety** - Auto-branch + stash before changes
- 🎨 **Rich Terminal UI** - Progress bars, colored output
- 📦 **Pipeline Support** - Chain skills: `plan → implement → review`
- 🔌 **Extensible Engines** - Codex, Gemini, Claude (plugin architecture)
- ⚙️ **Type-Safe Config** - Pydantic v2 models, `.skillpackrc`
- 🪝 **Claude Code Hooks** - Quality gates, change tracking

## Quick Start

### Installation

```bash
# From source (recommended)
git clone https://github.com/example/delta-skillpack
cd delta-skillpack
pip install -e .

# Required CLI tools
npm i -g @openai/codex       # Codex CLI
npm i -g @google/gemini-cli  # Gemini CLI
npm i -g @anthropic-ai/claude-code  # Claude Code

# Authenticate each
codex login
# gemini uses OAuth automatically
# claude uses API key or OAuth
```

### Basic Usage

```bash
cd /path/to/your/repo

# Check environment
skill doctor

# Generate 5 implementation plans (Claude Opus 4.5)
skill plan "Add candlestick chart to Trade page"

# Pick a plan and implement (Codex GPT-5.2)
skill implement -f .skillpack/runs/xxx/plans/plan_3.md

# Code review (Claude Opus 4.5)
skill run review "Review the recent changes"

# Generate UI spec (Gemini 3 Pro)
skill run ui "Mobile layout for Trade page"

# Run full pipeline
skill pipeline plan,implement,review --task "Add user authentication"
```

## Commands

| Command | Alias | Description | Engine |
|---------|-------|-------------|--------|
| `skill doctor` | `d` | Check environment | - |
| `skill plan <task>` | `p` | Generate plans (5 variants) | Claude |
| `skill implement -f <plan>` | `i` | Execute a plan | Codex |
| `skill run review <scope>` | - | Code review | Claude |
| `skill run ui <task>` | `u` | Generate UI spec | Gemini |
| `skill run <name> <task>` | `r` | Run any workflow | varies |
| `skill pipeline <skills...>` | - | Chain skills | varies |
| `skill history` | `h` | Show recent runs | - |
| `skill list` | `ls` | List available skills | - |

## Skill Configuration

### plan.json (Claude Opus 4.5)
```json
{
  "name": "plan",
  "engine": "claude",
  "variants": 5,
  "claude": {
    "model": "claude-opus-4-5-20251101",
    "timeout_seconds": 600
  }
}
```

### implement.json (Codex GPT-5.2)
```json
{
  "name": "implement",
  "engine": "codex",
  "depends_on": "plan",
  "codex": {
    "model": "gpt-5.2-codex",
    "sandbox": "workspace-write",
    "approval": "on-request"
  }
}
```

### ui.json (Gemini 3 Pro)
```json
{
  "name": "ui",
  "engine": "gemini",
  "gemini": {
    "model": "gemini-3-pro-preview",
    "timeout_seconds": 300
  }
}
```

## Claude Code Integration

SkillPack integrates with Claude Code hooks for automatic quality assurance:

```json
// ~/.claude/settings.json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python3 ~/.claude/hooks/quality-gate.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python3 ~/.claude/hooks/track-changes.py"
      }]
    }]
  }
}
```

## Output Structure

```
.skillpack/
└── runs/
    └── 20250130_143022/
        ├── meta.json         # Run metadata
        ├── plans/
        │   ├── plan_1.md     # Claude Opus 4.5
        │   ├── plan_2.md
        │   └── ...
        ├── implement/
        │   └── summary.md    # Codex GPT-5.2
        ├── review/
        │   └── review.md     # Claude Opus 4.5
        └── ui/
            └── ui_spec.md    # Gemini 3 Pro
```

## Architecture

```
skillpack/
├── models.py    # Pydantic v2 models (WorkflowDef, RunMeta, etc.)
├── engines.py   # Engine abstraction (Codex, Gemini, Claude)
├── core.py      # Orchestrator (SkillRunner, GitManager, Pipeline)
├── logging.py   # Structured logging with Rich
└── cli.py       # Click CLI with Rich UI
```

## Safety Defaults

- ✅ New git branch: `skill/<skill>/<run_id>`
- ✅ Auto-stash dirty changes
- ✅ Plan skill: read-only sandbox
- ✅ Implement skill: workspace-write (with approval)
- ✅ Quality gates for sensitive files
- ❌ No auto-push/merge
- ❌ No `danger-full-access` by default

## Testing

```bash
# Run all tests
pytest tests/ -v

# 163 tests covering:
# - Models (36 tests)
# - Engines (30 tests)
# - Core logic (34 tests)
# - CLI (40 tests)
# - Logging (20 tests)
```

## Extending

Add custom workflows:

1. Create `workflows/myskill.json`:
```json
{
  "name": "myskill",
  "engine": "claude",
  "variants": 1,
  "prompt_template": "myskill.md",
  "claude": {
    "model": "claude-opus-4-5-20251101"
  },
  "output": {
    "dir": "myskill",
    "pattern": "output.md"
  }
}
```

2. Create `prompts/myskill.md`:
```markdown
# Role
Your role description.

# Goal
{{TASK}}

# Output Format
...
```

3. Run:
```bash
skill run myskill "do something"
```

## Requirements

- Python 3.11+
- Git
- Codex CLI (`npm i -g @openai/codex`)
- Gemini CLI (`npm i -g @google/gemini-cli`)
- Claude Code (`npm i -g @anthropic-ai/claude-code`)

## License

MIT
