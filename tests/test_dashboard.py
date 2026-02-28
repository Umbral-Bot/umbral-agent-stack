"""
Tests for dashboard components: OpsLogger, dashboard_report, effectiveness_report, notion blocks.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestOpsLogger:
    def test_write_and_read(self, tmp_path):
        from infra.ops_logger import OpsLogger
        ol = OpsLogger(log_dir=tmp_path)

        ol.task_completed("t1", "ping", "system", "gemini_pro", 150.0, "vps")
        ol.task_failed("t2", "bad", "marketing", "connection error", "claude_pro")
        ol.task_blocked("t3", "pad", "lab", "vm_offline")
        ol.model_selected("t4", "coding", "chatgpt_plus", "preferred")
        ol.quota_warning("claude_pro", 0.85)
        ol.worker_health_change("vm", False)

        events = ol.read_events()
        assert len(events) == 6
        assert events[0]["event"] == "task_completed"
        assert events[0]["task_id"] == "t1"
        assert events[0]["duration_ms"] == 150
        assert events[1]["event"] == "task_failed"
        assert events[2]["event"] == "task_blocked"
        assert events[3]["event"] == "model_selected"
        assert events[4]["event"] == "quota_warning"
        assert events[4]["usage_pct"] == 85.0
        assert events[5]["event"] == "worker_health_change"

    def test_read_with_filter(self, tmp_path):
        from infra.ops_logger import OpsLogger
        ol = OpsLogger(log_dir=tmp_path)
        ol.task_completed("t1", "ping", "system", "gemini", 100, "vps")
        ol.task_failed("t2", "bad", "system", "err")
        ol.task_completed("t3", "ping", "system", "claude", 200, "vm")

        completed = ol.read_events(event_filter="task_completed")
        assert len(completed) == 2
        failed = ol.read_events(event_filter="task_failed")
        assert len(failed) == 1

    def test_read_empty_log(self, tmp_path):
        from infra.ops_logger import OpsLogger
        ol = OpsLogger(log_dir=tmp_path)
        assert ol.read_events() == []

    def test_read_with_limit(self, tmp_path):
        from infra.ops_logger import OpsLogger
        ol = OpsLogger(log_dir=tmp_path)
        for i in range(20):
            ol.task_completed(f"t{i}", "ping", "system", "gemini", 100, "vps")
        events = ol.read_events(limit=5)
        assert len(events) == 5


class TestDashboardReportPayload:
    def test_build_dashboard_payload_basic(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://127.0.0.1:8088")
        monkeypatch.setenv("WORKER_TOKEN", "test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from scripts.dashboard_report_vps import build_dashboard_payload
        with patch("scripts.dashboard_report_vps._worker_health", return_value={"status": "OK", "tasks": ["ping"]}), \
             patch("scripts.dashboard_report_vps._redis_stats", return_value={"pending": 0, "blocked": 0, "connected": True}), \
             patch("scripts.dashboard_report_vps._quota_stats", return_value=[{"provider": "gemini_pro", "used": 10, "limit": 500, "pct": 2.0, "window_h": 24.0}]), \
             patch("scripts.dashboard_report_vps._team_stats", return_value=[{"team": "system", "supervisor": "—", "description": "Internal", "requires_vm": False}]), \
             patch("scripts.dashboard_report_vps._recent_tasks", return_value=[{"task": "ping", "team": "system", "status": "done", "duration_s": 0.1, "task_id": "abc12345"}]), \
             patch("scripts.dashboard_report_vps._ops_log_summary", return_value={"total_events": 5, "completed": 4, "failed": 1, "success_rate": 80.0, "models_used": {"gemini": 4}}):
            payload = build_dashboard_payload()

        assert payload["dashboard_v2"] is True
        assert payload["overall_status"] == "Operativo"
        assert len(payload["quotas"]) == 1
        assert len(payload["teams"]) == 1
        assert len(payload["recent_tasks"]) == 1


class TestNotionBlocks:
    def test_build_dashboard_v2_blocks(self):
        from worker.notion_client import _build_dashboard_v2_blocks
        data = {
            "dashboard_v2": True,
            "timestamp": "2026-02-28 13:00 UTC",
            "overall_status": "Operativo",
            "vps_worker": {"status": "OK", "tasks": ["ping"]},
            "vm_worker": {"status": "OK", "tasks": ["ping", "notion.poll_comments"]},
            "redis": {"pending": 2, "blocked": 0, "connected": True},
            "quotas": [
                {"provider": "gemini_pro", "used": 50, "limit": 500, "pct": 10.0, "window_h": 24.0},
                {"provider": "claude_pro", "used": 180, "limit": 200, "pct": 90.0, "window_h": 5.0},
            ],
            "teams": [
                {"team": "system", "supervisor": "—", "description": "Internal", "requires_vm": False},
                {"team": "marketing", "supervisor": "Marketing Supervisor", "description": "SEO", "requires_vm": False},
            ],
            "recent_tasks": [
                {"task": "ping", "team": "system", "status": "done", "duration_s": 0.1, "task_id": "abc12345"},
            ],
            "ops_summary": {
                "total_events": 10,
                "completed": 8,
                "failed": 2,
                "success_rate": 80.0,
                "models_used": {"gemini_pro": 5, "claude_pro": 3},
            },
        }
        blocks = _build_dashboard_v2_blocks(data)
        assert len(blocks) > 10

        types = [b["type"] for b in blocks]
        assert "heading_2" in types
        assert "callout" in types
        assert "table" in types
        assert "divider" in types
        assert "heading_3" in types
        assert "toggle" in types

    def test_build_dashboard_v2_minimal(self):
        from worker.notion_client import _build_dashboard_v2_blocks
        data = {
            "dashboard_v2": True,
            "timestamp": "now",
            "overall_status": "Degradado",
            "vps_worker": {"status": "Offline", "tasks": []},
            "redis": {"pending": 0, "blocked": 0, "connected": False},
        }
        blocks = _build_dashboard_v2_blocks(data)
        assert len(blocks) >= 4
        callout = [b for b in blocks if b["type"] == "callout"]
        assert any("Degradado" in str(c) for c in callout)


class TestEffectivenessReport:
    def test_analyze_events(self, tmp_path):
        from infra.ops_logger import OpsLogger
        ol = OpsLogger(log_dir=tmp_path)
        for i in range(5):
            ol.task_completed(f"t{i}", "ping", "system", "gemini_pro", 100 + i * 10, "vps")
        ol.task_failed("t5", "bad", "marketing", "err", "claude_pro")
        ol.task_blocked("t6", "pad", "lab", "vm_offline")
        ol.quota_warning("claude_pro", 0.85)

        events = ol.read_events()

        from scripts.effectiveness_report import analyze
        report = analyze(events)
        assert report["tasks_completed"] == 5
        assert report["tasks_failed"] == 1
        assert report["tasks_blocked"] == 1
        assert report["success_rate"] == 83.3
        assert "gemini_pro" in report["by_model"]
        assert report["by_model"]["gemini_pro"]["completed"] == 5
        assert "system" in report["by_team"]
        assert report["quota_warnings"] == 1

    def test_to_markdown(self):
        from scripts.effectiveness_report import to_markdown
        report = {
            "period_days": 7,
            "total_events": 10,
            "tasks_completed": 8,
            "tasks_failed": 2,
            "tasks_blocked": 0,
            "success_rate": 80.0,
            "avg_tasks_per_day": 1.4,
            "tasks_per_day": {"2026-02-28": 5},
            "by_model": {"gemini_pro": {"requests": 8, "completed": 7, "failed": 1, "success_rate": 87.5, "avg_duration_ms": 120}},
            "by_team": {"system": {"completed": 8, "failed": 2, "blocked": 0}},
            "by_task_type": {"ping": {"count": 8, "avg_duration_ms": 120}},
            "worker_distribution": {"vps": 6, "vm": 2},
            "quota_warnings": 1,
            "quota_restricted": 0,
        }
        md = to_markdown(report)
        assert "Efectividad" in md
        assert "gemini_pro" in md
        assert "80.0%" in md
