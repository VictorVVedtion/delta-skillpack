---
name: do
description: 智能任务执行器 v5.4 - CLI 优先，Grounding + 独立审查 + 交叉验证
version: 5.4.0
---

# /do - 智能任务执行器 v5.4

自动分析任务复杂度并选择最优执行路径，**CLI 优先模式**，多模型协作

## 参数

- `task`: 任务描述（必需）
- `-q, --quick`: 强制 DIRECT_CODE 路由，跳过规划
- `-d, --deep`: 强制 RALPH 路由，深度分析
- `-e, --explain`: 仅显示评分和路由决策，不执行
- `--parallel`: 启用并行执行
- `--no-parallel`: 禁用并行执行
- `--cli`: 强制 CLI 模式（默认已启用）
- `--resume`: 从最近检查点恢复
- `--resume <task_id>`: 恢复指定任务
- `--list-checkpoints`: 查看可恢复任务

---

## v5.4 核心特性

| 特性 | 说明 |
|------|------|
| **CLI 优先模式** | 默认使用 `codex exec --full-auto` 和 `gemini -s --yolo` |
| **禁止 MCP** | 不使用 `mcp__codex-cli__*` 或 `mcp__gemini-cli__*` |
| **Grounding 机制** | 每个结论必须有 `file:line` 格式的代码证据 |
| **独立审查者模式** | Codex 实现 → Gemini 审查（不同模型交叉审查） |
| **仲裁验证** | Claude 仲裁 Codex/Gemini 分歧 |
| **保守表述原则** | 禁止绝对表述，强制不确定性声明 |

---

## 执行指令

当用户调用此 Skill 时，按照以下步骤执行：

### Step 1: 解析参数

从用户输入中提取：
- `task`: 任务描述（引号内或参数后的内容）
- `quick_mode`: 是否包含 `-q` 或 `--quick`
- `deep_mode`: 是否包含 `-d` 或 `--deep`
- `explain_only`: 是否包含 `-e` 或 `--explain`
- `parallel_mode`: `--parallel` 或 `--no-parallel`

### Step 2: 任务路由

根据任务描述判断复杂度，确定执行路由：

#### 强制模式覆盖

- 如果 `deep_mode=true` → 使用 RALPH 路由
- 如果 `quick_mode=true` → 使用 DIRECT_CODE 路由

#### 自动路由（按优先级匹配）

1. **UI 任务 (UI_FLOW)** - 优先级最高
   匹配以下关键词（不区分大小写）：
   ```
   ## 基础 UI 关键词
   ui, ux, 界面, 组件, component, 页面, page, 布局, layout,
   样式, style, css, tailwind, 前端, frontend, 按钮, button,
   表单, form, modal, 弹窗, 导航, nav, menu, 菜单

   ## 框架特定
   jsx, tsx, hook, useState, useEffect, useContext,
   vue, template, slot, v-model, next, nuxt, svelte, astro

   ## 样式系统
   styled-components, emotion, css-in-js, css modules,
   shadcn, radix, chakra, material-ui, mui, antd,
   sass, scss, less, postcss

   ## 交互与动画
   animation, transition, framer, framer-motion, gsap, animate,
   gesture, drag, drop, hover, focus

   ## 视觉元素
   icon, svg, avatar, badge, tooltip, popover,
   typography, font, color, theme, dark mode
   ```

2. **简单任务 - 文本类 (DIRECT_TEXT)** → Claude 执行
   满足任意条件：
   - 关键词: `typo`, `拼写`, `readme`, `文档`, `docs`, `comment`, `注释`, `config`, `配置`
   - 文件类型: `.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.toml`, `.ini`
   - 任务描述少于 8 个词且不涉及代码逻辑

3. **简单任务 - 代码类 (DIRECT_CODE)** → Codex 执行
   满足任意条件：
   - 关键词: `fix`, `bug`, `function`, `method`, `add`, `remove`, `implement`, `修复`, `实现`
   - 文件类型: `.ts`, `.js`, `.py`, `.go`, `.rs`, `.java`, `.tsx`, `.jsx`, `.vue`
   - 不匹配 DIRECT_TEXT 信号的简单任务（< 10 词）

4. **超复杂任务 (ARCHITECT)** - 需要架构设计
   满足任意条件：
   - 包含: `architecture`, `架构`, `设计系统`, `microservice`, `微服务`, `design system`
   - 包含: `从零`, `from scratch`, `全新`, `brand new` + 大型项目关键词
   - 任务描述超过 50 个词且涉及多个系统/模块

5. **复杂任务 (RALPH)**
   满足任意条件：
   - 包含: `system`, `系统`, `完整`, `complete`, `全面`, `comprehensive`, `多模块`, `重构`, `refactor`
   - 包含: `fork`, `clone`, `构建`, `build` + 项目名
   - 任务描述超过 30 个词

6. **中等任务 (PLANNED)**
   - 默认路由，其他情况

#### 路由输出

如果 `explain_only=true`，输出路由决策后停止：

```
📊 任务复杂度分析
════════════════════════════════════════════════════════════
任务: {任务描述}
────────────────────────────────────────────────────────────
路由决策: {DIRECT_TEXT | DIRECT_CODE | PLANNED | RALPH | ARCHITECT | UI_FLOW}
执行模型: {Claude | Codex (CLI) | Gemini (CLI)}
执行模式: {线性 | 循环/并行}
阶段数量: {N}
────────────────────────────────────────────────────────────
评分详情:
  范围广度:    {scope}/25
  依赖复杂度:  {dependency}/20
  技术深度:    {technical}/20
  风险等级:    {risk}/15
  时间估算:    {time}/10
  UI 复杂度:   {ui}/10
  总分:        {total}/100
────────────────────────────────────────────────────────────
判断依据: {匹配的关键词或条件}
════════════════════════════════════════════════════════════
```

### Step 3: 准备输出目录

1. 确保 `.skillpack/current/` 目录存在
2. 清空该目录中的旧文件（可选）

### Step 4: 执行对应策略

根据路由结果执行对应的策略。

---

## CLI 优先模式 (v5.3+)

### 核心规则

1. 🖥️ **CLI 优先** - 默认使用 Bash 直接调用 Codex/Gemini CLI
2. ⛔ **禁止 MCP** - 不使用 `mcp__codex-cli__*` 或 `mcp__gemini-cli__*`
3. ⛔ **禁止替代** - 指定模型阶段禁止 Claude 自己执行
4. ❌ **禁止静默降级** - 代码任务需用户确认
5. ✅ **验证输出** - 每阶段明确标注实际使用的模型

### Codex CLI 调用

```bash
# 完全自动模式（推荐）
codex exec --full-auto "任务描述"

# 带上下文的调用
codex exec --full-auto --files src/auth/*.ts "implement JWT validation"
```

### Gemini CLI 调用

```bash
# Sandbox 模式 + YOLO（推荐）
gemini -s --yolo "@src/components analyze UI patterns"

# 带文件上下文
gemini -s --yolo "@src/pages/login.tsx implement form validation"
```

### CLI 调用失败处理

当 CLI 调用失败时：

```
════════════════════════════════════════════════════════════
⚠️ CLI 调用失败
════════════════════════════════════════════════════════════
命令: {codex exec --full-auto | gemini -s --yolo}
错误: {错误信息}
────────────────────────────────────────────────────────────
📋 选项:
  [1] 重试 - 重新执行 CLI 命令
  [2] 降级 - 使用 Claude 执行（需确认）
  [3] 中止 - 终止当前任务
────────────────────────────────────────────────────────────
```

**禁止**：自动降级到 Claude 执行

---

## 执行策略

### DIRECT_TEXT（文本直接执行）

**适用于**：文档、配置、注释修改
**执行模型**：Claude
**阶段数**：1

**执行流程**：

1. 使用 Glob/Grep 找到相关文件
2. 使用 Read 读取内容
3. 使用 Edit 进行修改
4. 完成后保存输出到 `.skillpack/current/output.txt`

**输出标注**：
```
执行模型: Claude (DIRECT_TEXT)
```

---

### DIRECT_CODE（代码直接执行）

**适用于**：简单代码修复、函数添加
**执行模型**：Codex (CLI)
**阶段数**：1

**执行流程**：

1. Claude 分析任务，收集相关文件内容
2. **调用 Codex CLI**：
   ```bash
   codex exec --full-auto "任务描述 + 相关文件内容"
   ```
3. 验证 Codex 输出并应用变更
4. 完成后保存输出到 `.skillpack/current/output.txt`

**输出标注**：
```
执行模型: Codex via CLI (DIRECT_CODE)
命令: codex exec --full-auto "<prompt>"
```

---

### PLANNED（计划执行）

**适用于**：中等复杂度任务
**执行模型**：Claude (规划) → Codex CLI (实现/审查)
**阶段数**：3

#### Phase 1: 规划 (Planning) - Claude

使用 TodoWrite 追踪，执行以下步骤：

1. **任务分析**：理解任务目标和范围
2. **实施步骤**：按顺序列出具体步骤
3. **关键文件**：需要创建或修改的文件列表
4. **注意事项**：潜在风险和注意点

**输出**：保存到 `.skillpack/current/1_plan.md`

**规划阶段限制**：只读操作，不执行 Edit/Write/Bash

#### Phase 2: 实现 (Implementing) - Codex CLI

**调用 Codex CLI**：
```bash
codex exec --full-auto "基于以下规划执行实现：{Phase 1 规划内容}"
```

验证 Codex 输出并应用变更

**输出**：保存到 `.skillpack/current/2_implementation.md`

#### Phase 3: 审查 (Reviewing) - Codex CLI

**调用 Codex CLI**：
```bash
codex exec --full-auto "审查以下代码变更：{Phase 2 实现的代码}

检查项：
1. 代码质量
2. 潜在 Bug
3. 安全问题
4. 性能问题"
```

**输出**：保存到 `.skillpack/current/3_review.md`

---

### RALPH（复杂任务自动化）v5.4

**适用于**：复杂任务、深度模式
**执行模型**：Claude (分析/规划/仲裁) → Codex CLI (执行) → Gemini CLI (独立审查)
**阶段数**：5

#### Phase 1: 深度分析 (Analyzing) - Claude

作为 Ralph（高级任务分析专家），执行深度分析：

1. **任务分解**：将任务拆分为独立的子任务
2. **依赖关系**：子任务之间的依赖顺序
3. **执行计划**：建议的执行顺序和策略
4. **风险评估**：潜在的技术难点和风险

输出子任务列表（JSON 格式）：
```json
{
  "subtasks": [
    {"id": 1, "name": "子任务名", "description": "描述", "dependencies": []}
  ]
}
```

**输出**：保存到 `.skillpack/current/1_analysis.md`

**分析阶段限制**：只读操作

#### Phase 2: 规划 (Planning) - Claude

基于分析结果，为每个子任务生成详细实施步骤。

**输出**：保存到 `.skillpack/current/2_plan.md`

#### Phase 3: 执行子任务 (Implementing) - Codex CLI

按依赖顺序，对每个子任务调用 Codex CLI：

```bash
codex exec --full-auto "执行子任务 {N}: {子任务名}
{子任务实施步骤}
{相关文件内容}"
```

- 每个子任务完成后保存到 `.skillpack/current/3_subtask_N.md`
- 使用 TodoWrite 追踪每个子任务的进度

**输出**：保存到 `.skillpack/current/3_subtask_*.md`

#### Phase 4: 独立审查 (Independent Review) - Gemini CLI ⭐ v5.4 新增

**由 Gemini 独立审查 Codex 的实现**（交叉验证）：

```bash
gemini -s --yolo "@.skillpack/current/3_subtask_*.md 审查以下实现：

任务描述: {原始任务}

审查重点:
1. 需求是否完全覆盖
2. 代码质量和最佳实践
3. 潜在 Bug 和安全问题
4. 改进建议

输出格式:
- 问题列表（严重性 + file:line + 具体问题）
- 改进建议
- 置信度评估 (high/medium/low)"
```

**Grounding 要求**：每个问题必须引用具体的 `file:line`

**输出**：保存到 `.skillpack/current/4_review.md`

#### Phase 5: 仲裁验证 (Arbitration) - Claude ⭐ v5.4 新增

Claude 对 Codex 实现和 Gemini 审查进行仲裁：

1. **分析 Gemini 审查报告**：识别高优先级问题
2. **验证问题有效性**：检查 `file:line` 引用是否准确
3. **决策**：
   - 如果 Gemini 审查通过 → 任务完成
   - 如果存在高优先级问题 → 回到 Phase 3 修复
   - 如果 Codex/Gemini 存在分歧 → Claude 仲裁决定

**输出**：保存到 `.skillpack/current/5_arbitration.md`

---

### ARCHITECT（架构优先）v5.4

**适用于**：超复杂任务、系统设计
**执行模型**：Gemini CLI (架构分析/审查) → Claude (设计/规划/仲裁) → Codex CLI (实施)
**阶段数**：6

#### Phase 1: 架构分析 (Architecture Analysis) - Gemini CLI

```bash
gemini -s --yolo "@. 作为系统架构师，分析以下需求：
{任务描述}

输出：
1. 系统边界和模块划分
2. 技术选型建议
3. 数据流设计
4. 关键接口定义
5. 潜在风险和解决方案"
```

**输出**：保存到 `.skillpack/current/1_architecture_analysis.md`

#### Phase 2: 架构设计 (Architecture Design) - Claude

基于 Gemini 的分析，完善架构设计：

1. **模块详细设计**：每个模块的职责和接口
2. **依赖关系图**：模块间的依赖关系
3. **实施路线图**：分阶段实施计划
4. **测试策略**：测试方案

**输出**：保存到 `.skillpack/current/2_architecture_design.md`

#### Phase 3: 实施规划 (Implementation Planning) - Claude

基于架构设计，生成详细实施计划：

为每个模块生成：
1. 文件结构
2. 核心类/函数定义
3. 实施步骤

**输出**：保存到 `.skillpack/current/3_implementation_plan.md`

#### Phase 4: 分阶段实施 (Phased Implementation) - Codex CLI

按实施计划，逐阶段调用 Codex CLI：

```bash
codex exec --full-auto "执行阶段 {N}: {阶段名称}
{阶段实施步骤}
{架构设计摘要}
{相关文件内容}"
```

每阶段完成后保存到 `.skillpack/current/4_phase_N.md`

#### Phase 5: 独立审查 (Independent Review) - Gemini CLI ⭐ v5.4 调整

```bash
gemini -s --yolo "@.skillpack/current/4_phase_*.md 验收审查整个架构实现：

对照架构设计检查：
1. 是否符合架构设计
2. 模块边界是否清晰
3. 接口是否正确实现
4. 是否存在架构偏离

输出格式:
- 架构符合度评估
- 问题列表（file:line + 问题描述）
- 改进建议"
```

**输出**：保存到 `.skillpack/current/5_review.md`

#### Phase 6: 仲裁验证 (Arbitration) - Claude ⭐ v5.4 新增

Claude 最终仲裁验证：

1. **架构一致性检查**：实现是否符合设计
2. **审查有效性验证**：Gemini 审查问题是否准确
3. **最终决策**：通过/需修复/需重新设计

**输出**：保存到 `.skillpack/current/6_arbitration.md`

---

### UI_FLOW（UI 流程）

**适用于**：UI/前端相关任务
**执行模型**：Gemini CLI (设计/实现) → Claude (预览)
**阶段数**：3

#### Phase 1: UI 设计 (UI Design) - Gemini CLI

```bash
gemini -s --yolo "@src/components @src/styles 设计以下 UI 组件：
{任务描述}

输出：
1. 组件结构：需要创建的组件及其层次关系
2. 样式规范：颜色、字体、间距等设计规范
3. 交互设计：用户交互流程和状态变化
4. 响应式设计：不同屏幕尺寸的适配方案"
```

**输出**：保存到 `.skillpack/current/1_ui_design.md`

**设计阶段限制**：只读操作

#### Phase 2: 实现 UI 组件 (Implementing) - Gemini CLI

```bash
gemini -s --yolo "@.skillpack/current/1_ui_design.md 根据设计实现组件代码：

要求：
- 使用项目现有的 UI 框架和组件库
- 遵循项目代码风格
- 确保响应式设计
- 添加必要的注释"
```

验证 Gemini 输出并应用变更

**输出**：保存到 `.skillpack/current/2_implementation.md`

#### Phase 3: 预览验证 (Preview) - Claude

检查组件是否正确实现：
1. 组件是否正确渲染
2. 样式是否符合设计
3. 交互是否正常工作

如果项目有开发服务器，建议启动预览；如果有测试，运行测试验证。

**输出**：保存到 `.skillpack/current/3_preview.md`

---

## 路由-模型-阶段完整映射 (v5.4)

| 路由 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|------|---------|---------|---------|---------|---------|---------|
| **DIRECT_TEXT** | Claude | - | - | - | - | - |
| **DIRECT_CODE** | **Codex** | - | - | - | - | - |
| **PLANNED** | Claude | **Codex** | **Codex** | - | - | - |
| **RALPH** | Claude | Claude | **Codex** | **Gemini** | Claude | - |
| **ARCHITECT** | **Gemini** | Claude | Claude | **Codex** | **Gemini** | Claude |
| **UI_FLOW** | **Gemini** | **Gemini** | Claude | - | - | - |

**图例** (v5.3+ CLI 优先)：
- **Codex** = `codex exec --full-auto`
- **Gemini** = `gemini -s --yolo`
- Claude = 直接执行

---

## 阶段转换提示

**每个阶段开始时，必须输出清晰的进度提示**：

```
════════════════════════════════════════════════════════════
📍 Phase {N}/{TOTAL}: {阶段名称} ({Phase Name})
════════════════════════════════════════════════════════════
进度: {进度条} {百分比}%
上一阶段: {状态图标} {上一阶段结果}
当前任务: {当前阶段的目标}
执行模型: {Claude | Codex (CLI) | Gemini (CLI)}
输出文件: {对应的输出文件路径}
────────────────────────────────────────────────────────────
```

### 进度条计算

| 路由 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|------|---------|---------|---------|---------|---------|---------|
| DIRECT_TEXT | 100% | - | - | - | - | - |
| DIRECT_CODE | 100% | - | - | - | - | - |
| PLANNED | 30% | 60% | 100% | - | - | - |
| RALPH | 15% | 30% | 55% | 80% | 100% | - |
| ARCHITECT | 10% | 25% | 40% | 60% | 80% | 100% |
| UI_FLOW | 30% | 60% | 100% | - | - | - |

---

## v5.4 特性：Grounding 机制

### 要求

每个结论/问题必须有代码证据，格式为 `file:line`：

**正确示例**：
```
- 🔴 高优先级: `src/auth.ts:45` - 未处理 null 返回值
- 🟡 中优先级: `src/api/user.ts:112-118` - 缺少错误边界处理
```

**错误示例**（缺少 Grounding）：
```
- 代码质量一般
- 可能存在性能问题
```

### 保守表述原则

- ❌ 禁止: "代码完全正确"、"没有任何问题"
- ✅ 推荐: "在已审查范围内未发现明显问题"、"基于当前上下文，实现符合预期"

---

## 进度追踪

**必须使用 TodoWrite 工具追踪任务进度**：

1. 开始执行前，创建任务列表
2. 每个阶段开始时，更新对应任务为 `in_progress`
3. 每个阶段完成时，标记为 `completed`
4. 同时只有一个任务处于 `in_progress` 状态

---

## 输出管理

### 输出目录

- **当前执行**: `.skillpack/current/`
- **历史记录**: `.skillpack/history/<timestamp>/`

### 输出文件命名

| 路由 | 文件 |
|------|------|
| DIRECT_TEXT | `output.txt` |
| DIRECT_CODE | `output.txt` |
| PLANNED | `1_plan.md`, `2_implementation.md`, `3_review.md` |
| RALPH | `1_analysis.md`, `2_plan.md`, `3_subtask_*.md`, `4_review.md`, `5_arbitration.md` |
| ARCHITECT | `1_architecture_analysis.md`, `2_architecture_design.md`, `3_implementation_plan.md`, `4_phase_*.md`, `5_review.md`, `6_arbitration.md` |
| UI_FLOW | `1_ui_design.md`, `2_implementation.md`, `3_preview.md` |

---

## 错误处理

### CLI 调用失败恢复

当 CLI 调用失败时，按以下流程处理：

#### Step 1: 保存当前状态

将已完成的工作保存到 `.skillpack/current/`

#### Step 2: 诊断问题

```
════════════════════════════════════════════════════════════
⚠️ CLI 调用失败
════════════════════════════════════════════════════════════
失败阶段: Phase {N} - {阶段名称}
执行模型: {Codex | Gemini}
命令: {实际执行的命令}
错误类型: {超时 | 命令未找到 | 执行错误}
错误详情: {具体错误信息}
────────────────────────────────────────────────────────────
```

#### Step 3: 提供恢复选项

```
📋 恢复选项:
  [1] 重试 - 重新执行 CLI 命令
  [2] 降级 - 使用 Claude 执行（需确认）
  [3] 中止 - 终止执行，保留已完成部分

请选择操作 (1-3):
```

**注意**：选择 [2] 降级需要用户明确确认，禁止自动降级。

---

## 示例

### 文本任务
```
/do "fix typo in README"
```
→ DIRECT_TEXT 路由，Claude 直接修复

### 代码任务
```
/do "fix bug in auth.ts"
```
→ DIRECT_CODE 路由，Codex CLI 执行

### 中等任务
```
/do "add user authentication"
```
→ PLANNED 路由，Claude 规划 → Codex CLI 实现/审查

### 复杂任务
```
/do "build complete authentication system with OAuth"
```
→ RALPH 路由：Claude 分析/规划 → Codex CLI 执行 → Gemini CLI 审查 → Claude 仲裁

### 超复杂任务
```
/do "design new microservice architecture for the platform"
```
→ ARCHITECT 路由：Gemini CLI 架构分析 → Claude 设计/规划 → Codex CLI 实施 → Gemini CLI 审查 → Claude 仲裁

### UI 任务
```
/do "创建登录页面组件"
/do "add framer motion animation to button"
```
→ UI_FLOW 路由，Gemini CLI 设计/实现 → Claude 预览

### 强制模式
```
/do -q "add feature X"      # 快速模式，DIRECT_CODE
/do -d "add feature X"      # 深度模式，RALPH
/do -e "add feature X"      # 仅显示路由决策
```
