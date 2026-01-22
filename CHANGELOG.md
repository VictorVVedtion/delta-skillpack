# Changelog

All notable changes to Delta SkillPack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [5.4.2] - 2026-01-21

### Added
- Configurable logging module (`skillpack/logging.py`) with:
  - Console and file output with rotation
  - JSON structured logging format
  - Colored console output
  - Task context logging
- Comprehensive CLI execution tests for `dispatch.py` (coverage: 47% → 94%)
- Config schema validation with JSON Schema (`skillpack/schema.py`)
- `CHANGELOG.md` file

### Changed
- Total test coverage: 91.86% (552 tests)
- Version bumped to 5.4.2

## [5.4.1] - 2026-01-20

### Changed
- Unified version number across all modules to 5.4.1

### Added
- Complete Python package (CLI, router, executor, dispatcher)
- E2E tests for config loading, CLI calls, routing decisions

## [5.4.0] - 2026-01-19

### Added
- **Grounding Mechanism** - Enforce `file:line` code evidence for conclusions
- **Independent Reviewer Mode** - Codex implementation → Gemini review → Claude arbitration
- **Conservative Expression Principle** - Prohibit absolute statements
- **Cross-Validation** - Multi-model verification

## [5.3.0] - 2026-01-19

### Added
- **CLI-First Mode** - Default to CLI over MCP
- RALPH 5-phase workflow with independent review and arbitration
- ARCHITECT 6-phase workflow with independent review and arbitration

### Changed
- MCP calls disabled by default for improved stability

## [5.2.0] - 2026-01-19

### Added
- Async parallel execution for independent tasks
- DAG dependency analysis
- Wave-based parallel task management

## [5.1.0] - 2026-01-18

### Added
- CLI direct call fallback mechanism
- MCP timeout auto-degradation
- Task granularity control

## [5.0.0] - 2026-01-18

### Added
- Atomic checkpoints with SHA-256 validation
- Structured JSONL logging
- Smart degradation strategy

### Changed
- Complete checkpoint system rewrite

## [4.0.0] - 2026-01-17

### Added
- MCP forced call constraints
- Loop execution engine
- Route separation

## [3.0.0] - 2026-01-16

### Added
- Unified entry point `/do`
- 6-dimension scoring system
- Multi-model collaboration
- Checkpoint mechanism

[Unreleased]: https://github.com/VictorVVedition/delta-skillpack/compare/v5.4.2...HEAD
[5.4.2]: https://github.com/VictorVVedition/delta-skillpack/compare/v5.4.1...v5.4.2
[5.4.1]: https://github.com/VictorVVedition/delta-skillpack/compare/v5.4.0...v5.4.1
[5.4.0]: https://github.com/VictorVVedition/delta-skillpack/compare/v5.3.0...v5.4.0
[5.3.0]: https://github.com/VictorVVedition/delta-skillpack/compare/v5.2.0...v5.3.0
[5.2.0]: https://github.com/VictorVVedition/delta-skillpack/compare/v5.1.0...v5.2.0
[5.1.0]: https://github.com/VictorVVedition/delta-skillpack/compare/v5.0.0...v5.1.0
[5.0.0]: https://github.com/VictorVVedition/delta-skillpack/compare/v4.0.0...v5.0.0
[4.0.0]: https://github.com/VictorVVedition/delta-skillpack/compare/v3.0.0...v4.0.0
[3.0.0]: https://github.com/VictorVVedition/delta-skillpack/releases/tag/v3.0.0
