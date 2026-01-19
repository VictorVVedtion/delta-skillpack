# 循环执行引擎 v5.0.0

## 概述

循环执行引擎 (Loop Engine) 是 RALPH 和 ARCHITECT 路由的核心，实现"任务未完成自动继续"的迭代执行模式。通过与 Stop Hook 协作，在任务未完成时拦截退出并重新注入上下文。

## v5.0 增强

| 特性 | 说明 |
|------|------|
| **原子状态保存** | 与 `checkpoint.md` v2.0 集成，SHA-256 校验 |
| **结构化日志** | 迭代事件记录到 `execution.log.jsonl` |
| **智能 MCP 调度** | 与 `mcp-dispatch.md` v5.0 集成，失败自动重试 |

---

## 适用路由

| 路由 | 循环模式 | 说明 |
|------|----------|------|
| DIRECT | 否 | 单次执行 |
| PLANNED | 否 | 线性三阶段 |
| **RALPH** | **是** | 循环执行直到完成 |
| **ARCHITECT** | **是** | 循环执行直到完成 |
| UI_FLOW | 否 | 线性三阶段 |

---

## 状态文件

### 文件位置

```
.claude/ralph-delta.local.md
```

### 文件格式

```markdown
# Delta Loop State

## Meta
- Task ID: {uuid}
- Route: RALPH
- Started: {timestamp}
- Last Updated: {timestamp}

## Iteration
- Current: {N}
- Max Allowed: {max_iterations}
- Status: IN_PROGRESS | COMPLETED | FAILED | USER_ABORT

## Progress
- Current Phase: {phase_number}
- Completed Phases: [1, 2, ...]
- Current Subtask: {subtask_index} / {total_subtasks}

## Pending Work
{remaining_tasks_description}

## Completed Work
{completed_work_summary}

## Promise
<!-- 仅当任务完全完成时设置 -->
<promise>TASK_COMPLETE</promise>
```

### 状态字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `Task ID` | UUID | 任务唯一标识 |
| `Route` | String | 使用的路由 (RALPH/ARCHITECT) |
| `Current` | Integer | 当前迭代次数 |
| `Max Allowed` | Integer | 最大迭代次数 (默认 20) |
| `Status` | Enum | 当前状态 |
| `Pending Work` | Markdown | 剩余工作描述 |
| `Promise` | Tag | 完成承诺标记 |

---

## 迭代流程

### 1. 初始化

```
/do "complex task" → RALPH 路由
    ↓
创建状态文件 .claude/ralph-delta.local.md
    ↓
设置 Iteration.Current = 1
设置 Status = IN_PROGRESS
    ↓
开始 Phase 1
```

### 2. 正常迭代

```
完成一个阶段/子任务
    ↓
更新状态文件
    - 增加 Completed Phases
    - 更新 Pending Work
    - 更新 Last Updated
    ↓
检查是否完成所有工作？
    ├── 是 → 设置 <promise>TASK_COMPLETE</promise>
    └── 否 → 继续下一阶段/子任务
```

### 3. 会话结束检测

当 Claude 即将结束回复时：

```
检查状态文件
    ↓
是否存在 <promise>TASK_COMPLETE</promise>？
    ├── 是 → 正常结束，归档状态文件
    └── 否 → Stop Hook 拦截
              ↓
          Iteration.Current < Max Allowed？
              ├── 是 → 重新注入 Prompt
              └── 否 → 输出迭代上限警告
```

---

## Stop Hook 集成

### 触发条件

Stop Hook 在以下条件下触发：

1. 状态文件存在 (`.claude/ralph-delta.local.md`)
2. Status = `IN_PROGRESS`
3. 无 `<promise>TASK_COMPLETE</promise>` 标记
4. Iteration.Current < Max Allowed

### 重注入 Prompt 模板

```markdown
════════════════════════════════════════════════════════════
🔄 迭代继续 | 第 {N}/{MAX} 次
════════════════════════════════════════════════════════════

## 上次进度
{completed_work_summary}

## 待完成工作
{pending_work}

## 当前位置
- 路由: {route}
- 阶段: Phase {current_phase}
- 子任务: {current_subtask}

## 指令
继续执行未完成的工作。完成所有工作后，必须在状态文件中设置：
<promise>TASK_COMPLETE</promise>

────────────────────────────────────────────────────────────
```

---

## 完成条件

### 完成检测

任务被视为完成当且仅当：

1. **所有阶段完成**：Completed Phases 包含所有必要阶段
2. **所有子任务完成**：对于 RALPH/ARCHITECT，所有子任务已完成
3. **审查通过**：最后的审查阶段已完成

### 设置完成标记

```markdown
## Promise
<promise>TASK_COMPLETE</promise>

## Completion Summary
- Total Iterations: {count}
- Total Duration: {time}
- Files Modified: {count}
- Review Score: {score}/100
```

### 完成后处理

```
检测到 <promise>TASK_COMPLETE</promise>
    ↓
归档状态文件
    - 移动到 .skillpack/history/{timestamp}/
    - 生成完成报告
    ↓
清理工作目录
    ↓
输出最终摘要
```

---

## 迭代限制

### 默认配置

```yaml
max_iterations: 20           # 最大迭代次数
warning_threshold: 15        # 开始警告的迭代次数
auto_checkpoint_interval: 3  # 自动保存检查点的间隔
```

### 可配置项 (.skillpackrc)

```json
{
  "loop": {
    "max_iterations": 20,
    "warning_threshold": 15,
    "auto_checkpoint_interval": 3,
    "timeout_per_iteration_minutes": 30
  }
}
```

### 达到上限处理

```
Iteration.Current >= Max Allowed
    ↓
╔════════════════════════════════════════════════════════════╗
║ ⚠️ 达到迭代上限                                            ║
╠════════════════════════════════════════════════════════════╣
║ 当前迭代: {current}/{max}                                  ║
║ 已完成: {completed_summary}                                ║
║ 未完成: {pending_summary}                                  ║
╠════════════════════════════════════════════════════════════╣
║ 📋 选项:                                                   ║
║   [1] ➕ 增加迭代上限 (+10)                                ║
║   [2] 🔀 简化任务范围                                      ║
║   [3] 📝 保存进度并退出                                    ║
║   [4] ⛔ 放弃此任务                                        ║
╚════════════════════════════════════════════════════════════╝
请选择 (1-4):
```

---

## 状态更新规范

### 每阶段结束时

```python
def update_state_after_phase(phase_num: int, result: dict):
    """阶段完成后更新状态"""
    state = read_state_file()

    # 更新已完成阶段
    state.completed_phases.append(phase_num)

    # 更新待完成工作
    state.pending_work = calculate_remaining_work()

    # 更新已完成工作摘要
    state.completed_work += format_phase_summary(phase_num, result)

    # 更新时间戳
    state.last_updated = now()

    # 检查是否全部完成
    if all_phases_completed(state):
        state.promise = "TASK_COMPLETE"

    write_state_file(state)
```

### 每子任务结束时

```python
def update_state_after_subtask(subtask_index: int, result: dict):
    """子任务完成后更新状态"""
    state = read_state_file()

    # 更新子任务进度
    state.current_subtask = subtask_index + 1

    # 更新已完成工作
    state.completed_work += format_subtask_summary(subtask_index, result)

    # 保存检查点 (每 N 个子任务)
    if subtask_index % state.auto_checkpoint_interval == 0:
        save_checkpoint(state)

    write_state_file(state)
```

---

## 恢复机制

### 从状态文件恢复

```bash
/do --resume
```

```
检测到未完成状态文件
    ↓
╔════════════════════════════════════════════════════════════╗
║ 🔄 发现未完成任务                                          ║
╠════════════════════════════════════════════════════════════╣
║ 任务: {task_description}                                   ║
║ 路由: {route}                                              ║
║ 进度: Phase {current}/{total}, 迭代 {iteration}           ║
║ 中断时间: {last_updated}                                   ║
╠════════════════════════════════════════════════════════════╣
║ 📋 选项:                                                   ║
║   [1] ▶️ 继续执行                                          ║
║   [2] 🔄 从头开始                                          ║
║   [3] 📝 查看详细进度                                      ║
║   [4] ❌ 放弃此任务                                        ║
╚════════════════════════════════════════════════════════════╝
请选择 (1-4):
```

---

## 示例：RALPH 循环

### 初始状态

```markdown
# Delta Loop State

## Meta
- Task ID: abc123
- Route: RALPH
- Started: 2026-01-18 10:00:00
- Last Updated: 2026-01-18 10:00:00

## Iteration
- Current: 1
- Max Allowed: 20
- Status: IN_PROGRESS

## Progress
- Current Phase: 1
- Completed Phases: []
- Current Subtask: 0 / 5

## Pending Work
1. Phase 1: 深度分析
2. Phase 2: 规划
3. Phase 3: 执行 5 个子任务
4. Phase 4: 综合审查

## Completed Work
(none)

## Promise
<!-- 未完成 -->
```

### 迭代 3 后状态

```markdown
# Delta Loop State

## Meta
- Task ID: abc123
- Route: RALPH
- Started: 2026-01-18 10:00:00
- Last Updated: 2026-01-18 10:35:00

## Iteration
- Current: 3
- Max Allowed: 20
- Status: IN_PROGRESS

## Progress
- Current Phase: 3
- Completed Phases: [1, 2]
- Current Subtask: 2 / 5

## Pending Work
1. Phase 3: 完成剩余 3 个子任务
2. Phase 4: 综合审查

## Completed Work
### Phase 1: 深度分析
- 识别 5 个核心子任务
- 确定依赖关系

### Phase 2: 规划
- 制定执行计划
- 分配资源

### Phase 3: 子任务进度
- [x] 子任务 1: 用户模型
- [x] 子任务 2: 认证服务
- [ ] 子任务 3: 权限检查
- [ ] 子任务 4: 会话管理
- [ ] 子任务 5: 安全审计

## Promise
<!-- 未完成 -->
```

### 完成状态

```markdown
# Delta Loop State

## Meta
- Task ID: abc123
- Route: RALPH
- Started: 2026-01-18 10:00:00
- Last Updated: 2026-01-18 11:20:00

## Iteration
- Current: 5
- Max Allowed: 20
- Status: COMPLETED

## Progress
- Current Phase: 4
- Completed Phases: [1, 2, 3, 4]
- Current Subtask: 5 / 5

## Pending Work
(none)

## Completed Work
### Phase 1-4 完整摘要...

## Promise
<promise>TASK_COMPLETE</promise>

## Completion Summary
- Total Iterations: 5
- Total Duration: 1h 20m
- Files Modified: 12
- Review Score: 92/100
```

---

## 与检查点系统集成 (v5.0 增强)

循环引擎与 `checkpoint.md` v2.0 模块协作：

1. **原子保存**：使用 write-rename 模式，防止数据损坏
2. **SHA-256 校验**：每次保存自动计算校验和
3. **多版本备份**：保留 3 个状态文件备份
4. **恢复点**：状态文件作为恢复的主要数据源
5. **历史记录**：完成后归档到 `.skillpack/history/`

```
.skillpack/
├── current/
│   ├── checkpoint.json           # 检查点数据
│   ├── checkpoint.json.sha256    # 校验和文件
│   ├── checkpoint.json.backup.*  # 多版本备份
│   ├── execution.log.jsonl       # 结构化日志
│   └── ...
└── history/
    └── 2026-01-18_abc123/
        ├── ralph-delta.state.md  # 归档的状态文件
        ├── checkpoint.json
        └── ...

.claude/
└── ralph-delta.local.md          # 活跃的状态文件
```

---

## 日志记录 (v5.0 新增)

迭代相关事件自动记录到 `execution.log.jsonl`：

```json
{"ts":"...","level":"INFO","event":"iteration_start","iteration":1,"phase":1}
{"ts":"...","level":"INFO","event":"iteration_complete","iteration":1,"subtasks_done":2}
{"ts":"...","level":"WARN","event":"iteration_retry","iteration":2,"reason":"mcp_timeout"}
```

### 迭代事件类型

| 事件 | 说明 |
|------|------|
| `iteration_start` | 新迭代开始 |
| `iteration_complete` | 迭代完成 |
| `iteration_retry` | 迭代中重试 |
| `stop_hook_trigger` | Stop Hook 触发 |
| `prompt_reinjected` | Prompt 重新注入 |
| `task_complete` | 任务最终完成 |
