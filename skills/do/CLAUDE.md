# /do Skill - 执行指令 v5.4.0

当用户调用 `/do <任务>` 时，按以下流程执行：

---

## ⚠️ 铁律 - 必须遵循（最高优先级）

### 1. 执行模式检测

每个 mandatory 阶段开始前，**必须**：
1. 读取 `.skillpackrc` 中的 `cli.prefer_cli_over_mcp`
2. 如果 `true` → 使用 **Bash 调用 CLI**
3. 如果 `false` → 使用 **MCP 工具**

### 2. CLI 调用命令（当 `prefer_cli_over_mcp: true`）

| 模型 | CLI 命令 |
|------|----------|
| **Codex** | `codex exec "<prompt>" --full-auto` |
| **Gemini** | `gemini "<prompt>" -s --yolo` |

### 3. 禁止行为

| ❌ 禁止 | 说明 |
|--------|------|
| 当配置为 CLI 优先时使用 MCP 工具 | 违反配置约定 |
| Claude 自己执行 Codex/Gemini 的任务 | 违反模型分工 |
| 跳过模型调用直接完成 | 违反执行流程 |
| 静默降级（MCP 失败后自动 Claude 接管） | 必须用户确认 |

### 4. 强制调用阶段

| 路由 | 阶段 | 执行模型 | 执行方式（由配置决定） |
|------|------|----------|------------------------|
| DIRECT_CODE | Phase 1 | Codex | CLI 或 MCP |
| PLANNED | Phase 2-3 | Codex | CLI 或 MCP |
| RALPH | Phase 3 | Codex | CLI 或 MCP |
| RALPH | Phase 4 | **Gemini** | CLI 或 MCP |
| ARCHITECT | Phase 1 | Gemini | CLI 或 MCP |
| ARCHITECT | Phase 4 | Codex | CLI 或 MCP |
| ARCHITECT | Phase 5 | **Gemini** | CLI 或 MCP |
| UI_FLOW | Phase 1-2 | Gemini | CLI 或 MCP |

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
| **异步并行执行** | 使用 `run_in_background: true` 同时启动多个任务 |
| **DAG 依赖分析** | 自动构建任务依赖图，识别可并行任务 |
| **波次管理** | 按依赖分组，同一波次内并行执行 |
| **跨模型并行** | Codex + Gemini 同时工作 |
| **TaskOutput 轮询** | 定期检查后台任务状态，收集结果 |
| **并行恢复** | 中断后可恢复正在执行的并行任务 |

## v5.0/5.1 特性

| 特性 | 说明 |
|------|------|
| **原子检查点** | SHA-256 校验和 + write-rename 模式 |
| **CLI 直接调用** | `--cli` 标志绕过 MCP |
| **自动 CLI 降级** | MCP 超时后自动切换到 CLI |
| **结构化日志** | JSONL 格式执行日志 |
| **任务粒度控制** | 自动拆分大任务（< 5000 tokens） |
| **智能降级策略** | 文档任务可快速降级，代码任务需确认 |

---

## 核心原则

1. **立即行动** - 不要只是解释，要真正执行任务
2. **量化决策** - 使用评分系统，决策有据可循
3. **CLI 优先** - 所有 Codex/Gemini 调用使用 CLI（`codex exec --full-auto`、`gemini -s --yolo`）
4. **禁止 MCP** - 不使用 `mcp__codex-cli__*` 或 `mcp__gemini-cli__*`
5. **循环执行** - RALPH/ARCHITECT 使用 Stop Hook 迭代直到完成
6. **持续追踪** - 使用 TodoWrite 追踪进度
7. **原子检查点** - SHA-256 校验 + 多版本备份，关键节点安全保存
8. **两阶段审查** - 规格合规 + 代码质量双保障
9. **结构化日志** - JSONL 格式记录执行过程
10. **异步并行** - 无依赖任务并行执行，显著提升效率 (v5.2)
11. **Grounding 必须** - 每个分析结论必须有代码证据 (v5.4)
12. **独立审查** - 实现者 ≠ 审查者，Codex 实现 → Gemini 审查 (v5.4)
13. **保守表述** - 不确定时使用保守语言，禁止绝对表述 (v5.4)
14. **交叉验证** - 关键结论需多源验证，分歧由 Claude 仲裁 (v5.4)
15. **真实执行** - 禁止 mock 数据，所有 CLI 调用必须真实执行 (v5.4.2)

---

## 禁止 Mock 原则 (v5.4.2)

| 规则 | 说明 |
|------|------|
| **禁止 mock 数据** | 所有 Codex/Gemini CLI 调用必须真实执行 |
| **禁止测试模式自动启用** | `PYTEST_CURRENT_TEST` 不触发 mock |
| **显式 mock 仅限测试** | 只有 `SKILLPACK_MOCK_MODE=1` 显式设置时才启用 |

---

## Step 0: 配置加载与知识库初始化

在任何阶段开始前：

### 配置文件查找顺序

```
查找 .skillpackrc 配置文件
    │
    ├── 1. 项目根目录 ./.skillpackrc （优先级最高）
    │      └── 存在 → 使用项目配置
    │
    └── 2. 全局目录 ~/.claude/.skillpackrc （默认配置）
           └── 存在 → 使用全局配置
```

**合并规则**：项目配置覆盖全局配置的相同字段。

### 知识库初始化

1. **检查配置**：按上述顺序查找 `.skillpackrc` 文件
2. **如果存在 `knowledge.default_notebook`**：
   ```
   ════════════════════════════════════════════════════════════
   📚 知识库初始化
   ════════════════════════════════════════════════════════════
   Notebook ID: {notebook_id}
   正在查询相关文档...
   ────────────────────────────────────────────────────────────
   ```
3. **调用 NotebookLM**：使用 `mcp__notebooklm-mcp__notebook_query` 查询
4. **注入上下文**：将查询结果用于后续所有阶段

**铁律：不查询知识库就不开始执行（如已配置）**

---

## Step 0.5: 执行模式检测（关键）

读取 `.skillpackrc` 后，立即检查执行模式：

```
检查 cli.prefer_cli_over_mcp
    │
    ├── true (CLI 优先模式)
    │   ════════════════════════════════════════════════════════════
    │   🖥️ CLI 优先模式已启用
    │   ════════════════════════════════════════════════════════════
    │   所有 Codex/Gemini 调用将直接使用 CLI (Bash)
    │   跳过 MCP 协议，避免 stdio 通道中断
    │   ────────────────────────────────────────────────────────────
    │
    │   后续所有 mandatory 阶段：
    │   - Codex → 使用 `codex exec "<prompt>" -s workspace-write`
    │   - Gemini → 使用 `gemini "<prompt>"`
    │
    └── false (MCP 模式)
        继续使用 MCP 调用 (mcp__codex-cli__codex 等)
```

### CLI 优先模式下的调用方式

**Codex 任务**（代替 `mcp__codex-cli__codex`）：
```bash
# 使用 exec 子命令实现非交互式执行
# --full-auto = -a on-request + -s workspace-write
codex exec "任务描述

相关文件:
- path/to/file1.ts
- path/to/file2.ts

要求:
1. 具体要求
2. ..." --full-auto
```

**Gemini 任务**（代替 `mcp__gemini-cli__ask-gemini`）：
```bash
# 直接传递 prompt 实现非交互式
# --yolo 自动批准所有工具调用
gemini "@path/to/files 任务描述" -s --yolo
```

### ⚠️ 铁律

**当 `cli.prefer_cli_over_mcp: true` 时：**
1. **禁止**调用任何 `mcp__codex-cli__*` 或 `mcp__gemini-cli__*` 工具
2. **必须**使用 Bash 工具 + `codex exec` / `gemini` 命令
3. **必须**添加自动批准参数（`--full-auto` / `--yolo`）
4. 这是为了**彻底避免 MCP stdio 通道中断和 TTY 依赖问题**

---

## Step 1: 解析参数

从用户输入中提取：
- `task`: 任务描述
- `quick_mode`: `-q` 或 `--quick`
- `deep_mode`: `-d` 或 `--deep`
- `parallel_mode`: `--parallel` (强制启用并行)
- `no_parallel_mode`: `--no-parallel` (强制禁用并行)
- `explain_only`: `-e` 或 `--explain`
- `resume`: `--resume [task_id]`

---

## Step 2: 检查恢复模式

如果包含 `--resume`：

### 恢复流程

1. 检查 `.claude/ralph-delta.local.md` 状态文件
2. 如存在，读取并验证状态
3. 输出恢复信息：
   ```
   ════════════════════════════════════════════════════════════
   🔄 从检查点恢复
   ════════════════════════════════════════════════════════════
   任务: {task_description}
   路由: {route}
   恢复点: Phase {N}, 迭代 {iteration}
   已完成: {completed_percentage}%
   继续执行...
   ────────────────────────────────────────────────────────────
   ```
4. 从检查点继续执行

---

## Step 3: 复杂度评分

### 强制模式覆盖

- 如果 `quick_mode=true` → 使用 DIRECT 路由
- 如果 `deep_mode=true` → 使用 RALPH 路由

### 6 维度评分（参考 modules/scoring.md）

| 维度 | 权重 | 评估内容 |
|------|------|----------|
| 范围广度 | 25% | 影响文件数量 |
| 依赖复杂度 | 20% | 模块间依赖关系 |
| 技术深度 | 20% | 技术难度/新技术 |
| 风险等级 | 15% | 破坏性/可逆性 |
| 时间估算 | 10% | 预估完成时间 |
| UI 复杂度 | 10% | 界面/交互复杂度 |

### 快速信号调整

| 关键词 | 调整 |
|--------|------|
| `typo`, `拼写`, `注释` | -10 分 |
| `重构`, `refactor` | +15 分 |
| `系统`, `架构` | +20 分 |
| `完整`, `从零` | +25 分 |

---

## Step 4: 路由决策

| 总分 | 路由 | 执行模式 |
|------|------|----------|
| 0-20 | DIRECT | 线性 |
| 21-45 | PLANNED | 线性 |
| 46-70 | RALPH | **循环** |
| 71-100 | ARCHITECT | **循环** |
| UI 信号 | UI_FLOW | 线性 |

### --explain 模式输出

```
════════════════════════════════════════════════════════════
📊 任务复杂度分析
════════════════════════════════════════════════════════════
复杂度评分: {总分}/100

┌────────────────────────────────────────┐
│ 范围广度:    {条形图} {scope}/25       │
│ 依赖复杂度:  {条形图} {dependency}/20  │
│ 技术深度:    {条形图} {technical}/20   │
│ 风险等级:    {条形图} {risk}/15        │
│ 时间估算:    {条形图} {time}/10        │
│ UI 复杂度:   {条形图} {ui}/10          │
└────────────────────────────────────────┘

🚀 推荐路由: {路由名称} ({线性/循环})
📝 路由原因: {原因说明}
────────────────────────────────────────────────────────────
```

如果 `explain_only=true`，输出后停止。

---

## Step 5: 准备执行环境

1. 确保 `.skillpack/current/` 目录存在
2. 清空目录中的旧文件
3. 初始化检查点

### 循环模式额外步骤 (RALPH/ARCHITECT)

4. 创建状态文件 `.claude/ralph-delta.local.md`：

```markdown
# Delta Loop State

## Meta
- Task ID: {uuid}
- Route: {RALPH/ARCHITECT}
- Started: {timestamp}
- Last Updated: {timestamp}

## Iteration
- Current: 1
- Max Allowed: 20
- Status: IN_PROGRESS

## Progress
- Current Phase: 1
- Completed Phases: []
- Current Subtask: 0 / {total}

## Pending Work
{初始任务描述}

## Completed Work
(none)

## Promise
<!-- 任务完成后在此处设置完成标记 -->
```

---

## 执行策略

### DIRECT（直接执行）- 线性

**适用**: 0-20 分，简单任务

```
Phase 1 (100%): 执行
  └── Claude 直接完成任务
```

**行为**:
1. 使用 TodoWrite 创建简单任务列表
2. 直接使用工具完成任务
3. 保存输出到 `.skillpack/current/output.txt`

---

### PLANNED（计划执行）- 线性

**适用**: 21-45 分，中等复杂度任务

```
Phase 1 (30%): 规划        ← Claude
Phase 2 (60%): 实现        ← Codex (由配置决定 CLI/MCP)
Phase 3 (100%): 两阶段审查 ← Codex (由配置决定 CLI/MCP)
```

#### Phase 2/3: Codex 强制调用

**进入 Phase 2 时必须**：

1. 检查执行模式：
   - `cli.prefer_cli_over_mcp: true` → 使用 `codex exec "<prompt>" --full-auto`
   - `cli.prefer_cli_over_mcp: false` → 使用 `mcp__codex-cli__codex`
2. 输出阶段提示，明确标注执行模式
3. **立即调用** Codex（CLI 或 MCP）
4. **禁止** Claude 自己使用 Write/Edit 工具完成实现

---

### RALPH（复杂任务自动化）- 循环 (v5.4 更新)

**适用**: 46-70 分，复杂任务

```
Phase 1 (20%): 深度分析    ← Claude (直接执行)
Phase 2 (40%): 规划        ← Claude (直接执行)
Phase 3 (65%): 执行子任务  ← Codex (CLI: codex exec --full-auto) [循环迭代]
Phase 4 (85%): 独立审查    ← Gemini (CLI: gemini -s --yolo) ← v5.4 新增！
Phase 5 (100%): 仲裁验证   ← Claude (直接执行) ← v5.4 新增！
```

#### 循环执行机制

1. **状态文件**：创建 `.claude/ralph-delta.local.md`
2. **迭代执行**：每次迭代更新状态文件
3. **Stop Hook**：未完成时拦截退出，重新注入 Prompt
4. **完成标记**：完成后设置 `<promise>TASK_COMPLETE</promise>`

#### Phase 3: 子任务循环

每个子任务完成后：
1. 更新状态文件中的 `Current Subtask`
2. 更新 `Completed Work`
3. 检查是否全部完成

**全部子任务完成后**，进入 Phase 4。

#### Phase 3: Codex CLI 执行 (v5.4)

```
🚨 RALPH Phase 3 执行流程：

1. 输出阶段提示，明确标注 `🤖 执行模型: Codex (CLI)`
2. 准备 CLI 命令：
   codex exec "任务描述

   相关文件:
   - file1.ts
   - file2.ts

   要求:
   1. 具体要求
   2. ..." --full-auto
3. 使用 Bash 工具执行
4. 等待 Codex 返回结果
5. 更新状态文件
6. 验证并保存输出

禁止行为：
❌ Claude 自己使用 Write/Edit 工具写代码
❌ 使用 MCP 调用 (mcp__codex-cli__codex)
❌ 跳过 CLI 调用直接完成任务
```

#### Phase 4: Gemini 独立审查 (v5.4 新增)

```
🚨 RALPH Phase 4 独立审查流程：

1. 输出阶段提示，明确标注 `🤖 执行模型: Gemini (CLI) - 独立审查`
2. （如配置 NotebookLM）查询需求文档作为参考
3. 准备 CLI 命令：
   gemini "@.skillpack/current/3_*.md 审查代码实现

   审查重点:
   1. 需求是否完全覆盖
   2. 代码质量和最佳实践
   3. 潜在 Bug 和安全问题

   输出格式:
   - 问题列表（严重性 + 文件:行号 + 具体问题）
   - 改进建议" -s --yolo
4. 使用 Bash 工具执行
5. 保存审查报告

独立审查的意义：
✅ 实现者 ≠ 审查者，避免确认偏差
✅ 不同模型视角，发现更多问题
✅ 为 Claude 仲裁提供第二意见
```

#### Phase 5: Claude 仲裁验证 (v5.4 新增)

```
🚨 RALPH Phase 5 仲裁流程：

1. 读取 Codex 实现输出 (Phase 3)
2. 读取 Gemini 审查报告 (Phase 4)
3. 识别分歧点
4. 验证双方证据（使用 Grounding 格式）
5. 做出最终决定
6. 输出仲裁报告

仲裁原则：
- 采纳有更强代码证据支撑的结论
- 如证据强度相当，采用保守结论
- 必须在报告中说明仲裁理由
```

---

### ARCHITECT（架构优先）- 循环 (v5.4 更新)

**适用**: 71-100 分，超复杂任务

```
Phase 1 (15%): 架构分析    ← Gemini (CLI: gemini -s --yolo)
Phase 2 (25%): 架构设计    ← Claude (直接执行)
Phase 3 (40%): 实施规划    ← Claude (直接执行)
Phase 4 (65%): 分阶段实施  ← Codex (CLI: codex exec --full-auto) [循环迭代]
Phase 5 (85%): 独立审查    ← Gemini (CLI: gemini -s --yolo) ← v5.4 调整！
Phase 6 (100%): 仲裁验证   ← Claude (直接执行) ← v5.4 新增！
```

#### Phase 1: Gemini 架构分析

```
🚨 ARCHITECT Phase 1 强制执行流程：

1. 检查执行模式：
   - cli.prefer_cli_over_mcp: true → 使用 gemini "@{project_path} 分析整个项目架构..." -s --yolo
   - cli.prefer_cli_over_mcp: false → 使用 mcp__gemini-cli__ask-gemini
2. 输出阶段提示，明确标注执行模式
3. 立即调用 Gemini（CLI 或 MCP）
4. 等待 Gemini 返回结果
5. 保存到 1_architecture_analysis.md

禁止行为：
❌ Claude 自己进行架构分析
❌ 跳过 Gemini 调用
❌ 当配置为 CLI 优先时使用 MCP
```

#### Phase 4/5: Codex 实施

同 RALPH 的 MCP 强制调用流程。

---

### UI_FLOW（UI 流程）- 线性

**适用**: UI 信号，前端任务

```
Phase 1 (30%): UI设计   ← Gemini (由配置决定 CLI/MCP)
Phase 2 (60%): 实现     ← Gemini (由配置决定 CLI/MCP)
Phase 3 (100%): 预览    ← Claude
```

#### Phase 1/2: Gemini UI 开发

```
🚨 UI_FLOW Phase 1/2 强制执行流程：

1. 检查执行模式：
   - cli.prefer_cli_over_mcp: true → 使用 gemini "@{components_path} 设计/实现 UI..." -s --yolo
   - cli.prefer_cli_over_mcp: false → 使用 mcp__gemini-cli__ask-gemini
2. 输出阶段提示，明确标注执行模式
3. 立即调用 Gemini（CLI 或 MCP）
4. 等待 Gemini 返回结果
5. 保存输出

禁止行为：
❌ Claude 自己实现 UI 代码
❌ 跳过 Gemini 调用
❌ 当配置为 CLI 优先时使用 MCP
```

---

## MCP 调用模板

### Codex 开发调用

```python
prompt = f"""
任务: {task_description}

相关文件:
{list_of_files}

要求:
{requirements}

输出格式:
- 创建/修改的文件列表
- 每个文件的完整代码
"""

mcp__codex-cli__codex(
    prompt=prompt,
    sandbox="workspace-write"
)
```

### Gemini 架构分析

```python
prompt = f"""
@{project_root_path}

分析整个项目架构:
1. 模块依赖关系
2. 技术栈识别
3. 架构模式识别
4. 改进建议
"""

mcp__gemini-cli__ask-gemini(
    prompt=prompt
)
```

### Gemini UI 开发

```python
prompt = f"""
@{components_path}

任务: {ui_task}

设计要求:
{design_requirements}

技术栈: {tech_stack}
"""

mcp__gemini-cli__ask-gemini(
    prompt=prompt
)
```

---

## 阶段提示格式

**每个阶段开始时必须输出**：

```
════════════════════════════════════════════════════════════
📍 Phase {N}/{TOTAL}: {阶段名称} | {路由} 路由
🤖 执行模型: {Claude/Codex/Gemini} {(MCP 强制调用) 或 (直接执行)}
════════════════════════════════════════════════════════════
进度: {进度条} {百分比}%

📊 复杂度评分: {总分}/100
┌────────────────────────────────────────┐
│ 范围广度:    {条形图} {scope}/25       │
│ 依赖复杂度:  {条形图} {dependency}/20  │
│ 技术深度:    {条形图} {technical}/20   │
│ 风险等级:    {条形图} {risk}/15        │
│ 时间估算:    {条形图} {time}/10        │
│ UI 复杂度:   {条形图} {ui}/10          │
└────────────────────────────────────────┘

上一阶段: {状态} {结果}
当前任务: {目标}
输出文件: {路径}
────────────────────────────────────────────────────────────
```

---

## MCP 失败处理

### 指数退避重试 (v5.0)

MCP 调用失败时，先自动重试：

```yaml
retry_policy:
  max_attempts: 3
  backoff:
    initial_delay_ms: 1000    # 首次重试延迟 1 秒
    multiplier: 2             # 每次延迟翻倍
    max_delay_ms: 30000       # 最大延迟 30 秒
    jitter: true              # 添加随机抖动
```

**重试序列**: 立即 → 1s → 2s → 4s → 询问用户

### 错误分类

| 级别 | 错误类型 | 处理策略 |
|------|----------|----------|
| L1 | 网络超时、速率限制、服务暂不可用 | 自动指数退避重试 |
| L2 | 认证过期、配额超限、模型过载 | 询问用户确认 |
| L3 | 请求无效、内容过滤、未知错误 | 报告错误，用户决策 |

### 智能降级策略 (v5.0)

根据任务类型决定降级行为：

| 任务类型 | 降级策略 | 说明 |
|----------|----------|------|
| 文档更新 | `auto` | 可自动降级到 Claude |
| 配置修改 | `auto` | 可自动降级到 Claude |
| 代码实现 | `require_confirmation` | 必须用户确认 |
| 架构设计 | `require_confirmation` | 必须用户确认 |
| UI 开发 | `require_confirmation` | 必须用户确认 |

### 用户选择界面

自动重试失败后，显示选项：

```
╔════════════════════════════════════════════════════════════╗
║ ⚠️ MCP 调用失败                                            ║
╠════════════════════════════════════════════════════════════╣
║ 模型: {Codex/Gemini}                                       ║
║ 工具: {tool_name}                                          ║
║ 错误: {error_message}                                      ║
║ 重试: {retry_count}/3 (已用尽)                             ║
╠════════════════════════════════════════════════════════════╣
║ 📋 恢复选项:                                               ║
║   [1] 🔄 重试 - 再次尝试 MCP 调用                          ║
║   [2] 🔀 Claude 接管 - 允许 Claude 完成此阶段              ║
║   [3] ⏭️ 跳过 - 跳过此阶段                                 ║
║   [4] ⛔ 中止 - 终止执行                                   ║
╚════════════════════════════════════════════════════════════╝
请选择 (1-4):
```

**重要**：代码任务必须获得用户选择后才能继续，**禁止静默降级**。

---

## 状态文件更新规范

### 每阶段完成后

更新 `.claude/ralph-delta.local.md`：

1. 添加阶段到 `Completed Phases`
2. 更新 `Current Phase`
3. 更新 `Completed Work` 摘要
4. 更新 `Pending Work`
5. 更新 `Last Updated`

### 每子任务完成后

1. 更新 `Current Subtask`
2. 添加到 `Completed Work`

### 全部完成时

**必须设置完成标记**：

```markdown
## Promise
<promise>TASK_COMPLETE</promise>

## Completion Summary
- Total Iterations: {count}
- Total Duration: {time}
- Files Modified: {count}
- Review Score: {score}/100
```

---

## 阶段完成输出

**成功：**
```
✅ Phase {N} 完成
├── 执行模型: {实际使用的模型}
├── MCP 工具: {tool_name 或 N/A}
├── 耗时: {duration}
└── 输出: {output_file}
```

**降级执行：**
```
⚠️ Phase {N} 完成 (降级执行)
├── 原计划模型: {planned_model}
├── 实际模型: Claude (用户授权降级)
├── 降级原因: {reason}
└── 输出: {output_file}
```

---

## 任务完成输出

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 任务完成

📋 任务: {task_description}
📊 复杂度: {score}/100 ({路由})
🔄 迭代次数: {iterations} (仅循环模式)
🚀 执行路径: {阶段描述}

📁 变更文件:
  - path/to/file1.ts (新增)
  - path/to/file2.ts (修改)

📝 摘要:
  {2-3句话总结}

📄 输出文件:
  - .skillpack/current/1_*.md
  - .skillpack/current/2_*.md
  - ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 错误处理

### 自动恢复

| 错误类型 | 策略 |
|----------|------|
| 网络超时 | 等待 5 秒重试，最多 3 次 |
| 语法错误 | 自动尝试修复，最多 2 次 |
| 文件锁定 | 等待 2 秒重试，最多 5 次 |
| MCP 失败 | 询问用户选择恢复选项 |

### 恢复选项菜单

```
════════════════════════════════════════════════════════════
⚠️ 执行错误
════════════════════════════════════════════════════════════
阶段: Phase {N} - {阶段名称}
错误类型: {错误分类}
错误消息: {错误信息}
────────────────────────────────────────────────────────────

📋 恢复选项:
  [1] 🔄 继续 - 从失败点继续执行
  [2] 🔁 重试 - 重新执行当前步骤
  [3] ⏪ 回滚 - 撤销本次所有变更
  [4] ⏭️ 跳过 - 跳过当前阶段
  [5] ⛔ 中止 - 终止执行

请选择 (1-5):
```

---

## 进度追踪

**必须使用 TodoWrite 工具追踪任务进度**：

1. 开始执行前，创建任务列表
2. 每个阶段开始时，更新为 `in_progress`
3. 每个阶段完成时，标记为 `completed`
4. 同时只有一个任务处于 `in_progress` 状态

---

## 两阶段审查

### 阶段 A: 规格审查

- 需求覆盖检查
- 遗漏功能检测
- 超范围功能警告

### 阶段 B: 代码质量审查

- 代码风格一致性
- 潜在 Bug 检测
- 性能问题识别
- 安全隐患检查

### 输出格式

```
════════════════════════════════════════════════════════════
📋 阶段 A: 规格审查报告
════════════════════════════════════════════════════════════
✅ 需求覆盖: {covered}/{total} ({percentage}%)
⚠️ 超范围功能: {count} 项
────────────────────────────────────────────────────────────

════════════════════════════════════════════════════════════
🔍 阶段 B: 代码质量审查报告
════════════════════════════════════════════════════════════
🎨 代码风格: {count} 个建议
🐛 潜在 Bug: {count} 个问题
⚡ 性能问题: {count} 个
🔒 安全检查: {count} 个建议

📊 综合评分: {score}/100
────────────────────────────────────────────────────────────
```

---

## 原子检查点机制 (v5.0)

### 写入流程

```
保存检查点
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 1: 生成临时文件                         │
│   文件名: checkpoint.json.tmp.{random_id}   │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 2: 写入完整数据 + 计算 SHA-256          │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 3: 原子重命名 (mv tmp → checkpoint.json)│
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 4: 更新校验和文件 (.sha256)             │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 5: 轮转备份 (保留 3 个版本)             │
└─────────────────────────────────────────────┘
```

### 校验失败恢复

1. 尝试 `.backup.1` → `.backup.2` → `.backup.3`
2. 所有备份无效时提供选项：
   - 从历史记录恢复
   - 放弃检查点，重新开始
   - 手动检查文件

---

## 结构化日志 (v5.0)

### 日志位置

`.skillpack/current/execution.log.jsonl`

### 日志格式

```json
{"ts":"2026-01-19T10:00:00Z","level":"INFO","phase":1,"model":"gemini","event":"phase_start","msg":"开始架构分析"}
{"ts":"2026-01-19T10:05:00Z","level":"INFO","phase":1,"model":"gemini","event":"mcp_call","msg":"调用 ask-gemini","metrics":{"tokens":1500}}
{"ts":"2026-01-19T10:15:00Z","level":"INFO","phase":1,"model":"gemini","event":"phase_complete","msg":"架构分析完成","metrics":{"duration_ms":900000}}
```

### 事件类型

| 事件 | 说明 |
|------|------|
| `phase_start` | 阶段开始 |
| `phase_complete` | 阶段完成 |
| `mcp_call` | MCP 工具调用 |
| `mcp_retry` | MCP 重试 |
| `mcp_fallback` | MCP 降级 |
| `checkpoint_write` | 检查点保存 |
| `error` | 错误发生 |

---

## 任务粒度控制 (v5.0)

### MCP 调用限制

| 限制项 | 阈值 | 处理策略 |
|--------|------|----------|
| Prompt 长度 | < 5000 tokens | 自动拆分 |
| 文件数量 | < 10 个 | 分批处理 |
| 代码行数 | < 500 行/次 | 按模块拆分 |
| 复杂度评分 | < 40/子任务 | 进一步拆分 |

### 自动拆分策略

大任务自动拆分为多个 MCP 调用：

```
原始任务: "实现用户认证系统"
    │
    ▼
拆分后:
├── MCP Call 1: 创建用户模型和数据库 Schema
├── MCP Call 2: 实现注册接口
├── MCP Call 3: 实现登录接口
├── MCP Call 4: 实现 JWT 验证中间件
└── MCP Call 5: 添加单元测试
```

---

## 并行执行 (v5.2 新增)

### 启用条件

并行执行在以下条件下启用：
1. 配置 `parallel.enabled = true`，或
2. 用户指定 `--parallel` 参数

### 并行执行流程

```
1. 分析子任务依赖关系，构建 DAG
   ↓
2. 计算执行波次（无依赖任务分到同一波次）
   ↓
3. 并行启动当前波次的所有任务
   - 使用 Task 工具 + run_in_background: true
   - 同一消息中发送多个 Task 调用
   ↓
4. TaskOutput 轮询收集结果
   - poll_interval_seconds 间隔检查
   - 更新检查点中的任务状态
   ↓
5. 当前波次完成后，进入下一波次
   ↓
6. 回到 Step 3 直到全部完成
```

### 并行启动示例

在 Phase 3 (执行子任务) 中，如果有 3 个无依赖子任务：

```markdown
════════════════════════════════════════════════════════════
🚀 Wave 1/2 开始 | 并行启动 3 个任务
════════════════════════════════════════════════════════════
├── [Codex] subtask_1: 创建用户模型
├── [Codex] subtask_2: 创建认证服务
└── [Gemini] subtask_3: 设计登录表单
────────────────────────────────────────────────────────────
```

**Claude 在单条消息中同时发送 3 个 Task 工具调用**，每个都设置 `run_in_background: true`。

### 结果收集

```markdown
════════════════════════════════════════════════════════════
⏳ Wave 1 执行中 | 已用时间: 45s
════════════════════════════════════════════════════════════
[●●●●●] subtask_1 - 创建用户模型 (Codex)    - ✅ 完成 (38s)
[●●●●○] subtask_2 - 创建认证服务 (Codex)    - 运行中
[●●●○○] subtask_3 - 设计登录表单 (Gemini)   - 运行中
────────────────────────────────────────────────────────────
进度: 1/3 完成 | 下次轮询: 5s
────────────────────────────────────────────────────────────
```

### 串行模式

当 `parallel.enabled = false` 或用户指定 `--no-parallel` 时，行为与 v5.1 一致，子任务串行执行。

---

## 模块引用

| 模块 | 功能 | 版本 |
|------|------|------|
| `modules/scoring.md` | 6 维度加权评分系统 | v1.0 |
| `modules/routing.md` | 路由决策矩阵 | v1.0 |
| `modules/checkpoint.md` | 原子检查点与恢复机制 | **v3.0** |
| `modules/recovery.md` | 错误处理与恢复策略 | **v2.2** |
| `modules/review.md` | 两阶段审查 + 保守表述 | **v2.0** |
| `modules/mcp-dispatch.md` | CLI 调度与独立审查 | **v5.4.0** |
| `modules/loop-engine.md` | 循环执行引擎 | **v5.2** |
| `modules/config-schema.md` | 配置验证规范 | **v5.4** |
| `modules/logging.md` | 结构化日志系统 | v1.0 |
| `modules/grounding.md` | Grounding 机制 | **v1.0** |
| `modules/test-classification.md` | 测试分类标准 | **v1.0** |
| `modules/cross-validation.md` | 交叉验证机制 | **v1.0** |
