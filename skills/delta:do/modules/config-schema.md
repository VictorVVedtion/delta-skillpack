# 配置 Schema 验证规范 (Config Schema Validation Spec)

## 概述

配置验证用于确保 `.skillpackrc` 在启动时满足预期结构与约束，避免错误配置导致路由、日志或恢复流程异常。验证方式采用 JSON Schema + 规则校验，包含默认值合并与跨字段约束检查。

---

## Schema 版本

当前版本: **3.0**

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
      "enum": ["3.0"],
      "default": "3.0",
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
| `version` | string | `"3.0"` | Schema 版本 |
| `knowledge` | object | `{}` | 知识库相关配置 |
| `routing` | object | `{}` | 路由评分与阈值 |
| `checkpoint` | object | `{}` | 检查点保存配置 |
| `logging` | object | `{}` | 日志输出配置 |
| `output` | object | `{}` | 输出目录与归档策略 |
| `loop` | object | `{}` | 迭代执行限制 |
| `recovery` | object | `{}` | 自动恢复配置 |

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
Schema: 3.0
错误数: {count}
────────────────────────────────────────────────────────────
[CFG-001] 路径: {json_path}
原因: {reason}
修复: {suggestion}
────────────────────────────────────────────────────────────
```

---

## 迁移指南 (v2.0 → v3.0)

1. **版本升级**: 将 `version` 改为 `"3.0"`。
2. **补齐新字段**: 新增 `output`, `loop`, `recovery` 配置块，按默认值补齐。
3. **历史保留迁移**: 如 v2 使用 `checkpoint.max_history`，请迁移到 `output.max_history`。
4. **日志格式统一**: `logging.format` 固定为 `jsonl`，移除不支持的格式值。
5. **移除未知字段**: v3 禁止额外字段，需删除未在 Schema 中定义的键。

迁移完成后运行 Schema 校验，确保无错误提示。
