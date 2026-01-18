"""
知识库管理模块

集成 NotebookLM 进行知识库的创建、查询和管理
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Any


@dataclass
class NotebookInfo:
    """Notebook 信息"""
    notebook_id: str
    title: str
    source_count: int = 0


class KnowledgeManager:
    """
    知识库管理器

    负责：
    - 创建项目专用 notebook
    - 查询 notebook 内容
    - 同步项目文件到 notebook
    """

    def __init__(
        self,
        project_dir: Path,
        mcp_caller: Optional[Callable[[str, dict], Any]] = None
    ):
        """
        Args:
            project_dir: 项目目录
            mcp_caller: MCP 工具调用函数 (用于 Claude Code 集成)
        """
        self.project_dir = project_dir
        self.config_path = project_dir / ".skillpackrc"
        self.mcp_caller = mcp_caller

    def _load_config(self) -> dict:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        return {}

    def _save_config(self, config: dict):
        """保存配置"""
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def get_notebook_id(self) -> Optional[str]:
        """获取当前配置的 notebook ID"""
        config = self._load_config()
        return config.get("knowledge", {}).get("default_notebook")

    def set_notebook_id(self, notebook_id: str):
        """设置 notebook ID 到配置"""
        config = self._load_config()
        if "knowledge" not in config:
            config["knowledge"] = {}
        config["knowledge"]["default_notebook"] = notebook_id
        self._save_config(config)

    def get_project_name(self) -> str:
        """获取项目名称（用于 notebook 标题）"""
        return self.project_dir.name

    def create_notebook_title(self) -> str:
        """生成 notebook 标题"""
        project_name = self.get_project_name()
        return f"SkillPack: {project_name}"

    def has_notebook(self) -> bool:
        """检查是否已配置 notebook"""
        return self.get_notebook_id() is not None


# Claude Code 集成辅助函数
def generate_init_instructions(project_dir: Path) -> str:
    """
    生成初始化指令（供 Claude Code 执行）

    Returns:
        Claude Code 可执行的指令文本
    """
    project_name = project_dir.name
    config_path = project_dir / ".skillpackrc"

    return f"""
## 初始化 SkillPack 知识库

请执行以下步骤：

1. 创建 NotebookLM notebook:
   ```
   使用 mcp__notebooklm-mcp__notebook_create 创建标题为 "SkillPack: {project_name}" 的 notebook
   ```

2. 获取 notebook ID 后，更新配置文件 {config_path}:
   ```json
   {{
     "knowledge": {{
       "default_notebook": "<notebook_id>",
       "auto_query": true
     }}
   }}
   ```

3. 可选：添加项目关键文件为 source
"""


def parse_notebook_id_from_response(response: str) -> Optional[str]:
    """
    从 MCP 响应中解析 notebook ID

    Args:
        response: MCP 工具返回的响应

    Returns:
        notebook_id 或 None
    """
    # 尝试解析 JSON 响应
    try:
        data = json.loads(response)
        # 常见的 ID 字段名
        for key in ["notebook_id", "id", "notebookId"]:
            if key in data:
                return data[key]
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试从文本中提取 UUID 格式的 ID
    import re
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    matches = re.findall(uuid_pattern, response.lower())
    if matches:
        return matches[0]

    return None
