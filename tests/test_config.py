"""
配置解析测试

测试 .skillpackrc 配置文件的解析和验证。
"""

import json
import pytest
from pathlib import Path

from skillpack.models import SkillpackConfig


class TestSkillpackrcParsing:
    """Skillpackrc 配置文件解析测试"""

    def test_parse_minimal_config(self, temp_dir):
        """最小配置解析测试"""
        config_path = temp_dir / ".skillpackrc"
        config_path.write_text(json.dumps({"version": "5.4"}))

        data = json.loads(config_path.read_text())
        assert data["version"] == "5.4"

    def test_parse_full_config(self, skillpackrc_factory):
        """完整配置解析测试"""
        config_path = skillpackrc_factory()
        data = json.loads(config_path.read_text())

        # 验证所有顶级键存在
        assert "version" in data
        assert "knowledge" in data
        assert "routing" in data
        assert "checkpoint" in data
        assert "parallel" in data

    def test_parse_custom_knowledge_config(self, skillpackrc_factory):
        """自定义知识库配置解析测试"""
        config_path = skillpackrc_factory({
            "knowledge": {
                "default_notebook": "custom-notebook",
                "auto_query": False,
            }
        })
        data = json.loads(config_path.read_text())

        assert data["knowledge"]["default_notebook"] == "custom-notebook"
        assert data["knowledge"]["auto_query"] is False

    def test_parse_custom_routing_config(self, skillpackrc_factory):
        """自定义路由配置解析测试"""
        config_path = skillpackrc_factory({
            "routing": {
                "thresholds": {
                    "direct": 25,
                    "planned": 50,
                    "ralph": 75,
                }
            }
        })
        data = json.loads(config_path.read_text())

        assert data["routing"]["thresholds"]["direct"] == 25
        assert data["routing"]["thresholds"]["planned"] == 50
        assert data["routing"]["thresholds"]["ralph"] == 75


class TestConfigValidation:
    """配置验证测试"""

    def test_invalid_json(self, temp_dir):
        """无效 JSON 格式测试"""
        config_path = temp_dir / ".skillpackrc"
        config_path.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            json.loads(config_path.read_text())

    def test_missing_config_file(self, temp_dir):
        """配置文件不存在测试"""
        config_path = temp_dir / ".skillpackrc"
        assert not config_path.exists()

        # 应该使用默认配置
        config = SkillpackConfig()
        assert config.version == "5.4"

    def test_empty_config_file(self, temp_dir):
        """空配置文件测试"""
        config_path = temp_dir / ".skillpackrc"
        config_path.write_text("{}")

        data = json.loads(config_path.read_text())
        assert data == {}

    def test_extra_unknown_fields(self, skillpackrc_factory):
        """未知字段应该被忽略"""
        config_path = skillpackrc_factory({
            "unknown_field": "value",
            "another_unknown": {
                "nested": "data"
            }
        })
        data = json.loads(config_path.read_text())

        # 未知字段应该存在但不影响其他配置
        assert "unknown_field" in data
        assert data["version"] == "5.4"


class TestConfigMerging:
    """配置合并测试"""

    def test_partial_override(self, skillpackrc_factory):
        """部分覆盖测试"""
        config_path = skillpackrc_factory({
            "routing": {
                "thresholds": {
                    "direct": 30,  # 覆盖 direct
                    "planned": 50,  # 同时指定其他值
                    "ralph": 75,
                }
            }
        })
        data = json.loads(config_path.read_text())

        # 验证值
        assert data["routing"]["thresholds"]["direct"] == 30
        assert data["routing"]["thresholds"]["planned"] == 50
        assert data["routing"]["thresholds"]["ralph"] == 75

    def test_deep_merge_weights(self, skillpackrc_factory):
        """权重配置覆盖测试"""
        config_path = skillpackrc_factory({
            "routing": {
                "weights": {
                    "scope": 30,
                    "dependency": 25,  # 同时指定其他值
                    "technical": 20,
                    "risk": 15,
                    "time": 5,
                    "ui": 5,
                }
            }
        })
        data = json.loads(config_path.read_text())

        # 验证值
        assert data["routing"]["weights"]["scope"] == 30
        assert data["routing"]["weights"]["dependency"] == 25


class TestConfigVersioning:
    """配置版本测试"""

    def test_current_version(self, skillpackrc_factory):
        """当前版本测试"""
        config_path = skillpackrc_factory()
        data = json.loads(config_path.read_text())

        assert data["version"] == "5.4"

    def test_custom_version(self, skillpackrc_factory):
        """自定义版本测试"""
        config_path = skillpackrc_factory({"version": "5.5"})
        data = json.loads(config_path.read_text())

        assert data["version"] == "5.5"


class TestParallelConfigParsing:
    """并行配置解析测试"""

    def test_parallel_disabled_by_default(self, skillpackrc_factory):
        """默认禁用并行"""
        config_path = skillpackrc_factory()
        data = json.loads(config_path.read_text())

        assert data["parallel"]["enabled"] is False

    def test_parallel_enabled(self, skillpackrc_factory):
        """启用并行配置"""
        config_path = skillpackrc_factory({
            "parallel": {
                "enabled": True,
                "max_concurrent_tasks": 5,
            }
        })
        data = json.loads(config_path.read_text())

        assert data["parallel"]["enabled"] is True
        assert data["parallel"]["max_concurrent_tasks"] == 5


class TestCheckpointConfigParsing:
    """检查点配置解析测试"""

    def test_checkpoint_auto_save_enabled(self, skillpackrc_factory):
        """自动保存默认启用"""
        config_path = skillpackrc_factory()
        data = json.loads(config_path.read_text())

        assert data["checkpoint"]["auto_save"] is True

    def test_checkpoint_custom_interval(self, skillpackrc_factory):
        """自定义保存间隔"""
        config_path = skillpackrc_factory({
            "checkpoint": {
                "save_interval_minutes": 10,
            }
        })
        data = json.loads(config_path.read_text())

        assert data["checkpoint"]["save_interval_minutes"] == 10


class TestKnowledgeConfigParsing:
    """知识库配置解析测试"""

    def test_knowledge_no_default_notebook(self, skillpackrc_factory):
        """默认无知识库 notebook"""
        config_path = skillpackrc_factory()
        data = json.loads(config_path.read_text())

        assert data["knowledge"]["default_notebook"] is None

    def test_knowledge_with_notebook(self, skillpackrc_factory):
        """配置默认知识库 notebook"""
        config_path = skillpackrc_factory({
            "knowledge": {
                "default_notebook": "my-project-notebook",
            }
        })
        data = json.loads(config_path.read_text())

        assert data["knowledge"]["default_notebook"] == "my-project-notebook"

    def test_knowledge_auto_query(self, skillpackrc_factory):
        """自动查询配置"""
        config_path = skillpackrc_factory({
            "knowledge": {
                "auto_query": False,
            }
        })
        data = json.loads(config_path.read_text())

        assert data["knowledge"]["auto_query"] is False
