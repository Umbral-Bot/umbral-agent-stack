"""
Tests for R13 — Governance Metrics Report.

Validates:
- Empty ops_log returns zeroed metrics
- Sample events produce correct aggregations
- Success rate calculation (edge cases included)
- Tasks-by-team aggregation
- JSON output format (valid JSON with required keys)
- Markdown output format (sections + tables)
- Tasks-by-day aggregation
- Model usage aggregation
- Worker distribution
- Duration averages (global and per-type)
- build_report integration with temp log file

Run: python -m pytest tests/test_governance_metrics.py -v
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.governance_metrics_report import analyze, to_json, to_markdown, build_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(days_ago: int = 0, hour: int = 12) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    return dt.isoformat()


def _completed(task: str = "ping", team: str = "general", model: str = "gemini_pro",
               duration_ms: int = 500, worker: str = "vps", days_ago: int = 0) -> Dict[str, Any]:
    return {
        "event": "task_completed",
        "ts": _ts(days_ago),
        "task_id": f"t-{id(task)}-{days_ago}",
        "task": task,
        "team": team,
        "model": model,
        "duration_ms": duration_ms,
        "worker": worker,
    }


def _failed(task: str = "llm.generate", team: str = "research", model: str = "claude_pro",
            days_ago: int = 0) -> Dict[str, Any]:
    return {
        "event": "task_failed",
        "ts": _ts(days_ago),
        "task_id": f"f-{id(task)}-{days_ago}",
        "task": task,
        "team": team,
        "model": model,
        "error": "timeout",
    }


def _blocked(task: str = "notion.write_transcript", team: str = "general",
             days_ago: int = 0) -> Dict[str, Any]:
    return {
        "event": "task_blocked",
        "ts": _ts(days_ago),
        "task_id": f"b-{id(task)}-{days_ago}",
        "task": task,
        "team": team,
        "reason": "quota exceeded",
    }


def _model_selected(model: str = "gemini_pro", task_type: str = "research",
                    days_ago: int = 0) -> Dict[str, Any]:
    return {
        "event": "model_selected",
        "ts": _ts(days_ago),
        "task_id": f"ms-{id(model)}-{days_ago}",
        "task_type": task_type,
        "model": model,
        "reason": "preferred",
    }


SAMPLE_EVENTS: List[Dict[str, Any]] = [
    _completed("ping", "general", "gemini_pro", 200, "vps", 0),
    _completed("llm.generate", "research", "gemini_pro", 800, "vps", 0),
    _completed("research.web", "research", "gemini_flash", 1200, "vm", 1),
    _completed("llm.generate", "general", "claude_pro", 600, "vps", 1),
    _completed("ping", "general", "gemini_pro", 150, "vps", 2),
    _failed("llm.generate", "research", "claude_pro", 0),
    _failed("research.web", "research", "gemini_pro", 1),
    _blocked("notion.write_transcript", "general", 0),
    _blocked("llm.generate", "research", 2),
    _model_selected("gemini_pro", "research", 0),
    _model_selected("claude_pro", "coding", 1),
    _model_selected("gemini_pro", "research", 1),
]


# ---------------------------------------------------------------------------
# 1. test_report_with_empty_ops_log
# ---------------------------------------------------------------------------

class TestEmptyOpsLog:
    def test_report_with_empty_ops_log(self):
        report = analyze([])
        assert report["tasks_total"] == 0
        assert report["tasks_completed"] == 0
        assert report["tasks_failed"] == 0
        assert report["tasks_blocked"] == 0
        assert report["success_rate"] == 0.0
        assert report["tasks_by_day"] == {}
        assert report["tasks_by_team"] == {}
        assert report["tasks_by_task_type"] == {}
        assert report["model_usage"] == {}
        assert report["avg_duration_ms"] == 0
        assert report["worker_distribution"] == {}


# ---------------------------------------------------------------------------
# 2. test_report_with_sample_events
# ---------------------------------------------------------------------------

class TestSampleEvents:
    def test_report_with_sample_events(self):
        report = analyze(SAMPLE_EVENTS)
        assert report["tasks_total"] == 9  # 5 completed + 2 failed + 2 blocked
        assert report["tasks_completed"] == 5
        assert report["tasks_failed"] == 2
        assert report["tasks_blocked"] == 2

    def test_model_usage_includes_selections_and_completions(self):
        report = analyze(SAMPLE_EVENTS)
        assert "gemini_pro" in report["model_usage"]
        assert report["model_usage"]["gemini_pro"] > 0

    def test_worker_distribution(self):
        report = analyze(SAMPLE_EVENTS)
        assert "vps" in report["worker_distribution"]
        assert "vm" in report["worker_distribution"]
        assert report["worker_distribution"]["vps"] == 4
        assert report["worker_distribution"]["vm"] == 1


# ---------------------------------------------------------------------------
# 3. test_success_rate_calculation
# ---------------------------------------------------------------------------

class TestSuccessRate:
    def test_success_rate_calculation(self):
        report = analyze(SAMPLE_EVENTS)
        expected = round(5 / 7 * 100, 1)  # 5 completed, 2 failed
        assert report["success_rate"] == expected

    def test_success_rate_all_completed(self):
        events = [_completed(days_ago=i) for i in range(10)]
        report = analyze(events)
        assert report["success_rate"] == 100.0

    def test_success_rate_all_failed(self):
        events = [_failed(days_ago=i) for i in range(5)]
        report = analyze(events)
        assert report["success_rate"] == 0.0

    def test_success_rate_no_exec(self):
        events = [_blocked(days_ago=0)]
        report = analyze(events)
        assert report["success_rate"] == 0.0


# ---------------------------------------------------------------------------
# 4. test_tasks_by_team_aggregation
# ---------------------------------------------------------------------------

class TestTasksByTeam:
    def test_tasks_by_team_aggregation(self):
        report = analyze(SAMPLE_EVENTS)
        teams = report["tasks_by_team"]
        assert "general" in teams
        assert "research" in teams
        assert teams["general"]["completed"] == 3
        assert teams["general"]["blocked"] == 1
        assert teams["research"]["failed"] == 2
        assert teams["research"]["blocked"] == 1

    def test_team_success_rate(self):
        report = analyze(SAMPLE_EVENTS)
        gen = report["tasks_by_team"]["general"]
        assert gen["success_rate"] == 100.0  # 3 completed, 0 failed
        res = report["tasks_by_team"]["research"]
        expected = round(2 / 4 * 100, 1)  # 2 completed, 2 failed
        assert res["success_rate"] == expected


# ---------------------------------------------------------------------------
# 5. test_json_output_format
# ---------------------------------------------------------------------------

class TestJsonOutput:
    def test_json_output_format(self):
        report = analyze(SAMPLE_EVENTS)
        output = to_json(report, days=7)
        parsed = json.loads(output)
        assert "generated_at" in parsed
        assert "period_days" in parsed
        assert parsed["period_days"] == 7
        assert parsed["tasks_total"] == 9
        assert "tasks_by_team" in parsed
        assert "tasks_by_task_type" in parsed
        assert "model_usage" in parsed
        assert "success_rate" in parsed
        assert "avg_duration_ms" in parsed
        assert "worker_distribution" in parsed

    def test_json_is_valid(self):
        report = analyze([])
        output = to_json(report, days=1)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# 6. test_markdown_output_format
# ---------------------------------------------------------------------------

class TestMarkdownOutput:
    def test_markdown_output_format(self):
        report = analyze(SAMPLE_EVENTS)
        md = to_markdown(report, days=7)
        assert "# Métricas de gobernanza" in md
        assert "## Resumen" in md
        assert "## Por team" in md
        assert "## Por task type" in md
        assert "## Uso de modelos" in md

    def test_markdown_contains_data(self):
        report = analyze(SAMPLE_EVENTS)
        md = to_markdown(report, days=7)
        assert "Tasks totales: 9" in md
        assert "Completadas: 5" in md
        assert "Fallidas: 2" in md
        assert "Bloqueadas: 2" in md

    def test_markdown_empty_report(self):
        report = analyze([])
        md = to_markdown(report, days=7)
        assert "# Métricas de gobernanza" in md
        assert "Tasks totales: 0" in md
        assert "## Por team" not in md  # no data = no section

    def test_markdown_has_tables(self):
        report = analyze(SAMPLE_EVENTS)
        md = to_markdown(report, days=7)
        assert "| Team |" in md
        assert "| Task |" in md
        assert "| Modelo |" in md


# ---------------------------------------------------------------------------
# 7. test_tasks_by_day
# ---------------------------------------------------------------------------

class TestTasksByDay:
    def test_tasks_by_day(self):
        report = analyze(SAMPLE_EVENTS)
        by_day = report["tasks_by_day"]
        assert len(by_day) >= 1
        total_in_days = sum(by_day.values())
        assert total_in_days == 9  # completed + failed + blocked

    def test_days_are_sorted(self):
        report = analyze(SAMPLE_EVENTS)
        days = list(report["tasks_by_day"].keys())
        assert days == sorted(days)


# ---------------------------------------------------------------------------
# 8. test_avg_duration
# ---------------------------------------------------------------------------

class TestAvgDuration:
    def test_avg_duration_ms(self):
        report = analyze(SAMPLE_EVENTS)
        durations = [200, 800, 1200, 600, 150]
        expected = round(sum(durations) / len(durations))
        assert report["avg_duration_ms"] == expected

    def test_avg_duration_by_type(self):
        report = analyze(SAMPLE_EVENTS)
        by_type = report["avg_duration_by_type"]
        assert "ping" in by_type
        assert by_type["ping"] == round((200 + 150) / 2)
        assert "llm.generate" in by_type


# ---------------------------------------------------------------------------
# 9. test_tasks_by_task_type
# ---------------------------------------------------------------------------

class TestTasksByTaskType:
    def test_task_types(self):
        report = analyze(SAMPLE_EVENTS)
        types = report["tasks_by_task_type"]
        assert "llm.generate" in types
        assert types["llm.generate"]["completed"] == 2
        assert types["llm.generate"]["failed"] == 1
        assert "research.web" in types

    def test_task_type_success_rate(self):
        report = analyze(SAMPLE_EVENTS)
        llm = report["tasks_by_task_type"]["llm.generate"]
        expected = round(2 / 3 * 100, 1)
        assert llm["success_rate"] == expected


# ---------------------------------------------------------------------------
# 10. test_build_report with temp log file
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_build_report_with_temp_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "scripts.governance_metrics_report.get_quota_usage",
            lambda: {},
        )
        log_dir = tmp_path / ".config" / "umbral"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "ops_log.jsonl"

        events = [
            _completed("ping", "general", "gemini_pro", 300, "vps", 0),
            _failed("llm.generate", "research", "claude_pro", 0),
        ]
        lines = [json.dumps(e) for e in events]
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        report = build_report(days=7, log_path=log_file)
        assert report["tasks_total"] == 2
        assert report["tasks_completed"] == 1
        assert report["tasks_failed"] == 1
        assert report["success_rate"] == 50.0
        assert isinstance(report.get("quota_usage"), dict)
