# OpenAlpha

智能任务执行器 v3.0.0 - 统一入口，量化决策，中断恢复

## 快速开始

```bash
# 基本用法 - 一个命令搞定一切
/do "实现用户认证系统"

# 查看任务复杂度评分和路由决策
/do "add feature X" --explain

# 从中断点恢复
/do --resume
```

## 命令参考

### `/do "任务"` - 统一入口

智能分析任务复杂度，自动选择最优执行路径：

```bash
# 简单任务 (0-20分) → DIRECT 直接执行
/do "fix typo in README"

# 中等任务 (21-45分) → PLANNED 规划执行
/do "add user authentication"

# 复杂任务 (46-70分) → RALPH 自动化
/do "build complete CMS"

# 超复杂任务 (71-100分) → ARCHITECT 架构优先
/do "design new microservice architecture"

# UI 任务 → UI_FLOW
/do "创建登录页面组件"
```

**可选参数：**

| 参数 | 说明 |
|------|------|
| `-q, --quick` | 强制 DIRECT 路由，跳过规划 |
| `-d, --deep` | 强制 RALPH 路由，深度分析 |
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

| 总分 | 路由 | 阶段 | 核心原则 |
|------|------|------|----------|
| 0-20 | **DIRECT** | 1 | 立即行动 |
| 21-45 | **PLANNED** | 3 | 计划先行 |
| 46-70 | **RALPH** | 4 | 分而治之 |
| 71-100 | **ARCHITECT** | 5 | 架构优先 |
| UI 信号 | **UI_FLOW** | 3 | 用户至上 |

### 复杂度信号

- **简单**: typo, 注释, 重命名, 单文件修改
- **中等**: 新功能, bug 修复, 小重构
- **复杂**: 系统, 架构, 多模块, 重构
- **超复杂**: 从零构建, 架构设计, 系统迁移
- **UI**: 页面, 组件, 样式, 布局, 前端

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

## AI 模型分工

按路由自动选择最优模型：

| 模型 | 核心优势 | 最佳场景 |
|------|----------|----------|
| **Claude Opus 4.5** | 精细控制、代码质量、任务协调 | 规划、Debug、重构、协调 |
| **Codex (GPT-5.2)** | 强推理、复杂开发、生态成熟 | 新功能实现、API集成、脚本 |
| **Gemini 3 Pro** | 超长上下文、多模态、视觉理解 | UI/UX、项目分析、看图写码 |

### 路由-模型对应

| 路由 | 阶段分配 |
|------|----------|
| **DIRECT** | Claude (全程) |
| **PLANNED** | Claude (规划) → Codex (实现/审查) |
| **RALPH** | Claude (分析/规划) → Codex (执行/审查) |
| **ARCHITECT** | Gemini (架构分析) → Claude (设计/规划) → Codex (实施/审查) |
| **UI_FLOW** | Gemini (设计/实现) → Claude (预览) |

## 输出目录

```
.skillpack/
├── current/
│   ├── checkpoint.json       # 检查点（支持恢复）
│   ├── 1_*.md               # 阶段输出
│   └── error.log            # 错误日志
└── history/<timestamp>/      # 历史记录
```

### 输出文件

| 路由 | 输出文件 |
|------|----------|
| DIRECT | `output.txt` |
| PLANNED | `1_plan.md`, `2_implementation.md`, `3_review.md` |
| RALPH | `1_analysis.md`, `2_plan.md`, `3_subtask_*.md`, `4_review.md` |
| ARCHITECT | `1_architecture_analysis.md`, `2_architecture_design.md`, `3_implementation_plan.md`, `4_phase_*.md`, `5_acceptance_review.md` |
| UI_FLOW | `1_ui_design.md`, `2_implementation.md`, `3_preview.md` |

## 配置文件

创建 `.skillpackrc` 配置默认行为：

```json
{
  "version": "2.0",
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
  "review": {
    "enabled": true,
    "auto_fix": true
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
| `codex-cli` | GPT-5.2 (xhigh reasoning) | 代码实现、API 集成、复杂开发 |
| `gemini-cli` | Gemini 3 Pro Preview | 架构分析、UI/UX、多模态理解 |
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

- **delta-skillpack v3.0.0** - 提供 `/do` 命令及相关 skills（已全局安装）
