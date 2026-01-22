"""
配置模式验证

提供 .skillpackrc 配置文件的 JSON Schema 验证功能。
"""

from typing import Any, Dict, List, Optional, Tuple
import json
from pathlib import Path


# JSON Schema for .skillpackrc
SKILLPACKRC_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SkillpackConfig",
    "description": "Delta Skillpack configuration file schema",
    "type": "object",
    "properties": {
        "version": {
            "type": "string",
            "description": "Configuration version",
            "pattern": r"^\d+\.\d+$",
            "examples": ["5.4"]
        },
        "knowledge": {
            "type": "object",
            "properties": {
                "default_notebook": {
                    "type": ["string", "null"],
                    "description": "Default NotebookLM notebook ID"
                },
                "auto_query": {
                    "type": "boolean",
                    "default": True,
                    "description": "Automatically query knowledge base"
                }
            },
            "additionalProperties": False
        },
        "routing": {
            "type": "object",
            "properties": {
                "weights": {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "integer", "minimum": 0, "maximum": 100},
                        "dependency": {"type": "integer", "minimum": 0, "maximum": 100},
                        "technical": {"type": "integer", "minimum": 0, "maximum": 100},
                        "risk": {"type": "integer", "minimum": 0, "maximum": 100},
                        "time": {"type": "integer", "minimum": 0, "maximum": 100},
                        "ui": {"type": "integer", "minimum": 0, "maximum": 100}
                    },
                    "additionalProperties": False
                },
                "thresholds": {
                    "type": "object",
                    "properties": {
                        "direct": {"type": "integer", "minimum": 0, "maximum": 100},
                        "planned": {"type": "integer", "minimum": 0, "maximum": 100},
                        "ralph": {"type": "integer", "minimum": 0, "maximum": 100}
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        },
        "checkpoint": {
            "type": "object",
            "properties": {
                "auto_save": {"type": "boolean", "default": True},
                "atomic_writes": {"type": "boolean", "default": True},
                "backup_count": {"type": "integer", "minimum": 0, "maximum": 10},
                "save_interval_minutes": {"type": "integer", "minimum": 1},
                "max_history": {"type": "integer", "minimum": 1}
            },
            "additionalProperties": False
        },
        "cross_validation": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "default": True},
                "require_arbitration_on_disagreement": {"type": "boolean"},
                "min_confidence_for_auto_pass": {
                    "type": "string",
                    "enum": ["low", "medium", "high"]
                }
            },
            "additionalProperties": False
        },
        "output": {
            "type": "object",
            "properties": {
                "current_dir": {"type": "string"},
                "history_dir": {"type": "string"}
            },
            "additionalProperties": False
        },
        "mcp": {
            "type": "object",
            "properties": {
                "timeout_seconds": {"type": "integer", "minimum": 1},
                "max_retries": {"type": "integer", "minimum": 0},
                "auto_fallback_to_cli": {"type": "boolean"}
            },
            "additionalProperties": False
        },
        "cli": {
            "type": "object",
            "properties": {
                "prefer_cli_over_mcp": {"type": "boolean", "default": True},
                "cli_timeout_seconds": {"type": "integer", "minimum": 1},
                "codex_command": {"type": "string"},
                "gemini_command": {"type": "string"},
                "auto_context": {"type": "boolean"},
                "max_context_files": {"type": "integer", "minimum": 1},
                "max_lines_per_file": {"type": "integer", "minimum": 1}
            },
            "additionalProperties": False
        },
        "parallel": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "default": False},
                "max_concurrent_tasks": {"type": "integer", "minimum": 1, "maximum": 10},
                "fallback_to_serial_on_failure": {"type": "boolean"}
            },
            "additionalProperties": False
        },
        "logging": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["debug", "info", "warning", "error", "critical"],
                    "default": "info"
                },
                "console_enabled": {"type": "boolean", "default": True},
                "file_enabled": {"type": "boolean", "default": True},
                "file_path": {"type": "string"},
                "max_size_mb": {"type": "integer", "minimum": 1, "maximum": 100},
                "backup_count": {"type": "integer", "minimum": 0, "maximum": 10},
                "json_format": {"type": "boolean", "default": False}
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}


class ValidationError:
    """验证错误"""
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def validate_type(value: Any, expected_type: Any, path: str) -> List[ValidationError]:
    """验证值类型"""
    errors = []

    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(ValidationError(path, f"expected string, got {type(value).__name__}"))
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(ValidationError(path, f"expected integer, got {type(value).__name__}"))
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(ValidationError(path, f"expected boolean, got {type(value).__name__}"))
    elif expected_type == "object":
        if not isinstance(value, dict):
            errors.append(ValidationError(path, f"expected object, got {type(value).__name__}"))
    elif expected_type == "array":
        if not isinstance(value, list):
            errors.append(ValidationError(path, f"expected array, got {type(value).__name__}"))
    elif isinstance(expected_type, list):
        # Union type, e.g. ["string", "null"]
        valid = False
        for t in expected_type:
            if t == "null" and value is None:
                valid = True
                break
            elif t == "string" and isinstance(value, str):
                valid = True
                break
            elif t == "integer" and isinstance(value, int) and not isinstance(value, bool):
                valid = True
                break
        if not valid:
            errors.append(ValidationError(path, f"expected one of {expected_type}, got {type(value).__name__}"))

    return errors


def validate_schema(
    data: Dict[str, Any],
    schema: Dict[str, Any],
    path: str = ""
) -> List[ValidationError]:
    """
    验证数据是否符合 schema。

    Args:
        data: 要验证的数据
        schema: JSON Schema
        path: 当前路径（用于错误消息）

    Returns:
        验证错误列表
    """
    errors: List[ValidationError] = []

    # 检查类型
    if "type" in schema:
        type_errors = validate_type(data, schema["type"], path or "root")
        if type_errors:
            return type_errors  # 类型错误直接返回

    # 验证对象属性
    if schema.get("type") == "object" and isinstance(data, dict):
        properties = schema.get("properties", {})

        for key, value in data.items():
            key_path = f"{path}.{key}" if path else key

            if key in properties:
                prop_schema = properties[key]
                errors.extend(validate_schema(value, prop_schema, key_path))
            elif schema.get("additionalProperties") is False:
                errors.append(ValidationError(key_path, "unknown property"))

        # 检查 enum
        if "enum" in schema and data not in schema["enum"]:
            errors.append(ValidationError(path, f"must be one of {schema['enum']}"))

    # 验证数值范围
    if schema.get("type") == "integer" and isinstance(data, int):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(ValidationError(path, f"must be >= {schema['minimum']}"))
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(ValidationError(path, f"must be <= {schema['maximum']}"))

    # 验证 enum
    if "enum" in schema and data not in schema["enum"]:
        errors.append(ValidationError(path, f"must be one of {schema['enum']}"))

    return errors


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
    """
    验证配置字典。

    Args:
        config: 配置字典

    Returns:
        (是否有效, 错误列表)
    """
    errors = validate_schema(config, SKILLPACKRC_SCHEMA)
    return len(errors) == 0, errors


def validate_config_file(path: Path) -> Tuple[bool, List[ValidationError]]:
    """
    验证配置文件。

    Args:
        path: 配置文件路径

    Returns:
        (是否有效, 错误列表)
    """
    if not path.exists():
        return False, [ValidationError("file", f"config file not found: {path}")]

    try:
        config = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return False, [ValidationError("file", f"invalid JSON: {e}")]

    return validate_config(config)


def format_validation_errors(errors: List[ValidationError]) -> str:
    """格式化验证错误为用户友好的消息"""
    if not errors:
        return "✅ 配置有效"

    lines = ["❌ 配置验证失败:"]
    for error in errors:
        lines.append(f"  • {error}")
    return "\n".join(lines)
