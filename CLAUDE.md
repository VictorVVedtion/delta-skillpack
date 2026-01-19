# OpenAlpha

智能任务执行器 v5.2.0 - 统一入口，量化决策，多模型协作，**异步并行执行**

## 快速开始

```bash
# 基本用法 - 一个命令搞定一切
/do "实现用户认证系统"

# 查看任务复杂度评分和路由决策
/do "add feature X" --explain

# 从中断点恢复
/do --resume

# 启用并行执行（同时执行无依赖任务）
/do "build complete CMS" --parallel

# 使用 CLI 直接调用（绕过 MCP）
/do "fix bug" --cli
```

## v5.2 新特性

| 特性 | 说明 |
|------|------|
| **异步并行执行** | 使用 `run_in_background` 同时启动多个后台任务 |
| **DAG 依赖分析** | 自动构建任务依赖图，识别可并行任务 |
| **波次管理** | 按依赖分组，同一波次内并行执行 |
| **跨模型并行** | Codex + Gemini 同时工作 |
| **TaskOutput 轮询** | 定期检查后台任务状态，收集结果 |
| **并行恢复** | 中断后可恢复正在执行的并行任务 |

## v5.1 特性

| 特性 | 说明 |
|------|------|
| **CLI 直接调用** | `--cli` 标志强制使用 Bash 直接调用 Codex/Gemini |
| **自动 CLI 降级** | MCP 超时后自动切换到 CLI 直接调用 |
| **三层防御策略** | 任务粒度拆分 → MCP 重试 → CLI 降级 |

## 命令参考

### `/do "任务"` - 统一入口

智能分析任务复杂度，自动选择最优执行路径和模型：

```bash
# 文本任务 (DIRECT_TEXT) → Claude 直接执行
/do "fix typo in README"

# 代码任务 (DIRECT_CODE) → Codex 执行
/do "fix bug in auth.ts"

# 中等任务 (PLANNED) → Claude 规划 + Codex 实现
/do "add user authentication"

# 复杂任务 (RALPH) → Claude 分析 + Codex 执行
/do "build complete CMS"

# 超复杂任务 (ARCHITECT) → Gemini 架构 + Claude 设计 + Codex 实施
/do "design new microservice architecture"

# UI 任务 (UI_FLOW) → Gemini 设计/实现
/do "创建登录页面组件"
```

**可选参数：**

| 参数 | 说明 |
|------|------|
| `-q, --quick` | 强制 DIRECT_CODE 路由，跳过规划 |
| `-d, --deep` | 强制 RALPH 路由，深度分析 |
| `--parallel` | 强制启用并行执行（v5.2 新增） |
| `--no-parallel` | 强制禁用并行执行（v5.2 新增） |
| `--cli` | 强制使用 CLI 直接调用（绕过 MCP） |
| `-e, --explain` | 仅显示评分和路由决策 |
| `--resume` | 从最近检查点恢复 |
| `--resume <task_id>` | 恢复指定任务 |
| `--list-checkpoints` | 查看可恢复任务 |

## 智能路由逻辑

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

| 路由 | 执行模式 | 阶段 | 核心原则 | 主执行模型 |
|------|----------|------|----------|------------|
| **DIRECT_TEXT** | 线性 | 1 | 立即行动 | Claude |
| **DIRECT_CODE** | 线性 | 1 | 立即行动 | **Codex** |
| **PLANNED** | 线性 | 3 | 计划先行 | Claude + **Codex** |
| **RALPH** | **循环/并行** | 4 | 分而治之 | Claude + **Codex** |
| **ARCHITECT** | **循环/并行** | 5 | 架构优先 | **Gemini** + Claude + **Codex** |
| **UI_FLOW** | 线性 | 3 | 用户至上 | **Gemini** |

**并行模式 (v5.2)**: RALPH 和 ARCHITECT 路由支持并行执行，同一波次内的无依赖子任务可同时启动。

### 复杂度信号

- **文本简单**: typo, 注释, 文档, 配置, README
- **代码简单**: fix, bug, 单文件修复, 函数添加
- **中等**: 新功能, bug 修复, 小重构
- **复杂**: 系统, 架构, 多模块, 重构
- **超复杂**: 从零构建, 架构设计, 系统迁移
- **UI**: 页面, 组件, 样式, 布局, 前端, jsx, tsx, shadcn, framer-motion...

## 核心功能

### 检查点机制

长任务可安全中断并恢复：

```bash
# 查看可恢复的任务
/do --list-checkpoints

# 恢复最近任务
/do --resume

# 恢复指定任务
/do --resume task-uuid-1234
```

### 两阶段审查

- **阶段 A (规格审查)**: 需求覆盖检查、遗漏功能检测
- **阶段 B (代码质量)**: 代码风格、Bug检测、性能、安全

### 循环执行引擎 (v4.0)

RALPH 和 ARCHITECT 路由使用循环执行模式，通过 Stop Hook 实现"任务未完成自动继续"：

```
开始 → 创建状态文件 → 执行阶段
         ↑                    ↓
         └──── Stop Hook ←────┘
                  ↓
        检测 <promise>TASK_COMPLETE</promise>？
              ├── 否 → 重新注入 Prompt，继续迭代
              └── 是 → 归档状态，结束
```

**状态文件**: `.claude/ralph-delta.local.md`

**默认配置**:
- 最大迭代次数: 20
- 自动检查点间隔: 每 3 个子任务

### 异步并行执行 (v5.2 新增)

当 `parallel.enabled = true` 或使用 `--parallel` 时，子任务可并行执行：

```
1. 构建任务依赖图 (DAG)
   ↓
2. 计算执行波次（无依赖任务分到同一波次）
   ↓
3. 并行启动当前波次所有任务
   │ ┌─────┬─────┬─────┐
   │ │Task1│Task2│Task3│ ← run_in_background: true
   │ └─────┴─────┴─────┘
   ↓
4. TaskOutput 轮询收集结果
   ↓
5. 波次完成后进入下一波次
   ↓
6. 回到 Step 3 直到全部完成
```

**性能提升**:
- 5 个无依赖子任务: ~3x 提速
- UI + Backend 混合: ~1.7x 提速
- 多文件审查: ~2.7x 提速

### MCP 强制调用与 CLI 后备 (v5.1)

指定阶段必须通过 MCP 工具调用对应模型，MCP 失败时可降级到 CLI 直接调用：

#### 强制使用 Codex 的阶段

| 路由 | 阶段 | MCP 工具 |
|------|------|----------|
| DIRECT_CODE | Phase 1 | `mcp__codex-cli__codex` |
| PLANNED | Phase 2-3 | `mcp__codex-cli__codex` |
| RALPH | Phase 2-4 | `mcp__codex-cli__codex` |
| ARCHITECT | Phase 3-5 | `mcp__codex-cli__codex` |

#### 强制使用 Gemini 的阶段

| 路由 | 阶段 | MCP 工具 |
|------|------|----------|
| UI_FLOW | Phase 1-2 | `mcp__gemini-cli__ask-gemini` |
| ARCHITECT | Phase 1 | `mcp__gemini-cli__ask-gemini` |

**核心规则**:
1. ⛔ 禁止替代 - 指定模型阶段禁止 Claude 自己执行
2. 🖥️ CLI 后备 - MCP 失败后可切换到 CLI 直接调用
3. ❌ 禁止静默降级到 Claude - 代码任务需用户确认
4. ✅ 验证输出 - 每阶段明确标注实际使用的模型

### CLI 直接调用 (v5.1 新增)

当 MCP 超时或使用 `--cli` 标志时，直接通过 Bash 调用 CLI：

```bash
# Codex CLI
/cli-codex "fix bug in auth.ts"

# Gemini CLI
/cli-gemini "@src/components analyze UI patterns"
```

## AI 模型分工

按路由自动选择最优模型：

| 模型 | 核心优势 | 最佳场景 |
|------|----------|----------|
| **Claude Opus 4.5** | 精细控制、任务协调、规划分析 | 规划、设计、协调、文档 |
| **Codex (GPT-5.2)** | 强推理、复杂开发、生态成熟 | **代码实现、API集成、审查** |
| **Gemini 3 Pro** | 超长上下文、多模态、视觉理解 | **UI/UX、架构分析、看图写码** |

### 路由-模型-阶段完整映射

| 路由 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|------|---------|---------|---------|---------|---------|
| **DIRECT_TEXT** | Claude | - | - | - | - |
| **DIRECT_CODE** | **Codex** | - | - | - | - |
| **PLANNED** | Claude | **Codex** | **Codex** | - | - |
| **RALPH** | Claude | **Codex** | **Codex** | **Codex** | - |
| **ARCHITECT** | **Gemini** | Claude | **Codex** | **Codex** | **Codex** |
| **UI_FLOW** | **Gemini** | **Gemini** | Claude | - | - |

**图例**：
- **Codex** = 强制使用 `mcp__codex-cli__codex`
- **Gemini** = 强制使用 `mcp__gemini-cli__ask-gemini`
- Claude = 直接执行

### 模型选择原则

1. **代码工作优先 Codex** - 简单代码任务直接用 Codex，复杂任务 Codex 负责实现和审查
2. **前端工作全面 Gemini** - UI 设计、组件实现、样式开发全部交给 Gemini
3. **Claude 负责协调** - 规划、分析、设计、预览验证

## 输出目录

```
.skillpack/
├── current/
│   ├── checkpoint.json       # 检查点（支持恢复）
│   ├── 1_*.md               # 阶段输出
│   └── error.log            # 错误日志
└── history/<timestamp>/      # 历史记录

.claude/
└── ralph-delta.local.md     # 循环状态文件（活跃时）
```

### 输出文件

| 路由 | 输出文件 |
|------|----------|
| DIRECT_TEXT | `output.txt` |
| DIRECT_CODE | `output.txt` |
| PLANNED | `1_plan.md`, `2_implementation.md`, `3_review.md` |
| RALPH | `1_analysis.md`, `2_plan.md`, `3_subtask_*.md`, `4_review.md` |
| ARCHITECT | `1_architecture_analysis.md`, `2_architecture_design.md`, `3_implementation_plan.md`, `4_phase_*.md`, `5_acceptance_review.md` |
| UI_FLOW | `1_ui_design.md`, `2_implementation.md`, `3_preview.md` |

## 配置文件

创建 `.skillpackrc` 配置默认行为：

```json
{
  "version": "5.0",
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
    "save_interval_minutes": 5,
    "max_history": 10
  },
  "mcp": {
    "timeout_seconds": 180,
    "auto_fallback_to_cli": true
  },
  "cli": {
    "codex_path": "codex",
    "gemini_path": "gemini",
    "prefer_cli_over_mcp": false,
    "cli_timeout_seconds": 300
  },
  "parallel": {
    "enabled": false,
    "max_concurrent_tasks": 3,
    "poll_interval_seconds": 5,
    "task_timeout_seconds": 300,
    "allow_cross_model_parallel": true,
    "fallback_to_serial_on_failure": true
  },
  "output": {
    "current_dir": ".skillpack/current",
    "history_dir": ".skillpack/history"
  }
}
```

## 项目结构

```
openalpha/
├── .skillpack/
│   ├── current/              # 当前执行输出
│   └── history/              # 历史记录
├── .skillpackrc              # 配置文件（可选）
├── CLAUDE.md                 # 项目说明
└── pyproject.toml            # 项目配置
```

## MCP 服务器配置

项目使用以下 MCP 服务器实现多模型协作（配置见 `.mcp.json`）：

| 服务器 | 模型 | 用途 |
|--------|------|------|
| `codex-cli` | GPT-5.2 (xhigh reasoning) | **代码实现、API 集成、审查** |
| `gemini-cli` | Gemini 3 Pro Preview | **UI/UX、架构分析、多模态理解** |
| `notebooklm-mcp` | - | 知识库查询、文档管理 |

### 安装依赖

```bash
# Codex CLI (官方)
npm install -g @openai/codex

# Gemini CLI (官方)
npm install -g @google/gemini-cli

# NotebookLM MCP
npm install -g notebooklm-mcp
```

### 模型配置

**Codex** (`~/.codex/config.toml`):
```toml
model = "gpt-5.2-codex"
model_reasoning_effort = "xhigh"
```

**Gemini**: 默认使用 `gemini-3-pro-preview`（通过 Gemini CLI 配置）

## 依赖插件

- **delta-skillpack v5.2.0** - 提供 `/do` 命令及相关 skills（已全局安装）
  - v5.2 新增：异步并行执行（`--parallel` / `--no-parallel`）
  - v5.2 新增：DAG 依赖分析、波次管理
  - v5.2 新增：跨模型并行（Codex + Gemini 同时工作）
  - v5.2 新增：TaskOutput 轮询收集、并行恢复
  - v5.1：`--cli` 标志，CLI 直接调用，自动 CLI 降级
  - v5.0：原子检查点、结构化日志、任务粒度控制
  - v4.0：MCP 强制调用、循环执行引擎
