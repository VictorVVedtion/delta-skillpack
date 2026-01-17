# Delta SkillPack v2

> **Multi-Engine AI Workflow Orchestration** for Claude Code, Codex GPT-5.2, and Gemini 3 Pro
> _Transform terminal AI agents into repeatable, versioned, git-safe development workflows_

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/tests-192%20passed-brightgreen.svg" alt="192 tests passed">
  <img src="https://img.shields.io/badge/engines-3%20SOTA%20models-purple.svg" alt="3 SOTA Models">
</p>

<p align="center">
  <b>Keywords:</b> Claude Code Skills | AI Coding Assistant | Multi-Model Orchestration | PRD-Driven Development | Autonomous Code Generation | Terminal AI Agent Framework
</p>

---

## What is Delta SkillPack?

Delta SkillPack is a **skill-based workflow orchestrator** that routes tasks to the best AI engine:

| Task Type | Engine | Model | Capability |
|-----------|--------|-------|------------|
| **Planning** | Claude | Opus 4.5 | Extended Thinking for deep architecture analysis |
| **Implementation** | Codex | GPT-5.2 | Extra High reasoning for code generation |
| **UI/UX Design** | Gemini | 3 Pro | Visual understanding with Vercel guidelines |
| **Code Review** | Claude | Opus 4.5 | Extended Thinking for thorough review |
| **Automation** | Ralph | Multi-engine | PRD-driven autonomous development loops |

```bash
# Before: Ad-hoc, single-engine, inconsistent
codex exec "implement auth"

# After: Multi-engine, git-safe, tracked, auditable
skill plan "implement auth"              # Claude Opus 4.5 → 5 variant plans
skill implement -f plan_3.md             # Codex GPT-5.2 → code generation
skill run review                         # Claude Opus 4.5 → code review
```

---

## Capabilities (What It CAN Do)

### Core Skills

| Skill | Engine | Description |
|-------|--------|-------------|
| `skill plan` | Claude Opus 4.5 | Generate 5 implementation plans with Extended Thinking |
| `skill implement` | Codex GPT-5.2 | Execute code from plan with Extra High reasoning |
| `skill run review` | Claude Opus 4.5 | Deep code review with Extended Thinking |
| `skill run ui` | Gemini 3 Pro | UI/UX specs following Vercel Web Interface Guidelines |

### Ralph Automation (PRD-Driven Development)

| Capability | Description |
|------------|-------------|
| **PRD Generation** | Auto-decompose tasks into atomic User Stories |
| **Pipeline Selection** | Route stories to appropriate skill chains by type |
| **Quality Gates** | Automatic pytest + ruff verification |
| **Git Integration** | Auto-branch, auto-commit passing stories |
| **Self-Healing** | Classify errors and apply remediation strategies |
| **Knowledge Learning** | Extract patterns from success/failure for improvement |

### Infrastructure Features

- **Async Parallel Execution** - Run up to 5 variants concurrently
- **Git Safety** - Auto-branch (`skill/<name>/<run_id>`) + auto-stash
- **Type-Safe Config** - Pydantic v2 models with validation
- **Rich Terminal UI** - Progress bars, colored output, tables
- **Pipeline Support** - Chain skills: `plan → implement → review`
- **Extensible** - Add custom workflows via JSON + prompt templates

---

## Limitations (What It CANNOT Do)

### Technical Limitations

| Limitation | Reason |
|------------|--------|
| **No real-time collaboration** | CLI-based, single-user operation |
| **Requires external CLI tools** | Depends on `codex`, `gemini`, `claude` binaries |
| **No IDE integration** | Terminal-only (no VS Code/JetBrains plugins) |
| **No cloud deployment** | Local execution only |
| **Network-dependent** | Requires API connectivity to AI providers |

### Scope Limitations

| What It Won't Do | Why |
|------------------|-----|
| **Replace human judgment** | AI outputs require human review for critical decisions |
| **Handle production deployments** | Development tool only, not CI/CD pipeline |
| **Manage secrets/credentials** | No built-in secrets management |
| **Auto-push to remote** | Safety: requires manual push after review |
| **Bypass security reviews** | Quality gates are advisory, not enforcement |

### Model Limitations

| Model | Limitation |
|-------|------------|
| Claude Opus 4.5 | Context window limits, may truncate large codebases |
| Codex GPT-5.2 | Sandbox restrictions, limited file system access |
| Gemini 3 Pro | Best for visual/UI tasks, less optimal for pure logic |

---

## Quick Start

### Prerequisites

```bash
# Required: Python 3.10+
python --version  # Python 3.10+

# Required: Node.js for CLI tools
node --version    # Node.js 18+

# Required: Git
git --version
```

### Installation

```bash
# Clone repository
git clone https://github.com/user/delta-skillpack-v2.git
cd delta-skillpack-v2

# Install Python package
pip install -e .

# Install AI CLI tools
npm i -g @openai/codex           # Codex GPT-5.2
npm i -g @google/gemini-cli      # Gemini 3 Pro
npm i -g @anthropic-ai/claude-code  # Claude Code

# Authenticate (one-time setup)
codex login
# gemini: uses OAuth automatically
# claude: uses API key or OAuth
```

### Verify Installation

```bash
# Check all dependencies
skill doctor
```

### Basic Usage

```bash
cd /path/to/your/repo

# Generate 5 implementation plans
skill plan "Add user authentication with OAuth"

# Pick best plan and implement
skill implement -f .skillpack/runs/xxx/plans/plan_3.md

# Code review
skill run review

# UI design spec
skill run ui "Mobile-responsive login form"
```

---

## Commands Reference

### Core Commands

| Command | Alias | Description | Engine |
|---------|-------|-------------|--------|
| `skill doctor` | `d` | Check environment setup | - |
| `skill plan <task>` | `p` | Generate 5 implementation plans | Claude Opus 4.5 |
| `skill implement -f <plan>` | `i` | Execute plan with code generation | Codex GPT-5.2 |
| `skill run review` | - | Deep code review | Claude Opus 4.5 |
| `skill run ui <task>` | `u` | Generate UI/UX specification | Gemini 3 Pro |
| `skill pipeline <skills...>` | - | Chain multiple skills | varies |
| `skill history` | `h` | Show recent runs | - |
| `skill list` | `ls` | List available skills | - |

### Ralph Automation Commands

| Command | Description |
|---------|-------------|
| `skill ralph init <task>` | Initialize PRD from task description |
| `skill ralph init -f <file>` | Load existing PRD JSON file |
| `skill ralph status` | Show PRD execution status |
| `skill ralph start` | Start autonomous development loop |
| `skill ralph start --dry-run` | Preview execution without changes |
| `skill ralph cancel` | Cancel running automation |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Delta SkillPack Orchestrator                        │
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
│   │         PRD → Stories → Pipelines → Verify → Commit          │      │
│   └─────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
skillpack/
├── models.py       # Pydantic v2 models (302 LOC)
├── engines.py      # Engine abstraction layer (263 LOC)
├── core.py         # SkillRunner orchestrator (468 LOC)
├── logging.py      # Rich structured logging (200+ LOC)
├── cli.py          # Click CLI with aliases (729 LOC)
└── ralph/          # Autonomous development system
    ├── orchestrator.py  # Story pipeline dispatcher (680 LOC)
    ├── memory.py        # 4-channel persistence (188 LOC)
    ├── verify.py        # Quality gates (128 LOC)
    ├── browser.py       # Playwright MCP integration (141 LOC)
    ├── dev_server.py    # Dev server lifecycle (106 LOC)
    ├── self_heal.py     # Error classification (164 LOC)
    ├── learning.py      # Knowledge extraction (110 LOC)
    └── dashboard.py     # Rich live monitoring (64 LOC)
```

---

## Ralph: PRD-Driven Automation

Ralph transforms a task description into working, tested code through autonomous iteration.

### How It Works

```
Task Description
       │
       ▼
┌──────────────┐
│  PRD Init    │  Decompose into User Stories with types
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│                   Story Execution Loop                    │
│                                                          │
│  for each story in priority order:                       │
│                                                          │
│    Select pipeline by story.type:                        │
│    ┌────────────┬────────────────────────────────────┐  │
│    │ feature    │ plan → implement → review → verify │  │
│    │ ui         │ ui → implement → review → browser  │  │
│    │ refactor   │ plan → implement → review → verify │  │
│    │ test       │ implement → review → verify        │  │
│    │ docs       │ plan → implement → review          │  │
│    └────────────┴────────────────────────────────────┘  │
│                                                          │
│    Run quality gates (pytest + ruff)                     │
│    if passed: git commit + mark complete                 │
│    else: retry (max 3 attempts) or self-heal             │
│                                                          │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│   Complete   │  Output: <promise>COMPLETE</promise>
└──────────────┘
```

### Memory Channels

| Channel | File | Purpose |
|---------|------|---------|
| PRD State | `.skillpack/ralph/prd.json` | Task/story tracking |
| Progress Log | `.skillpack/ralph/progress.txt` | Iteration history |
| Knowledge Base | `.skillpack/ralph/AGENTS.md` | Learned patterns |
| Git History | `git log` | Code change audit |

---

## Configuration

### Workflow Definition (workflows/plan.json)

```json
{
  "name": "plan",
  "engine": "claude",
  "variants": 5,
  "prompt_template": "plan.md",
  "claude": {
    "model": "claude-opus-4-5-20251101",
    "timeout_seconds": 600,
    "extended_thinking": true,
    "dangerously_skip_permissions": false
  },
  "output": {
    "dir": "plans",
    "pattern": "plan_{i}.md"
  }
}
```

### Repository Config (.skillpackrc)

```json
{
  "default_engine": "codex",
  "auto_stash": true,
  "auto_branch": true,
  "parallel_variants": 5,
  "log_level": "info"
}
```

---

## Safety & Security

### Built-in Protections

| Protection | Description |
|------------|-------------|
| **Git branching** | Auto-creates `skill/<name>/<run_id>` branch |
| **Auto-stash** | Preserves uncommitted changes before operations |
| **Sandbox modes** | `read-only`, `workspace-write`, `danger-full-access` |
| **Quality gates** | pytest + ruff must pass before commit |
| **Max retries** | Stories retry max 3 times before failing |
| **No auto-push** | Requires manual push after review |

### Permission Levels

| Mode | Description | Use Case |
|------|-------------|----------|
| `read-only` | No file modifications | Planning, review |
| `workspace-write` | Project files only | Implementation |
| `danger-full-access` | Full system access | Requires explicit flag |

---

## Testing

```bash
# Run all tests (192 tests)
pytest tests/ -v

# With coverage
pytest tests/ --cov=skillpack --cov-report=term-missing

# Lint check
ruff check skillpack/
```

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| models.py | 36 | 95% |
| engines.py | 30 | 80% |
| core.py | 34 | 75% |
| cli.py | 40 | 85% |
| logging.py | 20 | 90% |
| ralph/* | 32 | 45% |

---

## FAQ

### Q: How is this different from raw Codex/Claude usage?

**A:** SkillPack adds:
- Multi-engine routing (best model for each task)
- Git safety (branching, stashing)
- Parallel variant generation
- Quality gates (pytest + ruff)
- Auditable run history
- PRD-driven automation (Ralph)

### Q: Can I use my own AI models?

**A:** Currently supports Codex, Gemini, and Claude. The engine abstraction layer allows adding new engines by implementing the `Engine` protocol.

### Q: Is this production-ready?

**A:** It's designed for development workflows. Production deployment pipelines should use established CI/CD tools.

### Q: How do I handle API rate limits?

**A:** Built-in step-level retry with exponential backoff handles transient rate limits. Configure `StepRetryConfig` for custom behavior.

---

## Comparison

| Feature | Delta SkillPack | Raw CLI | Other Tools |
|---------|-----------------|---------|-------------|
| Multi-engine routing | ✅ | ❌ | Varies |
| Git safety | ✅ Auto-branch/stash | ❌ Manual | Varies |
| Parallel variants | ✅ Up to 5 | ❌ | ❌ |
| Quality gates | ✅ pytest + ruff | ❌ | Varies |
| PRD automation | ✅ Ralph | ❌ | ❌ |
| Run history | ✅ .skillpack/runs | ❌ | Varies |
| Type-safe config | ✅ Pydantic v2 | ❌ | Varies |

---

## Requirements

- **Python**: 3.10+
- **Node.js**: 18+ (for CLI tools)
- **Git**: Any recent version
- **CLI Tools**:
  - `codex` (`npm i -g @openai/codex`)
  - `gemini` (`npm i -g @google/gemini-cli`)
  - `claude` (`npm i -g @anthropic-ai/claude-code`)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Delta SkillPack v2</b><br>
  <sub>Multi-Engine AI Workflow Orchestration</sub><br>
  <sub>Claude Opus 4.5 • Codex GPT-5.2 • Gemini 3 Pro • Ralph Automation</sub>
</p>

<p align="center">
  <i>Built for developers who want repeatable, auditable AI-assisted development</i>
</p>
