"""
测试 schema.py 配置验证功能
"""

import json
import pytest
from pathlib import Path

from skillpack.schema import (
    validate_config,
    validate_config_file,
    validate_schema,
    format_validation_errors,
    ValidationError,
    SKILLPACKRC_SCHEMA,
)


class TestValidateConfig:
    """测试配置验证"""

    def test_valid_minimal_config(self):
        """测试最小有效配置"""
        config = {"version": "5.4"}
        is_valid, errors = validate_config(config)
        assert is_valid
        assert len(errors) == 0

    def test_valid_full_config(self):
        """测试完整有效配置"""
        config = {
            "version": "5.4",
            "knowledge": {
                "default_notebook": "abc-123",
                "auto_query": True
            },
            "routing": {
                "weights": {
                    "scope": 25,
                    "dependency": 20,
                    "technical": 20,
                    "risk": 15,
                    "time": 10,
                    "ui": 10
                },
                "thresholds": {
                    "direct": 20,
                    "planned": 45,
                    "ralph": 70
                }
            },
            "checkpoint": {
                "auto_save": True,
                "atomic_writes": True,
                "backup_count": 3,
                "save_interval_minutes": 5,
                "max_history": 10
            },
            "cli": {
                "prefer_cli_over_mcp": True,
                "cli_timeout_seconds": 600,
                "codex_command": "codex",
                "gemini_command": "gemini"
            },
            "parallel": {
                "enabled": False,
                "max_concurrent_tasks": 3
            }
        }
        is_valid, errors = validate_config(config)
        assert is_valid, f"Errors: {[str(e) for e in errors]}"

    def test_unknown_property_rejected(self):
        """测试未知属性被拒绝"""
        config = {
            "version": "5.4",
            "unknown_key": "value"
        }
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("unknown property" in str(e) for e in errors)

    def test_invalid_type_rejected(self):
        """测试无效类型被拒绝"""
        config = {
            "version": 5.4  # 应该是字符串
        }
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("string" in str(e) for e in errors)

    def test_integer_out_of_range(self):
        """测试整数超出范围"""
        config = {
            "version": "5.4",
            "routing": {
                "weights": {
                    "scope": 150  # 超过 100
                }
            }
        }
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("100" in str(e) for e in errors)

    def test_integer_negative(self):
        """测试负数被拒绝"""
        config = {
            "version": "5.4",
            "checkpoint": {
                "backup_count": -1
            }
        }
        is_valid, errors = validate_config(config)
        assert not is_valid

    def test_enum_validation(self):
        """测试枚举值验证"""
        config = {
            "version": "5.4",
            "cross_validation": {
                "min_confidence_for_auto_pass": "invalid"
            }
        }
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("one of" in str(e) for e in errors)

    def test_null_value_allowed_for_nullable(self):
        """测试可空字段允许 null"""
        config = {
            "version": "5.4",
            "knowledge": {
                "default_notebook": None
            }
        }
        is_valid, errors = validate_config(config)
        assert is_valid

    def test_nested_unknown_property(self):
        """测试嵌套未知属性"""
        config = {
            "version": "5.4",
            "cli": {
                "prefer_cli_over_mcp": True,
                "unknown_cli_option": True
            }
        }
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("unknown_cli_option" in str(e) for e in errors)


class TestValidateConfigFile:
    """测试配置文件验证"""

    def test_valid_file(self, temp_dir):
        """测试有效配置文件"""
        config_path = temp_dir / ".skillpackrc"
        config_path.write_text(json.dumps({"version": "5.4"}))

        is_valid, errors = validate_config_file(config_path)
        assert is_valid

    def test_missing_file(self, temp_dir):
        """测试缺失文件"""
        config_path = temp_dir / ".skillpackrc"

        is_valid, errors = validate_config_file(config_path)
        assert not is_valid
        assert any("not found" in str(e) for e in errors)

    def test_invalid_json(self, temp_dir):
        """测试无效 JSON"""
        config_path = temp_dir / ".skillpackrc"
        config_path.write_text("{ invalid json }")

        is_valid, errors = validate_config_file(config_path)
        assert not is_valid
        assert any("invalid JSON" in str(e) for e in errors)

    def test_invalid_config_content(self, temp_dir):
        """测试无效配置内容"""
        config_path = temp_dir / ".skillpackrc"
        config_path.write_text(json.dumps({"invalid_key": "value"}))

        is_valid, errors = validate_config_file(config_path)
        assert not is_valid


class TestValidationError:
    """测试 ValidationError 类"""

    def test_error_str(self):
        """测试错误字符串格式"""
        error = ValidationError("routing.weights.scope", "must be >= 0")
        assert str(error) == "routing.weights.scope: must be >= 0"

    def test_error_path(self):
        """测试错误路径"""
        error = ValidationError("cli.timeout", "expected integer")
        assert error.path == "cli.timeout"
        assert error.message == "expected integer"


class TestFormatValidationErrors:
    """测试错误格式化"""

    def test_no_errors(self):
        """测试无错误"""
        result = format_validation_errors([])
        assert "有效" in result

    def test_with_errors(self):
        """测试有错误"""
        errors = [
            ValidationError("version", "expected string"),
            ValidationError("cli.timeout", "must be >= 1")
        ]
        result = format_validation_errors(errors)
        assert "失败" in result
        assert "version" in result
        assert "cli.timeout" in result


class TestSchemaStructure:
    """测试 Schema 结构"""

    def test_schema_has_version(self):
        """测试 schema 包含版本属性"""
        assert "version" in SKILLPACKRC_SCHEMA["properties"]

    def test_schema_has_all_sections(self):
        """测试 schema 包含所有配置节"""
        expected_sections = [
            "version", "knowledge", "routing", "checkpoint",
            "cross_validation", "output", "mcp", "cli", "parallel"
        ]
        for section in expected_sections:
            assert section in SKILLPACKRC_SCHEMA["properties"]

    def test_routing_weights_complete(self):
        """测试路由权重完整"""
        weights = SKILLPACKRC_SCHEMA["properties"]["routing"]["properties"]["weights"]["properties"]
        expected = ["scope", "dependency", "technical", "risk", "time", "ui"]
        for weight in expected:
            assert weight in weights
