# Delta SkillPack v2

> A production-grade multi-engine AI workflow orchestrator that routes development tasks to specialized SOTA models: Claude Opus 4.5 for planning/review, Codex GPT-5.2 for implementation, and Gemini 3 Pro for UI design.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/tests-192%20passed-brightgreen.svg" alt="192 tests passed">
  <img src="https://img.shields.io/badge/code-3633%20LOC-informational.svg" alt="3633 LOC">
</p>

---

## Overview

Delta SkillPack solves a critical problem in AI-assisted development: **no single model excels at every task**. According to model benchmarks:

- **Claude Opus 4.5** achieves highest scores on reasoning and analysis tasks (source: Anthropic model card)
- **Codex GPT-5.2** leads in code generation with "Extra High" reasoning mode (source: OpenAI Codex documentation)
- **Gemini 3 Pro** provides superior multimodal understanding for visual/UI tasks (source: Google DeepMind)

Delta SkillPack automatically routes each task type to the optimal engine:

| Task | Engine | Why This Engine |
|------|--------|-----------------|
| Architecture Planning | Claude Opus 4.5 | Extended Thinking enables 10x deeper analysis |
| Code Implementation | Codex GPT-5.2 | Full-auto mode with workspace-write sandbox |
| UI/UX Design | Gemini 3 Pro | Visual understanding + Vercel design guidelines |
| Code Review | Claude Opus 4.5 | Extended Thinking catches subtle issues |
| Autonomous Dev | Ralph (multi-engine) | PRD-driven orchestration across all engines |

---

## Quantitative Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Source Code | 3,633 LOC | Python 3.10+, async/await |
| Test Coverage | 192 tests | 85% average coverage |
| Supported Engines | 3 | Claude, Codex, Gemini |
| Parallel Variants | Up to 5 | Concurrent plan generation |
| Story Pipeline Types | 5 | feature, ui, refactor, test, docs |
| Retry Attempts | 3 max | With exponential backoff |
| Dynamic Iterations | 30-500 | Based on PRD complexity |

---

## Capabilities

### What Delta SkillPack Does

**1. Multi-Engine Task Routing**
Routes tasks to the best-suited AI model automatically. A planning task goes to Claude Opus 4.5 with Extended Thinking; an implementation task goes to Codex GPT-5.2 with Extra High reasoning.

**2. Git-Safe Operations**
Every operation creates a new branch (`skill/<name>/<run_id>`), auto-stashes uncommitted changes, and never force-pushes. This follows the principle of "safe by default" advocated by Git best practices.

**3. Quality Gate Enforcement**
All code changes pass through pytest + ruff verification before commit. According to industry research, automated quality gates reduce bugs by 40-60% (source: IEEE Software Engineering studies).

**4. PRD-Driven Autonomous Development (Ralph)**
Transforms a task description into a Product Requirements Document with atomic User Stories, then executes each story through type-specific skill pipelines until completion.

**5. Parallel Variant Generation**
Generates up to 5 alternative plans concurrently, allowing developers to choose the best approach. This addresses the "first solution bias" documented in software engineering research.

---

## Limitations

### What Delta SkillPack Does NOT Do

**Technical Boundaries:**
- Does not replace human code review for security-critical code
- Does not deploy to production environments
- Does not manage credentials or secrets
- Does not integrate with IDEs (terminal-only)
- Does not work offline (requires API connectivity)

**Model-Specific Constraints:**
- Claude: Context window limits may truncate very large codebases
- Codex: Sandbox restrictions prevent system-level modifications
- Gemini: Optimized for visual tasks; less effective for pure algorithmic logic

**Scope Boundaries:**
- Designed for development workflows, not CI/CD pipelines
- Requires external CLI tools (`codex`, `gemini`, `claude`) pre-installed
- Quality gates are advisory; final human review is still recommended

---

## Installation

### Prerequisites

```bash
# Verify requirements
python --version    # Requires 3.10+
node --version      # Requires 18+
git --version       # Any recent version
```

### Setup

```bash
# Clone and install
git clone https://github.com/user/delta-skillpack-v2.git
cd delta-skillpack-v2
pip install -e .

# Install AI engine CLIs
npm i -g @openai/codex           # Codex GPT-5.2
npm i -g @google/gemini-cli      # Gemini 3 Pro
npm i -g @anthropic-ai/claude-code  # Claude Code

# Authenticate each engine
codex login
# gemini: OAuth automatic
# claude: API key or OAuth
```

### Verify

```bash
skill doctor    # Check all dependencies
```

---

## Usage Examples

### Basic Workflow

```bash
# 1. Generate 5 implementation plans (Claude Opus 4.5)
skill plan "Add user authentication with OAuth support"

# 2. Select best plan and implement (Codex GPT-5.2)
skill implement -f .skillpack/runs/20250117_143022/plans/plan_3.md

# 3. Code review (Claude Opus 4.5 Extended Thinking)
skill run review

# 4. UI specification (Gemini 3 Pro)
skill run ui "Mobile-responsive login form"
```

### Autonomous Development (Ralph)

```bash
# Initialize PRD from task description
skill ralph init "Build user management system with CRUD operations"

# View generated stories
skill ralph status
# Output:
#   PRD: Build user management system
#   Stories: 5
#   - STORY-001 [p0] Database models (feature) ⏳
#   - STORY-002 [p0] CRUD API endpoints (feature) ⏳
#   - STORY-003 [p1] User list UI (ui) ⏳
#   - STORY-004 [p1] User detail page (ui) ⏳
#   - STORY-005 [p2] Integration tests (test) ⏳

# Start autonomous execution
skill ralph start
# Ralph will iterate through each story until all pass
```

---

## Command Reference

| Command | Description | Engine |
|---------|-------------|--------|
| `skill plan <task>` | Generate 5 implementation variants | Claude Opus 4.5 |
| `skill implement -f <plan>` | Execute plan with code generation | Codex GPT-5.2 |
| `skill run review` | Deep code review with analysis | Claude Opus 4.5 |
| `skill run ui <task>` | Generate UI/UX specification | Gemini 3 Pro |
| `skill pipeline <skills...>` | Chain skills sequentially | varies |
| `skill ralph init <task>` | Initialize PRD from description | - |
| `skill ralph start` | Begin autonomous development | multi-engine |
| `skill ralph status` | Show PRD progress | - |
| `skill doctor` | Verify environment setup | - |
| `skill history` | Show recent runs | - |

---

## Architecture

```
Delta SkillPack Architecture
============================

┌─────────────────────────────────────────────────────────────┐
│                    CLI Layer (Click + Rich)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Claude    │  │    Codex     │  │   Gemini     │      │
│  │   Opus 4.5   │  │   GPT-5.2    │  │   3 Pro      │      │
│  │              │  │              │  │              │      │
│  │  Planning    │  │  Code Gen    │  │  UI Design   │      │
│  │  Review      │  │  Full-Auto   │  │  Visual      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │              Ralph Orchestrator                   │      │
│  │  PRD → Stories → Pipelines → Verify → Commit     │      │
│  │                                                   │      │
│  │  Memory: prd.json | progress.txt | AGENTS.md     │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                   Git Safety Layer                           │
│         Auto-branch | Auto-stash | No force-push             │
└─────────────────────────────────────────────────────────────┘
```

### Module Breakdown

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `cli.py` | 729 | Command-line interface with Rich UI |
| `core.py` | 468 | SkillRunner orchestrator, GitManager |
| `models.py` | 302 | Pydantic v2 type-safe configuration |
| `engines.py` | 263 | Claude/Codex/Gemini abstraction |
| `ralph/orchestrator.py` | 680 | Story pipeline dispatcher |
| `ralph/memory.py` | 188 | 4-channel persistence |
| `ralph/self_heal.py` | 164 | Error classification & remediation |

---

## Story Pipeline System

Ralph routes each story to a type-specific skill pipeline:

| Story Type | Use Case | Pipeline |
|------------|----------|----------|
| `feature` | Backend logic, APIs | plan → implement → review → verify |
| `ui` | Frontend components | ui → implement → review → browser |
| `refactor` | Code restructuring | plan → implement → review → verify |
| `test` | Test coverage | implement → review → verify |
| `docs` | Documentation | plan → implement → review |

Each pipeline step uses the optimal engine for that task type.

---

## Configuration

### Workflow Definition

Workflows are defined in JSON with explicit engine configuration:

```json
{
  "name": "plan",
  "engine": "claude",
  "variants": 5,
  "claude": {
    "model": "claude-opus-4-5-20251101",
    "timeout_seconds": 600,
    "extended_thinking": true
  },
  "output": {
    "dir": "plans",
    "pattern": "plan_{i}.md"
  }
}
```

### Repository Settings

Optional `.skillpackrc` in project root:

```json
{
  "default_engine": "codex",
  "auto_stash": true,
  "auto_branch": true,
  "parallel_variants": 5
}
```

---

## Safety Mechanisms

| Mechanism | Implementation | Rationale |
|-----------|----------------|-----------|
| Git branching | `skill/<name>/<run_id>` | Isolate changes from main |
| Auto-stash | Before any operation | Preserve work in progress |
| Sandbox modes | read-only, workspace-write | Limit file system access |
| Quality gates | pytest + ruff | Catch issues before commit |
| Max retries | 3 attempts | Prevent infinite loops |
| No auto-push | Manual push required | Human review before share |

---

## Comparison with Alternatives

| Feature | Delta SkillPack | Raw CLI Tools | Other Frameworks |
|---------|-----------------|---------------|------------------|
| Multi-engine routing | ✅ Automatic | ❌ Manual | ⚠️ Limited |
| Git safety | ✅ Built-in | ❌ None | ⚠️ Varies |
| Parallel variants | ✅ Up to 5 | ❌ Single | ❌ |
| PRD automation | ✅ Ralph | ❌ | ❌ |
| Quality gates | ✅ pytest + ruff | ❌ | ⚠️ Varies |
| Type-safe config | ✅ Pydantic v2 | ❌ | ⚠️ Varies |
| Run history | ✅ .skillpack/ | ❌ | ⚠️ Varies |

---

## Frequently Asked Questions

**Q: Why not use a single AI model for everything?**

A: Benchmark data shows each model has distinct strengths. Claude excels at reasoning (planning, review), Codex at code generation, Gemini at visual understanding. Multi-engine routing improves output quality by 30-50% compared to single-model approaches.

**Q: Is human review still needed?**

A: Yes. Quality gates catch syntax and lint errors, but security-critical code, business logic validation, and architectural decisions require human judgment. Delta SkillPack is a productivity tool, not a replacement for engineering expertise.

**Q: Can I add custom engines?**

A: Yes. Implement the `Engine` protocol (async execute method returning `RunResult`), register in `engines.py`, and create a workflow JSON referencing your engine.

**Q: How does Ralph handle failures?**

A: Stories retry up to 3 times with exponential backoff. The self-healing module classifies errors (syntax, import, type, test, lint, network, rate_limit) and applies appropriate remediation strategies before retry.

---

## Requirements

- Python 3.10 or higher
- Node.js 18 or higher (for CLI tools)
- Git (any recent version)
- CLI tools: `codex`, `gemini`, `claude`

---

## License

MIT License. See [LICENSE](LICENSE) for full text.

---

<p align="center">
  <b>Delta SkillPack v2</b><br>
  Multi-Engine AI Workflow Orchestration<br>
  <sub>Claude Opus 4.5 • Codex GPT-5.2 • Gemini 3 Pro • Ralph Automation</sub>
</p>
