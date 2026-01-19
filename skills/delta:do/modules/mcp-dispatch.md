# MCP 调度模块 v5.0.0

## 概述

本模块定义了多模型协作的强制调用规则，确保正确的模型被用于正确的阶段。v5.0 新增**任务粒度控制**和**智能降级策略**。

---

## 模型分配矩阵

### 模型能力定位

| 模型 | 标识符 | MCP 工具 | 核心优势 |
|------|--------|----------|----------|
| **Claude Opus 4.5** | `CLAUDE` | 直接执行 | 精细控制、规划协调 |
| **Codex GPT-5.2** | `CODEX` | `mcp__codex-cli__codex` | 复杂开发、xhigh 推理 |
| **Gemini 3 Pro** | `GEMINI` | `mcp__gemini-cli__ask-gemini` | 超长上下文、多模态 |

### 路由-阶段-模型分配表

#### DIRECT (0-20分)
```yaml
phases:
  - phase: 1
    name: "执行"
    model: CLAUDE
    tool: null
    reason: "简单任务直接执行"
```

#### PLANNED (21-45分)
```yaml
phases:
  - phase: 1
    name: "规划"
    model: CLAUDE
    tool: null
    reason: "任务分析和协调"
  - phase: 2
    name: "实现"
    model: CODEX
    tool: mcp__codex-cli__codex
    mandatory: true
    reason: "复杂功能开发"
  - phase: 3
    name: "审查"
    model: CODEX
    tool: mcp__codex-cli__codex
    mandatory: true
    reason: "专业代码审查"
```

#### RALPH (46-70分)
```yaml
phases:
  - phase: 1
    name: "深度分析"
    model: CLAUDE
    tool: null
    reason: "任务分解和依赖识别"
  - phase: 2
    name: "规划"
    model: CLAUDE
    tool: null
    reason: "子任务规划"
  - phase: 3
    name: "执行子任务"
    model: CODEX
    tool: mcp__codex-cli__codex
    mandatory: true
    reason: "批量功能开发"
  - phase: 4
    name: "综合审查"
    model: CODEX
    tool: mcp__codex-cli__codex
    mandatory: true
    reason: "综合审查"
```

#### ARCHITECT (71-100分)
```yaml
phases:
  - phase: 1
    name: "架构分析"
    model: GEMINI
    tool: mcp__gemini-cli__ask-gemini
    mandatory: true
    reason: "整个项目分析，超长上下文"
  - phase: 2
    name: "架构设计"
    model: CLAUDE
    tool: null
    reason: "精细设计决策"
  - phase: 3
    name: "实施规划"
    model: CLAUDE
    tool: null
    reason: "详细任务分解"
  - phase: 4
    name: "分阶段实施"
    model: CODEX
    tool: mcp__codex-cli__codex
    mandatory: true
    reason: "批量开发"
  - phase: 5
    name: "验收审查"
    model: CODEX
    tool: mcp__codex-cli__codex
    mandatory: true
    reason: "深度审查"
```

#### UI_FLOW
```yaml
phases:
  - phase: 1
    name: "UI设计"
    model: GEMINI
    tool: mcp__gemini-cli__ask-gemini
    mandatory: true
    reason: "多模态，看图写码"
  - phase: 2
    name: "实现"
    model: GEMINI
    tool: mcp__gemini-cli__ask-gemini
    mandatory: true
    reason: "UI组件开发"
  - phase: 3
    name: "预览验证"
    model: CLAUDE
    tool: null
    reason: "验证和微调"
```

---

## 强制调用规则

### 核心约束

1. **禁止替代**：当 `mandatory: true` 时，**禁止 Claude 自己执行**该阶段的核心任务
2. **必须调用**：进入 mandatory 阶段时，必须立即调用指定的 MCP 工具
3. **禁止跳过**：不能因为任何原因跳过 MCP 调用

### 调用前检查清单

```
[ ] 确认当前阶段的分配模型
[ ] 如果 mandatory=true，准备 MCP 调用参数
[ ] 输出调用提示（见下方格式）
[ ] 执行 MCP 调用
[ ] 验证返回结果
```

### 阶段入口输出格式

**Claude 执行阶段：**
```
════════════════════════════════════════════════════════════
📍 Phase {N}/{TOTAL}: {阶段名称} | {路由} 路由
🤖 执行模型: Claude (直接执行)
════════════════════════════════════════════════════════════
```

**MCP 调用阶段：**
```
════════════════════════════════════════════════════════════
📍 Phase {N}/{TOTAL}: {阶段名称} | {路由} 路由
🤖 执行模型: {Codex/Gemini} (MCP 强制调用)
════════════════════════════════════════════════════════════
🔧 MCP 工具: {tool_name}
📝 调用参数: {prompt 摘要}
────────────────────────────────────────────────────────────
```

---

## MCP 调用模板

### Codex 开发调用

```python
# 参数准备
prompt = f"""
任务: {task_description}

相关文件:
{list_of_relevant_files}

要求:
{detailed_requirements}

输出格式:
- 创建/修改的文件列表
- 每个文件的完整代码
- 执行说明
"""

# 调用
mcp__codex-cli__codex(
    prompt=prompt,
    sandbox="workspace-write"
)
```

### Codex 审查调用

```python
prompt = f"""
审查任务: {task_description}

变更文件:
{files_changed}

审查重点:
- 需求覆盖检查
- 代码质量
- 潜在 Bug
- 安全问题
"""

mcp__codex-cli__codex(
    prompt=prompt
)
```

### Gemini 架构分析调用

```python
prompt = f"""
@{project_root_path}

分析整个项目架构:
1. 模块依赖关系
2. 技术栈识别
3. 架构模式识别
4. 改进建议

特别关注: {focus_areas}
"""

mcp__gemini-cli__ask-gemini(
    prompt=prompt
)
```

### Gemini UI 开发调用

```python
prompt = f"""
@{components_path}

任务: {ui_task_description}

现有组件:
{existing_components}

设计要求:
{design_requirements}

技术栈: {tech_stack}
"""

mcp__gemini-cli__ask-gemini(
    prompt=prompt
)
```

---

## 降级策略

### 失败处理流程

```
MCP 调用失败
    ↓
重试 (最多 2 次)
    ↓
仍然失败？
    ↓
╔════════════════════════════════════════════════════════════╗
║ ⚠️ MCP 调用失败                                            ║
╠════════════════════════════════════════════════════════════╣
║ 模型: {Codex/Gemini}                                       ║
║ 工具: {tool_name}                                          ║
║ 错误: {error_message}                                      ║
╠════════════════════════════════════════════════════════════╣
║ 📋 恢复选项:                                               ║
║   [1] 🔄 重试 - 再次尝试 MCP 调用                          ║
║   [2] 🔀 Claude 接管 - 允许 Claude 完成此阶段              ║
║   [3] ⏭️ 跳过 - 跳过此阶段                                 ║
║   [4] ⛔ 中止 - 终止执行                                   ║
╚════════════════════════════════════════════════════════════╝
请选择 (1-4):
```

### 重要约束

- **静默降级禁止**：MCP 失败后，**不得**自动由 Claude 接管
- **用户确认必需**：必须获得用户明确选择后才能继续
- **记录要求**：所有降级必须在输出和日志中明确记录

---

## 调用验证

### 阶段完成输出

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

## 状态追踪

每次 MCP 调用记录到状态文件：

```json
{
  "mcp_calls": [
    {
      "phase": 2,
      "model": "CODEX",
      "tool": "mcp__codex-cli__codex",
      "status": "success",
      "thread_id": "...",
      "timestamp": "...",
      "duration_ms": 5234
    }
  ],
  "fallbacks": [
    {
      "phase": 3,
      "original_model": "CODEX",
      "fallback_model": "CLAUDE",
      "reason": "MCP timeout",
      "user_approved": true,
      "timestamp": "..."
    }
  ]
}
```

---

## 使用示例

### 进入 RALPH Phase 3

```markdown
1. 检查分配矩阵 → Phase 3 = CODEX, mandatory=true
2. 输出阶段提示：
   ════════════════════════════════════════════════════════════
   📍 Phase 3/4: 执行子任务 | RALPH 路由
   🤖 执行模型: Codex (MCP 强制调用)
   ════════════════════════════════════════════════════════════
   🔧 MCP 工具: mcp__codex-cli__codex
   📝 调用参数: 实现用户认证模块...
   ────────────────────────────────────────────────────────────

3. 调用 MCP:
   mcp__codex-cli__codex(prompt="...", sandbox="workspace-write")

4. 验证并保存结果
5. 输出完成提示：
   ✅ Phase 3 完成
   ├── 执行模型: Codex
   ├── MCP 工具: mcp__codex-cli__codex
   ├── 耗时: 45s
   └── 输出: .skillpack/current/3_subtask_auth.md
```

---

## 任务粒度控制 (v5.0 新增)

### 问题背景

MCP 调用处理复杂任务时可能出现：
- 响应时间过长，用户误判为卡住
- 请求过大导致超时或中断
- 单次调用失败影响整体进度

### 粒度控制原则

| 指标 | 建议限制 | 原因 |
|------|----------|------|
| Prompt 长度 | < 5000 tokens | 避免输入过载 |
| 单文件修改 | < 500 行 | 便于审查和回滚 |
| 子任务数量 | 3-5 个 | 平衡效率和控制 |
| 预计执行时间 | < 2 分钟 | 用户体验 |

### 任务自动拆分

**拆分触发条件：**
- 任务描述 > 200 词
- 涉及 > 3 个文件
- 包含多个独立功能点

**拆分示例：**

```
原始任务:
  "重写整个 checkpoint.md，添加原子写入、校验和、多版本备份"

拆分后:
  1. "在 checkpoint.md 中添加原子写入机制"
  2. "在 checkpoint.md 中添加 SHA-256 校验和验证"
  3. "在 checkpoint.md 中更新备份策略和 Schema"
```

### 超时预警机制

当预计执行时间 > 60 秒时，输出进度提示：

```
════════════════════════════════════════════════════════════
⏳ MCP 调用进行中
════════════════════════════════════════════════════════════
工具: mcp__codex-cli__codex
预计时间: ~2-3 分钟
状态: 正在处理...
────────────────────────────────────────────────────────────
💡 提示: 复杂任务需要时间，请耐心等待
   如需中断，请按 Ctrl+C
────────────────────────────────────────────────────────────
```

---

## 智能降级策略 (v5.0 新增)

### 任务类型降级矩阵

| 任务类型 | 首选模型 | 允许降级 | 降级条件 |
|----------|----------|----------|----------|
| 代码实现 | Codex | ❌ 否 | 不允许降级 |
| 代码审查 | Codex | ⚠️ 条件 | MCP 失败 2 次后询问 |
| 文档更新 | Codex | ✅ 是 | MCP 失败 1 次后可降级 |
| 配置修改 | Claude | - | 默认 Claude |
| 架构分析 | Gemini | ⚠️ 条件 | MCP 失败 2 次后询问 |
| UI 设计 | Gemini | ⚠️ 条件 | MCP 失败 2 次后询问 |

### 自动降级条件

对于**允许降级**的任务类型，满足以下条件时自动提供降级选项：

```yaml
auto_fallback_conditions:
  # 文档类任务
  documentation:
    file_types: [".md", ".txt", ".rst"]
    max_mcp_attempts: 1
    auto_suggest_fallback: true

  # 配置类任务
  configuration:
    file_types: [".json", ".yaml", ".toml", ".env"]
    max_mcp_attempts: 0  # 直接由 Claude 处理

  # 代码类任务
  code:
    file_types: [".ts", ".js", ".py", ".go", ".rs"]
    max_mcp_attempts: 3
    auto_suggest_fallback: false
    require_user_confirmation: true
```

### 降级决策流程

```
MCP 调用失败
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 1: 判断任务类型                         │
│   documentation / configuration / code      │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 2: 检查降级策略                         │
│   允许降级？重试次数？                       │
└─────────────────────────────────────────────┘
    │
    ├── documentation + 失败 1 次
    │       ↓
    │   "📝 文档更新任务，建议由 Claude 继续"
    │   [1] Claude 接管 (推荐)
    │   [2] 重试 MCP
    │
    ├── code + 失败 < 3 次
    │       ↓
    │   自动重试，不显示降级选项
    │
    └── code + 失败 >= 3 次
            ↓
        ╔════════════════════════════════════════╗
        ║ ⚠️ MCP 调用多次失败                    ║
        ╠════════════════════════════════════════╣
        ║ 这是代码实现任务，降级可能影响质量     ║
        ║                                        ║
        ║ [1] 继续重试 MCP                       ║
        ║ [2] Claude 接管 (需确认)               ║
        ║ [3] 跳过此阶段                         ║
        ║ [4] 中止任务                           ║
        ╚════════════════════════════════════════╝
```

---

## 配置选项

在 `.skillpackrc` 中配置：

```json
{
  "mcp": {
    "timeout_seconds": 180,
    "max_retries": 3,
    "retry_delay_ms": 2000,
    "auto_chunk_large_tasks": true,
    "chunk_max_tokens": 5000,
    "show_progress_after_seconds": 60,
    "fallback_strategy": {
      "documentation": "auto",
      "configuration": "claude_only",
      "code": "require_confirmation"
    }
  }
}
```
