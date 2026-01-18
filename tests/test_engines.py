"""Unit tests for skillpack.engines module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from skillpack.engines import (
    BaseEngine,
    ClaudeEngine,
    CodexEngine,
    Engine,
    GeminiEngine,
    get_engine,
)
from skillpack.models import (
    ClaudeConfig,
    CodexConfig,
    GeminiConfig,
    RunResult,
    SandboxMode,
)


class TestEngineProtocol:
    """Tests for Engine protocol compliance."""

    def test_codex_implements_protocol(self, sample_codex_config: CodexConfig):
        engine = CodexEngine(sample_codex_config)
        assert isinstance(engine, Engine)
        assert hasattr(engine, "name")
        assert hasattr(engine, "available")
        assert hasattr(engine, "execute")

    def test_gemini_implements_protocol(self, sample_gemini_config: GeminiConfig):
        engine = GeminiEngine(sample_gemini_config)
        assert isinstance(engine, Engine)

    def test_claude_implements_protocol(self, sample_claude_config: ClaudeConfig):
        engine = ClaudeEngine(sample_claude_config)
        assert isinstance(engine, Engine)


class TestBaseEngine:
    """Tests for BaseEngine base class."""

    @pytest.mark.asyncio
    async def test_run_process_success(self, temp_dir: Path):
        """Test successful subprocess execution."""

        class TestEngine(BaseEngine):
            def __init__(self):
                super().__init__()
                self._binary = "echo"

            @property
            def name(self) -> str:
                return "test"

            async def execute(self, repo, prompt, output_file, variant=1):
                return RunResult(variant=variant, success=True)

        engine = TestEngine()
        returncode, stdout, stderr = await engine._run_process(
            ["echo", "hello"],
            temp_dir,
            timeout=10,
        )
        assert returncode == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_run_process_timeout(self, temp_dir: Path):
        """Test subprocess timeout handling."""

        class TestEngine(BaseEngine):
            def __init__(self):
                super().__init__()
                self._binary = "sleep"

            @property
            def name(self) -> str:
                return "test"

            async def execute(self, repo, prompt, output_file, variant=1):
                return RunResult(variant=variant, success=True)

        engine = TestEngine()
        returncode, stdout, stderr = await engine._run_process(
            ["sleep", "10"],
            temp_dir,
            timeout=1,
        )
        assert returncode == -1
        assert "timed out" in stderr.lower()

    def test_available_with_binary(self):
        """Test binary availability check."""

        class TestEngine(BaseEngine):
            def __init__(self):
                super().__init__()
                self._binary = "python3"  # Should exist

            @property
            def name(self) -> str:
                return "test"

            async def execute(self, repo, prompt, output_file, variant=1):
                return RunResult(variant=variant, success=True)

        engine = TestEngine()
        assert engine.available is True

    def test_available_without_binary(self):
        """Test unavailable binary detection."""

        class TestEngine(BaseEngine):
            def __init__(self):
                super().__init__()
                self._binary = "nonexistent_binary_12345"

            @property
            def name(self) -> str:
                return "test"

            async def execute(self, repo, prompt, output_file, variant=1):
                return RunResult(variant=variant, success=True)

        engine = TestEngine()
        assert engine.available is False


class TestCodexEngine:
    """Tests for CodexEngine."""

    def test_engine_name(self, sample_codex_config: CodexConfig):
        engine = CodexEngine(sample_codex_config)
        assert engine.name == "codex"

    def test_engine_binary(self, sample_codex_config: CodexConfig):
        engine = CodexEngine(sample_codex_config)
        assert engine._binary == "codex"

    @pytest.mark.asyncio
    async def test_execute_unavailable(self, sample_codex_config: CodexConfig, temp_dir: Path):
        """Test execution when codex is not installed."""
        with patch("shutil.which", return_value=None):
            engine = CodexEngine(sample_codex_config)
            result = await engine.execute(
                repo=temp_dir,
                prompt="test prompt",
                output_file=temp_dir / "output.md",
                variant=1,
            )
            assert result.success is False
            assert "codex not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_success(self, sample_codex_config: CodexConfig, temp_dir: Path):
        """Test successful codex execution."""
        with patch("shutil.which", return_value="/usr/bin/codex"):
            engine = CodexEngine(sample_codex_config)

            async def mock_run(*args, **kwargs):
                return (0, "Plan generated", "")

            with patch.object(engine, "_run_process", new=AsyncMock(side_effect=mock_run)):
                result = await engine.execute(
                    repo=temp_dir,
                    prompt="Generate plan",
                    output_file=temp_dir / "plan.md",
                    variant=1,
                )
                assert result.success is True
                assert result.variant == 1
                assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_failure(self, sample_codex_config: CodexConfig, temp_dir: Path):
        """Test failed codex execution."""
        with patch("shutil.which", return_value="/usr/bin/codex"):
            engine = CodexEngine(sample_codex_config)

            async def mock_run(*args, **kwargs):
                return (1, "", "Error: API rate limit exceeded")

            with patch.object(engine, "_run_process", new=AsyncMock(side_effect=mock_run)):
                result = await engine.execute(
                    repo=temp_dir,
                    prompt="Generate plan",
                    output_file=temp_dir / "plan.md",
                    variant=1,
                )
                assert result.success is False
                assert "rate limit" in result.error.lower()

    def test_command_building_read_only(self):
        """Test command line arguments for read-only mode."""
        config = CodexConfig(
            sandbox=SandboxMode.READ_ONLY,
            model="gpt-5.2",
        )
        engine = CodexEngine(config)
        # Verify config is stored correctly
        assert engine.config.sandbox == SandboxMode.READ_ONLY
        assert engine.config.model == "gpt-5.2"

    def test_command_building_full_auto(self):
        """Test command line arguments for full-auto mode."""
        config = CodexConfig(
            sandbox=SandboxMode.WORKSPACE_WRITE,
            full_auto=True,
        )
        engine = CodexEngine(config)
        assert engine.config.full_auto is True


class TestGeminiEngine:
    """Tests for GeminiEngine."""

    def test_engine_name(self, sample_gemini_config: GeminiConfig):
        engine = GeminiEngine(sample_gemini_config)
        assert engine.name == "gemini"

    def test_engine_binary(self, sample_gemini_config: GeminiConfig):
        engine = GeminiEngine(sample_gemini_config)
        assert engine._binary == "gemini"

    @pytest.mark.asyncio
    async def test_execute_unavailable(self, sample_gemini_config: GeminiConfig, temp_dir: Path):
        """Test execution when gemini is not installed."""
        with patch("shutil.which", return_value=None):
            engine = GeminiEngine(sample_gemini_config)
            result = await engine.execute(
                repo=temp_dir,
                prompt="test prompt",
                output_file=temp_dir / "output.md",
                variant=1,
            )
            assert result.success is False
            assert "gemini not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_writes_output(self, sample_gemini_config: GeminiConfig, temp_dir: Path):
        """Test that successful execution writes output file."""
        output_file = temp_dir / "ui_spec.md"

        with patch("shutil.which", return_value="/usr/bin/gemini"):
            engine = GeminiEngine(sample_gemini_config)

            async def mock_run(*args, **kwargs):
                return (0, "# UI Specification\n\nGenerated content", "")

            with patch.object(engine, "_run_process", new=AsyncMock(side_effect=mock_run)):
                result = await engine.execute(
                    repo=temp_dir,
                    prompt="Generate UI spec",
                    output_file=output_file,
                    variant=1,
                )
                assert result.success is True
                assert output_file.exists()
                assert "UI Specification" in output_file.read_text()


class TestClaudeEngine:
    """Tests for ClaudeEngine."""

    def test_engine_name(self, sample_claude_config: ClaudeConfig):
        engine = ClaudeEngine(sample_claude_config)
        assert engine.name == "claude"

    def test_engine_binary(self, sample_claude_config: ClaudeConfig):
        engine = ClaudeEngine(sample_claude_config)
        assert engine._binary == "claude"

    @pytest.mark.asyncio
    async def test_execute_unavailable(self, sample_claude_config: ClaudeConfig, temp_dir: Path):
        """Test execution when claude is not installed."""
        with patch("shutil.which", return_value=None):
            engine = ClaudeEngine(sample_claude_config)
            result = await engine.execute(
                repo=temp_dir,
                prompt="test prompt",
                output_file=temp_dir / "output.md",
                variant=1,
            )
            assert result.success is False
            assert "claude not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_skip_permissions(self, temp_dir: Path):
        """Test execution with dangerously_skip_permissions flag."""
        config = ClaudeConfig(dangerously_skip_permissions=True)

        with patch("shutil.which", return_value="/usr/bin/claude"):
            engine = ClaudeEngine(config)
            assert engine.config.dangerously_skip_permissions is True


class TestGetEngine:
    """Tests for engine factory function."""

    def test_get_codex_engine(self):
        engine = get_engine("codex")
        assert isinstance(engine, CodexEngine)
        assert engine.name == "codex"

    def test_get_gemini_engine(self):
        engine = get_engine("gemini")
        assert isinstance(engine, GeminiEngine)
        assert engine.name == "gemini"

    def test_get_claude_engine(self):
        engine = get_engine("claude")
        assert isinstance(engine, ClaudeEngine)
        assert engine.name == "claude"

    def test_get_engine_with_config(self):
        config = {
            "sandbox": "workspace-write",
            "full_auto": True,
            "model": "gpt-5.2",
        }
        engine = get_engine("codex", config)
        assert isinstance(engine, CodexEngine)
        assert engine.config.sandbox == SandboxMode.WORKSPACE_WRITE
        assert engine.config.model == "gpt-5.2"

    def test_get_unknown_engine(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("unknown_engine")

    def test_get_engine_empty_config(self):
        engine = get_engine("codex", {})
        assert isinstance(engine, CodexEngine)
        # Should use defaults
        assert engine.config.sandbox == SandboxMode.WORKSPACE_WRITE


class TestEngineIntegration:
    """Integration tests for engine execution patterns."""

    @pytest.mark.asyncio
    async def test_variant_tag_injection(self, sample_codex_config: CodexConfig, temp_dir: Path):
        """Test that variant tags are injected into prompts."""
        captured_prompt = None

        with patch("shutil.which", return_value="/usr/bin/codex"):
            engine = CodexEngine(sample_codex_config)

            async def capture_run(cmd, cwd, input_text=None, timeout=600):
                nonlocal captured_prompt
                captured_prompt = input_text
                return (0, "Success", "")

            with patch.object(engine, "_run_process", new=AsyncMock(side_effect=capture_run)):
                await engine.execute(
                    repo=temp_dir,
                    prompt="Test prompt",
                    output_file=temp_dir / "out.md",
                    variant=3,
                )

        assert captured_prompt is not None
        assert "V3" in captured_prompt
        assert "Test prompt" in captured_prompt

    @pytest.mark.asyncio
    async def test_output_truncation(self, sample_codex_config: CodexConfig, temp_dir: Path):
        """Test that long output is truncated."""
        with patch("shutil.which", return_value="/usr/bin/codex"):
            engine = CodexEngine(sample_codex_config)

            long_error = "E" * 5000  # Longer than 2000 char limit

            async def mock_run(*args, **kwargs):
                return (1, "", long_error)

            with patch.object(engine, "_run_process", new=AsyncMock(side_effect=mock_run)):
                result = await engine.execute(
                    repo=temp_dir,
                    prompt="Test",
                    output_file=temp_dir / "out.md",
                    variant=1,
                )

        assert len(result.error) <= 2000
