# 日志系统规范 (Logging System Spec)

## 概述

结构化日志用于完整记录执行过程、性能指标与关键事件，便于问题定位、性能分析与任务回溯。日志采用 JSONL 流式写入，保证可追加、可索引、可批量分析。

---

## 日志格式

日志采用 JSONL（每行一个 JSON 对象）：

```json
{"timestamp":"2026-01-18T10:30:00Z","level":"INFO","phase":"Phase 2/3","model":"Codex","event":"phase_start","msg":"开始实现","metrics":{"duration_ms":0,"tokens_used":0,"files_count":0},"context":{"task_id":"uuid-v4","route":"PLANNED"}}
```

规则：
- 一行一条事件记录，禁止多行 JSON。
- `timestamp` 使用 ISO 8601 UTC 格式。
- `metrics` 与 `context` 可为空或省略。

---

## 日志文件

执行日志文件固定为：

```
.skillpack/current/execution.log.jsonl
```

---

## 日志字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timestamp` | string | 是 | 事件时间 (ISO 8601) |
| `level` | string | 是 | 日志级别 |
| `phase` | string | 是 | 执行阶段 (如 `Phase 1/3`) |
| `model` | string | 是 | 执行模型 (如 `Claude`, `Codex`, `Gemini`) |
| `event` | string | 是 | 事件类型 |
| `msg` | string | 是 | 可读消息 |
| `metrics` | object | 否 | 性能指标对象 |
| `context` | object | 否 | 上下文扩展字段 |

---

## 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| `ERROR` | 错误 | 任务失败、不可恢复错误 |
| `WARN` | 警告 | 降级、重试、潜在风险 |
| `INFO` | 信息 | 阶段切换、关键事件 |
| `DEBUG` | 调试 | 细节流程、参数记录 |
| `TRACE` | 追踪 | 最细粒度事件 |

---

## 事件类型

核心事件：
- `phase_start`, `phase_complete`
- `mcp_call`, `mcp_retry`, `mcp_fail`
- `checkpoint_write`, `checkpoint_verify`
- `file_read`, `file_write`
- `recovery_start`, `recovery_success`, `recovery_fail`

---

## 性能指标

`metrics` 对象字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `duration_ms` | number | 事件耗时 |
| `tokens_used` | number | 使用 token 数 |
| `files_count` | number | 关联文件数量 |

---

## 日志轮转

自动归档策略：
1. 任务完成时，将 `execution.log.jsonl` 移动到历史目录：
   `.skillpack/history/<timestamp>/execution.log.jsonl`
2. 当 `output.auto_archive=false` 时，保留在 `current` 目录。
3. 仅保留最近 `output.max_history` 份历史记录，超出部分按时间清理。

---

## 查询示例

使用 `jq` 查询日志：

```bash
# 查看所有错误
jq -r 'select(.level=="ERROR") | .timestamp + " " + .msg' .skillpack/current/execution.log.jsonl

# 统计事件类型数量
jq -r '.event' .skillpack/current/execution.log.jsonl | sort | uniq -c

# 查看阶段完成耗时
jq -r 'select(.event=="phase_complete") | .phase + " " + (.metrics.duration_ms|tostring)' .skillpack/current/execution.log.jsonl
```
