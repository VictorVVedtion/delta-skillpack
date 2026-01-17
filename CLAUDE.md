# Delta SkillPack v2

Multi-engine AI workflow orchestrator for Claude Code.

## Quick Reference

### Available Skills

| Skill | Engine | Use When |
|-------|--------|----------|
| `delta:plan` | Claude Opus 4.5 | Need implementation plans with multiple variants |
| `delta:implement` | Codex GPT-5.2 | Ready to write code from a plan |
| `delta:review` | Claude Opus 4.5 | Implementation complete, need code review |
| `delta:ui` | Gemini 3 Pro | Designing user interfaces |
| `delta:ralph-init` | - | Starting complex multi-story development |
| `delta:ralph-start` | Multi-engine | Running autonomous development loop |
| `delta:ralph-status` | - | Checking Ralph progress |

### Commands

- `/ralph-loop "task"` - Start autonomous development
- `/cancel-ralph` - Stop running Ralph loop

## Skill Routing Rules

### Automatic Routing

When handling user requests, automatically route to appropriate skills:

```
Task Type                          → Skill to Use
──────────────────────────────────────────────────────────
Complex planning (multi-approach)  → delta:plan -n 5
Code implementation (≥3 files)     → delta:implement
Code review needed                 → delta:review
UI/UX design                       → delta:ui
Large autonomous task              → delta:ralph-init → delta:ralph-start
Simple single-file fix             → Direct execution (no skill needed)
```

### Decision Flow

```
User Request
    │
    ├─ Is it a simple fix? ──────────────────→ Execute directly
    │
    ├─ Needs planning? ──────────────────────→ delta:plan
    │       │
    │       └─ User selects plan ────────────→ delta:implement
    │
    ├─ UI/visual design? ────────────────────→ delta:ui
    │
    ├─ Large multi-story task? ──────────────→ delta:ralph-init
    │       │                                      │
    │       └─────────────────────────────────→ delta:ralph-start
    │
    └─ After implementation ─────────────────→ delta:review
```

## CLI Usage

```bash
# Planning
skill plan "Implement feature X" --variants 5

# Implementation
skill implement -f .skillpack/runs/<id>/plans/plan_1.md
skill implement "Task description" --full-auto

# Review
skill run review

# UI Design
skill ui "Design settings page"

# Ralph Autonomous Loop
skill ralph init "Build user management system"
skill ralph status
skill ralph start
skill ralph cancel
```

## Output Locations

All outputs are saved to `.skillpack/`:

```
.skillpack/
├── runs/
│   └── <run_id>/
│       ├── plans/          # plan output
│       ├── implement/      # implementation summary
│       ├── review/         # review reports
│       └── ui/             # UI specifications
└── ralph/
    ├── prd.json           # Product Requirements Document
    ├── progress.txt       # Progress log
    └── AGENTS.md          # Knowledge base
```

## Integration with Superpowers

This skillpack works alongside obra-superpowers:

- Use `superpowers-brainstorming` before `delta:plan` for requirement exploration
- Use `superpowers-systematic-debugging` when fixing issues
- Use `superpowers-test-driven-development` alongside `delta:implement`
- Use `superpowers-verification-before-completion` after `delta:review`

## Git Safety

- Creates new branch: `skill/<skill>/<run_id>`
- Auto-stashes uncommitted changes
- Never force pushes
- Commits only on successful verification
