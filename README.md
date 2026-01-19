# Delta SkillPack v3.0.0

> 🚀 智能任务执行器 - 统一入口，量化决策，多模型协作

[![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)](https://claude.ai/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 特性

- 🎯 **统一入口** - `/do "任务"` 一个命令搞定一切
- 🧠 **量化决策** - 6 维度加权评分，决策可追溯
- 🤖 **多模型协作** - Claude + Codex + Gemini 智能分工
- 💾 **中断恢复** - 检查点机制，长任务可安全中断
- ✅ **质量保证** - 两阶段审查，规格合规 + 代码质量

## 快速开始

### 1. 安装 MCP 服务器

```bash
# Codex CLI (GPT-5.2)
npm install -g @openai/codex

# Gemini CLI (Gemini 3 Pro)
npm install -g @google/gemini-cli

# NotebookLM MCP (可选)
npm install -g notebooklm-mcp
```

### 2. 配置模型

**Codex** (`~/.codex/config.toml`):
```toml
model = "gpt-5.2-codex"
model_reasoning_effort = "xhigh"
```

**Gemini**: 首次运行 `gemini` 命令进行 OAuth 认证

### 3. 安装 Claude Code 插件

将 `delta-skillpack` 添加到 Claude Code 插件目录：
```bash
# 插件会自动加载 .mcp.json 配置
```

### 4. 使用

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
| `--explain, -e` | 仅显示评分和路由决策 |
| `--resume` | 从最近检查点恢复 |
| `--resume <task_id>` | 恢复指定任务 |
| `--list-checkpoints` | 查看可恢复任务 |

**示例：**
```bash
/do "实现用户认证" --quick       # 跳过规划
/do "重构整个系统" --deep        # 强制深度分析
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

| 总分 | 路由 | 阶段 | 核心原则 |
|------|------|------|----------|
| 0-20 | **DIRECT** | 1 | 立即行动 |
| 21-45 | **PLANNED** | 3 | 计划先行 |
| 46-70 | **RALPH** | 4 | 分而治之 |
| 71-100 | **ARCHITECT** | 5 | 架构优先 |
| UI 信号 | **UI_FLOW** | 3 | 用户至上 |

## AI 模型分工

| 模型 | 配置 | 最佳场景 |
|------|------|----------|
| **Claude Opus 4.5** | 默认 | 规划、协调、Debug、重构 |
| **Codex (GPT-5.2)** | xhigh reasoning | 代码实现、API 集成、审查 |
| **Gemini 3 Pro** | Preview | 架构分析、UI/UX、多模态 |

### 路由-模型对应

| 路由 | 模型调用链 |
|------|-----------|
| **DIRECT** | Claude (全程) |
| **PLANNED** | Claude → Codex → Codex |
| **RALPH** | Claude → Codex → Codex |
| **ARCHITECT** | Gemini → Claude → Codex |
| **UI_FLOW** | Gemini → Gemini → Claude |

## MCP 服务器配置

项目根目录的 `.mcp.json` 定义了 MCP 服务器：

```json
{
  "mcpServers": {
    "codex-cli": {
      "command": "codex",
      "args": ["mcp-server"]
    },
    "gemini-cli": {
      "command": "npx",
      "args": ["-y", "gemini-mcp-tool"]
    },
    "notebooklm-mcp": {
      "command": "notebooklm-mcp"
    }
  }
}
```

## 输出目录

```
.skillpack/
├── current/
│   ├── checkpoint.json       # 检查点（支持恢复）
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
| RALPH | `1_analysis.md`, `2_plan.md`, `3_subtask_*.md`, `4_review.md` |
| ARCHITECT | `1_architecture_analysis.md`, `2_architecture_design.md`, `3_implementation_plan.md`, `4_phase_*.md`, `5_acceptance_review.md` |
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

## 项目结构

```
delta-skillpack/
├── .mcp.json              # MCP 服务器配置
├── .skillpack/            # 任务输出目录
│   ├── current/           # 当前任务
│   └── history/           # 历史记录
├── .skillpackrc           # 配置文件（可选）
├── CLAUDE.md              # Claude Code 项目文档
└── README.md              # 本文件
```

## 配置文件

创建 `.skillpackrc` 自定义默认行为：

```json
{
  "version": "3.0",
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
    "save_interval_minutes": 5
  },
  "review": {
    "enabled": true,
    "auto_fix": true
  }
}
```

## 设计原则

- **KISS** - 简单的规则评分路由，决策透明
- **SOLID** - 策略模式执行器，单一职责
- **DRY** - 复用评分和检查点逻辑
- **YAGNI** - 仅实现当前需要的功能

## 版本历史

### v3.0.0 (2026-01-18)
- 🎯 统一入口 `/do` 命令
- 🧠 6 维度量化评分系统
- 🤖 多模型协作 (Claude + Codex + Gemini)
- 💾 检查点中断恢复机制
- ✅ 两阶段审查系统
- 📦 MCP 服务器集成

## License

MIT © 2026
