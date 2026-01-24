"""
分支管理测试 (v6.0)
"""

import pytest
from pathlib import Path
import tempfile

from skillpack.tasks import BranchManager, Branch
from skillpack.tasks.branch import BranchState


class TestBranchManager:
    """BranchManager 测试"""

    def test_create_branch(self):
        """创建分支"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            branch = manager.create_branch("main", "主分支")

            assert branch.name == "main"
            assert branch.state == BranchState.ACTIVE
            assert branch.created_at is not None

    def test_create_multiple_branches(self):
        """创建多个分支"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            manager.create_branch("main", "主分支")
            branch_a = manager.create_branch("方案A", "使用 Redis")
            branch_b = manager.create_branch("方案B", "使用本地缓存")

            branches = manager.list_branches()
            assert len(branches) == 3

    def test_max_branches_limit(self):
        """分支数量限制"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(max_branches=2, storage_dir=Path(tmpdir) / "branches")
            manager.create_branch("main", "主分支")
            manager.create_branch("branch-1", "分支1")

            with pytest.raises(ValueError):
                manager.create_branch("branch-2", "分支2")

    def test_switch_branch(self):
        """切换分支"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            main = manager.create_branch("main", "主分支")
            feature = manager.create_branch("feature", "功能分支")

            assert manager.get_current_branch().id == feature.id

            manager.switch_branch(main.id)
            assert manager.get_current_branch().id == main.id

    def test_abandon_branch(self):
        """放弃分支"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            main = manager.create_branch("main", "主分支")
            feature = manager.create_branch("feature", "功能分支")

            result = manager.abandon_branch(feature.id)
            assert result is True

            branch = manager.get_branch(feature.id)
            assert branch.state == BranchState.ABANDONED

    def test_cannot_abandon_main_branch(self):
        """不能放弃主分支"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            main = manager.create_branch("main", "主分支")

            result = manager.abandon_branch(main.id)
            assert result is False

    def test_merge_branch(self):
        """合并分支"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            main = manager.create_branch("main", "主分支")
            feature = manager.create_branch("feature", "功能分支")

            # 设置高置信度
            feature.confidence = 0.9
            feature.result = "实现完成"

            result = manager.merge_branch(feature.id, main.id)
            assert result is True

            merged = manager.get_branch(feature.id)
            assert merged.state == BranchState.MERGED

    def test_merge_low_confidence_fails(self):
        """低置信度合并失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            main = manager.create_branch("main", "主分支")
            feature = manager.create_branch("feature", "功能分支")

            # 设置低置信度
            feature.confidence = 0.5

            result = manager.merge_branch(feature.id, main.id)
            assert result is False

    def test_merge_force(self):
        """强制合并"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            main = manager.create_branch("main", "主分支")
            feature = manager.create_branch("feature", "功能分支")

            # 设置低置信度
            feature.confidence = 0.5

            result = manager.merge_branch(feature.id, main.id, force=True)
            assert result is True

    def test_compare_branches(self):
        """比较分支"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BranchManager(storage_dir=Path(tmpdir) / "branches")
            main = manager.create_branch("main", "主分支")
            branch_a = manager.create_branch("方案A", "使用 Redis")
            branch_b = manager.create_branch("方案B", "使用本地缓存")

            branch_a.confidence = 0.85
            branch_b.confidence = 0.72

            comparison = manager.compare_branches([branch_a.id, branch_b.id])
            assert comparison["recommended"] == branch_a.id
            assert comparison["confidence_diff"] == pytest.approx(0.13, 0.01)


class TestBranch:
    """Branch 测试"""

    def test_add_checkpoint(self):
        """添加检查点"""
        branch = Branch(
            id="branch-1",
            name="测试分支",
            created_at="2024-01-01T00:00:00",
        )

        cp = branch.add_checkpoint("初始实现", ["src/main.ts"])

        assert len(branch.checkpoints) == 1
        assert cp.description == "初始实现"
        assert "src/main.ts" in cp.files_snapshot

    def test_multiple_checkpoints(self):
        """多个检查点"""
        branch = Branch(
            id="branch-1",
            name="测试分支",
            created_at="2024-01-01T00:00:00",
        )

        branch.add_checkpoint("v1", ["file1.ts"])
        branch.add_checkpoint("v2", ["file1.ts", "file2.ts"])
        branch.add_checkpoint("v3", ["file1.ts", "file2.ts", "file3.ts"])

        assert len(branch.checkpoints) == 3
        assert branch.checkpoints[0].id == "cp-1"
        assert branch.checkpoints[2].id == "cp-3"
