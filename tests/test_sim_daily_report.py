"""Tests for SIM daily report script behavior."""

from datetime import datetime, timezone
import sys

import scripts.sim_daily_report as sim_daily_report


def test_build_report_includes_topics_urls_and_llm_summary():
    now = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)
    events = [
        {
            "event": "task_completed",
            "task": "research.web",
            "team": "marketing",
            "task_id": "r1",
            "ts": "2026-03-04T11:10:00+00:00",
        },
        {
            "event": "task_completed",
            "task": "research.web",
            "team": "advisory",
            "task_id": "r2",
            "ts": "2026-03-04T11:15:00+00:00",
        },
        {
            "event": "task_completed",
            "task": "llm.generate",
            "team": "system",
            "task_id": "l1",
            "ts": "2026-03-04T11:30:00+00:00",
        },
    ]
    task_details = {
        "r1": {
            "input": {"query": "tendencias BIM 2026"},
            "result": {
                "result": {
                    "results": [
                        {"url": "https://example.com/a"},
                        {"url": "https://example.com/b"},
                    ]
                }
            },
        },
        "r2": {
            "input": {"query": "adopcion BIM LATAM"},
            "result": {
                "result": {
                    "results": [
                        {"url": "https://example.com/b"},
                        {"url": "https://example.com/c"},
                    ]
                }
            },
        },
        "l1": {"result": {"result": {"text": "Resumen ejecutivo para la jornada."}}},
    }

    report = sim_daily_report.build_report(
        events=events,
        task_details=task_details,
        now=now,
        window_hours=8,
        max_topics=10,
        max_urls=10,
    )

    assert "Temas cubiertos:" in report
    assert "1. tendencias BIM 2026" in report
    assert "2. adopcion BIM LATAM" in report
    assert "URLs encontradas (research.web):" in report
    assert "https://example.com/a" in report
    assert "https://example.com/b" in report
    assert "https://example.com/c" in report
    assert "Resumen ejecutivo para la jornada." in report


def test_main_without_notion_flag_does_not_post(monkeypatch, capsys):
    class _DummyOpsLogger:
        def read_events(self, limit):  # noqa: ARG002
            return []

    called = {"post": False}

    def _fake_post(*args, **kwargs):  # noqa: ARG001
        called["post"] = True
        return {"comment_id": "unused"}

    monkeypatch.setattr(sim_daily_report, "OpsLogger", _DummyOpsLogger)
    monkeypatch.setattr(sim_daily_report, "_load_task_details", lambda task_ids: {})  # noqa: ARG005
    monkeypatch.setattr(sim_daily_report, "post_report_via_worker", _fake_post)
    monkeypatch.setattr(sys, "argv", ["sim_daily_report.py", "--hours", "8", "--limit", "10"])

    rc = sim_daily_report.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert called["post"] is False
    assert "Usa --notion para postear" in out


def test_main_with_notion_flag_posts(monkeypatch, capsys):
    class _DummyOpsLogger:
        def read_events(self, limit):  # noqa: ARG002
            return []

    called = {"post": False}

    def _fake_post(*args, **kwargs):  # noqa: ARG001
        called["post"] = True
        return {"comment_id": "cmt-123", "parts": 1, "page_id": None}

    monkeypatch.setattr(sim_daily_report, "OpsLogger", _DummyOpsLogger)
    monkeypatch.setattr(sim_daily_report, "_load_task_details", lambda task_ids: {})  # noqa: ARG005
    # Task 036b: main() now calls post_report (paginator wrapper), not post_report_via_worker.
    monkeypatch.setattr(sim_daily_report, "post_report", _fake_post)
    monkeypatch.setattr(
        sys,
        "argv",
        ["sim_daily_report.py", "--hours", "8", "--limit", "10", "--notion"],
    )

    rc = sim_daily_report.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert called["post"] is True
    assert "Notion comment posted: cmt-123" in out
