"""Tests for dispatcher.alert_manager.AlertManager."""

from unittest.mock import MagicMock

from dispatcher.alert_manager import AlertManager


def test_task_failed_generates_notion_comment():
    wc = MagicMock()
    am = AlertManager(wc, control_room_page_id="page-123")

    ok = am.alert_task_failed(
        task_id="t-001",
        task_name="research.web",
        team="marketing",
        error="Connection timeout",
        envelope={"task_type": "research", "input": {"selected_model": "gemini_pro"}},
    )

    assert ok is True
    wc.notion_add_comment.assert_called_once()
    kwargs = wc.notion_add_comment.call_args.kwargs
    assert kwargs["page_id"] == "page-123"
    assert "Tarea fallida" in kwargs["text"]
    assert "research.web" in kwargs["text"]
    assert "marketing" in kwargs["text"]
    assert "Connection timeout" in kwargs["text"]


def test_worker_down_generates_alert():
    wc = MagicMock()
    am = AlertManager(wc, control_room_page_id=None)

    ok = am.alert_worker_down("http://127.0.0.1:8088", "Connection refused")

    assert ok is True
    wc.notion_add_comment.assert_called_once()
    text = wc.notion_add_comment.call_args.kwargs["text"]
    assert "Worker no responde" in text
    assert "127.0.0.1:8088" in text
    assert "Connection refused" in text


def test_cooldown_prevents_duplicate_alerts_for_5_minutes():
    now = {"value": 1000.0}

    def _time():
        return now["value"]

    wc = MagicMock()
    am = AlertManager(wc, cooldown_seconds=300, time_fn=_time)

    assert am.alert_worker_down("http://worker", "refused") is True
    assert am.alert_worker_down("http://worker", "refused") is False
    assert wc.notion_add_comment.call_count == 1

    now["value"] += 301.0
    assert am.alert_worker_down("http://worker", "refused") is True
    assert wc.notion_add_comment.call_count == 2


def test_task_failed_with_minimal_envelope_does_not_crash():
    wc = MagicMock()
    am = AlertManager(wc)

    ok = am.alert_task_failed(
        task_id="t-xyz",
        task_name="ping",
        team="system",
        error="boom",
        envelope={},
    )

    assert ok is True
    wc.notion_add_comment.assert_called_once()
