"""
模型用量追踪与统计

提供用量数据收集、持久化存储和统计分析功能。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Optional, List, Dict
import json


@dataclass
class UsageRecord:
    """单次模型调用记录"""
    timestamp: str                    # ISO 8601 格式
    model: str                        # claude, codex, gemini
    route: str                        # DIRECT, PLANNED, RALPH, etc.
    phase: int                        # 执行阶段
    phase_name: str                   # 阶段名称
    task_id: Optional[str] = None     # 任务 ID
    success: bool = True
    duration_ms: int = 0
    error: Optional[str] = None
    mode: str = "cli"                 # cli, mcp, direct


@dataclass
class ModelStats:
    """单模型统计"""
    model: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    total_duration_ms: int
    avg_duration_ms: float
    by_route: Dict[str, int] = field(default_factory=dict)
    by_phase: Dict[str, int] = field(default_factory=dict)


@dataclass
class UsageSummary:
    """用量总结"""
    period_start: Optional[datetime]
    period_end: datetime
    total_tasks: int
    total_calls: int
    models: Dict[str, ModelStats] = field(default_factory=dict)
    route_distribution: Dict[str, int] = field(default_factory=dict)


class UsageStore:
    """用量数据持久化存储"""

    DEFAULT_PATH = ".skillpack/usage.jsonl"

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else Path(self.DEFAULT_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_record(self, record: UsageRecord) -> None:
        """追加单条记录（JSONL 格式）"""
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def load_all_records(self) -> List[UsageRecord]:
        """加载所有记录"""
        if not self.path.exists():
            return []

        records = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        records.append(UsageRecord(**data))
                    except (json.JSONDecodeError, TypeError):
                        # 跳过损坏的记录
                        continue
        return records

    def load_records_since(self, since: datetime) -> List[UsageRecord]:
        """加载指定时间后的记录"""
        all_records = self.load_all_records()
        return [
            r for r in all_records
            if datetime.fromisoformat(r.timestamp) >= since
        ]

    def clear(self) -> None:
        """清空所有记录"""
        if self.path.exists():
            self.path.unlink()


class UsageAnalyzer:
    """用量分析器"""

    def __init__(self, store: Optional[UsageStore] = None):
        self.store = store or UsageStore()

    def analyze(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> UsageSummary:
        """分析指定时间范围的用量"""
        records = self.store.load_all_records()

        # 时间过滤
        if since:
            records = [
                r for r in records
                if datetime.fromisoformat(r.timestamp) >= since
            ]
        if until:
            records = [
                r for r in records
                if datetime.fromisoformat(r.timestamp) <= until
            ]

        if not records:
            return self._empty_summary(since, until)

        # 按模型分组统计
        model_data: Dict[str, Dict] = defaultdict(lambda: {
            "calls": 0,
            "successes": 0,
            "total_duration": 0,
            "by_route": defaultdict(int),
            "by_phase": defaultdict(int)
        })

        task_ids: set = set()
        route_counts: Dict[str, int] = defaultdict(int)

        for record in records:
            m = model_data[record.model]
            m["calls"] += 1
            if record.success:
                m["successes"] += 1
            m["total_duration"] += record.duration_ms
            m["by_route"][record.route] += 1
            m["by_phase"][record.phase_name] += 1

            if record.task_id:
                task_ids.add(record.task_id)
            route_counts[record.route] += 1

        # 构建模型统计
        models: Dict[str, ModelStats] = {}
        for model, data in model_data.items():
            calls = data["calls"]
            models[model] = ModelStats(
                model=model,
                total_calls=calls,
                successful_calls=data["successes"],
                failed_calls=calls - data["successes"],
                success_rate=data["successes"] / calls if calls > 0 else 0,
                total_duration_ms=data["total_duration"],
                avg_duration_ms=data["total_duration"] / calls if calls > 0 else 0,
                by_route=dict(data["by_route"]),
                by_phase=dict(data["by_phase"])
            )

        return UsageSummary(
            period_start=since,
            period_end=until or datetime.now(),
            total_tasks=len(task_ids),
            total_calls=len(records),
            models=models,
            route_distribution=dict(route_counts)
        )

    def get_today_stats(self) -> UsageSummary:
        """获取今日统计"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.analyze(since=today)

    def get_week_stats(self) -> UsageSummary:
        """获取本周统计"""
        week_ago = datetime.now() - timedelta(days=7)
        return self.analyze(since=week_ago)

    def _empty_summary(
        self,
        since: Optional[datetime],
        until: Optional[datetime]
    ) -> UsageSummary:
        """创建空统计"""
        return UsageSummary(
            period_start=since,
            period_end=until or datetime.now(),
            total_tasks=0,
            total_calls=0,
            models={},
            route_distribution={}
        )


def format_duration(ms: int) -> str:
    """格式化时长"""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    else:
        return f"{ms / 60000:.1f}m"


def print_dashboard(summary: UsageSummary, period_label: str) -> str:
    """生成仪表盘文本"""
    lines = []

    # 标题
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append(f"║  📊 Skillpack 模型用量仪表盘 ({period_label})")
    lines.append("╠══════════════════════════════════════════════════════════════╣")
    lines.append(f"║  📋 总任务数: {summary.total_tasks:>6}    📞 总调用数: {summary.total_calls:>6}")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")

    # 模型统计表格
    if summary.models:
        lines.append("┌─────────┬────────┬────────┬──────────┬────────────┐")
        lines.append("│  模型   │ 调用数 │ 成功率 │  总耗时  │  平均耗时  │")
        lines.append("├─────────┼────────┼────────┼──────────┼────────────┤")

        # 按调用数排序
        sorted_models = sorted(
            summary.models.items(),
            key=lambda x: -x[1].total_calls
        )

        for model, stats in sorted_models:
            success_rate = f"{stats.success_rate * 100:.1f}%"
            total_time = format_duration(stats.total_duration_ms)
            avg_time = format_duration(int(stats.avg_duration_ms))

            icon = {"claude": "🧠", "codex": "⚙️", "gemini": "💎"}.get(model, "🤖")
            lines.append(
                f"│ {icon} {model:<5} │ {stats.total_calls:>6} │ {success_rate:>6} │ {total_time:>8} │ {avg_time:>10} │"
            )

        lines.append("└─────────┴────────┴────────┴──────────┴────────────┘")
    else:
        lines.append("  (暂无数据)")

    # 路由分布
    if summary.route_distribution:
        lines.append("")
        lines.append("📈 路由分布:")
        sorted_routes = sorted(
            summary.route_distribution.items(),
            key=lambda x: -x[1]
        )
        max_count = max(summary.route_distribution.values()) if summary.route_distribution else 1

        for route, count in sorted_routes:
            bar_len = min(int(count / max_count * 20), 20)
            bar = "█" * bar_len
            lines.append(f"  {route:<12} │ {bar} {count}")

    return "\n".join(lines)


def summary_to_json(summary: UsageSummary) -> str:
    """转换为 JSON"""
    data = {
        "period": {
            "start": summary.period_start.isoformat() if summary.period_start else None,
            "end": summary.period_end.isoformat() if summary.period_end else None
        },
        "total_tasks": summary.total_tasks,
        "total_calls": summary.total_calls,
        "models": {
            k: asdict(v) for k, v in summary.models.items()
        },
        "route_distribution": summary.route_distribution
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
