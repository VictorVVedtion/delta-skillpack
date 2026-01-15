# Delta SkillPack v2

> Modern workflow orchestrator for terminal AI agents: **Codex GPT-5.2**, **Gemini 3 Pro**, and **Claude Opus 4.5**.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/tests-191%20passed-brightgreen.svg" alt="191 tests passed">
</p>

## Why SkillPack?

Transform ad-hoc prompts into **repeatable, versioned, auditable workflows** with **multi-engine orchestration**:

```bash
# Before: Manual, single-engine, inconsistent
codex exec "implement this feature"

# After: Multi-engine, parallel plans, git-safe, tracked
skill plan "implement this feature"   # → Claude Opus 4.5 generates 5 plans
skill implement -f plan_3.md          # → Codex GPT-5.2 Extra High executes
skill run review "check the code"     # → Claude Opus 4.5 Extended Thinking
skill run ui "mobile layout"          # → Gemini 3 Pro with Vercel Guidelines

# NEW: Industrial Automation (Ralph)
skill ralph init "Add user authentication with OAuth"
skill ralph start  # → Autonomous PRD-driven development
```

## Key Innovation: Multi-Engine Orchestration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SkillPack Orchestrator                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐      │
│   │     Claude      │   │      Codex      │   │     Gemini      │      │
│   │    Opus 4.5     │   │    GPT-5.2      │   │     3 Pro       │      │
│   ├─────────────────┤   ├─────────────────┤   ├─────────────────┤      │
│   │ • Planning      │   │ • Code Gen      │   │ • UI/UX Design  │      │
│   │ • Review        │   │ • Full-Auto     │   │ • Visual Specs  │      │
│   │ • Extended      │   │ • Extra High    │   │ • Vercel        │      │
│   │   Thinking      │   │   Reasoning     │   │   Guidelines    │      │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘      │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │                    Ralph Automation                          │      │
│   │         PRD-Driven Autonomous Development Loop               │      │
│   │   Story → Skill Pipeline → Verify → Commit → Next Story     │      │
│   └─────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

- 🚀 **Async Parallel Execution** - Generate 5 plans concurrently
- 🧠 **SOTA Models** - Opus 4.5 Extended Thinking, GPT-5.2 Extra High, Gemini 3 Pro
- 🤖 **Ralph Automation** - PRD-driven autonomous development loops
- 🔒 **Git Safety** - Auto-branch + stash before changes
- 🎨 **Rich Terminal UI** - Progress bars, colored output
- 📦 **Pipeline Support** - Chain skills: `plan → implement → review`
- 🌐 **Vercel UI Guidelines** - Industry-standard web interface patterns
- 🔌 **Extensible Engines** - Codex, Gemini, Claude (plugin architecture)
- ⚙️ **Type-Safe Config** - Pydantic v2 models, `.skillpackrc`
- 🪝 **Claude Code Hooks** - Quality gates, change tracking

## Quick Start

### Installation

```bash
# From source
git clone https://github.com/VictorVVedtion/delta-skillpack.git
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

# Pick a plan and implement (Codex GPT-5.2 Extra High)
skill implement -f .skillpack/runs/xxx/plans/plan_3.md

# Code review (Claude Opus 4.5 Extended Thinking)
skill run review "Review the recent changes"

# Generate UI spec (Gemini 3 Pro + Vercel Guidelines)
skill run ui "Mobile layout for Trade page"

# Run full pipeline
skill pipeline plan implement review "Add user authentication"
```

## Commands

| Command | Alias | Description | Engine |
|---------|-------|-------------|--------|
| `skill doctor` | `d` | Check environment | - |
| `skill plan <task>` | `p` | Generate plans (5 variants) | Claude Opus 4.5 |
| `skill implement -f <plan>` | `i` | Execute a plan | Codex GPT-5.2 |
| `skill run review <scope>` | - | Code review | Claude Opus 4.5 |
| `skill run ui <task>` | `u` | Generate UI spec | Gemini 3 Pro |
| `skill run <name> <task>` | `r` | Run any workflow | varies |
| `skill pipeline <skills...>` | - | Chain skills | varies |
| `skill history` | `h` | Show recent runs | - |
| `skill list` | `ls` | List available skills | - |

---

## 🤖 Ralph - Industrial Automation

Ralph is the autonomous development system that transforms a task into working code through PRD-driven iteration.

### Ralph Commands

| Command | Description |
|---------|-------------|
| `skill ralph init <task>` | Initialize PRD from task description |
| `skill ralph init -f <file>` | Load existing PRD JSON file |
| `skill ralph status` | Show PRD execution status |
| `skill ralph start` | Start automation loop |
| `skill ralph start --dry-run` | Preview execution plan |
| `skill ralph next-story --json` | Get next story (for scripts) |
| `skill ralph story-status --story-id <id>` | Check story status |
| `skill ralph cancel` | Cancel running loop |

### How Ralph Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Industrial Automation Pipeline                       │
│                                                                          │
│  ┌─────────────┐                                                        │
│  │ 1. Task     │  User: "Add K-line chart with time range selector"    │
│  └──────┬──────┘                                                        │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────┐  Auto-generate structured PRD                          │
│  │ 2. PRD      │  Split into atomic User Stories                        │
│  │    Init     │  Mark types: feature/ui/refactor/test/docs             │
│  └──────┬──────┘                                                        │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Story Execution Loop                         │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ for each story in priority order:                          │ │   │
│  │  │                                                            │ │   │
│  │  │   Select pipeline based on story.type:                     │ │   │
│  │  │   ┌────────────┬─────────────────────────────────────────┐ │ │   │
│  │  │   │ feature    │ plan → implement → review → verify      │ │ │   │
│  │  │   │ ui         │ ui → implement → review → browser       │ │ │   │
│  │  │   │ refactor   │ plan → implement → review → verify      │ │ │   │
│  │  │   │ test       │ implement → review → verify             │ │ │   │
│  │  │   │ docs       │ plan → implement → review               │ │ │   │
│  │  │   └────────────┴─────────────────────────────────────────┘ │ │   │
│  │  │                                                            │ │   │
│  │  │   Run quality gates (pytest + ruff)                        │ │   │
│  │  │   if passed: git commit + mark complete                    │ │   │
│  │  │   else: retry (max 3 attempts)                             │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────┐                                                        │
│  │ 3. Complete │  Output: <promise>COMPLETE</promise>                   │
│  └─────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Story Types & Pipelines

| Type | When to Use | Skill Pipeline |
|------|-------------|----------------|
| `feature` | Backend/logic functionality | plan → implement → review → verify |
| `ui` | Frontend/visual components | ui → implement → review → browser |
| `refactor` | Code restructuring | plan → implement → review → verify |
| `test` | Test coverage addition | implement → review → verify |
| `docs` | Documentation updates | plan → implement → review |

### Ralph Example

```bash
# Initialize PRD from task
skill ralph init "Add user authentication with OAuth support"

# View generated stories
skill ralph status
# Output:
#   PRD: Add user authentication
#   Stories: 4
#   - STORY-001 [p0] Set up OAuth provider config (feature)
#   - STORY-002 [p1] Create login/logout UI components (ui)
#   - STORY-003 [p1] Implement session management (feature)
#   - STORY-004 [p2] Add authentication tests (test)

# Start autonomous development
skill ralph start

# Ralph will automatically:
# 1. Execute each story through its skill pipeline
# 2. Run quality gates (pytest + ruff)
# 3. Commit passing changes
# 4. Retry failed stories (max 3 times)
# 5. Output <promise>COMPLETE</promise> when done
```

### Memory Persistence

Ralph maintains context across iterations:

| Channel | File | Purpose |
|---------|------|---------|
| PRD State | `.skillpack/ralph/prd.json` | Task tracking |
| Progress Log | `.skillpack/ralph/progress.txt` | Learning history |
| Knowledge Base | `.skillpack/ralph/AGENTS.md` | Pattern accumulation |
| Git History | `git log` | Code changes |

---

## Skill Configuration

### plan.json (Claude Opus 4.5 + Extended Thinking)
```json
{
  "name": "plan",
  "engine": "claude",
  "variants": 5,
  "claude": {
    "model": "claude-opus-4-5-20251101",
    "timeout_seconds": 600,
    "extended_thinking": true
  }
}
```

### implement.json (Codex GPT-5.2 + Extra High Reasoning)
```json
{
  "name": "implement",
  "engine": "codex",
  "depends_on": "plan",
  "codex": {
    "model": "gpt-5.2-codex",
    "sandbox": "workspace-write",
    "full_auto": true,
    "reasoning_effort": "xhigh"
  }
}
```

### review.json (Claude Opus 4.5 + Extended Thinking)
```json
{
  "name": "review",
  "engine": "claude",
  "claude": {
    "model": "claude-opus-4-5-20251101",
    "timeout_seconds": 600,
    "extended_thinking": true
  }
}
```

### ui.json (Gemini 3 Pro + Vercel Guidelines)
```json
{
  "name": "ui",
  "engine": "gemini",
  "gemini": {
    "model": "gemini-3-pro",
    "timeout_seconds": 300
  }
}
```

## Output Structure

```
.skillpack/
├── runs/                           # Per-run outputs
│   └── 20250115_143022/
│       ├── meta.json               # Run metadata
│       ├── plans/
│       │   ├── plan_1.md           # Claude Opus 4.5
│       │   ├── plan_2.md
│       │   └── ...
│       ├── implement/
│       │   └── summary.md          # Codex GPT-5.2
│       ├── review/
│       │   └── review.md           # Claude Opus 4.5
│       └── ui/
│           └── ui_spec.md          # Gemini 3 Pro
│
└── ralph/                          # Ralph automation data
    ├── prd.json                    # PRD task list
    ├── session.json                # Session state
    ├── progress.txt                # Learning log
    ├── AGENTS.md                   # Knowledge base
    ├── screenshots/                # UI verification
    └── iterations/                 # Per-iteration outputs
        └── 001/
            ├── plan_output.md
            ├── implement_output.md
            └── review_output.md
```

## Architecture

```
skillpack/
├── models.py       # Pydantic v2 models (WorkflowDef, PRD, UserStory, etc.)
├── engines.py      # Engine abstraction (Codex, Gemini, Claude)
├── core.py         # Orchestrator (SkillRunner, GitManager, Pipeline)
├── logging.py      # Structured logging with Rich
├── cli.py          # Click CLI with Rich UI + Ralph commands
└── ralph/          # Industrial automation module
    ├── memory.py       # 4-channel persistence
    ├── orchestrator.py # Skill pipeline dispatcher
    ├── verify.py       # Quality gates (pytest + ruff)
    └── browser.py      # Playwright MCP integration

workflows/          # Skill definitions (JSON)
prompts/            # Prompt templates (Markdown)
scripts/            # Automation scripts
    └── ralph-loop.sh   # External loop for context refresh
```

## Safety Defaults

- ✅ New git branch: `skill/<skill>/<run_id>`
- ✅ Auto-stash dirty changes
- ✅ Plan skill: read-only sandbox
- ✅ Implement skill: workspace-write (with approval)
- ✅ Quality gates for sensitive files
- ✅ Max 3 retry attempts per story
- ❌ No auto-push/merge
- ❌ No `danger-full-access` by default

## Testing

```bash
# Run all tests
pytest tests/ -v

# 191 tests covering:
# - Models (36 tests)
# - Engines (30 tests)
# - Core logic (34 tests)
# - CLI (40 tests)
# - Logging (20 tests)
# - Ralph (31 tests)

# Coverage
pytest tests/ --cov=skillpack --cov-report=term-missing
```

## Extending

### Add Custom Workflows

1. Create `workflows/myskill.json`:
```json
{
  "name": "myskill",
  "engine": "claude",
  "variants": 1,
  "prompt_template": "myskill.md",
  "claude": {
    "model": "claude-opus-4-5-20251101",
    "extended_thinking": true
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

- Python 3.10+
- Git
- Codex CLI (`npm i -g @openai/codex`)
- Gemini CLI (`npm i -g @google/gemini-cli`)
- Claude Code (`npm i -g @anthropic-ai/claude-code`)

## License

MIT

---

<p align="center">
  <b>Delta SkillPack v2</b> - Multi-Engine Workflow Orchestration
  <br>
  <sub>Claude Opus 4.5 • Codex GPT-5.2 • Gemini 3 Pro • Ralph Automation</sub>
</p>
