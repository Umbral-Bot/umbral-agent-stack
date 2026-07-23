"""
Tests for scripts/editorial/trigger_hitl2_publish.py (P2.6 — HITL-2 -> publish
bridge CLI). Verifies the script never calls the Worker with a live
(non-dry-run) request unless both --live and --telegram-confirmed are given,
and that it never fabricates the Telegram confirmation itself.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from scripts.editorial import trigger_hitl2_publish as thp


def test_default_invocation_is_dry_run_and_unconfirmed(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["trigger_hitl2_publish.py", "--notion-page-id", "pub-1"])
    fake_wc = MagicMock()
    fake_wc.run.return_value = {
        "ok": False,
        "error": "telegram_confirmation_missing",
        "would_publish": False,
    }
    with patch("scripts.editorial.trigger_hitl2_publish._resolve_worker_client", return_value=fake_wc):
        exit_code = thp.main()

    assert exit_code == 0
    input_data = fake_wc.run.call_args.args[1]
    assert input_data["dry_run"] is True
    assert input_data["telegram_confirmed"] is False
    out = capsys.readouterr().out
    assert "HITL2_NOT_READY reason=telegram_confirmation_missing" in out


def test_live_without_telegram_confirmed_refuses_before_any_worker_call(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["trigger_hitl2_publish.py", "--notion-page-id", "pub-1", "--live"])
    fake_wc = MagicMock()
    with patch("scripts.editorial.trigger_hitl2_publish._resolve_worker_client", return_value=fake_wc):
        exit_code = thp.main()

    assert exit_code == 3
    fake_wc.run.assert_not_called()
    err = capsys.readouterr().err
    assert "--live requires --telegram-confirmed" in err


def test_telegram_confirmed_without_live_still_forces_dry_run(monkeypatch, capsys):
    # --telegram-confirmed alone (no --live) must NOT be enough to go live —
    # the operator must explicitly opt into --live too.
    monkeypatch.setattr(
        "sys.argv",
        ["trigger_hitl2_publish.py", "--notion-page-id", "pub-1", "--telegram-confirmed"],
    )
    fake_wc = MagicMock()
    fake_wc.run.return_value = {"ok": True, "would_publish": True, "dry_run": True}
    with patch("scripts.editorial.trigger_hitl2_publish._resolve_worker_client", return_value=fake_wc):
        exit_code = thp.main()

    assert exit_code == 0
    input_data = fake_wc.run.call_args.args[1]
    assert input_data["dry_run"] is True
    assert input_data["telegram_confirmed"] is True


def test_live_with_telegram_confirmed_calls_worker_non_dry_run(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["trigger_hitl2_publish.py", "--notion-page-id", "pub-1", "--telegram-confirmed", "--live"],
    )
    fake_wc = MagicMock()
    fake_wc.run.return_value = {
        "ok": True,
        "published": True,
        "published_url": "https://umbralbim.io/noticias/x",
    }
    with patch("scripts.editorial.trigger_hitl2_publish._resolve_worker_client", return_value=fake_wc):
        exit_code = thp.main()

    assert exit_code == 0
    input_data = fake_wc.run.call_args.args[1]
    assert input_data["dry_run"] is False
    assert input_data["telegram_confirmed"] is True
    out = capsys.readouterr().out
    assert "HITL2_PUBLISHED_OK" in out


def test_blocked_response_prints_error_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["trigger_hitl2_publish.py", "--notion-page-id", "pub-1"])
    fake_wc = MagicMock()
    fake_wc.run.return_value = {"ok": False, "error": "visual_asset_not_ready"}
    with patch("scripts.editorial.trigger_hitl2_publish._resolve_worker_client", return_value=fake_wc):
        exit_code = thp.main()

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "HITL2_BLOCKED error=visual_asset_not_ready" in out


def test_worker_call_failure_returns_4(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["trigger_hitl2_publish.py", "--notion-page-id", "pub-1"])
    fake_wc = MagicMock()
    fake_wc.run.side_effect = RuntimeError("connection refused")
    with patch("scripts.editorial.trigger_hitl2_publish._resolve_worker_client", return_value=fake_wc):
        exit_code = thp.main()

    assert exit_code == 4
    err = capsys.readouterr().err
    assert "Worker call failed" in err
