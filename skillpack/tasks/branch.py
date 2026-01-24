"""
分支管理器 (v6.0)

支持 Codex fork 功能和探索性分支。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pathlib import Path
import json


class BranchState(Enum):
    """分支状态"""
    ACTIVE = "active"           # 活跃
    MERGED = "merged"           # 已合并
    ABANDONED = "abandoned"     # 已放弃
    PAUSED = "paused"           # 暂停


@dataclass
class BranchCheckpoint:
    """分支检查点"""
    id: str                     # 检查点 ID
    created_at: str             # 创建时间
    description: str            # 描述
    files_snapshot: List[str]   # 文件快照列表
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Branch:
    """分支"""
    id: str                                   # 分支 ID
    name: str                                 # 分支名称
    description: str = ""                     # 描述
    parent_id: Optional[str] = None           # 父分支 ID
    state: BranchState = BranchState.ACTIVE   # 状态
    created_at: str = ""                      # 创建时间
    updated_at: str = ""                      # 更新时间

    # 执行信息
    task_id: Optional[str] = None             # 关联的任务 ID
    model: str = "codex"                      # 执行模型
    thread_id: Optional[str] = None           # Codex 线程 ID
    fork_id: Optional[str] = None             # Codex fork ID

    # 检查点
    checkpoints: List[BranchCheckpoint] = field(default_factory=list)

    # 结果
    result: Optional[str] = None              # 执行结果
    confidence: float = 0.0                   # 置信度

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_checkpoint(self, description: str, files: List[str]) -> BranchCheckpoint:
        """添加检查点"""
        checkpoint = BranchCheckpoint(
            id=f"cp-{len(self.checkpoints) + 1}",
            created_at=datetime.now().isoformat(),
            description=description,
            files_snapshot=files,
        )
        self.checkpoints.append(checkpoint)
        self.updated_at = datetime.now().isoformat()
        return checkpoint


class BranchManager:
    """
    分支管理器

    支持功能:
    - 创建/切换/合并分支
    - 与 Codex fork 功能集成
    - 分支比较和选择
    - 回滚支持
    """

    def __init__(
        self,
        max_branches: int = 5,
        storage_dir: Optional[Path] = None,
    ):
        """
        初始化分支管理器

        Args:
            max_branches: 最大并行分支数
            storage_dir: 存储目录
        """
        self._max_branches = max_branches
        self._storage_dir = storage_dir or Path(".skillpack/branches")
        self._branches: Dict[str, Branch] = {}
        self._current_branch_id: Optional[str] = None
        self._main_branch_id: Optional[str] = None

    def create_branch(
        self,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        model: str = "codex",
    ) -> Branch:
        """
        创建分支

        Args:
            name: 分支名称
            description: 描述
            parent_id: 父分支 ID
            task_id: 关联任务 ID
            model: 执行模型

        Returns:
            创建的分支

        Raises:
            ValueError: 超过最大分支数
        """
        # 检查分支数量
        active_count = sum(
            1 for b in self._branches.values()
            if b.state == BranchState.ACTIVE
        )
        if active_count >= self._max_branches:
            raise ValueError(f"活跃分支数已达上限 ({self._max_branches})")

        # 创建分支
        branch_id = f"branch-{len(self._branches) + 1}"
        now = datetime.now().isoformat()

        branch = Branch(
            id=branch_id,
            name=name,
            description=description,
            parent_id=parent_id or self._main_branch_id,
            created_at=now,
            updated_at=now,
            task_id=task_id,
            model=model,
        )

        self._branches[branch_id] = branch

        # 设置为主分支（如果是第一个）
        if not self._main_branch_id:
            self._main_branch_id = branch_id

        # 设置为当前分支
        self._current_branch_id = branch_id

        # 持久化
        self._save()

        return branch

    def get_branch(self, branch_id: str) -> Optional[Branch]:
        """获取分支"""
        return self._branches.get(branch_id)

    def get_current_branch(self) -> Optional[Branch]:
        """获取当前分支"""
        if self._current_branch_id:
            return self._branches.get(self._current_branch_id)
        return None

    def switch_branch(self, branch_id: str) -> bool:
        """
        切换分支

        Args:
            branch_id: 目标分支 ID

        Returns:
            是否切换成功
        """
        if branch_id not in self._branches:
            return False

        branch = self._branches[branch_id]
        if branch.state != BranchState.ACTIVE:
            return False

        self._current_branch_id = branch_id
        return True

    def merge_branch(
        self,
        source_id: str,
        target_id: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """
        合并分支

        Args:
            source_id: 源分支 ID
            target_id: 目标分支 ID（默认为主分支）
            force: 强制合并

        Returns:
            是否合并成功
        """
        if source_id not in self._branches:
            return False

        source = self._branches[source_id]
        target_id = target_id or self._main_branch_id

        if target_id not in self._branches:
            return False

        target = self._branches[target_id]

        # 检查置信度
        if not force and source.confidence < 0.7:
            return False

        # 标记为已合并
        source.state = BranchState.MERGED
        source.updated_at = datetime.now().isoformat()

        # 如果合并到主分支，更新主分支结果
        if target_id == self._main_branch_id:
            target.result = source.result
            target.updated_at = datetime.now().isoformat()

        # 切换到目标分支
        self._current_branch_id = target_id

        self._save()
        return True

    def abandon_branch(self, branch_id: str) -> bool:
        """放弃分支"""
        if branch_id not in self._branches:
            return False

        if branch_id == self._main_branch_id:
            return False  # 不能放弃主分支

        branch = self._branches[branch_id]
        branch.state = BranchState.ABANDONED
        branch.updated_at = datetime.now().isoformat()

        # 如果是当前分支，切换到主分支
        if self._current_branch_id == branch_id:
            self._current_branch_id = self._main_branch_id

        self._save()
        return True

    def list_branches(
        self,
        state: Optional[BranchState] = None,
    ) -> List[Branch]:
        """
        列出分支

        Args:
            state: 过滤状态

        Returns:
            分支列表
        """
        branches = list(self._branches.values())
        if state:
            branches = [b for b in branches if b.state == state]
        branches.sort(key=lambda b: b.created_at, reverse=True)
        return branches

    def compare_branches(
        self,
        branch_ids: List[str],
    ) -> Dict[str, Any]:
        """
        比较分支

        Args:
            branch_ids: 分支 ID 列表

        Returns:
            比较结果
        """
        branches = [
            self._branches[bid]
            for bid in branch_ids
            if bid in self._branches
        ]

        if len(branches) < 2:
            return {"error": "需要至少 2 个分支进行比较"}

        # 按置信度排序
        branches.sort(key=lambda b: b.confidence, reverse=True)

        return {
            "branches": [
                {
                    "id": b.id,
                    "name": b.name,
                    "confidence": b.confidence,
                    "state": b.state.value,
                    "checkpoints": len(b.checkpoints),
                }
                for b in branches
            ],
            "recommended": branches[0].id if branches else None,
            "confidence_diff": (
                branches[0].confidence - branches[1].confidence
                if len(branches) >= 2
                else 0
            ),
        }

    def rollback(self, branch_id: str, checkpoint_id: str) -> bool:
        """
        回滚到检查点

        Args:
            branch_id: 分支 ID
            checkpoint_id: 检查点 ID

        Returns:
            是否回滚成功
        """
        if branch_id not in self._branches:
            return False

        branch = self._branches[branch_id]

        # 查找检查点
        checkpoint = None
        checkpoint_idx = -1
        for i, cp in enumerate(branch.checkpoints):
            if cp.id == checkpoint_id:
                checkpoint = cp
                checkpoint_idx = i
                break

        if not checkpoint:
            return False

        # 删除后续检查点
        branch.checkpoints = branch.checkpoints[:checkpoint_idx + 1]
        branch.updated_at = datetime.now().isoformat()

        self._save()
        return True

    def set_codex_fork(self, branch_id: str, fork_id: str, thread_id: str):
        """设置 Codex fork 信息"""
        if branch_id not in self._branches:
            return

        branch = self._branches[branch_id]
        branch.fork_id = fork_id
        branch.thread_id = thread_id
        branch.updated_at = datetime.now().isoformat()
        self._save()

    def update_confidence(self, branch_id: str, confidence: float):
        """更新分支置信度"""
        if branch_id not in self._branches:
            return

        branch = self._branches[branch_id]
        branch.confidence = confidence
        branch.updated_at = datetime.now().isoformat()
        self._save()

    def _save(self):
        """保存到文件"""
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "main_branch_id": self._main_branch_id,
                "current_branch_id": self._current_branch_id,
                "branches": {
                    bid: {
                        "id": b.id,
                        "name": b.name,
                        "description": b.description,
                        "parent_id": b.parent_id,
                        "state": b.state.value,
                        "created_at": b.created_at,
                        "updated_at": b.updated_at,
                        "task_id": b.task_id,
                        "model": b.model,
                        "thread_id": b.thread_id,
                        "fork_id": b.fork_id,
                        "result": b.result,
                        "confidence": b.confidence,
                        "checkpoints": [
                            {
                                "id": cp.id,
                                "created_at": cp.created_at,
                                "description": cp.description,
                                "files_snapshot": cp.files_snapshot,
                            }
                            for cp in b.checkpoints
                        ],
                    }
                    for bid, b in self._branches.items()
                },
            }

            state_file = self._storage_dir / "branches.json"
            state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            pass

    def _load(self):
        """从文件加载"""
        state_file = self._storage_dir / "branches.json"
        if not state_file.exists():
            return

        try:
            data = json.loads(state_file.read_text())
            self._main_branch_id = data.get("main_branch_id")
            self._current_branch_id = data.get("current_branch_id")

            for bid, bdata in data.get("branches", {}).items():
                checkpoints = [
                    BranchCheckpoint(
                        id=cp["id"],
                        created_at=cp["created_at"],
                        description=cp["description"],
                        files_snapshot=cp["files_snapshot"],
                    )
                    for cp in bdata.get("checkpoints", [])
                ]

                self._branches[bid] = Branch(
                    id=bdata["id"],
                    name=bdata["name"],
                    description=bdata.get("description", ""),
                    parent_id=bdata.get("parent_id"),
                    state=BranchState(bdata.get("state", "active")),
                    created_at=bdata.get("created_at", ""),
                    updated_at=bdata.get("updated_at", ""),
                    task_id=bdata.get("task_id"),
                    model=bdata.get("model", "codex"),
                    thread_id=bdata.get("thread_id"),
                    fork_id=bdata.get("fork_id"),
                    result=bdata.get("result"),
                    confidence=bdata.get("confidence", 0.0),
                    checkpoints=checkpoints,
                )
        except Exception:
            pass
