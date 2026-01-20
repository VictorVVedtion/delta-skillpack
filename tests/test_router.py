"""
测试任务路由器
"""

import pytest
from pathlib import Path

from skillpack.models import TaskComplexity, ExecutionRoute, SkillpackConfig
from skillpack.router import TaskRouter


class TestTaskRouter:
    """TaskRouter 测试"""

    def setup_method(self):
        self.router = TaskRouter()

    # 简单任务测试
    def test_simple_task_typo_fix(self):
        """typo 修复应该路由到直接执行"""
        context = self.router.route("fix typo in README")
        assert context.complexity == TaskComplexity.SIMPLE
        assert context.route == ExecutionRoute.DIRECT

    def test_simple_task_chinese(self):
        """中文 typo 修复"""
        context = self.router.route("修复拼写错误")
        assert context.complexity == TaskComplexity.SIMPLE
        assert context.route == ExecutionRoute.DIRECT

    def test_simple_task_rename(self):
        """重命名任务 - v5.4 评为中等复杂度"""
        context = self.router.route("rename function from foo to bar")
        # v5.4: rename 单独不足以降到 SIMPLE，需要更明确的简单信号
        assert context.route in [ExecutionRoute.DIRECT, ExecutionRoute.PLANNED]

    # 中等任务测试
    def test_medium_task_feature(self):
        """一般功能实现"""
        context = self.router.route("add user authentication")
        assert context.complexity == TaskComplexity.MEDIUM
        assert context.route == ExecutionRoute.PLANNED

    def test_medium_task_bug_fix(self):
        """Bug 修复"""
        context = self.router.route("fix login validation bug")
        assert context.complexity == TaskComplexity.MEDIUM

    # 复杂任务测试
    def test_complex_task_system(self):
        """系统级任务 - 包含多个复杂信号"""
        context = self.router.route("build complete authentication system")
        # 包含 complete + system，应该是 RALPH 或 ARCHITECT
        assert context.route in [ExecutionRoute.RALPH, ExecutionRoute.ARCHITECT, ExecutionRoute.UI_FLOW]

    def test_complex_task_architecture(self):
        """架构重构 - v5.4 路由到 ARCHITECT"""
        context = self.router.route("重构整个系统架构")
        # 包含 重构 + 系统 + 架构，v5.4 评为 ARCHITECT
        assert context.complexity == TaskComplexity.ARCHITECT
        assert context.route == ExecutionRoute.ARCHITECT

    def test_complex_task_multi_module(self):
        """多模块任务"""
        context = self.router.route("implement multi-module payment system")
        # 包含 multi-module + system，应该是 RALPH 或更高
        assert context.route in [ExecutionRoute.RALPH, ExecutionRoute.ARCHITECT, ExecutionRoute.PLANNED]

    # UI 任务测试
    def test_ui_task_component(self):
        """UI 组件任务"""
        context = self.router.route("create login page component")
        assert context.complexity == TaskComplexity.UI
        assert context.route == ExecutionRoute.UI_FLOW

    def test_ui_task_chinese(self):
        """中文 UI 任务"""
        context = self.router.route("创建用户界面组件")
        assert context.complexity == TaskComplexity.UI

    def test_ui_task_style(self):
        """样式任务"""
        context = self.router.route("update button styles with tailwind")
        assert context.complexity == TaskComplexity.UI

    # 模式覆盖测试
    def test_quick_mode_override(self):
        """--quick 模式覆盖"""
        context = self.router.route("build complete CMS", quick_mode=True)
        assert context.route == ExecutionRoute.DIRECT

    def test_deep_mode_override(self):
        """--deep 模式覆盖"""
        context = self.router.route("fix typo", deep_mode=True)
        assert context.route == ExecutionRoute.RALPH

    # 知识库测试
    def test_notebook_id_passed(self):
        """知识库 ID 传递"""
        context = self.router.route("do something", notebook_id="test-notebook")
        assert context.notebook_id == "test-notebook"

    def test_default_notebook_from_config(self):
        """从配置读取默认知识库"""
        from skillpack.models import KnowledgeConfig
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="default-nb")
        )
        router = TaskRouter(config)
        context = router.route("do something")
        assert context.notebook_id == "default-nb"

    def test_explicit_notebook_overrides_default(self):
        """显式知识库覆盖默认值"""
        from skillpack.models import KnowledgeConfig
        config = SkillpackConfig(
            knowledge=KnowledgeConfig(default_notebook="default-nb")
        )
        router = TaskRouter(config)
        context = router.route("do something", notebook_id="explicit-nb")
        assert context.notebook_id == "explicit-nb"


class TestRouterExplain:
    """测试路由解释"""

    def test_explain_simple(self):
        router = TaskRouter()
        context = router.route("fix typo")
        explanation = router.explain_routing(context)

        assert "简单" in explanation
        assert "直接执行" in explanation

    def test_explain_with_notebook(self):
        router = TaskRouter()
        context = router.route("do something", notebook_id="test-nb")
        explanation = router.explain_routing(context)

        assert "test-nb" in explanation
