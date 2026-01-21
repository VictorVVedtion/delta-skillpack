---
name: do
description: 智能任务执行器 - 抗幻觉升级（Grounding + 独立审查 + 保守表述 + CLI优先）
version: 5.4.2
---

# delta:do - 智能任务执行器 v5.4.0

## 核心法则

1. **量化决策** - 6 维度加权评分，决策可追溯
2. **CLI 优先** - Codex/Gemini 通过 CLI 直接调用，避免 MCP 中断
3. **中断可恢复** - 检查点机制，长任务安全中断
4. **质量保证** - 两阶段审查，规格合规 + 代码质量
5. **立即行动** - 不只解释，真正执行
6. **异步并行** - 同时执行多个无依赖任务，显著提升效率 (v5.2)
7. **抗幻觉** - Grounding + 独立审查 + 保守表述 (v5.4)
8. **证据优先** - 每个结论必须有代码证据支撑 (v5.4)
9. **真实执行** - 禁止 mock 数据，所有 CLI 调用必须真实执行 (v5.4.2)

---

## v5.4 新特性

| 特性 | 说明 |
|------|------|
| **Grounding 机制** | 每个结论必须有 `file:line` 格式的代码证据 |
| **独立审查者模式** | Codex 实现 → Gemini 审查（不同模型交叉审查） |
| **保守表述原则** | 禁止绝对表述，强制不确定性声明 |
| **交叉验证** | 多模型验证，Claude 仲裁分歧 |
| **测试分类标准** | 基于代码行为而非文件名判断 |
| **NotebookLM 知识锚点** | 文档作为第三验证源（可选） |

## v5.2 新特性

| 特性 | 说明 |
|------|------|
| **异步并行执行** | 使用 `run_in_background` 同时启动多个任务 |
| **DAG 依赖分析** | 自动构建任务依赖图，识别可并行任务 |
| **波次管理** | 按依赖分组，同一波次内并行执行 |
| **跨模型并行** | Codex + Gemini 同时工作 |
| **TaskOutput 轮询** | 定期检查后台任务状态，收集结果 |
| **并行恢复** | 中断后可恢复正在执行的并行任务 |

## v5.0/5.1 特性

| 特性 | 说明 |
|------|------|
| **原子检查点** | SHA-256 校验和 + write-rename 模式，数据不丢失 |
| **CLI 直接调用** | `--cli` 标志绕过 MCP，直接通过 Bash 调用 |
| **自动 CLI 降级** | MCP 超时后自动切换到 CLI |
| **结构化日志** | JSONL 格式执行日志，便于追踪和分析 |
| **任务粒度控制** | 自动拆分大任务，避免 MCP 超时 |
| **智能降级策略** | 文档任务可快速降级，代码任务需确认 |

---

## 调用方式

```bash
/do <任务描述>                # 智能路由
/do <任务描述> --quick        # 强制 DIRECT_CODE
/do <任务描述> --deep         # 强制 RALPH
/do <任务描述> --parallel     # 强制启用并行执行 (v5.2)
/do <任务描述> --no-parallel  # 强制禁用并行执行 (v5.2)
/do <任务描述> --explain      # 仅显示评分和路由
/do --resume                  # 从检查点恢复
/do --resume <task_id>        # 恢复指定任务
/do --list-checkpoints        # 查看可恢复任务
```

## 示例

```
/do fix typo in README                      # → DIRECT_TEXT (Codex v5.4.1+)
/do fix bug in auth.ts                      # → DIRECT_CODE (Codex)
/do add user authentication with JWT        # → PLANNED (Claude + Codex)
/do 完整 fork hyperliquid SDK               # → RALPH (Claude + Codex)
/do design microservice architecture        # → ARCHITECT (Gemini + Claude + Codex)
/do 创建登录页面组件                          # → UI_FLOW (Gemini)
/do add shadcn dialog with framer animation # → UI_FLOW (Gemini)
```

---

## 路由决策

基于 `modules/scoring.md` 的 6 维度评分（总分 100）：

| 总分 | 路由 | 阶段 | 核心原则 |
|------|------|------|----------|
| 0-20 | **DIRECT** | 1 | 立即行动 |
| 21-45 | **PLANNED** | 3 | 计划先行 |
| 46-70 | **RALPH** | 4 | 分而治之 |
| 71-100 | **ARCHITECT** | 5 | 架构优先 |
| UI 信号 | **UI_FLOW** | 3 | 用户至上 |

### 复杂度信号

**UI 任务信号 (优先级最高) → UI_FLOW 路由:**
- 基础关键词: ui, ux, 界面, 组件, component, 页面, page, 布局, layout, 样式, css, 前端, frontend
- 框架: jsx, tsx, hook, useState, vue, next, nuxt, svelte, astro
- 样式系统: shadcn, radix, chakra, material-ui, antd, styled-components, emotion, sass
- 动画: framer, framer-motion, gsap, animation, transition
- 响应式: responsive, breakpoint, flex, grid, mobile
- 组件: button, form, modal, card, table, tabs, dialog, toast

**文本简单任务信号 → DIRECT_TEXT 路由:**
- 包含: typo, 拼写, readme, 文档, docs, comment, 注释, config, 配置
- 文件类型: .md, .txt, .json, .yaml, .toml
- 描述少于 8 个词且不涉及代码

**代码简单任务信号 → DIRECT_CODE 路由:**
- 包含: fix, bug, function, method, add, remove, implement, 修复, 实现
- 文件类型: .ts, .js, .py, .go, .rs, .java, .tsx, .jsx
- 不匹配 DIRECT_TEXT 的简单任务

**超复杂任务信号 → ARCHITECT 路由:**
- 包含: architecture, 架构, microservice, 微服务, design system, 系统设计
- 包含: 从零, from scratch + 大型项目
- 描述超过 50 个词且涉及多系统

**复杂任务信号 → RALPH 路由:**
- 包含: system, 系统, 完整, complete, 多模块, 重构, refactor
- 包含: fork, clone, 构建, build + 项目名
- 描述超过 30 个词

**中等任务信号 → PLANNED 路由:**
- 默认路由，不匹配以上类别

---

## CLI 优先模式（v5.3.0+ 强制）

所有 Codex/Gemini 调用必须使用 CLI 直接调用，不使用 MCP。

### CLI 调用命令

| 模型 | CLI 命令 |
|------|----------|
| **Codex** | `codex exec "<prompt>" --full-auto` |
| **Gemini** | `gemini "<prompt>" -s --yolo` |

### 核心约束

1. **⛔ 禁止 MCP** - 不使用 `mcp__codex-cli__*` 或 `mcp__gemini-cli__*`
2. **✅ 使用 Bash** - 通过 Bash 工具执行 CLI 命令
3. **✅ 自动批准** - Codex 加 `--full-auto`，Gemini 加 `--yolo`

### 强制 Codex 阶段

| 路由 | 阶段 | CLI 命令 |
|------|------|----------|
| DIRECT_CODE | Phase 1 | `codex exec --full-auto` |
| PLANNED | Phase 2-3 | `codex exec --full-auto` |
| RALPH | Phase 3 | `codex exec --full-auto` |
| ARCHITECT | Phase 4 | `codex exec --full-auto` |

### 强制 Gemini 阶段

| 路由 | 阶段 | CLI 命令 |
|------|------|----------|
| UI_FLOW | Phase 1-2 | `gemini -s --yolo` |
| ARCHITECT | Phase 1 | `gemini -s --yolo` |
| **RALPH** | **Phase 4 (独立审查)** | `gemini -s --yolo` **(v5.4 新增)** |
| **ARCHITECT** | **Phase 5 (独立审查)** | `gemini -s --yolo` **(v5.4 调整)** |

---

## 执行策略

### DIRECT_TEXT（文本直接执行）- Codex (v5.4.1+)

```
Phase 1 (100%): Codex 执行
  └── Codex CLI 直接操作（文本/配置/文档修改）
```

### DIRECT_CODE（代码直接执行）- Codex

```
Phase 1 (100%): Codex 执行
  ├── Claude 收集相关文件内容
  ├── **调用 Codex**（CLI 或 MCP，由配置决定）
  └── 验证并应用变更
```

### PLANNED（计划执行）- Claude + Codex

```
Phase 1 (30%): 规划 - Claude
Phase 2 (60%): 实现 - Codex (由配置决定 CLI/MCP)
Phase 3 (100%): 审查 - Codex (由配置决定 CLI/MCP)
```

### RALPH（复杂任务自动化）- Claude + Codex + Gemini (v5.4)

```
Phase 1 (20%): 深度分析    - Claude
Phase 2 (40%): 规划        - Claude
Phase 3 (65%): 执行子任务  - Codex (CLI)
Phase 4 (85%): 独立审查    - Gemini (CLI) ← v5.4 新增！
Phase 5 (100%): 仲裁验证   - Claude ← v5.4 新增！
```

### ARCHITECT（架构优先）- Gemini + Claude + Codex (v5.4)

```
Phase 1 (15%): 架构分析    - Gemini (CLI)
Phase 2 (25%): 架构设计    - Claude
Phase 3 (40%): 实施规划    - Claude
Phase 4 (65%): 分阶段实施  - Codex (CLI)
Phase 5 (85%): 独立审查    - Gemini (CLI) ← v5.4 调整！
Phase 6 (100%): 仲裁验证   - Claude ← v5.4 新增！
```

### UI_FLOW（UI 流程）- Gemini

```
Phase 1 (30%): UI 设计 - Gemini (由配置决定 CLI/MCP)
Phase 2 (60%): 实现 - Gemini (由配置决定 CLI/MCP)
Phase 3 (100%): 预览验证 - Claude
```

---

## 阶段转换提示

**每个阶段开始时，输出清晰的进度提示**：

```
════════════════════════════════════════════════════════════
📍 Phase {N}/{TOTAL}: {阶段名称} ({Phase Name})
════════════════════════════════════════════════════════════
进度: {进度条} {百分比}%
上一阶段: {状态图标} {上一阶段结果}
当前任务: {当前阶段的目标}
执行模型: {Claude | Codex (MCP) | Gemini (MCP)}
输出文件: {对应的输出文件路径}
────────────────────────────────────────────────────────────
```

---

## 错误处理

### 模型调用失败

```
════════════════════════════════════════════════════════════
⚠️ 模型调用失败
════════════════════════════════════════════════════════════
模型: {Codex/Gemini}
执行模式: {CLI/MCP}
错误: {错误信息}
────────────────────────────────────────────────────────────
📋 选项:
  [1] 重试 - 重新调用模型
  [2] 切换模式 - CLI ↔ MCP 切换后重试
  [3] 降级 - 使用 Claude 执行（需确认）
  [4] 中止 - 终止当前任务
────────────────────────────────────────────────────────────
```

**禁止**：自动降级到 Claude（必须用户确认）

---

## 输出管理

```
.skillpack/
├── current/
│   ├── checkpoint.json       # 检查点
│   ├── checkpoint.json.sha256 # 校验和 (v5.0)
│   ├── checkpoint.json.backup.* # 备份 (v5.0)
│   ├── execution.log.jsonl   # 执行日志 (v5.0)
│   ├── 1_*.md               # 阶段输出
│   └── error.log            # 错误日志
└── history/<timestamp>/      # 历史记录
```

| 路由 | 输出文件 |
|------|----------|
| DIRECT_TEXT | `output.txt` |
| DIRECT_CODE | `output.txt` |
| PLANNED | `1_plan.md`, `2_implementation.md`, `3_review.md` |
| RALPH | `1_analysis.md`, `2_plan.md`, `3_subtask_*.md`, `4_review.md`, `5_arbitration.md` |
| ARCHITECT | `1_architecture_analysis.md`, `2_architecture_design.md`, `3_implementation_plan.md`, `4_phase_*.md`, `5_review.md`, `6_arbitration.md` |
| UI_FLOW | `1_ui_design.md`, `2_implementation.md`, `3_preview.md` |

---

## 模块引用

| 模块 | 功能 | 版本 |
|------|------|------|
| `modules/scoring.md` | 6 维度加权评分系统 | v1.0 |
| `modules/routing.md` | 路由决策矩阵 | v1.0 |
| `modules/checkpoint.md` | 检查点与恢复机制 | **v3.0** |
| `modules/recovery.md` | 错误处理与恢复策略 | **v2.2** |
| `modules/review.md` | 两阶段审查 + 保守表述 | **v2.0** |
| `modules/mcp-dispatch.md` | CLI 调度与独立审查 | **v5.4.0** |
| `modules/loop-engine.md` | 循环执行引擎 | **v5.2** |
| `modules/config-schema.md` | 配置验证规范 | **v5.4** |
| `modules/logging.md` | 日志系统规范 | v1.0 |
| `modules/grounding.md` | Grounding 机制 | **v1.0** |
| `modules/test-classification.md` | 测试分类标准 | **v1.0** |
| `modules/cross-validation.md` | 交叉验证机制 | **v1.0** |

---

## 与其他 Skills 的关系

`/do` 是统一入口，内部会调用：
- 文本任务: Claude 直接操作
- 代码任务: Codex (CLI) 执行
- 中等任务: Claude 规划 + Codex (CLI) 实现/审查
- 复杂任务: Claude 分析 + Codex (CLI) 执行 + Gemini (CLI) 独立审查 + Claude 仲裁
- 超复杂任务: Gemini (CLI) 架构分析 + Claude 设计 + Codex (CLI) 实施 + Gemini (CLI) 审查 + Claude 仲裁
- UI 任务: Gemini (CLI) 设计/实现 + Claude 预览
