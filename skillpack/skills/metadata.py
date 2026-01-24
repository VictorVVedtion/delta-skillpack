"""
Skill 元数据解析 (v6.0)

解析 SKILL.toml 和 SKILL.md 文件。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import re


@dataclass
class ModelConfig:
    """模型配置"""
    primary: str = "codex"            # 主要模型
    fallback: Optional[str] = None    # 回退模型
    reasoning_effort: str = "medium"  # 推理努力级别


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str                                       # Skill 名称
    version: str = "1.0.0"                          # 版本号
    description: str = ""                           # 描述
    triggers: List[str] = field(default_factory=list)  # 触发词列表
    models: ModelConfig = field(default_factory=ModelConfig)  # 模型配置
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他 Skill
    tags: List[str] = field(default_factory=list)  # 标签
    author: str = ""                                # 作者
    enabled: bool = True                            # 是否启用
    priority: int = 100                             # 优先级（越小越高）

    # 执行配置
    sandbox_mode: str = "workspace-write"           # 沙箱模式
    timeout_seconds: int = 300                      # 超时时间
    max_retries: int = 1                            # 最大重试次数


def parse_skill_toml(content: str) -> SkillMetadata:
    """
    解析 SKILL.toml 内容

    Args:
        content: TOML 文件内容

    Returns:
        SkillMetadata 元数据对象
    """
    try:
        import tomllib
        data = tomllib.loads(content)
    except ImportError:
        # Python < 3.11 使用 tomli
        try:
            import tomli
            data = tomli.loads(content)
        except ImportError:
            # 回退到简单解析
            data = _simple_toml_parse(content)

    return _dict_to_metadata(data)


def parse_skill_md(content: str) -> Dict[str, Any]:
    """
    解析 SKILL.md 前置元数据

    支持 YAML 前置格式:
    ---
    name: skill-name
    version: 1.0.0
    triggers:
      - trigger1
      - trigger2
    ---

    Args:
        content: Markdown 文件内容

    Returns:
        元数据字典
    """
    # 匹配 YAML 前置
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return {}

    yaml_content = match.group(1)

    try:
        import yaml
        return yaml.safe_load(yaml_content) or {}
    except ImportError:
        # 简单解析
        return _simple_yaml_parse(yaml_content)


def _dict_to_metadata(data: Dict[str, Any]) -> SkillMetadata:
    """将字典转换为 SkillMetadata"""
    skill_data = data.get("skill", data)

    # 解析模型配置
    models_data = skill_data.get("models", {})
    models = ModelConfig(
        primary=models_data.get("primary", "codex"),
        fallback=models_data.get("fallback"),
        reasoning_effort=models_data.get("reasoning_effort", "medium"),
    )

    return SkillMetadata(
        name=skill_data.get("name", "unknown"),
        version=skill_data.get("version", "1.0.0"),
        description=skill_data.get("description", ""),
        triggers=skill_data.get("triggers", []),
        models=models,
        dependencies=skill_data.get("dependencies", []),
        tags=skill_data.get("tags", []),
        author=skill_data.get("author", ""),
        enabled=skill_data.get("enabled", True),
        priority=skill_data.get("priority", 100),
        sandbox_mode=skill_data.get("sandbox_mode", "workspace-write"),
        timeout_seconds=skill_data.get("timeout_seconds", 300),
        max_retries=skill_data.get("max_retries", 1),
    )


def _simple_toml_parse(content: str) -> Dict[str, Any]:
    """简单的 TOML 解析（不依赖外部库）"""
    result = {"skill": {}}
    current_section = "skill"

    for line in content.splitlines():
        line = line.strip()

        # 跳过注释和空行
        if not line or line.startswith("#"):
            continue

        # 检测 section
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            if section.startswith("skill."):
                subsection = section[6:]
                if subsection not in result["skill"]:
                    result["skill"][subsection] = {}
                current_section = subsection
            continue

        # 解析键值对
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            # 解析值
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            elif value.startswith("[") and value.endswith("]"):
                # 简单数组解析
                items = value[1:-1].split(",")
                value = [item.strip().strip('"').strip("'") for item in items if item.strip()]
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)

            if current_section == "skill":
                result["skill"][key] = value
            else:
                if current_section not in result["skill"]:
                    result["skill"][current_section] = {}
                result["skill"][current_section][key] = value

    return result


def _simple_yaml_parse(content: str) -> Dict[str, Any]:
    """简单的 YAML 解析（不依赖外部库）"""
    result = {}
    current_key = None
    current_list = None

    for line in content.splitlines():
        # 跳过注释和空行
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 检测列表项
        if stripped.startswith("- "):
            if current_list is not None:
                current_list.append(stripped[2:].strip().strip('"').strip("'"))
            continue

        # 解析键值对
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()

            if value:
                # 有值，直接赋值
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)

                result[key] = value
                current_key = None
                current_list = None
            else:
                # 无值，可能是列表或嵌套
                current_key = key
                current_list = []
                result[key] = current_list

    return result
