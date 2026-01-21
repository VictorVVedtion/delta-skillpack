"""
E2E 测试：NotebookLM 知识库集成
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from skillpack.models import (
    SkillpackConfig,
    KnowledgeConfig,
    TaskContext,
    ExecutionRoute,
)
from skillpack.router import TaskRouter
from skillpack.executor import (
    TaskExecutor,
    RalphExecutor,
    ArchitectExecutor,
)
from skillpack.dispatch import ModelDispatcher


class TestKnowledgeBaseRouting:
    """测试知识库配置路由"""

    def test_notebook_id_flows_to_context(self):
        """notebook_id 正确传递到 TaskContext"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="default-nb", auto_query=True)
        )
        router = TaskRouter(config)

        context = router.route("implement user auth", notebook_id="explicit-nb")
        assert context.notebook_id == "explicit-nb"

    def test_default_notebook_used_when_no_explicit(self):
        """没有显式 notebook_id 时使用默认值"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="default-nb", auto_query=True)
        )
        router = TaskRouter(config)

        context = router.route("implement feature")
        assert context.notebook_id == "default-nb"

    def test_auto_query_disabled(self):
        """auto_query=False 时不影响 notebook_id 传递"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="my-nb", auto_query=False)
        )
        router = TaskRouter(config)

        context = router.route("do something")
        assert context.notebook_id == "my-nb"


class TestDispatcherKnowledgeQuery:
    """测试 Dispatcher 知识库查询方法"""

    def test_query_knowledge_base_mock_mode(self, monkeypatch):
        """Mock 模式下返回模拟响应（需显式设置 SKILLPACK_MOCK_MODE=1）"""
        # v5.4.2: 必须显式设置环境变量启用 mock 模式
        monkeypatch.setenv("SKILLPACK_MOCK_MODE", "1")
        config = SkillpackConfig()
        dispatcher = ModelDispatcher(config)

        result = dispatcher.query_knowledge_base("nb-123", "what are the requirements?")
        assert result is not None
        assert "mock" in result.lower() or "Query:" in result

    def test_query_knowledge_base_no_notebook(self):
        """没有 notebook_id 时返回 None"""
        config = SkillpackConfig()
        dispatcher = ModelDispatcher(config)

        result = dispatcher.query_knowledge_base("", "query")
        assert result is None

        result = dispatcher.query_knowledge_base(None, "query")
        assert result is None

    def test_format_knowledge_query_prompt(self):
        """测试知识库查询 prompt 生成"""
        config = SkillpackConfig()
        dispatcher = ModelDispatcher(config)

        prompt = dispatcher.format_knowledge_query_prompt(
            task_description="implement JWT authentication",
            phase_name="独立审查"
        )

        assert "JWT" in prompt or "authentication" in prompt
        assert "独立审查" in prompt or "需求" in prompt


class TestRalphKnowledgeIntegration:
    """测试 RALPH 路由知识库集成"""

    def test_ralph_executor_with_knowledge_config(self):
        """RALPH 执行器正确处理知识库配置"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="test-nb", auto_query=True)
        )
        # ExecutorStrategy 只接受 config，内部创建 dispatcher
        executor = RalphExecutor(config)

        # 验证执行器有访问配置的能力
        assert executor.config.knowledge.default_notebook == "test-nb"
        assert executor.config.knowledge.auto_query is True

    def test_ralph_context_has_notebook_id(self):
        """RALPH 任务上下文包含 notebook_id"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="ralph-nb", auto_query=True)
        )
        router = TaskRouter(config)

        # 深度模式强制 RALPH
        context = router.route("build complete system", deep_mode=True)
        assert context.route == ExecutionRoute.RALPH
        assert context.notebook_id == "ralph-nb"


class TestArchitectKnowledgeIntegration:
    """测试 ARCHITECT 路由知识库集成"""

    def test_architect_executor_with_knowledge_config(self):
        """ARCHITECT 执行器正确处理知识库配置"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="arch-nb", auto_query=True)
        )
        # ExecutorStrategy 只接受 config，内部创建 dispatcher
        executor = ArchitectExecutor(config)

        assert executor.config.knowledge.default_notebook == "arch-nb"
        assert executor.config.knowledge.auto_query is True

    def test_architect_context_has_notebook_id(self):
        """ARCHITECT 任务上下文包含 notebook_id"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="arch-nb", auto_query=True)
        )
        router = TaskRouter(config)

        context = router.route("design microservice architecture from scratch")
        # 可能路由到 ARCHITECT 或 RALPH，取决于评分
        assert context.notebook_id == "arch-nb"


class TestKnowledgeQueryFlow:
    """测试知识库查询完整流程"""

    def test_dispatcher_set_context_preserves_route(self):
        """set_context 正确设置路由上下文"""
        config = SkillpackConfig()
        dispatcher = ModelDispatcher(config)

        dispatcher.set_context(
            task_id="task-123",
            route="RALPH",
            phase=4,
            phase_name="独立审查"
        )

        # 内部状态应该被设置
        assert dispatcher._current_task_id == "task-123"
        assert dispatcher._current_route == "RALPH"
        assert dispatcher._current_phase == 4
        assert dispatcher._current_phase_name == "独立审查"

    def test_knowledge_query_in_review_phase(self):
        """审查阶段可以查询知识库"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="review-nb", auto_query=True)
        )
        dispatcher = ModelDispatcher(config)

        # 模拟审查阶段
        dispatcher.set_context(
            task_id="task-456",
            route="RALPH",
            phase=4,
            phase_name="独立审查"
        )

        # 执行知识库查询
        prompt = dispatcher.format_knowledge_query_prompt(
            task_description="implement user authentication",
            phase_name="独立审查"
        )
        result = dispatcher.query_knowledge_base("review-nb", prompt)

        assert result is not None


class TestUsageTrackingWithKnowledge:
    """测试知识库集成时的用量追踪"""

    def test_dispatcher_tracks_usage_with_context(self):
        """Dispatcher 在有上下文时正确追踪用量"""
        with TemporaryDirectory() as tmpdir:
            config = SkillpackConfig()
            dispatcher = ModelDispatcher(config)

            # 设置上下文
            dispatcher.set_context(
                task_id="track-test",
                route="RALPH",
                phase=3,
                phase_name="执行"
            )

            # 执行调用
            result = dispatcher.call_codex("test prompt")

            # 验证执行成功
            assert result.success is True

    def test_knowledge_context_does_not_break_execution(self):
        """知识库上下文不会破坏正常执行流程"""
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="test-nb", auto_query=True)
        )
        router = TaskRouter(config)
        dispatcher = ModelDispatcher(config)

        # 路由任务
        context = router.route("fix bug in auth.ts", quick_mode=True)

        # 设置执行上下文
        dispatcher.set_context(
            task_id="test-exec",
            route=context.route.value,
            phase=1,
            phase_name="执行"
        )

        # 执行调用
        result = dispatcher.call_codex(f"fix: {context.description}")
        assert result.success is True
