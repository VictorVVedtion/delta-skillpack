"""
Gemini CLI 适配器 (v6.0)

根据 Gemini CLI 版本提供适配的命令和功能。
支持 Gemini 3 Pro/Flash 智能路由、Agent Skills 等。
"""

from typing import Dict, List, Optional
from .base import BaseAdapter, CLIVersion, FeatureStatus, AdapterCommand


class GeminiAdapter(BaseAdapter):
    """
    Gemini CLI 适配器

    支持功能:
    - v0.25+: Gemini 3 Pro/Flash 路由, Agent Skills, JSON 输出, Workspace 集成
    - v0.20+: Gemini 3 Pro, 沙箱模式, YOLO 模式
    - v0.15+: @ 文件引用
    """

    # Flash 模型复杂度阈值
    FLASH_COMPLEXITY_THRESHOLD = 5  # 低于此分数使用 Flash

    @property
    def cli_name(self) -> str:
        return "gemini"

    @property
    def min_supported_version(self) -> str:
        return "0.15.0"

    @property
    def recommended_version(self) -> str:
        return "0.25.0"

    def get_available_features(self) -> Dict[str, FeatureStatus]:
        """获取当前版本可用的功能列表"""
        return {
            "agent-skills": self._check_feature("agent-skills", "0.25.0"),
            "json-output": self._check_feature("json-output", "0.25.0"),
            "workspace-integration": self._check_feature("workspace-integration", "0.25.0"),
            "policy-engine": self._check_feature("policy-engine", "0.25.0"),
            "gemini-3-flash": self._check_feature("gemini-3-flash", "0.25.0"),
            "gemini-3-pro": self._check_feature("gemini-3-pro", "0.20.0"),
            "sandbox": self._check_feature("sandbox", "0.20.0"),
            "yolo": self._check_feature("yolo", "0.20.0"),
            "file-context": self._check_feature("file-context", "0.15.0"),
        }

    def build_exec_command(
        self,
        prompt: str,
        sandbox: str = "workspace-write",
        context_files: Optional[List[str]] = None,
        model: Optional[str] = None,
        json_output: bool = False,
        use_skills: bool = False,
        **kwargs
    ) -> AdapterCommand:
        """
        构建 Gemini 执行命令

        Args:
            prompt: 任务提示
            sandbox: 沙箱模式 (映射为 -s 参数)
            context_files: 上下文文件列表 (使用 @ 语法)
            model: 模型名称 (覆盖默认)
            json_output: 是否输出 JSON
            use_skills: 是否使用 Agent Skills

        Returns:
            AdapterCommand 命令结构
        """
        args = []
        env = {}

        # 构建 prompt (包含 @ 文件引用)
        full_prompt = self._build_gemini_prompt(prompt, context_files)
        args.append(full_prompt)

        # 沙箱模式 (v0.20+)
        if sandbox and self.version.has_feature("sandbox"):
            args.append("-s")

        # YOLO 模式 (v0.20+)
        if self.version.has_feature("yolo"):
            args.append("--yolo")

        # 模型选择 (v0.25+)
        if model and self.version.has_feature("gemini-3-flash"):
            args.extend(["-m", model])

        # JSON 输出 (v0.25+)
        if json_output and self.version.has_feature("json-output"):
            args.append("--json")

        # Agent Skills (v0.25+)
        if use_skills and self.version.has_feature("agent-skills"):
            args.append("--enable-skills")

        return AdapterCommand(
            base_command=self.cli_name,
            args=args,
            env=env,
            timeout_seconds=kwargs.get("timeout_seconds", 600),
            sandbox_mode=sandbox,
        )

    def build_ui_command(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        visual_reference: Optional[str] = None,
    ) -> AdapterCommand:
        """
        构建 UI/UX 任务命令

        Args:
            prompt: UI 任务提示
            context_files: 相关组件文件
            visual_reference: 视觉参考图片路径

        Returns:
            AdapterCommand 命令结构
        """
        files = list(context_files or [])

        # 添加视觉参考 (如果有)
        if visual_reference:
            files.insert(0, visual_reference)

        return self.build_exec_command(
            prompt=prompt,
            context_files=files,
            sandbox="workspace-write",
        )

    def build_architecture_command(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
    ) -> AdapterCommand:
        """
        构建架构分析命令

        Args:
            prompt: 架构分析提示
            context_files: 相关文件

        Returns:
            AdapterCommand 命令结构
        """
        # 架构分析使用 Pro 模型
        return self.build_exec_command(
            prompt=prompt,
            context_files=context_files,
            model="gemini-3-pro" if self.version.has_feature("gemini-3-pro") else None,
            sandbox="read-only",  # 分析阶段只读
        )

    def select_model(
        self,
        ui_complexity: int,
        is_analysis_only: bool = False,
    ) -> str:
        """
        智能模型选择

        Args:
            ui_complexity: UI 复杂度分数 (0-10)
            is_analysis_only: 是否仅分析

        Returns:
            推荐的模型名称
        """
        # 检查是否支持 Flash 模型
        if not self.version.has_feature("gemini-3-flash"):
            if self.version.has_feature("gemini-3-pro"):
                return "gemini-3-pro"
            return "gemini-2.5-pro"  # 降级

        # 简单 UI 使用 Flash
        if ui_complexity < self.FLASH_COMPLEXITY_THRESHOLD and not is_analysis_only:
            return "gemini-3-flash"

        # 复杂任务或分析使用 Pro
        return "gemini-3-pro"

    def _build_gemini_prompt(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        max_files: int = 15,
    ) -> str:
        """
        构建 Gemini prompt (使用 @ 语法)

        Gemini CLI 使用 @ 语法引用文件，如:
        @src/components/Button.tsx analyze this component
        """
        if not context_files:
            return prompt

        # 检查是否支持 @ 文件引用
        if not self.version.has_feature("file-context"):
            return prompt

        # 构建文件引用
        file_refs = " ".join(f"@{f}" for f in context_files[:max_files])
        return f"{file_refs} {prompt}"

    def get_command_string(self, cmd: AdapterCommand) -> str:
        """格式化命令字符串（用于日志）"""
        args_display = []
        for arg in cmd.args:
            if arg.startswith("-"):
                args_display.append(arg)
            elif len(arg) > 50:
                args_display.append('"<prompt>"')
            else:
                args_display.append(f'"{arg}"')

        return f"{cmd.base_command} {' '.join(args_display)}"
