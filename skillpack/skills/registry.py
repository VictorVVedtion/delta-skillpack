"""
Skill 注册表 (v6.0)

管理 Skill 的注册、查找和执行。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import fnmatch

from .metadata import SkillMetadata, parse_skill_toml, parse_skill_md


@dataclass
class SkillInfo:
    """Skill 完整信息"""
    metadata: SkillMetadata              # 元数据
    path: Path                           # Skill 路径
    prompt_template: str = ""            # Prompt 模板
    loaded_at: str = ""                  # 加载时间
    source: str = "user"                 # 来源 (builtin, user, project)

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def triggers(self) -> List[str]:
        return self.metadata.triggers

    @property
    def enabled(self) -> bool:
        return self.metadata.enabled


class SkillRegistry:
    """
    Skill 注册表

    支持功能:
    - Skill 注册和注销
    - 按名称/触发词查找
    - 优先级排序
    - 冲突检测
    """

    def __init__(self):
        self._skills: Dict[str, SkillInfo] = {}       # name -> SkillInfo
        self._triggers: Dict[str, str] = {}           # trigger -> skill_name
        self._tags: Dict[str, List[str]] = {}         # tag -> [skill_names]
        self._load_callbacks: List[Callable[[SkillInfo], None]] = []
        self._unload_callbacks: List[Callable[[str], None]] = []

    def register(self, skill: SkillInfo, force: bool = False) -> bool:
        """
        注册 Skill

        Args:
            skill: Skill 信息
            force: 是否强制覆盖

        Returns:
            是否注册成功
        """
        name = skill.name

        # 检查是否已存在
        if name in self._skills and not force:
            existing = self._skills[name]
            # 比较优先级
            if skill.metadata.priority >= existing.metadata.priority:
                return False

        # 检查触发词冲突
        for trigger in skill.triggers:
            if trigger in self._triggers and self._triggers[trigger] != name:
                if not force:
                    # 检查优先级
                    existing_name = self._triggers[trigger]
                    if existing_name in self._skills:
                        existing = self._skills[existing_name]
                        if skill.metadata.priority >= existing.metadata.priority:
                            continue  # 保留现有触发词映射
                # 覆盖触发词映射
                self._triggers[trigger] = name

        # 注册 Skill
        self._skills[name] = skill

        # 注册触发词
        for trigger in skill.triggers:
            self._triggers[trigger] = name

        # 注册标签
        for tag in skill.metadata.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            if name not in self._tags[tag]:
                self._tags[tag].append(name)

        # 调用回调
        for callback in self._load_callbacks:
            try:
                callback(skill)
            except Exception:
                pass

        return True

    def unregister(self, name: str) -> bool:
        """
        注销 Skill

        Args:
            name: Skill 名称

        Returns:
            是否注销成功
        """
        if name not in self._skills:
            return False

        skill = self._skills[name]

        # 移除触发词映射
        for trigger in skill.triggers:
            if trigger in self._triggers and self._triggers[trigger] == name:
                del self._triggers[trigger]

        # 移除标签映射
        for tag in skill.metadata.tags:
            if tag in self._tags and name in self._tags[tag]:
                self._tags[tag].remove(name)

        # 移除 Skill
        del self._skills[name]

        # 调用回调
        for callback in self._unload_callbacks:
            try:
                callback(name)
            except Exception:
                pass

        return True

    def get(self, name: str) -> Optional[SkillInfo]:
        """按名称获取 Skill"""
        return self._skills.get(name)

    def get_by_trigger(self, trigger: str) -> Optional[SkillInfo]:
        """按触发词获取 Skill"""
        skill_name = self._triggers.get(trigger)
        if skill_name:
            return self._skills.get(skill_name)
        return None

    def find_by_trigger(self, text: str) -> Optional[SkillInfo]:
        """
        在文本中查找匹配的 Skill

        支持模糊匹配和通配符。
        """
        text_lower = text.lower()

        # 精确匹配
        for trigger, name in self._triggers.items():
            if trigger.lower() in text_lower:
                skill = self._skills.get(name)
                if skill and skill.enabled:
                    return skill

        return None

    def find_by_tag(self, tag: str) -> List[SkillInfo]:
        """按标签查找 Skill"""
        names = self._tags.get(tag, [])
        return [self._skills[name] for name in names if name in self._skills]

    def find_by_pattern(self, pattern: str) -> List[SkillInfo]:
        """按模式查找 Skill（支持通配符）"""
        results = []
        for name, skill in self._skills.items():
            if fnmatch.fnmatch(name, pattern):
                results.append(skill)
        return results

    def list_all(self, enabled_only: bool = True) -> List[SkillInfo]:
        """列出所有 Skill"""
        skills = list(self._skills.values())
        if enabled_only:
            skills = [s for s in skills if s.enabled]
        # 按优先级排序
        skills.sort(key=lambda s: s.metadata.priority)
        return skills

    def list_triggers(self) -> Dict[str, str]:
        """列出所有触发词映射"""
        return self._triggers.copy()

    def on_load(self, callback: Callable[[SkillInfo], None]):
        """注册加载回调"""
        self._load_callbacks.append(callback)

    def on_unload(self, callback: Callable[[str], None]):
        """注册注销回调"""
        self._unload_callbacks.append(callback)

    def clear(self):
        """清空注册表"""
        self._skills.clear()
        self._triggers.clear()
        self._tags.clear()

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __iter__(self):
        return iter(self._skills.values())
