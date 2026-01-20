# Delta SkillPack v5.4.1

> 🚀 智能任务执行器 - 统一入口，量化决策，多模型协作，CLI 优先 + 独立审查 + 交叉验证

[![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)](https://claude.ai/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)

## 特性

- 🎯 **统一入口** - `/do "任务"` 一个命令搞定一切
- 🧠 **量化决策** - 6 维度加权评分，决策可追溯
- 🤖 **多模型协作** - Claude + Codex + Gemini 智能分工
- 💾 **中断恢复** - 原子检查点机制，长任务可安全中断
- ✅ **质量保证** - 两阶段审查，规格合规 + 代码质量
- 🔍 **Grounding 机制** - 每个结论必须有代码证据 `file:line` (v5.4)
- 🔄 **独立审查者** - Codex 实现 → Gemini 审查 → Claude 仲裁 (v5.4)
- 🖥️ **CLI 优先** - 使用 `codex exec --full-auto` 和 `gemini -s --yolo` (v5.3)
- ⚡ **异步并行** - 无依赖任务并行执行，显著提升效率 (v5.2)
- 🔀 **CLI 降级** - MCP 失败时自动降级到 CLI 直接调用 (v5.1)

## 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/your-org/delta-skillpack.git
cd delta-skillpack

# 安装 Python 依赖 (推荐使用 uv)
uv sync

# 或使用 pip
pip install -e .
```

### 2. 安装 CLI 工具

```bash
# Codex CLI (GPT-5.2) - 必需
npm install -g @openai/codex

# Gemini CLI (Gemini 3 Pro) - 必需
npm install -g @google/gemini-cli

# NotebookLM MCP (可选 - 知识库功能)
npm install -g notebooklm-mcp
```

### 3. 配置模型

**Codex** (`~/.codex/config.toml`):
```toml
model = "gpt-5.2-codex"
model_reasoning_effort = "xhigh"
```

**Gemini**: 首次运行 `gemini` 命令进行 OAuth 认证

### 4. 验证安装

```bash
# 验证 Codex CLI
codex --version

# 验证 Gemini CLI
gemini --version

# 验证 Skillpack
uv run python -m skillpack.cli --version
```

### 5. 使用

```bash
# 简单任务 (0-20分) → 直接执行
/do "fix typo in README"

# 中等任务 (21-45分) → 规划执行
/do "add user authentication"

# 复杂任务 (46-70分) → 分而治之
/do "build complete CMS"

# 超复杂任务 (71-100分) → 架构优先
/do "design microservice architecture"

# UI 任务 → 用户至上
/do "创建登录页面组件"
```

## 命令参考

### `/do "任务"` - 统一入口

| 参数 | 说明 |
|------|------|
| `--quick, -q` | 强制 DIRECT 路由，跳过规划 |
| `--deep, -d` | 强制 RALPH 路由，深度分析 |
| `--parallel` | 强制启用并行执行 (v5.2) |
| `--no-parallel` | 强制禁用并行执行 (v5.2) |
| `--cli` | 强制使用 CLI 直接调用（绕过 MCP）(v5.1) |
| `--explain, -e` | 仅显示评分和路由决策 |
| `--resume` | 从最近检查点恢复 |
| `--resume <task_id>` | 恢复指定任务 |
| `--list-checkpoints` | 查看可恢复任务 |

**示例：**
```bash
/do "实现用户认证" --quick       # 跳过规划，直接执行
/do "重构整个系统" --deep        # 强制深度分析
/do "实现多个功能" --parallel    # 强制并行执行
/do "fix bug" --cli              # CLI 直接调用
/do "添加按钮" --explain         # 仅显示路由决策
/do --resume                     # 恢复中断任务
```

## 智能路由

### 6 维度评分系统

| 维度 | 权重 | 评估内容 |
|------|------|----------|
| 范围广度 | 25% | 影响文件数量 |
| 依赖复杂度 | 20% | 模块间依赖关系 |
| 技术深度 | 20% | 技术难度/新技术 |
| 风险等级 | 15% | 破坏性/可逆性 |
| 时间估算 | 10% | 预估完成时间 |
| UI 复杂度 | 10% | 界面/交互复杂度 |

### 路由决策

| 总分 | 路由 | 阶段数 | 核心原则 | 执行模型 |
|------|------|--------|----------|----------|
| 0-20 | **DIRECT** | 1 | 立即行动 | Codex CLI |
| 21-45 | **PLANNED** | 3 | 计划先行 | Claude → Codex → Codex |
| 46-70 | **RALPH** | 5 | 分而治之 | Claude → Codex → Gemini → Claude |
| 71-100 | **ARCHITECT** | 6 | 架构优先 | Gemini → Claude → Codex → Gemini → Claude |
| UI 信号 | **UI_FLOW** | 3 | 用户至上 | Gemini → Gemini → Claude |

## AI 模型分工

| 模型 | 配置 | 核心优势 | 最佳场景 |
|------|------|----------|----------|
| **Claude Opus 4.5** | 默认 | 精细控制、任务协调 | 规划、设计、协调、仲裁 |
| **Codex (GPT-5.2)** | xhigh reasoning | 强推理、代码生成 | 代码实现、API 集成、审查 |
| **Gemini 3 Pro** | Preview | 超长上下文、多模态 | 架构分析、UI/UX、独立审查 |

### 路由-模型-阶段完整映射 (v5.4)

| 路由 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|------|---------|---------|---------|---------|---------|---------|
| **DIRECT** | Codex | - | - | - | - | - |
| **PLANNED** | Claude | Codex | Codex | - | - | - |
| **RALPH** | Claude | Claude | Codex | **Gemini** | Claude | - |
| **ARCHITECT** | **Gemini** | Claude | Claude | Codex | **Gemini** | Claude |
| **UI_FLOW** | **Gemini** | **Gemini** | Claude | - | - | - |

**图例**:
- **Codex** = `codex exec --full-auto` (CLI 调用)
- **Gemini** = `gemini -s --yolo` (CLI 调用)
- Claude = 直接执行

## CLI 优先模式 (v5.3+)

v5.3 起默认使用 CLI 直接调用，**禁止 MCP 工具调用**：

### Codex CLI 调用

```bash
# 完全自动模式
codex exec "fix bug in auth.ts" --full-auto

# 带文件上下文
codex exec "implement JWT validation" --full-auto --files src/auth/*.ts
```

### Gemini CLI 调用

```bash
# Sandbox + YOLO 模式
gemini "@src/components analyze UI patterns" -s --yolo

# 带文件引用
gemini "@src/pages/login.tsx implement form validation" -s --yolo
```

### 配置选项

在 `.skillpackrc` 中配置：

```json
{
  "cli": {
    "prefer_cli_over_mcp": true,
    "cli_timeout_seconds": 600,
    "codex_command": "codex",
    "gemini_command": "gemini",
    "auto_context": true,
    "max_context_files": 15
  }
}
```

## 输出目录

```
.skillpack/
├── current/
│   ├── checkpoint.json       # 检查点（支持恢复）
│   ├── checkpoint.json.sha256 # 校验和
│   ├── execution.log.jsonl   # 执行日志
│   ├── 1_plan.md            # 规划阶段输出
│   ├── 2_implementation.md  # 实现阶段输出
│   └── 3_review.md          # 审查阶段输出
└── history/<timestamp>/      # 历史记录归档
```

### 各路由输出文件

| 路由 | 输出文件 |
|------|----------|
| DIRECT | `output.txt` |
| PLANNED | `1_plan.md`, `2_implementation.md`, `3_review.md` |
| RALPH | `1_analysis.md`, `2_plan.md`, `3_subtask_*.md`, `4_review.md`, `5_arbitration.md` |
| ARCHITECT | `1_architecture_analysis.md`, `2_architecture_design.md`, `3_implementation_plan.md`, `4_phase_*.md`, `5_review.md`, `6_arbitration.md` |
| UI_FLOW | `1_ui_design.md`, `2_implementation.md`, `3_preview.md` |

## 检查点与恢复

长任务支持安全中断和恢复：

```bash
# 查看可恢复的任务
/do --list-checkpoints

# 恢复最近任务
/do --resume

# 恢复指定任务
/do --resume task-uuid-1234
```

### 原子检查点 (v5.0)

- SHA-256 校验和保护数据完整性
- write-rename 原子写入模式
- 保留最近 3 个备份版本
- 自动恢复损坏的检查点

## 配置文件

创建 `.skillpackrc` 自定义默认行为：

```json
{
  "version": "5.4",
  "knowledge": {
    "default_notebook": "your-notebook-id",
    "auto_query": true
  },
  "routing": {
    "weights": {
      "scope": 25,
      "dependency": 20,
      "technical": 20,
      "risk": 15,
      "time": 10,
      "ui": 10
    },
    "thresholds": {
      "direct": 20,
      "planned": 45,
      "ralph": 70
    }
  },
  "checkpoint": {
    "auto_save": true,
    "atomic_writes": true,
    "backup_count": 3,
    "save_interval_minutes": 5
  },
  "cli": {
    "prefer_cli_over_mcp": true,
    "cli_timeout_seconds": 600,
    "codex_command": "codex",
    "gemini_command": "gemini"
  },
  "cross_validation": {
    "enabled": true,
    "require_arbitration_on_disagreement": true,
    "min_confidence_for_auto_pass": "high"
  },
  "parallel": {
    "enabled": false,
    "max_concurrent_tasks": 3,
    "poll_interval_seconds": 5,
    "task_timeout_seconds": 300
  }
}
```

## 项目结构

```
delta-skillpack/
├── skillpack/             # Python 包
│   ├── cli.py            # CLI 命令入口
│   ├── models.py         # 数据模型
│   ├── router.py         # 路由决策
│   ├── executor.py       # 执行器策略
│   └── dispatch.py       # CLI/MCP 调度器
├── skills/delta:do/       # Skill 定义
│   ├── CLAUDE.md         # 主执行指令
│   ├── SKILL.md          # Skill 摘要
│   └── modules/          # 模块化规则
├── tests/                 # 测试套件
├── .skillpack/            # 任务输出目录
├── .skillpackrc           # 配置文件
├── pyproject.toml         # Python 项目配置
└── README.md              # 本文件
```

## 设计原则

- **KISS** - 简单的规则评分路由，决策透明
- **SOLID** - 策略模式执行器，单一职责
- **DRY** - 复用评分和检查点逻辑
- **YAGNI** - 仅实现当前需要的功能

## 版本历史

### v5.4.1 (2026-01-20)
- 🔧 **DIRECT_TEXT 修复** - 统一使用 Codex CLI 执行所有 DIRECT 任务
- 📦 **完整 Python 包** - 添加 `skillpack/` 包含 CLI、路由、执行器、调度器
- ✅ **E2E 测试通过** - 配置加载、CLI 调用、路由决策全面验证

### v5.4.0 (2026-01-19)
- 🔍 **Grounding 机制** - 每个结论必须有 `file:line` 格式的代码证据
- 👥 **独立审查者模式** - Codex 实现 → Gemini 审查 → Claude 仲裁
- 🛡️ **保守表述原则** - 禁止绝对表述，强制不确定性声明
- ✅ **交叉验证** - 多模型验证，分歧时 Claude 仲裁
- 📋 **测试分类标准** - 基于代码行为而非文件名判断
- 📚 **NotebookLM 知识锚点** - 文档作为第三验证源（可选）

### v5.3.0 (2026-01-19)
- 🖥️ **CLI 优先模式** - 默认使用 `codex exec --full-auto` 和 `gemini -s --yolo`
- ⛔ **禁止 MCP** - 不使用 `mcp__codex-cli__*` 或 `mcp__gemini-cli__*`
- 5️⃣ **RALPH 5 阶段** - 新增 Phase 4 独立审查 + Phase 5 仲裁验证
- 6️⃣ **ARCHITECT 6 阶段** - 新增 Phase 5 独立审查 + Phase 6 仲裁验证

### v5.2.0 (2026-01-19)
- ⚡ **异步并行执行** - 无依赖任务并行执行，显著提升效率
- 📊 **DAG 依赖分析** - 自动构建任务依赖图，识别可并行任务
- 🌊 **波次管理** - 按依赖分组，同一波次内并行执行
- 🔀 **跨模型并行** - Codex + Gemini 同时工作
- 📡 **TaskOutput 轮询** - 定期检查后台任务状态
- 🔄 **并行恢复** - 中断后可恢复正在执行的并行任务

### v5.1.0 (2026-01-18)
- 🖥️ CLI 直接调用后备机制
- 🔄 MCP 超时自动降级到 CLI
- 📏 任务粒度控制，大任务自动拆分

### v5.0.0 (2026-01-18)
- ⚛️ 原子检查点，SHA-256 校验和保护
- 📝 结构化 JSONL 日志系统
- 🎯 智能 MCP 降级策略

### v4.0.0 (2026-01-17)
- 🔧 MCP 强制调用约束
- 🔁 循环执行引擎 (RALPH/ARCHITECT)
- ⚙️ DIRECT_TEXT/DIRECT_CODE 路由分离

### v3.0.0 (2026-01-16)
- 🎯 统一入口 `/do` 命令
- 🧠 6 维度量化评分系统
- 🤖 多模型协作 (Claude + Codex + Gemini)
- 💾 检查点中断恢复机制
- ✅ 两阶段审查系统

## 测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_router.py -v

# 运行 E2E 测试
uv run pytest tests/e2e/ -v
```

## License

MIT © 2026
