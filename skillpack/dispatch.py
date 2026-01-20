"""
模型调度器

负责根据配置决定使用 CLI 或 MCP 调用 Codex/Gemini。
v5.4.0: CLI 优先模式，真实调用外部模型。
"""

import os
import subprocess
import shlex
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List
import json
import time

from .models import SkillpackConfig
from .usage import UsageStore, UsageRecord


class ModelType(Enum):
    """模型类型"""
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"


class ExecutionMode(Enum):
    """执行模式"""
    CLI = "cli"
    MCP = "mcp"


@dataclass
class DispatchResult:
    """调度结果"""
    success: bool
    output: str
    error: Optional[str] = None
    model: Optional[ModelType] = None
    mode: Optional[ExecutionMode] = None
    duration_ms: int = 0
    command: Optional[str] = None  # 实际执行的命令


class ModelDispatcher:
    """
    模型调度器 - 根据配置决定使用 CLI 或 MCP 调用模型。

    v5.3+: CLI 优先模式，禁止 MCP 调用。
    """

    def __init__(self, config: SkillpackConfig):
        self.config = config
        self.use_cli = config.cli.prefer_cli_over_mcp
        self._execution_log: List[dict] = []
        self._mock_mode = self._detect_mock_mode()
        # 用量追踪
        self._usage_store = UsageStore()
        self._current_task_id: Optional[str] = None
        self._current_route: Optional[str] = None
        self._current_phase: int = 0
        self._current_phase_name: str = ""

    def set_context(
        self,
        task_id: str,
        route: str,
        phase: int = 0,
        phase_name: str = ""
    ):
        """设置当前任务上下文（在执行器中调用）"""
        self._current_task_id = task_id
        self._current_route = route
        self._current_phase = phase
        self._current_phase_name = phase_name

    def _detect_mock_mode(self) -> bool:
        """检测是否启用 mock 模式（测试环境避免真实调用外部 CLI）"""
        return bool(os.environ.get("SKILLPACK_MOCK_MODE") or os.environ.get("PYTEST_CURRENT_TEST"))

    def _mock_result(self, model: ModelType, prompt: str) -> DispatchResult:
        """生成 mock 调用结果"""
        preview = (prompt or "").strip().replace("\n", " ")[:200]
        output = f"[mock {model.value} output] {preview}"
        return DispatchResult(
            success=True,
            output=output,
            model=model,
            mode=ExecutionMode.CLI,
            duration_ms=0,
            command="mock"
        )

    def get_execution_mode(self) -> ExecutionMode:
        """获取当前执行模式"""
        return ExecutionMode.CLI if self.use_cli else ExecutionMode.MCP

    def call_codex(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        sandbox: str = "workspace-write"
    ) -> DispatchResult:
        """
        调用 Codex 模型。

        Args:
            prompt: 任务提示
            context_files: 相关文件列表
            sandbox: 沙箱模式 (read-only, workspace-write, danger-full-access)

        Returns:
            DispatchResult 包含执行结果
        """
        if self._mock_mode:
            return self._mock_result(ModelType.CODEX, prompt)
        if self.use_cli:
            return self._call_codex_cli(prompt, context_files, sandbox)
        else:
            return self._call_codex_mcp(prompt, context_files, sandbox)

    def call_gemini(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        sandbox: bool = True
    ) -> DispatchResult:
        """
        调用 Gemini 模型。

        Args:
            prompt: 任务提示
            context_files: 相关文件列表（使用 @ 语法注入）
            sandbox: 是否使用沙箱模式

        Returns:
            DispatchResult 包含执行结果
        """
        if self._mock_mode:
            return self._mock_result(ModelType.GEMINI, prompt)
        if self.use_cli:
            return self._call_gemini_cli(prompt, context_files, sandbox)
        else:
            return self._call_gemini_mcp(prompt, context_files, sandbox)

    def query_knowledge_base(
        self,
        notebook_id: str,
        query: str
    ) -> Optional[str]:
        """
        查询 NotebookLM 知识库。

        Args:
            notebook_id: NotebookLM 笔记本 ID
            query: 查询内容

        Returns:
            查询结果文本，失败返回 None
        """
        # 先检查 notebook_id（无论是否 mock 模式）
        if not notebook_id:
            return None

        if self._mock_mode:
            return f"[mock knowledge base response] Query: {query[:100]}"

        start_time = time.time()

        try:
            # 使用 MCP 工具查询 NotebookLM
            # 注意：这里返回 MCP 调用参数，由调用方实际执行
            # 因为 MCP 调用需要在 Claude 上下文中完成
            return {
                "tool": "mcp__notebooklm-mcp__notebook_query",
                "params": {
                    "notebook_id": notebook_id,
                    "query": query
                }
            }
        except Exception as e:
            return None

    def format_knowledge_query_prompt(
        self,
        task_description: str,
        phase_name: str
    ) -> str:
        """
        生成知识库查询 prompt。

        Args:
            task_description: 任务描述
            phase_name: 当前阶段名称

        Returns:
            格式化的查询 prompt
        """
        return f"""查询与以下任务相关的需求文档和验收标准：

任务描述: {task_description}
当前阶段: {phase_name}

请返回：
1. 相关的功能需求
2. 验收标准和测试用例
3. 技术约束和注意事项
4. 相关的设计决策"""

    def _call_codex_cli(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        sandbox: str = "workspace-write"
    ) -> DispatchResult:
        """
        通过 CLI 调用 Codex。

        命令格式: codex exec "<prompt>" --full-auto
        """
        start_time = time.time()

        # 构建完整 prompt（包含文件上下文）
        full_prompt = self._build_prompt_with_context(prompt, context_files)

        # 构建命令
        # --full-auto = -a on-request + -s workspace-write
        cmd = [
            self.config.cli.codex_command,
            "exec",
            full_prompt,
            "--full-auto"
        ]

        # 如果 sandbox 不是默认值，显式指定
        if sandbox != "workspace-write":
            cmd = [
                self.config.cli.codex_command,
                "exec",
                full_prompt,
                "-s", sandbox,
                "-a", "on-request"
            ]

        command_str = f"{self.config.cli.codex_command} exec \"<prompt>\" --full-auto"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.cli.cli_timeout_seconds,
                cwd=Path.cwd()
            )

            duration_ms = int((time.time() - start_time) * 1000)

            self._log_execution(
                model=ModelType.CODEX,
                mode=ExecutionMode.CLI,
                success=result.returncode == 0,
                duration_ms=duration_ms,
                command=command_str
            )

            if result.returncode == 0:
                return DispatchResult(
                    success=True,
                    output=result.stdout,
                    model=ModelType.CODEX,
                    mode=ExecutionMode.CLI,
                    duration_ms=duration_ms,
                    command=command_str
                )
            else:
                return DispatchResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr or f"Exit code: {result.returncode}",
                    model=ModelType.CODEX,
                    mode=ExecutionMode.CLI,
                    duration_ms=duration_ms,
                    command=command_str
                )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return DispatchResult(
                success=False,
                output="",
                error=f"Codex CLI 超时 ({self.config.cli.cli_timeout_seconds}s)",
                model=ModelType.CODEX,
                mode=ExecutionMode.CLI,
                duration_ms=duration_ms,
                command=command_str
            )
        except FileNotFoundError:
            return DispatchResult(
                success=False,
                output="",
                error=f"Codex CLI 未找到: {self.config.cli.codex_command}",
                model=ModelType.CODEX,
                mode=ExecutionMode.CLI,
                command=command_str
            )
        except Exception as e:
            return DispatchResult(
                success=False,
                output="",
                error=f"Codex CLI 执行失败: {str(e)}",
                model=ModelType.CODEX,
                mode=ExecutionMode.CLI,
                command=command_str
            )

    def _call_gemini_cli(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        sandbox: bool = True
    ) -> DispatchResult:
        """
        通过 CLI 调用 Gemini。

        命令格式: gemini "<prompt>" -s --yolo
        """
        start_time = time.time()

        # Gemini 使用 @ 语法注入文件上下文
        full_prompt = self._build_gemini_prompt(prompt, context_files)

        # 构建命令
        cmd = [self.config.cli.gemini_command, full_prompt]

        if sandbox:
            cmd.append("-s")

        # --yolo 自动批准所有操作
        cmd.append("--yolo")

        command_str = f"{self.config.cli.gemini_command} \"<prompt>\" -s --yolo"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.cli.cli_timeout_seconds,
                cwd=Path.cwd()
            )

            duration_ms = int((time.time() - start_time) * 1000)

            self._log_execution(
                model=ModelType.GEMINI,
                mode=ExecutionMode.CLI,
                success=result.returncode == 0,
                duration_ms=duration_ms,
                command=command_str
            )

            if result.returncode == 0:
                return DispatchResult(
                    success=True,
                    output=result.stdout,
                    model=ModelType.GEMINI,
                    mode=ExecutionMode.CLI,
                    duration_ms=duration_ms,
                    command=command_str
                )
            else:
                return DispatchResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr or f"Exit code: {result.returncode}",
                    model=ModelType.GEMINI,
                    mode=ExecutionMode.CLI,
                    duration_ms=duration_ms,
                    command=command_str
                )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return DispatchResult(
                success=False,
                output="",
                error=f"Gemini CLI 超时 ({self.config.cli.cli_timeout_seconds}s)",
                model=ModelType.GEMINI,
                mode=ExecutionMode.CLI,
                duration_ms=duration_ms,
                command=command_str
            )
        except FileNotFoundError:
            return DispatchResult(
                success=False,
                output="",
                error=f"Gemini CLI 未找到: {self.config.cli.gemini_command}",
                model=ModelType.GEMINI,
                mode=ExecutionMode.CLI,
                command=command_str
            )
        except Exception as e:
            return DispatchResult(
                success=False,
                output="",
                error=f"Gemini CLI 执行失败: {str(e)}",
                model=ModelType.GEMINI,
                mode=ExecutionMode.CLI,
                command=command_str
            )

    def _call_codex_mcp(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        sandbox: str = "workspace-write"
    ) -> DispatchResult:
        """
        通过 MCP 调用 Codex。

        注意：当 cli.prefer_cli_over_mcp=true 时，此方法不会被调用。
        此方法提供给 MCP 模式使用，返回调用参数供 Claude 使用 MCP 工具。
        """
        full_prompt = self._build_prompt_with_context(prompt, context_files)

        # MCP 模式：返回调用参数，由 Claude 执行 MCP 调用
        mcp_params = {
            "tool": "mcp__codex-cli__codex",
            "params": {
                "prompt": full_prompt,
                "sandbox": sandbox
            }
        }

        return DispatchResult(
            success=True,
            output=json.dumps(mcp_params, ensure_ascii=False, indent=2),
            model=ModelType.CODEX,
            mode=ExecutionMode.MCP,
            command="mcp__codex-cli__codex"
        )

    def _call_gemini_mcp(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        sandbox: bool = True
    ) -> DispatchResult:
        """
        通过 MCP 调用 Gemini。

        注意：当 cli.prefer_cli_over_mcp=true 时，此方法不会被调用。
        """
        full_prompt = self._build_gemini_prompt(prompt, context_files)

        mcp_params = {
            "tool": "mcp__gemini-cli__ask-gemini",
            "params": {
                "prompt": full_prompt,
                "sandbox": sandbox
            }
        }

        return DispatchResult(
            success=True,
            output=json.dumps(mcp_params, ensure_ascii=False, indent=2),
            model=ModelType.GEMINI,
            mode=ExecutionMode.MCP,
            command="mcp__gemini-cli__ask-gemini"
        )

    def _build_prompt_with_context(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None
    ) -> str:
        """构建包含文件上下文的 prompt"""
        if not context_files or not self.config.cli.auto_context:
            return prompt

        # 读取文件内容
        context_parts = []
        for file_path in context_files[:self.config.cli.max_context_files]:
            try:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    lines = path.read_text().splitlines()
                    # 限制每个文件的行数
                    if len(lines) > self.config.cli.max_lines_per_file:
                        lines = lines[:self.config.cli.max_lines_per_file]
                        lines.append(f"... (truncated at {self.config.cli.max_lines_per_file} lines)")
                    content = "\n".join(lines)
                    context_parts.append(f"### {file_path}\n```\n{content}\n```")
            except Exception:
                continue

        if context_parts:
            context_section = "\n\n".join(context_parts)
            return f"{prompt}\n\n相关文件:\n{context_section}"

        return prompt

    def _build_gemini_prompt(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None
    ) -> str:
        """构建 Gemini prompt（使用 @ 语法）"""
        if not context_files:
            return prompt

        # Gemini 使用 @ 语法引用文件
        file_refs = " ".join(f"@{f}" for f in context_files[:self.config.cli.max_context_files])
        return f"{file_refs} {prompt}"

    def _log_execution(
        self,
        model: ModelType,
        mode: ExecutionMode,
        success: bool,
        duration_ms: int,
        command: str,
        error: Optional[str] = None
    ):
        """记录执行日志（内存 + 持久化）"""
        timestamp = datetime.now().isoformat()

        # 内存日志
        self._execution_log.append({
            "timestamp": timestamp,
            "model": model.value,
            "mode": mode.value,
            "success": success,
            "duration_ms": duration_ms,
            "command": command
        })

        # 持久化记录
        record = UsageRecord(
            timestamp=timestamp,
            model=model.value,
            route=self._current_route or "UNKNOWN",
            phase=self._current_phase,
            phase_name=self._current_phase_name,
            task_id=self._current_task_id,
            success=success,
            duration_ms=duration_ms,
            error=error,
            mode=mode.value
        )
        self._usage_store.append_record(record)

    def get_execution_log(self) -> List[dict]:
        """获取执行日志"""
        return self._execution_log.copy()

    def format_phase_header(
        self,
        phase: int,
        total_phases: int,
        phase_name: str,
        route: str,
        model: ModelType,
        progress_percent: int
    ) -> str:
        """
        格式化阶段头部输出。

        根据执行模式显示不同的标识。
        """
        mode_str = "CLI" if self.use_cli else "MCP 强制调用"
        model_name = model.value.capitalize()

        if model == ModelType.CLAUDE:
            mode_str = "直接执行"

        # 构建进度条
        progress_bar = self._build_progress_bar(progress_percent)

        return f"""════════════════════════════════════════════════════════════
📍 Phase {phase}/{total_phases}: {phase_name} | {route} 路由
🤖 执行模型: {model_name} ({mode_str})
════════════════════════════════════════════════════════════
进度: {progress_bar} {progress_percent}%
────────────────────────────────────────────────────────────"""

    def _build_progress_bar(self, percent: int, width: int = 20) -> str:
        """构建进度条"""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def format_phase_complete(
        self,
        phase: int,
        model: ModelType,
        duration_ms: int,
        output_file: str,
        degraded: bool = False,
        original_model: Optional[ModelType] = None
    ) -> str:
        """格式化阶段完成输出"""
        mode_str = "CLI" if self.use_cli else "MCP"
        model_name = model.value.capitalize()
        duration_str = f"{duration_ms / 1000:.1f}s"

        if degraded and original_model:
            return f"""⚠️ Phase {phase} 完成 (降级执行)
├── 原计划模型: {original_model.value.capitalize()}
├── 实际模型: {model_name} (用户授权降级)
├── 降级原因: MCP 调用失败
└── 输出: {output_file}"""

        return f"""✅ Phase {phase} 完成
├── 执行模型: {model_name}
├── 执行模式: {mode_str}
├── 耗时: {duration_str}
└── 输出: {output_file}"""


# 便捷函数：获取调度器实例
def get_dispatcher(config: SkillpackConfig) -> ModelDispatcher:
    """获取模型调度器实例"""
    return ModelDispatcher(config)
