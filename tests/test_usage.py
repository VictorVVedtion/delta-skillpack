"""
测试用量追踪模块
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from skillpack.usage import (
    UsageRecord,
    UsageStore,
    UsageAnalyzer,
    UsageSummary,
    ModelStats,
    format_duration,
    print_dashboard,
    summary_to_json,
)


class TestUsageRecord:
    """测试 UsageRecord 数据类"""

    def test_create_record(self):
        record = UsageRecord(
            timestamp="2026-01-20T10:30:00",
            model="codex",
            route="PLANNED",
            phase=2,
            phase_name="实现",
            task_id="task-abc123",
            success=True,
            duration_ms=45000,
            mode="cli"
        )
        assert record.model == "codex"
        assert record.route == "PLANNED"
        assert record.success is True
        assert record.duration_ms == 45000

    def test_record_defaults(self):
        record = UsageRecord(
            timestamp="2026-01-20T10:30:00",
            model="gemini",
            route="RALPH",
            phase=4,
            phase_name="独立审查"
        )
        assert record.task_id is None
        assert record.success is True
        assert record.duration_ms == 0
        assert record.error is None
        assert record.mode == "cli"

    def test_record_with_error(self):
        record = UsageRecord(
            timestamp="2026-01-20T10:30:00",
            model="codex",
            route="DIRECT",
            phase=1,
            phase_name="执行",
            success=False,
            error="Connection timeout"
        )
        assert record.success is False
        assert record.error == "Connection timeout"


class TestUsageStore:
    """测试 UsageStore 持久化"""

    def test_append_and_load(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")

            record = UsageRecord(
                timestamp="2026-01-20T10:30:00",
                model="codex",
                route="PLANNED",
                phase=2,
                phase_name="实现",
                success=True,
                duration_ms=45000
            )

            store.append_record(record)
            records = store.load_all_records()

            assert len(records) == 1
            assert records[0].model == "codex"
            assert records[0].duration_ms == 45000

    def test_append_multiple_records(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")

            for i in range(5):
                record = UsageRecord(
                    timestamp=f"2026-01-20T10:{30+i}:00",
                    model=["codex", "gemini", "claude"][i % 3],
                    route="RALPH",
                    phase=i + 1,
                    phase_name=f"Phase {i+1}",
                    success=True,
                    duration_ms=10000 * (i + 1)
                )
                store.append_record(record)

            records = store.load_all_records()
            assert len(records) == 5

    def test_load_empty_store(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "nonexistent.jsonl")
            records = store.load_all_records()
            assert records == []

    def test_load_records_since(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")

            # 添加不同时间的记录
            timestamps = [
                "2026-01-18T10:00:00",
                "2026-01-19T10:00:00",
                "2026-01-20T10:00:00",
            ]

            for ts in timestamps:
                record = UsageRecord(
                    timestamp=ts,
                    model="codex",
                    route="DIRECT",
                    phase=1,
                    phase_name="执行"
                )
                store.append_record(record)

            # 只加载 1月19日之后的记录
            since = datetime(2026, 1, 19, 0, 0, 0)
            recent = store.load_records_since(since)
            assert len(recent) == 2

    def test_clear_store(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "usage.jsonl"
            store = UsageStore(path)

            record = UsageRecord(
                timestamp="2026-01-20T10:30:00",
                model="codex",
                route="DIRECT",
                phase=1,
                phase_name="执行"
            )
            store.append_record(record)
            assert path.exists()

            store.clear()
            assert not path.exists()

    def test_corrupted_record_skipped(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "usage.jsonl"

            # 手动写入包含损坏记录的文件
            with open(path, "w") as f:
                f.write('{"timestamp":"2026-01-20T10:00:00","model":"codex","route":"DIRECT","phase":1,"phase_name":"执行"}\n')
                f.write('invalid json line\n')
                f.write('{"timestamp":"2026-01-20T11:00:00","model":"gemini","route":"RALPH","phase":4,"phase_name":"审查"}\n')

            store = UsageStore(path)
            records = store.load_all_records()

            # 损坏的记录被跳过
            assert len(records) == 2


class TestUsageAnalyzer:
    """测试 UsageAnalyzer 统计分析"""

    def test_analyze_empty(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")
            analyzer = UsageAnalyzer(store)

            summary = analyzer.analyze()
            assert summary.total_tasks == 0
            assert summary.total_calls == 0
            assert summary.models == {}

    def test_analyze_with_records(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")

            # 添加测试记录
            records = [
                UsageRecord("2026-01-20T10:00:00", "codex", "PLANNED", 2, "实现", "task-1", True, 30000),
                UsageRecord("2026-01-20T10:01:00", "codex", "PLANNED", 3, "审查", "task-1", True, 20000),
                UsageRecord("2026-01-20T10:02:00", "gemini", "RALPH", 4, "独立审查", "task-2", True, 15000),
                UsageRecord("2026-01-20T10:03:00", "gemini", "RALPH", 4, "独立审查", "task-2", False, 5000, "Timeout"),
            ]

            for r in records:
                store.append_record(r)

            analyzer = UsageAnalyzer(store)
            summary = analyzer.analyze()

            assert summary.total_tasks == 2  # task-1 and task-2
            assert summary.total_calls == 4
            assert "codex" in summary.models
            assert "gemini" in summary.models

            codex_stats = summary.models["codex"]
            assert codex_stats.total_calls == 2
            assert codex_stats.successful_calls == 2
            assert codex_stats.success_rate == 1.0

            gemini_stats = summary.models["gemini"]
            assert gemini_stats.total_calls == 2
            assert gemini_stats.successful_calls == 1
            assert gemini_stats.failed_calls == 1
            assert gemini_stats.success_rate == 0.5

    def test_route_distribution(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")

            routes = ["DIRECT", "PLANNED", "PLANNED", "RALPH", "RALPH", "RALPH"]
            for i, route in enumerate(routes):
                record = UsageRecord(
                    timestamp=f"2026-01-20T10:{i:02d}:00",
                    model="codex",
                    route=route,
                    phase=1,
                    phase_name="执行"
                )
                store.append_record(record)

            analyzer = UsageAnalyzer(store)
            summary = analyzer.analyze()

            assert summary.route_distribution["DIRECT"] == 1
            assert summary.route_distribution["PLANNED"] == 2
            assert summary.route_distribution["RALPH"] == 3

    def test_get_today_stats(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")

            # 今天的记录
            today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
            record = UsageRecord(
                timestamp=today.isoformat(),
                model="codex",
                route="DIRECT",
                phase=1,
                phase_name="执行"
            )
            store.append_record(record)

            # 昨天的记录
            yesterday = today - timedelta(days=1)
            old_record = UsageRecord(
                timestamp=yesterday.isoformat(),
                model="gemini",
                route="RALPH",
                phase=4,
                phase_name="审查"
            )
            store.append_record(old_record)

            analyzer = UsageAnalyzer(store)
            summary = analyzer.get_today_stats()

            assert summary.total_calls == 1
            assert "codex" in summary.models
            assert "gemini" not in summary.models

    def test_get_week_stats(self):
        with TemporaryDirectory() as tmpdir:
            store = UsageStore(Path(tmpdir) / "usage.jsonl")

            now = datetime.now()

            # 本周记录
            for i in range(3):
                record = UsageRecord(
                    timestamp=(now - timedelta(days=i)).isoformat(),
                    model="codex",
                    route="DIRECT",
                    phase=1,
                    phase_name="执行"
                )
                store.append_record(record)

            # 两周前的记录
            old_record = UsageRecord(
                timestamp=(now - timedelta(days=14)).isoformat(),
                model="gemini",
                route="RALPH",
                phase=4,
                phase_name="审查"
            )
            store.append_record(old_record)

            analyzer = UsageAnalyzer(store)
            summary = analyzer.get_week_stats()

            assert summary.total_calls == 3


class TestFormatDuration:
    """测试时长格式化"""

    def test_milliseconds(self):
        assert format_duration(500) == "500ms"
        assert format_duration(0) == "0ms"

    def test_seconds(self):
        assert format_duration(5000) == "5.0s"
        assert format_duration(30500) == "30.5s"

    def test_minutes(self):
        assert format_duration(60000) == "1.0m"
        assert format_duration(150000) == "2.5m"


class TestPrintDashboard:
    """测试仪表盘输出"""

    def test_empty_dashboard(self):
        summary = UsageSummary(
            period_start=None,
            period_end=datetime.now(),
            total_tasks=0,
            total_calls=0,
            models={},
            route_distribution={}
        )

        output = print_dashboard(summary, "今日")
        assert "今日" in output
        assert "总任务数" in output
        assert "(暂无数据)" in output

    def test_dashboard_with_data(self):
        summary = UsageSummary(
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            total_tasks=5,
            total_calls=20,
            models={
                "codex": ModelStats(
                    model="codex",
                    total_calls=10,
                    successful_calls=9,
                    failed_calls=1,
                    success_rate=0.9,
                    total_duration_ms=300000,
                    avg_duration_ms=30000,
                    by_route={"PLANNED": 5, "RALPH": 5},
                    by_phase={"实现": 5, "审查": 5}
                ),
                "gemini": ModelStats(
                    model="gemini",
                    total_calls=10,
                    successful_calls=8,
                    failed_calls=2,
                    success_rate=0.8,
                    total_duration_ms=200000,
                    avg_duration_ms=20000,
                    by_route={"RALPH": 10},
                    by_phase={"独立审查": 10}
                )
            },
            route_distribution={"PLANNED": 5, "RALPH": 15}
        )

        output = print_dashboard(summary, "本周")
        assert "本周" in output
        assert "总任务数" in output
        assert "5" in output
        assert "20" in output
        assert "codex" in output
        assert "gemini" in output
        assert "路由分布" in output


class TestSummaryToJson:
    """测试 JSON 序列化"""

    def test_serialize_empty_summary(self):
        summary = UsageSummary(
            period_start=None,
            period_end=datetime(2026, 1, 20, 12, 0, 0),
            total_tasks=0,
            total_calls=0,
            models={},
            route_distribution={}
        )

        json_str = summary_to_json(summary)
        data = json.loads(json_str)

        assert data["total_tasks"] == 0
        assert data["total_calls"] == 0
        assert data["period"]["start"] is None
        assert "2026-01-20" in data["period"]["end"]

    def test_serialize_with_data(self):
        summary = UsageSummary(
            period_start=datetime(2026, 1, 19, 0, 0, 0),
            period_end=datetime(2026, 1, 20, 12, 0, 0),
            total_tasks=3,
            total_calls=10,
            models={
                "codex": ModelStats(
                    model="codex",
                    total_calls=10,
                    successful_calls=9,
                    failed_calls=1,
                    success_rate=0.9,
                    total_duration_ms=100000,
                    avg_duration_ms=10000,
                    by_route={},
                    by_phase={}
                )
            },
            route_distribution={"DIRECT": 5, "PLANNED": 5}
        )

        json_str = summary_to_json(summary)
        data = json.loads(json_str)

        assert data["total_tasks"] == 3
        assert data["total_calls"] == 10
        assert "codex" in data["models"]
        assert data["models"]["codex"]["success_rate"] == 0.9
        assert data["route_distribution"]["DIRECT"] == 5
