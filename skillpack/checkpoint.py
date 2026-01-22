"""
检查点管理模块

提供任务检查点的保存、加载和恢复功能。
支持原子写入和备份机制。
"""

import hashlib
import json
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class PhaseStatus(Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseCheckpoint:
    """阶段检查点"""
    number: int
    name: str
    status: str = "pending"
    model: str = ""
    output_file: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    subtasks: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryInfo:
    """恢复信息"""
    can_resume: bool = True
    resume_phase: Optional[int] = None
    resume_subtask: Optional[str] = None
    notes: str = ""
    error_log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Checkpoint:
    """完整检查点"""
    version: str = "3.0"
    task_id: str = ""
    task_description: str = ""
    route: str = ""
    complexity_score: int = 0
    scoring_breakdown: Dict[str, int] = field(default_factory=dict)

    # 执行状态
    current_phase: int = 0
    total_phases: int = 0
    phases: List[PhaseCheckpoint] = field(default_factory=list)
    progress: float = 0.0
    status: str = "running"  # running, completed, failed, paused

    # 文件追踪
    created_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)

    # 恢复信息
    recovery: RecoveryInfo = field(default_factory=RecoveryInfo)

    # 配置快照
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    # 时间戳
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "version": self.version,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "route": self.route,
            "complexity_score": self.complexity_score,
            "scoring_breakdown": self.scoring_breakdown,
            "execution": {
                "current_phase": self.current_phase,
                "total_phases": self.total_phases,
                "phases": [asdict(p) if isinstance(p, PhaseCheckpoint) else p for p in self.phases],
                "progress": self.progress,
                "status": self.status,
            },
            "files": {
                "created": self.created_files,
                "modified": self.modified_files,
            },
            "recovery": asdict(self.recovery) if isinstance(self.recovery, RecoveryInfo) else self.recovery,
            "config_snapshot": self.config_snapshot,
            "timestamps": {
                "created": self.created_at,
                "updated": self.updated_at,
            }
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """从字典创建"""
        execution = data.get("execution", {})
        files = data.get("files", {})
        recovery_data = data.get("recovery", {})
        timestamps = data.get("timestamps", {})

        # 解析 phases
        phases = []
        for p in execution.get("phases", []):
            if isinstance(p, dict):
                phases.append(PhaseCheckpoint(
                    number=p.get("number", 0),
                    name=p.get("name", ""),
                    status=p.get("status", "pending"),
                    model=p.get("model", ""),
                    output_file=p.get("output_file"),
                    started_at=p.get("started_at"),
                    completed_at=p.get("completed_at"),
                    error=p.get("error"),
                    subtasks=p.get("subtasks"),
                ))
            else:
                phases.append(p)

        # 解析 recovery
        recovery = RecoveryInfo(
            can_resume=recovery_data.get("can_resume", True),
            resume_phase=recovery_data.get("resume_phase") or recovery_data.get("resume_point"),
            resume_subtask=recovery_data.get("resume_subtask"),
            notes=recovery_data.get("notes", ""),
            error_log=recovery_data.get("error_log", []),
        )

        return cls(
            version=data.get("version", "3.0"),
            task_id=data.get("task_id", ""),
            task_description=data.get("task_description", ""),
            route=data.get("route", ""),
            complexity_score=data.get("complexity_score", 0),
            scoring_breakdown=data.get("scoring_breakdown", {}),
            current_phase=execution.get("current_phase", 0),
            total_phases=execution.get("total_phases", 0),
            phases=phases,
            progress=execution.get("progress", 0.0),
            status=execution.get("status", data.get("status", "running")),
            created_files=files.get("created", []),
            modified_files=files.get("modified", files.get("pending_modification", [])),
            recovery=recovery,
            config_snapshot=data.get("config_snapshot", {}),
            created_at=timestamps.get("created", ""),
            updated_at=timestamps.get("updated", ""),
        )

    def get_resume_info(self) -> Dict[str, Any]:
        """获取恢复信息摘要"""
        # 找到第一个未完成的阶段
        resume_phase = None
        for phase in self.phases:
            if isinstance(phase, PhaseCheckpoint):
                if phase.status in ("pending", "running", "failed"):
                    resume_phase = phase.number
                    break
            elif isinstance(phase, dict):
                if phase.get("status") in ("pending", "running", "failed"):
                    resume_phase = phase.get("number")
                    break

        return {
            "task_id": self.task_id,
            "description": self.task_description,
            "route": self.route,
            "progress": self.progress,
            "status": self.status,
            "current_phase": self.current_phase,
            "total_phases": self.total_phases,
            "resume_phase": resume_phase,
            "can_resume": self.recovery.can_resume if isinstance(self.recovery, RecoveryInfo) else self.recovery.get("can_resume", True),
            "updated_at": self.updated_at,
        }


class CheckpointManager:
    """检查点管理器"""

    def __init__(
        self,
        current_dir: str = ".skillpack/current",
        history_dir: str = ".skillpack/history",
        atomic_writes: bool = True,
        backup_count: int = 3,
    ):
        self.current_dir = Path(current_dir)
        self.history_dir = Path(history_dir)
        self.atomic_writes = atomic_writes
        self.backup_count = backup_count

    def _checkpoint_path(self, directory: Optional[Path] = None) -> Path:
        """获取检查点文件路径"""
        return (directory or self.current_dir) / "checkpoint.json"

    def _checksum_path(self, directory: Optional[Path] = None) -> Path:
        """获取校验和文件路径"""
        return (directory or self.current_dir) / "checkpoint.json.sha256"

    def _compute_checksum(self, content: str) -> str:
        """计算 SHA-256 校验和"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def save(self, checkpoint: Checkpoint) -> bool:
        """
        保存检查点（支持原子写入）

        Args:
            checkpoint: 检查点对象

        Returns:
            是否保存成功
        """
        self.current_dir.mkdir(parents=True, exist_ok=True)

        checkpoint.updated_at = datetime.now().isoformat()
        content = json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=False)
        checksum = self._compute_checksum(content)

        checkpoint_path = self._checkpoint_path()
        checksum_path = self._checksum_path()

        if self.atomic_writes:
            # 原子写入：先写临时文件，再重命名
            temp_path = checkpoint_path.with_suffix(".json.tmp")
            temp_checksum_path = checksum_path.with_suffix(".sha256.tmp")

            try:
                # 备份现有文件
                if checkpoint_path.exists():
                    self._rotate_backups(checkpoint_path)

                # 写入临时文件
                temp_path.write_text(content, encoding="utf-8")
                temp_checksum_path.write_text(checksum, encoding="utf-8")

                # 原子重命名
                temp_path.rename(checkpoint_path)
                temp_checksum_path.rename(checksum_path)

                return True
            except Exception:
                # 清理临时文件
                temp_path.unlink(missing_ok=True)
                temp_checksum_path.unlink(missing_ok=True)
                return False
        else:
            # 直接写入
            checkpoint_path.write_text(content, encoding="utf-8")
            checksum_path.write_text(checksum, encoding="utf-8")
            return True

    def _rotate_backups(self, path: Path) -> None:
        """轮转备份文件"""
        if self.backup_count <= 0:
            return

        # 删除最老的备份
        oldest = path.with_suffix(f".json.backup.{self.backup_count}")
        oldest.unlink(missing_ok=True)

        # 轮转现有备份
        for i in range(self.backup_count - 1, 0, -1):
            src = path.with_suffix(f".json.backup.{i}")
            dst = path.with_suffix(f".json.backup.{i + 1}")
            if src.exists():
                src.rename(dst)

        # 创建新备份
        if path.exists():
            backup = path.with_suffix(".json.backup.1")
            shutil.copy2(path, backup)

    def load(self, directory: Optional[Path] = None) -> Optional[Checkpoint]:
        """
        加载检查点

        Args:
            directory: 检查点目录（默认为 current_dir）

        Returns:
            检查点对象，如果不存在或损坏则返回 None
        """
        checkpoint_path = self._checkpoint_path(directory)
        checksum_path = self._checksum_path(directory)

        if not checkpoint_path.exists():
            return None

        try:
            content = checkpoint_path.read_text(encoding="utf-8")

            # 验证校验和
            if checksum_path.exists():
                expected_checksum = checksum_path.read_text(encoding="utf-8").strip()
                actual_checksum = self._compute_checksum(content)
                if expected_checksum != actual_checksum:
                    # 尝试从备份恢复
                    return self._recover_from_backup(directory)

            data = json.loads(content)
            return Checkpoint.from_dict(data)

        except (json.JSONDecodeError, KeyError):
            return self._recover_from_backup(directory)

    def _recover_from_backup(self, directory: Optional[Path] = None) -> Optional[Checkpoint]:
        """从备份恢复"""
        checkpoint_path = self._checkpoint_path(directory)

        for i in range(1, self.backup_count + 1):
            backup_path = checkpoint_path.with_suffix(f".json.backup.{i}")
            if backup_path.exists():
                try:
                    content = backup_path.read_text(encoding="utf-8")
                    data = json.loads(content)
                    return Checkpoint.from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    continue

        return None

    def load_current(self) -> Optional[Checkpoint]:
        """加载当前检查点"""
        return self.load(self.current_dir)

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        列出所有可恢复的检查点

        Returns:
            检查点摘要列表
        """
        checkpoints = []

        # 当前检查点
        current = self.load_current()
        if current:
            info = current.get_resume_info()
            info["location"] = "current"
            info["path"] = str(self.current_dir)
            checkpoints.append(info)

        # 历史检查点
        if self.history_dir.exists():
            for entry in sorted(self.history_dir.iterdir(), reverse=True):
                if entry.is_dir():
                    cp = self.load(entry)
                    if cp:
                        info = cp.get_resume_info()
                        info["location"] = "history"
                        info["path"] = str(entry)
                        checkpoints.append(info)

        return checkpoints

    def archive_current(self) -> Optional[Path]:
        """
        将当前检查点归档到历史

        Returns:
            归档目录路径
        """
        current = self.load_current()
        if not current:
            return None

        self.history_dir.mkdir(parents=True, exist_ok=True)

        # 创建归档目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = self.history_dir / f"{timestamp}_{current.task_id[:8]}"
        archive_dir.mkdir(parents=True, exist_ok=True)

        # 复制所有文件
        for item in self.current_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, archive_dir / item.name)

        return archive_dir

    def restore_from_history(self, task_id: str) -> Optional[Checkpoint]:
        """
        从历史恢复检查点

        Args:
            task_id: 任务 ID 或历史目录名

        Returns:
            恢复的检查点对象
        """
        if not self.history_dir.exists():
            return None

        # 查找匹配的历史目录
        for entry in self.history_dir.iterdir():
            if entry.is_dir():
                if task_id in entry.name:
                    cp = self.load(entry)
                    if cp:
                        # 复制到 current
                        self.current_dir.mkdir(parents=True, exist_ok=True)
                        for item in entry.iterdir():
                            if item.is_file():
                                shutil.copy2(item, self.current_dir / item.name)
                        return self.load_current()

        return None

    def get_resumable_checkpoint(self, task_id: Optional[str] = None) -> Optional[Checkpoint]:
        """
        获取可恢复的检查点

        Args:
            task_id: 指定任务 ID（可选）

        Returns:
            可恢复的检查点对象
        """
        if task_id:
            # 先在 current 中查找
            current = self.load_current()
            if current and task_id in current.task_id:
                return current

            # 在历史中查找
            return self.restore_from_history(task_id)
        else:
            # 返回当前检查点
            return self.load_current()

    def update_phase(
        self,
        phase_number: int,
        status: str,
        output_file: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        更新阶段状态

        Args:
            phase_number: 阶段编号
            status: 新状态
            output_file: 输出文件路径
            error: 错误信息

        Returns:
            是否更新成功
        """
        checkpoint = self.load_current()
        if not checkpoint:
            return False

        # 更新阶段
        for phase in checkpoint.phases:
            phase_num = phase.number if isinstance(phase, PhaseCheckpoint) else phase.get("number")
            if phase_num == phase_number:
                if isinstance(phase, PhaseCheckpoint):
                    phase.status = status
                    if output_file:
                        phase.output_file = output_file
                    if error:
                        phase.error = error
                    if status == "running":
                        phase.started_at = datetime.now().isoformat()
                    elif status == "completed":
                        phase.completed_at = datetime.now().isoformat()
                else:
                    phase["status"] = status
                    if output_file:
                        phase["output_file"] = output_file
                    if error:
                        phase["error"] = error
                break

        # 更新当前阶段和进度
        checkpoint.current_phase = phase_number
        checkpoint.progress = phase_number / checkpoint.total_phases if checkpoint.total_phases > 0 else 0

        # 更新恢复信息
        if isinstance(checkpoint.recovery, RecoveryInfo):
            checkpoint.recovery.can_resume = status in ("running", "failed", "pending")
            checkpoint.recovery.resume_phase = phase_number if checkpoint.recovery.can_resume else None

        return self.save(checkpoint)

    def mark_completed(self) -> bool:
        """标记任务完成"""
        checkpoint = self.load_current()
        if not checkpoint:
            return False

        checkpoint.status = "completed"
        checkpoint.progress = 1.0
        if isinstance(checkpoint.recovery, RecoveryInfo):
            checkpoint.recovery.can_resume = False
            checkpoint.recovery.notes = "任务已完成"

        return self.save(checkpoint)

    def mark_failed(self, error: str) -> bool:
        """标记任务失败"""
        checkpoint = self.load_current()
        if not checkpoint:
            return False

        checkpoint.status = "failed"
        if isinstance(checkpoint.recovery, RecoveryInfo):
            checkpoint.recovery.can_resume = True
            checkpoint.recovery.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "error": error,
            })

        return self.save(checkpoint)
