# 配置 Schema 验证规范 (Config Schema Validation Spec)

## 概述

配置验证用于确保 `.skillpackrc` 在启动时满足预期结构与约束，避免错误配置导致路由、日志或恢复流程异常。验证方式采用 JSON Schema + 规则校验，包含默认值合并与跨字段约束检查。

---

## Schema 版本

当前版本: **5.0**

### v5.0 变更

| 变更 | 说明 |
|------|------|
| 新增 `parallel` 配置块 | 异步并行执行相关配置 |
| 新增 `parallel.enabled` | 是否启用并行执行（默认 false） |
| 新增 `parallel.max_concurrent_tasks` | 最大并发任务数 |
| 新增 `parallel.poll_interval_seconds` | TaskOutput 轮询间隔 |
| 新增 `parallel.task_timeout_seconds` | 单任务超时时间 |
| 新增 `parallel.allow_cross_model_parallel` | 允许跨模型并行 |
| 新增 `parallel.fallback_to_serial_on_failure` | 失败时降级到串行 |

### v4.0 变更

| 变更 | 说明 |
|------|------|
| 新增 `mcp` 配置块 | MCP 调用相关配置 |
| 新增 `cli` 配置块 | CLI 直接调用相关配置 |
| 新增 `mcp.auto_fallback_to_cli` | 自动降级到 CLI |

---

## 配置结构

以下为完整的 `.skillpackrc` JSON Schema 定义：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": ".skillpackrc",
  "type": "object",
  "additionalProperties": false,
  "required": ["version"],
  "properties": {
    "version": {
      "type": "string",
      "enum": ["5.0"],
      "default": "5.0",
      "description": "配置 Schema 版本"
    },
    "knowledge": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "default_notebook": {
          "anyOf": [
            {"type": "string", "pattern": "^[a-f0-9-]{36}$"},
            {"type": "null"}
          ],
          "default": null,
          "description": "默认 NotebookLM ID (UUID v4)"
        },
        "auto_query": {
          "type": "boolean",
          "default": true,
          "description": "启动时是否自动查询知识库"
        }
      }
    },
    "routing": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "weights": {
          "type": "object",
          "additionalProperties": false,
          "required": ["scope", "dependency", "technical", "risk", "time", "ui"],
          "properties": {
            "scope": {"type": "number", "minimum": 0, "maximum": 100, "default": 25},
            "dependency": {"type": "number", "minimum": 0, "maximum": 100, "default": 20},
            "technical": {"type": "number", "minimum": 0, "maximum": 100, "default": 20},
            "risk": {"type": "number", "minimum": 0, "maximum": 100, "default": 15},
            "time": {"type": "number", "minimum": 0, "maximum": 100, "default": 10},
            "ui": {"type": "number", "minimum": 0, "maximum": 100, "default": 10}
          }
        },
        "thresholds": {
          "type": "object",
          "additionalProperties": false,
          "required": ["direct", "planned", "ralph", "architect"],
          "properties": {
            "direct": {"type": "number", "minimum": 0, "maximum": 100, "default": 20},
            "planned": {"type": "number", "minimum": 0, "maximum": 100, "default": 45},
            "ralph": {"type": "number", "minimum": 0, "maximum": 100, "default": 70},
            "architect": {"type": "number", "minimum": 0, "maximum": 100, "default": 100}
          }
        }
      }
    },
    "checkpoint": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "auto_save": {"type": "boolean", "default": true},
        "atomic_writes": {"type": "boolean", "default": true},
        "backup_count": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
        "save_interval_minutes": {"type": "integer", "minimum": 1, "maximum": 120, "default": 5}
      }
    },
    "logging": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "level": {
          "type": "string",
          "enum": ["ERROR", "WARN", "INFO", "DEBUG", "TRACE"],
          "default": "INFO"
        },
        "format": {"type": "string", "enum": ["jsonl"], "default": "jsonl"},
        "performance_metrics": {"type": "boolean", "default": true}
      }
    },
    "output": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "current_dir": {"type": "string", "default": ".skillpack/current"},
        "history_dir": {"type": "string", "default": ".skillpack/history"},
        "auto_archive": {"type": "boolean", "default": true},
        "max_history": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
      }
    },
    "loop": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "max_iterations": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 20},
        "warning_threshold": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 15},
        "auto_checkpoint_interval": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 5}
      }
    },
    "recovery": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "auto_retry": {"type": "boolean", "default": true},
        "max_auto_retries": {"type": "integer", "minimum": 0, "maximum": 10, "default": 3},
        "auto_fix_syntax": {"type": "boolean", "default": true}
      }
    },
    "mcp": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "timeout_seconds": {"type": "integer", "minimum": 30, "maximum": 600, "default": 180},
        "max_retries": {"type": "integer", "minimum": 0, "maximum": 10, "default": 3},
        "retry_delay_ms": {"type": "integer", "minimum": 500, "maximum": 60000, "default": 2000},
        "auto_chunk_large_tasks": {"type": "boolean", "default": true},
        "chunk_max_tokens": {"type": "integer", "minimum": 1000, "maximum": 10000, "default": 5000},
        "show_progress_after_seconds": {"type": "integer", "minimum": 10, "maximum": 300, "default": 60},
        "auto_fallback_to_cli": {"type": "boolean", "default": true}
      }
    },
    "cli": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "codex_path": {"type": "string", "default": "codex"},
        "gemini_path": {"type": "string", "default": "gemini"},
        "prefer_cli_over_mcp": {"type": "boolean", "default": false},
        "cli_timeout_seconds": {"type": "integer", "minimum": 60, "maximum": 1800, "default": 300},
        "auto_context": {"type": "boolean", "default": true},
        "max_context_files": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        "max_lines_per_file": {"type": "integer", "minimum": 100, "maximum": 2000, "default": 500}
      }
    },
    "parallel": {
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "enabled": {"type": "boolean", "default": false},
        "max_concurrent_tasks": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
        "poll_interval_seconds": {"type": "integer", "minimum": 1, "maximum": 60, "default": 5},
        "task_timeout_seconds": {"type": "integer", "minimum": 60, "maximum": 1800, "default": 300},
        "allow_cross_model_parallel": {"type": "boolean", "default": true},
        "fallback_to_serial_on_failure": {"type": "boolean", "default": true},
        "auto_dag_analysis": {"type": "boolean", "default": true},
        "wave_completion_strategy": {
          "type": "string",
          "enum": ["wait_all", "continue_on_success"],
          "default": "wait_all"
        }
      }
    }
  }
}
```

---

## 字段说明表

字段路径使用点号表示。

### 顶层

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `version` | string | `"5.0"` | Schema 版本 |
| `knowledge` | object | `{}` | 知识库相关配置 |
| `routing` | object | `{}` | 路由评分与阈值 |
| `checkpoint` | object | `{}` | 检查点保存配置 |
| `logging` | object | `{}` | 日志输出配置 |
| `output` | object | `{}` | 输出目录与归档策略 |
| `loop` | object | `{}` | 迭代执行限制 |
| `recovery` | object | `{}` | 自动恢复配置 |
| `mcp` | object | `{}` | MCP 调用配置 (v4.0 新增) |
| `cli` | object | `{}` | CLI 直接调用配置 (v4.0 新增) |
| `parallel` | object | `{}` | 并行执行配置 (v5.0 新增) |

### knowledge

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `knowledge.default_notebook` | string \| null | `null` | 默认 NotebookLM ID (UUID v4) |
| `knowledge.auto_query` | boolean | `true` | 启动时自动查询知识库 |

### routing.weights

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `routing.weights.scope` | number | `25` | 范围广度权重 |
| `routing.weights.dependency` | number | `20` | 依赖复杂度权重 |
| `routing.weights.technical` | number | `20` | 技术深度权重 |
| `routing.weights.risk` | number | `15` | 风险等级权重 |
| `routing.weights.time` | number | `10` | 时间估算权重 |
| `routing.weights.ui` | number | `10` | UI 复杂度权重 |

### routing.thresholds

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `routing.thresholds.direct` | number | `20` | DIRECT 最大分 |
| `routing.thresholds.planned` | number | `45` | PLANNED 最大分 |
| `routing.thresholds.ralph` | number | `70` | RALPH 最大分 |
| `routing.thresholds.architect` | number | `100` | ARCHITECT 最大分 |

### checkpoint

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `checkpoint.auto_save` | boolean | `true` | 自动保存检查点 |
| `checkpoint.atomic_writes` | boolean | `true` | 原子写入避免部分写入 |
| `checkpoint.backup_count` | integer | `3` | 备份数量 |
| `checkpoint.save_interval_minutes` | integer | `5` | 自动保存间隔 (分钟) |

### logging

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `logging.level` | string | `"INFO"` | 日志级别 |
| `logging.format` | string | `"jsonl"` | 日志格式 |
| `logging.performance_metrics` | boolean | `true` | 是否记录性能指标 |

### output

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output.current_dir` | string | `".skillpack/current"` | 当前任务输出目录 |
| `output.history_dir` | string | `".skillpack/history"` | 历史任务目录 |
| `output.auto_archive` | boolean | `true` | 是否自动归档 |
| `output.max_history` | integer | `20` | 最大历史保留数 |

### loop

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `loop.max_iterations` | integer | `20` | 最大迭代次数 |
| `loop.warning_threshold` | integer | `15` | 预警阈值 (接近上限时提示) |
| `loop.auto_checkpoint_interval` | integer | `5` | 每 N 次迭代自动保存 |

### recovery

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `recovery.auto_retry` | boolean | `true` | 自动重试失败步骤 |
| `recovery.max_auto_retries` | integer | `3` | 最大自动重试次数 |
| `recovery.auto_fix_syntax` | boolean | `true` | 自动修复简单语法错误 |

### mcp (v4.0 新增)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mcp.timeout_seconds` | integer | `180` | MCP 调用超时时间 (秒) |
| `mcp.max_retries` | integer | `3` | MCP 最大重试次数 |
| `mcp.retry_delay_ms` | integer | `2000` | 重试间隔 (毫秒) |
| `mcp.auto_chunk_large_tasks` | boolean | `true` | 自动拆分大任务 |
| `mcp.chunk_max_tokens` | integer | `5000` | 任务拆分阈值 (tokens) |
| `mcp.show_progress_after_seconds` | integer | `60` | 显示进度提示阈值 (秒) |
| `mcp.auto_fallback_to_cli` | boolean | `true` | MCP 失败后自动降级到 CLI |

### cli (v4.0 新增)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `cli.codex_path` | string | `"codex"` | Codex CLI 可执行文件路径 |
| `cli.gemini_path` | string | `"gemini"` | Gemini CLI 可执行文件路径 |
| `cli.prefer_cli_over_mcp` | boolean | `false` | 优先使用 CLI（跳过 MCP） |
| `cli.cli_timeout_seconds` | integer | `300` | CLI 命令超时时间 (秒) |
| `cli.auto_context` | boolean | `true` | 自动收集相关文件上下文 |
| `cli.max_context_files` | integer | `10` | 最大上下文文件数 |
| `cli.max_lines_per_file` | integer | `500` | 每个文件最大行数 |

### parallel (v5.0 新增)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `parallel.enabled` | boolean | `false` | 是否启用并行执行 |
| `parallel.max_concurrent_tasks` | integer | `3` | 最大并发任务数 (1-10) |
| `parallel.poll_interval_seconds` | integer | `5` | TaskOutput 轮询间隔 (秒) |
| `parallel.task_timeout_seconds` | integer | `300` | 单任务超时时间 (秒) |
| `parallel.allow_cross_model_parallel` | boolean | `true` | 允许 Codex + Gemini 同时执行 |
| `parallel.fallback_to_serial_on_failure` | boolean | `true` | 并行失败时降级到串行模式 |
| `parallel.auto_dag_analysis` | boolean | `true` | 自动分析任务依赖关系 |
| `parallel.wave_completion_strategy` | string | `"wait_all"` | 波次完成策略: `wait_all` 或 `continue_on_success` |

---

## 验证流程

### Step 1: 读取配置

```
1. 定位项目根目录的 .skillpackrc
2. 文件不存在 → 直接使用默认配置
3. 读取并解析 JSON
```

### Step 2: Schema 校验

```
1. 按 JSON Schema 验证类型/枚举/必填字段
2. 合并 schema 默认值
3. 禁止未知字段 (additionalProperties=false)
```

### Step 3: 约束校验

```
1. routing.weights 总和必须为 100
2. routing.thresholds 必须递增 (direct < planned < ralph < architect)
3. loop.warning_threshold <= loop.max_iterations
4. loop.auto_checkpoint_interval <= loop.max_iterations
```

---

## 错误处理

验证失败时输出统一的错误提示格式：

```
════════════════════════════════════════════════════════════
⚠️ 配置验证失败
════════════════════════════════════════════════════════════
文件: .skillpackrc
Schema: 4.0
错误数: {count}
────────────────────────────────────────────────────────────
[CFG-001] 路径: {json_path}
原因: {reason}
修复: {suggestion}
────────────────────────────────────────────────────────────
```

---

## 迁移指南 (v4.0 → v5.0)

1. **版本升级**: 将 `version` 改为 `"5.0"`。
2. **新增 parallel 配置块**: 添加 `parallel` 配置块（默认禁用）。
3. **启用并行执行**: 设置 `parallel.enabled: true` 以启用异步并行执行。
4. **调整并发限制**: 根据系统资源调整 `max_concurrent_tasks`。

### 最小迁移示例

```json
{
  "version": "5.0",
  "parallel": {
    "enabled": false
  }
}
```

### 启用并行执行示例

```json
{
  "version": "5.0",
  "parallel": {
    "enabled": true,
    "max_concurrent_tasks": 3,
    "poll_interval_seconds": 5,
    "task_timeout_seconds": 300,
    "allow_cross_model_parallel": true,
    "fallback_to_serial_on_failure": true
  }
}
```

迁移完成后运行 Schema 校验，确保无错误提示。

---

## 迁移指南 (v3.0 → v4.0)

1. **版本升级**: 将 `version` 改为 `"4.0"`。
2. **新增 MCP 配置块**: 添加 `mcp` 配置块，按默认值补齐。
3. **新增 CLI 配置块**: 添加 `cli` 配置块，按默认值补齐。
4. **启用自动 CLI 降级**: 设置 `mcp.auto_fallback_to_cli: true` 以启用 MCP 超时后自动降级到 CLI。

### 最小迁移示例

```json
{
  "version": "4.0",
  "mcp": {
    "auto_fallback_to_cli": true
  },
  "cli": {
    "prefer_cli_over_mcp": false,
    "cli_timeout_seconds": 300
  }
}
```

迁移完成后运行 Schema 校验，确保无错误提示。

---

## 迁移指南 (v2.0 → v3.0)

1. **版本升级**: 将 `version` 改为 `"3.0"`。
2. **补齐新字段**: 新增 `output`, `loop`, `recovery` 配置块，按默认值补齐。
3. **历史保留迁移**: 如 v2 使用 `checkpoint.max_history`，请迁移到 `output.max_history`。
4. **日志格式统一**: `logging.format` 固定为 `jsonl`，移除不支持的格式值。
5. **移除未知字段**: v3 禁止额外字段，需删除未在 Schema 中定义的键。
