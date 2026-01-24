"""
Codex CLI 适配器 (v6.0)

根据 Codex CLI 版本提供适配的命令和功能。
支持 GPT-5.2-Codex、GPT-5.1-Codex-Max 等模型路由。
"""

from typing import Dict, List, Optional
from .base import BaseAdapter, CLIVersion, FeatureStatus, AdapterCommand


class CodexAdapter(BaseAdapter):
    """
    Codex CLI 适配器

    支持功能:
    - v0.89+: Skills 系统, Fork 分支, GPT-5.2-Codex
    - v0.85+: 多对话控制, 线程回滚
    - v0.80+: --full-auto, 沙箱模式
    """

    # 模型选择阈值
    MAX_MODEL_TOKEN_THRESHOLD = 100_000  # 超过此 token 数使用 Codex-Max

    @property
    def cli_name(self) -> str:
        return "codex"

    @property
    def min_supported_version(self) -> str:
        return "0.80.0"

    @property
    def recommended_version(self) -> str:
        return "0.89.0"

    def get_available_features(self) -> Dict[str, FeatureStatus]:
        """获取当前版本可用的功能列表"""
        return {
            "skills": self._check_feature("skills", "0.89.0"),
            "fork": self._check_feature("fork", "0.89.0"),
            "gpt-5.2-codex": self._check_feature("gpt-5.2-codex", "0.89.0"),
            "multi-conversation": self._check_feature("multi-conversation", "0.85.0"),
            "thread-rollback": self._check_feature("thread-rollback", "0.85.0"),
            "full-auto": self._check_feature("full-auto", "0.80.0"),
            "sandbox": self._check_feature("sandbox", "0.80.0"),
            "exec": self._check_feature("exec", "0.75.0"),
        }

    def build_exec_command(
        self,
        prompt: str,
        sandbox: str = "workspace-write",
        context_files: Optional[List[str]] = None,
        model: Optional[str] = None,
        use_skills: bool = False,
        fork_branch: Optional[str] = None,
        **kwargs
    ) -> AdapterCommand:
        """
        构建 Codex 执行命令

        Args:
            prompt: 任务提示
            sandbox: 沙箱模式 (read-only, workspace-write, danger-full-access)
            context_files: 上下文文件列表
            model: 模型名称 (覆盖默认)
            use_skills: 是否使用 Skills 系统
            fork_branch: Fork 分支名称

        Returns:
            AdapterCommand 命令结构
        """
        args = ["exec"]
        env = {}

        # 添加 prompt
        full_prompt = self._build_prompt_with_context(prompt, context_files)
        args.append(full_prompt)

        # 沙箱模式
        if sandbox == "workspace-write":
            # 使用 --full-auto (v0.80+)
            if self.version.has_feature("full-auto"):
                args.append("--full-auto")
            else:
                # 降级到基础沙箱
                args.extend(["-s", sandbox])
        elif sandbox:
            args.extend(["-s", sandbox])

        # 跳过 git 检查
        args.append("--skip-git-repo-check")

        # 模型选择 (v0.89+)
        if model:
            if self.version.has_feature("gpt-5.2-codex"):
                args.extend(["-m", model])
            # 低版本忽略模型参数，使用默认

        # Skills 系统 (v0.89+)
        if use_skills and self.version.has_feature("skills"):
            args.append("--enable-skills")

        # Fork 分支 (v0.89+)
        if fork_branch and self.version.has_feature("fork"):
            args.extend(["--fork", fork_branch])

        return AdapterCommand(
            base_command=self.cli_name,
            args=args,
            env=env,
            timeout_seconds=kwargs.get("timeout_seconds", 600),
            sandbox_mode=sandbox,
        )

    def build_planning_command(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
    ) -> AdapterCommand:
        """
        构建规划模式命令（只读沙箱）

        Args:
            prompt: 规划任务提示
            context_files: 上下文文件列表

        Returns:
            AdapterCommand 命令结构
        """
        return self.build_exec_command(
            prompt=prompt,
            sandbox="read-only",
            context_files=context_files,
        )

    def select_model(
        self,
        estimated_tokens: int,
        task_complexity: str,
        route: str,
    ) -> str:
        """
        智能模型选择

        Args:
            estimated_tokens: 预估 token 数
            task_complexity: 任务复杂度 (simple, medium, complex, architect)
            route: 执行路由

        Returns:
            推荐的模型名称
        """
        # 检查是否支持新模型
        if not self.version.has_feature("gpt-5.2-codex"):
            return "gpt-5.1-codex"  # 降级到旧版模型

        # ARCHITECT 路由或超大任务使用 Codex-Max
        if route == "ARCHITECT" or estimated_tokens > self.MAX_MODEL_TOKEN_THRESHOLD:
            return "gpt-5.1-codex-max"

        # 复杂任务使用高推理模式
        if task_complexity in ("complex", "architect"):
            return "gpt-5.2-codex"

        # 默认使用标准模型
        return "gpt-5.2-codex"

    def _build_prompt_with_context(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        max_files: int = 15,
        max_lines_per_file: int = 800,
    ) -> str:
        """构建包含文件上下文的 prompt"""
        if not context_files:
            return prompt

        from pathlib import Path

        context_parts = []
        for file_path in context_files[:max_files]:
            try:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    lines = path.read_text().splitlines()
                    if len(lines) > max_lines_per_file:
                        lines = lines[:max_lines_per_file]
                        lines.append(f"... (truncated at {max_lines_per_file} lines)")
                    content = "\n".join(lines)
                    context_parts.append(f"### {file_path}\n```\n{content}\n```")
            except Exception:
                continue

        if context_parts:
            context_section = "\n\n".join(context_parts)
            return f"{prompt}\n\n相关文件:\n{context_section}"

        return prompt

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
