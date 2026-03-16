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
        ol.model_selected("t4", "coding", "azure_foundry", "preferred")
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
    def _mock_payload(self):
        return {
            "status": "OK", "tasks": ["ping"],
        }

    def test_build_dashboard_payload_basic(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://127.0.0.1:8088")
        monkeypatch.setenv("WORKER_TOKEN", "test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from scripts.dashboard_report_vps import build_dashboard_payload
        with patch("scripts.dashboard_report_vps._worker_health", return_value={"status": "OK", "tasks": ["ping"]}), \
             patch("scripts.dashboard_report_vps._redis_stats", return_value={"pending": 0, "blocked": 0, "connected": True}), \
             patch("scripts.dashboard_report_vps._quota_stats", return_value=[{"provider": "gemini_pro", "used": 10, "limit": 500, "pct": 2.0, "window_h": 24.0, "resets_in_min": None}]), \
             patch("scripts.dashboard_report_vps._team_stats", return_value=[{"team": "system", "supervisor": "—", "description": "Internal", "requires_vm": False, "completed": 3, "active": 1}]), \
             patch("scripts.dashboard_report_vps._recent_tasks", return_value=[{"task": "research.web", "team": "system", "status": "done", "duration_s": 0.1, "task_id": "abc12345", "when": "14:00 28/02", "project_name": "Proyecto Embudo Ventas"}]), \
             patch("scripts.dashboard_report_vps._running_tasks", return_value=[]), \
             patch("scripts.dashboard_report_vps._ops_log_summary", return_value={"total_events": 5, "completed": 4, "failed": 1, "completed_today": 4, "success_rate": 80.0, "models_used": {"gemini": 4}, "trend": "+20% vs ayer"}), \
             patch("scripts.dashboard_report_vps._system_uptime", return_value="2d 5h"), \
             patch("scripts.dashboard_report_vps._last_error", return_value=None), \
             patch("scripts.dashboard_report_vps._active_alerts", return_value=[]), \
             patch("scripts.dashboard_report_vps._notion_ops_summary", return_value={"tasks_total": 8, "tasks_unlinked": 1, "deliverables_pending": 2, "deliverables_adjustments": 1, "bridge_live": 1}):
            payload = build_dashboard_payload()

        assert payload["dashboard_v2"] is True
        assert payload["overall_status"] == "Operativo"
        assert len(payload["quotas"]) == 1
        assert len(payload["teams"]) == 1
        assert len(payload["recent_tasks"]) == 1
        assert payload["recent_system_tasks"] == []
        assert payload["uptime"] == "2d 5h"
        assert payload["running_tasks"] == []
        assert payload["active_alerts"] == []
        assert payload["vm_recovery_mode"] == {"enabled": False}
        assert payload["notion_ops"]["deliverables_pending"] == 2
        assert "release_tracking" not in payload

    def test_build_dashboard_payload_degrades_when_vm_is_offline(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://127.0.0.1:8088")
        monkeypatch.setenv("WORKER_TOKEN", "test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from scripts import dashboard_report_vps as dashboard_module
        monkeypatch.setattr(dashboard_module, "WORKER_URL_VM", "http://100.109.16.40:8088")
        monkeypatch.setattr(dashboard_module, "WORKER_URL_VM_INTERACTIVE", None)
        build_dashboard_payload = dashboard_module.build_dashboard_payload
        with patch("scripts.dashboard_report_vps._worker_health", side_effect=[
            {"status": "OK", "tasks": ["ping"]},
            {"status": "Offline (ConnectTimeout)", "tasks": []},
        ]), \
             patch("scripts.dashboard_report_vps._redis_stats", return_value={"pending": 0, "blocked": 0, "connected": True}), \
             patch("scripts.dashboard_report_vps._quota_stats", return_value=[]), \
             patch("scripts.dashboard_report_vps._team_stats", return_value=[]), \
             patch("scripts.dashboard_report_vps._recent_tasks", return_value=[]), \
             patch("scripts.dashboard_report_vps._running_tasks", return_value=[]), \
             patch("scripts.dashboard_report_vps._ops_log_summary", return_value={"total_events": 0}), \
             patch("scripts.dashboard_report_vps._system_uptime", return_value=None), \
             patch("scripts.dashboard_report_vps._last_error", return_value=None), \
             patch("scripts.dashboard_report_vps._active_alerts", return_value=["Worker VM: Offline (ConnectTimeout)"]), \
             patch("scripts.dashboard_report_vps._notion_ops_summary", return_value=None):
            payload = build_dashboard_payload()

        assert payload["overall_status"] == "Degradado"

    def test_build_dashboard_payload_marks_vm_recovery_mode(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://127.0.0.1:8088")
        monkeypatch.setenv("WORKER_TOKEN", "test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from scripts import dashboard_report_vps as dashboard_module
        monkeypatch.setattr(dashboard_module, "WORKER_URL_VM", "http://127.0.0.1:28088")
        monkeypatch.setattr(dashboard_module, "WORKER_URL_VM_INTERACTIVE", "http://127.0.0.1:28089")
        build_dashboard_payload = dashboard_module.build_dashboard_payload
        with patch("scripts.dashboard_report_vps._worker_health", side_effect=[
            {"status": "OK", "tasks": ["ping"]},
            {"status": "OK", "tasks": ["ping"]},
            {"status": "OK", "tasks": ["gui.desktop_status"]},
        ]), \
             patch("scripts.dashboard_report_vps._redis_stats", return_value={"pending": 0, "blocked": 0, "connected": True}), \
             patch("scripts.dashboard_report_vps._quota_stats", return_value=[]), \
             patch("scripts.dashboard_report_vps._team_stats", return_value=[]), \
             patch("scripts.dashboard_report_vps._recent_tasks", return_value=[]), \
             patch("scripts.dashboard_report_vps._running_tasks", return_value=[]), \
             patch("scripts.dashboard_report_vps._ops_log_summary", return_value={"total_events": 0}), \
             patch("scripts.dashboard_report_vps._system_uptime", return_value=None), \
             patch("scripts.dashboard_report_vps._last_error", return_value=None), \
             patch("scripts.dashboard_report_vps._active_alerts", return_value=[]), \
             patch("scripts.dashboard_report_vps._notion_ops_summary", return_value={"tasks_total": 8, "tasks_unlinked": 1, "deliverables_pending": 2, "deliverables_adjustments": 1, "bridge_live": 1}):
            payload = build_dashboard_payload()

        assert payload["overall_status"] == "Operativo"
        assert payload["vm_recovery_mode"]["enabled"] is True
        assert payload["vm_recovery_mode"]["transport"] == "reverse_ssh_tunnel"

    def test_split_recent_tasks_separates_signal_from_noise(self, monkeypatch):
        from scripts.dashboard_report_vps import _split_recent_tasks

        recent = [
            {"task": "windows.fs.list", "team": "lab", "status": "done", "duration_s": 0.2, "task_id": "aaa111", "when": "14:00 28/02"},
            {"task": "research.web", "team": "marketing", "status": "done", "duration_s": 1.0, "task_id": "bbb222", "when": "14:01 28/02", "project_name": "Proyecto Embudo Ventas"},
        ]

        relevant, system = _split_recent_tasks(recent)
        assert [t["task_id"] for t in relevant] == ["bbb222"]
        assert [t["task_id"] for t in system] == ["aaa111"]

    def test_fingerprint_changes_with_data(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://127.0.0.1:8088")
        monkeypatch.setenv("WORKER_TOKEN", "test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from scripts.dashboard_report_vps import _payload_fingerprint
        fp1 = _payload_fingerprint({"status": "OK", "pending": 0, "timestamp": "t1"})
        fp2 = _payload_fingerprint({"status": "OK", "pending": 0, "timestamp": "t2"})
        fp3 = _payload_fingerprint({"status": "OK", "pending": 5, "timestamp": "t1"})
        assert fp1 == fp2, "timestamp changes should not affect fingerprint"
        assert fp1 != fp3, "data changes should affect fingerprint"


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
                {"provider": "gemini_pro", "used": 50, "limit": 500, "pct": 10.0, "window_h": 24.0, "resets_in_min": 120},
                {"provider": "claude_pro", "used": 180, "limit": 200, "pct": 90.0, "window_h": 5.0, "resets_in_min": 30},
            ],
            "teams": [
                {"team": "system", "supervisor": "—", "description": "Internal", "requires_vm": False, "completed": 10, "active": 1},
                {"team": "marketing", "supervisor": "Marketing Supervisor", "description": "SEO", "requires_vm": False, "completed": 5, "active": 0},
            ],
            "notion_ops": {
                "tasks_total": 12,
                "tasks_unlinked": 2,
                "deliverables_pending": 3,
                "deliverables_adjustments": 1,
                "bridge_live": 2,
            },
            "recent_tasks": [
                {"task": "ping", "team": "system", "status": "done", "duration_s": 0.1, "task_id": "abc12345", "when": "14:00 28/02"},
            ],
            "recent_system_tasks": [
                {"task": "windows.fs.list", "team": "lab", "status": "done", "duration_s": 0.2, "task_id": "def67890", "when": "14:05 28/02"},
            ],
            "running_tasks": [
                {"task": "notion.poll_comments", "team": "system", "elapsed": "5s"},
            ],
            "ops_summary": {
                "total_events": 10,
                "completed": 8,
                "failed": 2,
                "completed_today": 3,
                "success_rate": 80.0,
                "models_used": {"gemini_pro": 5, "claude_pro": 3},
                "trend": "+10% vs ayer",
            },
            "uptime": "1d 3h",
            "last_error": "bad_task — timeout connecting",
            "active_alerts": ["CUOTA CRITICA: claude_pro al 90%"],
        }
        blocks = _build_dashboard_v2_blocks(data)
        assert len(blocks) > 10

        types = [b["type"] for b in blocks]
        assert "heading_1" in types
        assert "heading_2" in types
        assert "callout" in types
        assert "table" in types
        assert "divider" in types
        assert "paragraph" in types

        callouts = [b for b in blocks if b["type"] == "callout"]
        assert any("green_background" in str(c) for c in callouts), "Operativo should use green_background"
        assert any("red_background" in str(c) for c in callouts), "Alert or error should use red_background"
        assert all("Seguimiento R16/R17" not in str(b) for b in blocks)
        assert any("Ruido tecnico / sistema" in str(b) for b in blocks)
        assert any("Este dashboard es tecnico" in str(b) for b in blocks)

    def test_build_dashboard_v2_blocks_show_vm_recovery_mode(self):
        from worker.notion_client import _build_dashboard_v2_blocks
        data = {
            "dashboard_v2": True,
            "timestamp": "2026-03-15 21:54 UTC",
            "overall_status": "Operativo",
            "vps_worker": {"status": "OK", "tasks": ["ping"]},
            "vm_worker": {"status": "OK", "tasks": ["ping"]},
            "vm_worker_interactive": {"status": "OK", "tasks": ["gui.desktop_status"]},
            "vm_recovery_mode": {"enabled": True, "transport": "reverse_ssh_tunnel"},
            "redis": {"pending": 0, "blocked": 0, "connected": True},
        }
        blocks = _build_dashboard_v2_blocks(data)
        assert any("recovery mode" in str(block).lower() for block in blocks)

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
        assert any("red_background" in str(c) for c in callout)

    def test_rich_text_annotations(self):
        from worker.notion_client import _rich
        normal = _rich("hello")
        assert "annotations" not in normal
        bold = _rich("hello", bold=True)
        assert bold["annotations"]["bold"] is True
        colored = _rich("hello", color="red")
        assert colored["annotations"]["color"] == "red"

    def test_in_trash_used_for_deletion(self):
        """Verify update_dashboard_page uses in_trash (not deprecated archived)."""
        import inspect
        from worker.notion_client import update_dashboard_page
        source = inspect.getsource(update_dashboard_page)
        assert '"in_trash": True' in source or "'in_trash': True" in source or '"in_trash"' in source
        assert '"archived": True' not in source, "Should use in_trash instead of deprecated archived"

    def test_quota_zone(self):
        from worker.notion_client import _quota_zone
        assert _quota_zone(50) == "OK"
        assert _quota_zone(75) == "ALERTA"
        assert _quota_zone(95) == "CRITICO"

    def test_column_list_block(self):
        from worker.notion_client import _block_column_list, _block_paragraph
        cols = _block_column_list([
            [_block_paragraph("Col 1")],
            [_block_paragraph("Col 2")],
        ])
        assert cols["type"] == "column_list"
        children = cols["column_list"]["children"]
        assert len(children) == 2
        assert children[0]["type"] == "column"
        assert children[0]["column"]["width_ratio"] == 0.5


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
