from __future__ import annotations

import shutil
from pathlib import Path

from infra.registry_backup_alert import classify_log_text, evaluate_backup_alert
from scripts.registry.check_backup_alert import main

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "registry_backup_alert"


def _copy_fixture_dir(tmp_path: Path, fixture_name: str) -> Path:
    source = FIXTURES_DIR / fixture_name
    destination = tmp_path / "logs"
    shutil.copytree(source, destination)
    return destination


def test_classify_log_text_detects_failure_markers_and_nonzero_exit_code():
    assert classify_log_text("STATUS: FAIL\n") == ("failure", "fail-marker")
    assert classify_log_text("Process exited with code 7\n") == ("failure", "exit-code-7")
    assert classify_log_text("EXIT CODE: 0\n") == ("success", "exit-code-0")


def test_evaluate_backup_alert_detects_two_consecutive_daily_failures(tmp_path):
    log_dir = _copy_fixture_dir(tmp_path, "alert_two_days")

    evaluation = evaluate_backup_alert(log_dir=log_dir)

    assert evaluation.alert is True
    assert evaluation.alert_pair is not None
    first, second = evaluation.alert_pair
    assert first.day.isoformat() == "2026-05-31"
    assert second.day.isoformat() == "2026-06-01"
    assert "ALERT registry backup failed on 2026-05-31 and 2026-06-01" in evaluation.summary
    assert str(log_dir.parent) not in evaluation.summary


def test_evaluate_backup_alert_stays_clear_when_success_breaks_streak(tmp_path):
    log_dir = _copy_fixture_dir(tmp_path, "clear_success_breaks_streak")

    evaluation = evaluate_backup_alert(log_dir=log_dir)

    assert evaluation.alert is False
    assert evaluation.alert_pair is None
    assert "OK registry backup alert clear" in evaluation.summary


def test_evaluate_backup_alert_ignores_malformed_logs_without_status(tmp_path):
    log_dir = _copy_fixture_dir(tmp_path, "malformed_logs_ignored")

    evaluation = evaluate_backup_alert(log_dir=log_dir)

    assert evaluation.alert is False
    assert [run.status for run in evaluation.daily_runs] == ["unknown", "failure", "unknown"]


def test_main_uses_env_override_and_prints_single_line_summary(tmp_path, monkeypatch, capsys):
    log_dir = _copy_fixture_dir(tmp_path, "alert_two_days")
    monkeypatch.setenv("UMBRAL_REGISTRY_BACKUP_LOG_DIR", str(log_dir))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    exit_code = main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    output = captured.out.strip()
    assert "\n" not in output
    assert output.startswith("ALERT registry backup failed on 2026-05-31 and 2026-06-01")
    assert str(log_dir.parent) not in output


def test_missing_log_directory_is_clear_state(tmp_path):
    missing_dir = tmp_path / "missing-logs"

    evaluation = evaluate_backup_alert(log_dir=missing_dir)

    assert evaluation.alert is False
    assert evaluation.summary == "OK registry backup alert clear: no log directory found for missing-logs"
