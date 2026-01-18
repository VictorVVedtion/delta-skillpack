# Skill: skill-do

智能任务执行器 - 自动分析任务复杂度并选择最优执行路径

## 元数据

```yaml
name: skill-do
description: 智能任务执行 - 自动路由，实时反馈
version: 2.0.0
triggers:
  - /skill-do
  - /do
arguments:
  task: 任务描述（必需）
  -q, --quick: 跳过规划，直接实现
  -d, --deep: 强制 Ralph 自动化模式
  -e, --explain: 仅显示路由决策，不执行
```

---

## 执行指令

当用户调用此 Skill 时，按照以下步骤执行：

### Step 1: 解析参数

从用户输入中提取：
- `task`: 任务描述（引号内或参数后的内容）
- `quick_mode`: 是否包含 `-q` 或 `--quick`
- `deep_mode`: 是否包含 `-d` 或 `--deep`
- `explain_only`: 是否包含 `-e` 或 `--explain`

### Step 2: 任务路由

根据任务描述判断复杂度，确定执行路由：

#### 路由规则

**强制模式覆盖：**
- 如果 `deep_mode=true` → 使用 RALPH 路由
- 如果 `quick_mode=true` → 使用 DIRECT 路由

**自动路由（按优先级匹配）：**

1. **UI 任务 (UI_FLOW)**
   匹配关键词（不区分大小写）：
   ```
   ui, ux, 界面, 组件, component, 页面, page, 布局, layout,
   样式, style, css, tailwind, 前端, frontend, 按钮, button,
   表单, form, modal, 弹窗, 导航, nav
   ```

2. **简单任务 (DIRECT)**
   满足任意条件：
   - 包含: `fix typo`, `修复拼写`, `update readme`, `更新文档`,
     `add comment`, `添加注释`, `rename`, `重命名`
   - 或：任务描述少于 10 个词

3. **复杂任务 (RALPH)**
   满足任意条件：
   - 包含: `system`, `系统`, `架构`, `architecture`, `完整`, `complete`,
     `全面`, `comprehensive`, `多模块`, `multi-module`, `重构`, `refactor`,
     `从零`, `from scratch`
   - 或：任务描述超过 30 个词

4. **中等任务 (PLANNED)**
   - 默认路由，其他情况

#### 路由输出

如果 `explain_only=true`，输出路由决策后停止：

```
📊 任务复杂度: [简单/中等/复杂/UI相关]
🚀 执行路径: [直接执行/规划→实现→审查/Ralph自动化/UI流程]
[⚡ 快速模式已启用 / 🔬 深度模式已启用]（如适用）
```

### Step 3: 准备输出目录

1. 确保 `.skillpack/current/` 目录存在
2. 清空该目录中的旧文件

### Step 4: 执行对应策略

根据路由结果执行对应的策略：

---

## 执行策略

### DIRECT（直接执行）

**适用于**：简单任务、快速模式

**执行流程**：

1. 使用 TodoWrite 创建任务列表
2. 直接完成任务，不需要规划阶段
3. 完成后保存输出到 `.skillpack/current/output.txt`

**行为要求**：
- 简洁高效，直接修改代码
- 不需要过多解释
- 完成后简要说明做了什么

---

### PLANNED（计划执行）

**适用于**：中等复杂度任务

**执行流程**：

#### Phase 1: 规划 (Planning)

使用 TodoWrite 追踪，执行以下步骤：

1. **任务分析**：理解任务目标和范围
2. **实施步骤**：按顺序列出具体步骤
3. **关键文件**：需要创建或修改的文件列表
4. **注意事项**：潜在风险和注意点

**输出**：保存到 `.skillpack/current/1_plan.md`

**规划阶段限制**：只读操作，不执行 Edit/Write/Bash

#### Phase 2: 实现 (Implementing)

按照规划逐步实现代码变更：
- 遵循现有代码风格
- 保持代码简洁清晰
- 添加必要的注释

**输出**：保存到 `.skillpack/current/2_implementation.md`

#### Phase 3: 审查 (Reviewing)

检查完成的代码变更：
1. **代码质量**：是否符合最佳实践
2. **潜在 Bug**：是否有明显的逻辑错误
3. **安全问题**：是否有安全隐患
4. **性能问题**：是否有性能瓶颈

**输出**：保存到 `.skillpack/current/3_review.md`

---

### RALPH（复杂任务自动化）

**适用于**：复杂任务、深度模式

**执行流程**：

#### Phase 1: 深度分析 (Analyzing)

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

#### Phase 2: 规划 (Planning)

基于分析结果，为每个子任务生成详细的实施步骤。

**输出**：保存到 `.skillpack/current/2_plan.md`

#### Phase 3: 逐个执行子任务 (Implementing)

按依赖顺序逐个执行子任务：
- 每个子任务完成后保存到 `.skillpack/current/3_subtask_N.md`
- 使用 TodoWrite 追踪每个子任务的进度

#### Phase 4: 综合审查 (Reviewing)

检查所有变更：
1. 所有子任务是否都已正确完成
2. 各模块之间是否正确集成
3. 是否有遗漏的功能
4. 代码质量是否合格

**输出**：保存到 `.skillpack/current/4_review.md`

---

### UI_FLOW（UI 流程）

**适用于**：UI/前端相关任务

**执行流程**：

#### Phase 1: UI 设计 (UI Design)

作为 UI/UX 设计专家，分析需求并输出：

1. **组件结构**：需要创建的组件及其层次关系
2. **样式规范**：颜色、字体、间距等设计规范
3. **交互设计**：用户交互流程和状态变化
4. **响应式设计**：不同屏幕尺寸的适配方案

**输出**：保存到 `.skillpack/current/1_ui_design.md`

**设计阶段限制**：只读操作

#### Phase 2: 实现 UI 组件 (Implementing)

根据设计实现组件：
- 使用项目现有的 UI 框架和组件库
- 遵循项目代码风格
- 确保响应式设计
- 添加必要的注释

**输出**：保存到 `.skillpack/current/2_implementation.md`

#### Phase 3: 预览验证 (Preview)

检查组件是否正确实现：
1. 组件是否正确渲染
2. 样式是否符合设计
3. 交互是否正常工作

如果项目有开发服务器，建议启动预览；如果有测试，运行测试验证。

**输出**：保存到 `.skillpack/current/3_preview.md`

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
| DIRECT | `output.txt` |
| PLANNED | `1_plan.md`, `2_implementation.md`, `3_review.md` |
| RALPH | `1_analysis.md`, `2_plan.md`, `3_subtask_*.md`, `4_review.md` |
| UI_FLOW | `1_ui_design.md`, `2_implementation.md`, `3_preview.md` |

### 每个阶段完成后

使用 Write 工具将阶段输出保存到对应文件。

---

## 配置支持

读取 `.skillpackrc` 配置文件（如存在）：

```json
{
  "knowledge": {
    "default_notebook": "notebook-id",
    "auto_query": true
  },
  "output": {
    "current_dir": ".skillpack/current",
    "history_dir": ".skillpack/history"
  }
}
```

如果配置了 `default_notebook`，可以在分析阶段使用 NotebookLM 查询相关知识。

---

## 示例

### 简单任务

```
/skill-do "fix typo in README"
```
→ DIRECT 路由，直接修复

### 中等任务

```
/skill-do "add user authentication"
```
→ PLANNED 路由，规划→实现→审查

### 复杂任务

```
/skill-do "build complete authentication system with OAuth"
```
→ RALPH 路由，深度分析→规划→逐个执行→综合审查

### UI 任务

```
/skill-do "创建登录页面组件"
```
→ UI_FLOW 路由，UI设计→实现→预览

### 强制模式

```
/skill-do -q "add feature X"      # 快速模式，跳过规划
/skill-do -d "add feature X"      # 深度模式，强制 Ralph
/skill-do -e "add feature X"      # 仅显示路由决策
```
