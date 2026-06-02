from pathlib import Path

from scripts.registry import registry_backup_alert as alert


FIXTURES = Path(__file__).parent / "fixtures" / "registry_backup_logs"


def test_alerts_on_two_consecutive_daily_failures(capsys):
    log_dir = FIXTURES / "two_failures"

    rc = alert.main(["--log-dir", str(log_dir)])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out.startswith("ALERT registry_backup consecutive_failures=2")
    assert "latest_day=2026-06-02" in captured.out
    assert "previous_day=2026-06-01" in captured.out
    assert "\n" == captured.out[-1:]
    assert captured.out.count("\n") == 1
    assert "git push failed" not in captured.out


def test_success_on_latest_day_breaks_failure_streak(capsys):
    log_dir = FIXTURES / "success_breaks"

    rc = alert.main(["--log-dir", str(log_dir)])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.startswith("OK registry_backup")
    assert "reason=no_consecutive_failure_pair" in captured.out


def test_latest_run_per_day_is_used():
    runs = alert.load_runs(FIXTURES / "latest_run_per_day")

    result = alert.evaluate_backup_health(runs)

    assert result["alert"] is False
    assert result["latest_day"] == "2026-06-02"
    assert result["latest_status"] == "success"
    assert result["previous_status"] == "failure"


def test_explicit_nonzero_exit_code_counts_as_failure():
    runs = alert.load_runs(FIXTURES / "exit_code_failures")

    result = alert.evaluate_backup_health(runs)

    assert result["alert"] is True
    assert result["reason"] == "two_consecutive_failures"


def test_missing_log_dir_is_not_an_alert(tmp_path, capsys):
    missing = tmp_path / "does-not-exist"

    rc = alert.main(["--log-dir", str(missing)])

    captured = capsys.readouterr()
    assert rc == 0
    assert "reason=insufficient_daily_logs" in captured.out


def test_env_override_selects_log_dir(monkeypatch):
    log_dir = FIXTURES / "two_failures"
    monkeypatch.setenv(alert.ENV_LOG_DIR, str(log_dir))

    assert alert.default_log_dir() == log_dir
