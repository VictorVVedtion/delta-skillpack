"""
Skill 加载器 (v6.0)

支持 Skill 的发现、加载和热重载。
"""

import os
import threading
from pathlib import Path
from typing import List, Optional, Dict, Set
from datetime import datetime
from dataclasses import dataclass

from .registry import SkillRegistry, SkillInfo
from .metadata import SkillMetadata, parse_skill_toml, parse_skill_md


@dataclass
class LoadResult:
    """加载结果"""
    loaded: List[str]           # 已加载的 Skill 名称
    failed: Dict[str, str]      # 失败的 Skill: 错误信息
    skipped: List[str]          # 跳过的 Skill 名称


class SkillLoader:
    """
    Skill 加载器

    支持功能:
    - 从目录发现和加载 Skill
    - 热重载（文件变更自动重载）
    - 增量加载
    - 依赖解析
    """

    # 支持的配置文件名
    CONFIG_FILES = ["SKILL.toml", "skill.toml", "SKILL.md", "skill.md"]

    def __init__(
        self,
        registry: SkillRegistry,
        user_dir: str = "~/.skillpack/skills",
        project_dir: str = ".skillpack/skills",
        debounce_ms: int = 500,
    ):
        """
        初始化加载器

        Args:
            registry: Skill 注册表
            user_dir: 用户 Skill 目录
            project_dir: 项目 Skill 目录
            debounce_ms: 热重载防抖时间
        """
        self._registry = registry
        self._user_dir = Path(user_dir).expanduser()
        self._project_dir = Path(project_dir)
        self._debounce_ms = debounce_ms

        # 热重载状态
        self._watch_thread: Optional[threading.Thread] = None
        self._watching = False
        self._last_reload: Dict[str, float] = {}

        # 加载状态
        self._loaded_paths: Set[Path] = set()

    def load_all(self, include_builtin: bool = True) -> LoadResult:
        """
        加载所有 Skill

        Args:
            include_builtin: 是否包含内置 Skill

        Returns:
            LoadResult 加载结果
        """
        result = LoadResult(loaded=[], failed={}, skipped=[])

        # 1. 加载内置 Skill
        if include_builtin:
            builtin_result = self._load_builtin()
            result.loaded.extend(builtin_result.loaded)
            result.failed.update(builtin_result.failed)

        # 2. 加载用户 Skill
        if self._user_dir.exists():
            user_result = self._load_from_directory(self._user_dir, source="user")
            result.loaded.extend(user_result.loaded)
            result.failed.update(user_result.failed)

        # 3. 加载项目 Skill
        if self._project_dir.exists():
            project_result = self._load_from_directory(self._project_dir, source="project")
            result.loaded.extend(project_result.loaded)
            result.failed.update(project_result.failed)

        return result

    def load_from_path(self, path: Path, source: str = "user") -> Optional[SkillInfo]:
        """
        从路径加载单个 Skill

        Args:
            path: Skill 目录或配置文件路径
            source: 来源标识

        Returns:
            SkillInfo 或 None
        """
        skill_dir = path if path.is_dir() else path.parent

        # 查找配置文件
        config_file = self._find_config_file(skill_dir)
        if not config_file:
            return None

        try:
            # 解析配置
            content = config_file.read_text(encoding="utf-8")

            if config_file.suffix == ".toml":
                metadata = parse_skill_toml(content)
            else:
                # Markdown 格式
                md_meta = parse_skill_md(content)
                metadata = SkillMetadata(
                    name=md_meta.get("name", skill_dir.name),
                    version=md_meta.get("version", "1.0.0"),
                    description=md_meta.get("description", ""),
                    triggers=md_meta.get("triggers", []),
                    tags=md_meta.get("tags", []),
                )

            # 读取 prompt 模板
            prompt_template = self._read_prompt_template(skill_dir, content if config_file.suffix == ".md" else "")

            # 创建 SkillInfo
            skill = SkillInfo(
                metadata=metadata,
                path=skill_dir,
                prompt_template=prompt_template,
                loaded_at=datetime.now().isoformat(),
                source=source,
            )

            # 注册
            self._registry.register(skill)
            self._loaded_paths.add(skill_dir)

            return skill

        except Exception as e:
            print(f"⚠️ 加载 Skill 失败 ({skill_dir}): {e}")
            return None

    def reload(self, name: str) -> bool:
        """
        重新加载指定 Skill

        Args:
            name: Skill 名称

        Returns:
            是否重载成功
        """
        skill = self._registry.get(name)
        if not skill:
            return False

        # 注销旧 Skill
        self._registry.unregister(name)

        # 重新加载
        new_skill = self.load_from_path(skill.path, skill.source)
        return new_skill is not None

    def start_watching(self):
        """启动热重载监视"""
        if self._watching:
            return

        self._watching = True
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()

    def stop_watching(self):
        """停止热重载监视"""
        self._watching = False
        if self._watch_thread:
            self._watch_thread.join(timeout=1)
            self._watch_thread = None

    def _load_builtin(self) -> LoadResult:
        """加载内置 Skill"""
        result = LoadResult(loaded=[], failed={}, skipped=[])

        # 内置 Skill 目录
        builtin_dir = Path(__file__).parent / "builtin"
        if builtin_dir.exists():
            for item in builtin_dir.iterdir():
                if item.is_dir() and self._find_config_file(item):
                    skill = self.load_from_path(item, source="builtin")
                    if skill:
                        result.loaded.append(skill.name)
                    else:
                        result.failed[item.name] = "加载失败"

        return result

    def _load_from_directory(self, directory: Path, source: str) -> LoadResult:
        """从目录加载所有 Skill"""
        result = LoadResult(loaded=[], failed={}, skipped=[])

        if not directory.exists():
            return result

        for item in directory.iterdir():
            if not item.is_dir():
                continue

            # 检查是否已加载
            if item in self._loaded_paths:
                result.skipped.append(item.name)
                continue

            skill = self.load_from_path(item, source=source)
            if skill:
                result.loaded.append(skill.name)
            else:
                result.failed[item.name] = "无法解析配置"

        return result

    def _find_config_file(self, directory: Path) -> Optional[Path]:
        """查找配置文件"""
        for config_name in self.CONFIG_FILES:
            config_path = directory / config_name
            if config_path.exists():
                return config_path
        return None

    def _read_prompt_template(self, skill_dir: Path, md_content: str = "") -> str:
        """读取 prompt 模板"""
        # 优先使用独立的 prompt.md 文件
        prompt_file = skill_dir / "prompt.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")

        # 如果是 SKILL.md，使用 YAML 之后的内容作为模板
        if md_content:
            import re
            match = re.match(r'^---\s*\n.*?\n---\s*\n(.*)$', md_content, re.DOTALL)
            if match:
                return match.group(1).strip()

        # 查找 CLAUDE.md
        claude_md = skill_dir / "CLAUDE.md"
        if claude_md.exists():
            return claude_md.read_text(encoding="utf-8")

        return ""

    def _watch_loop(self):
        """热重载监视循环"""
        import time

        while self._watching:
            try:
                self._check_changes()
            except Exception:
                pass
            time.sleep(self._debounce_ms / 1000)

    def _check_changes(self):
        """检查文件变更"""
        import os

        for skill_path in self._loaded_paths.copy():
            if not skill_path.exists():
                # 目录被删除，注销 Skill
                for skill in list(self._registry):
                    if skill.path == skill_path:
                        self._registry.unregister(skill.name)
                        self._loaded_paths.discard(skill_path)
                continue

            # 检查配置文件修改时间
            config_file = self._find_config_file(skill_path)
            if config_file:
                mtime = config_file.stat().st_mtime
                last_mtime = self._last_reload.get(str(skill_path), 0)

                if mtime > last_mtime:
                    # 文件已修改，重新加载
                    for skill in list(self._registry):
                        if skill.path == skill_path:
                            self.reload(skill.name)
                            break
                    self._last_reload[str(skill_path)] = mtime
