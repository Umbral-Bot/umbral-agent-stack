"""
Tests for auth_lifecycle_check.py CLI and OpsLogger.auth_lifecycle_check.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from infra.ops_logger import OpsLogger


NOW = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ops_logger(tmp_path):
    return OpsLogger(log_dir=tmp_path)


# ---------------------------------------------------------------------------
# OpsLogger.auth_lifecycle_check
# ---------------------------------------------------------------------------


class TestOpsLoggerAuthLifecycleCheck:
    def test_writes_event_with_correct_fields(self, ops_logger):
        ops_logger.auth_lifecycle_check(
            provider="linkedin",
            credential_ref="linkedin_company_access_token",
            status="warning",
            expires_at="2026-05-05T00:00:00Z",
            days_until_expiry=14,
            warning_days=14,
            critical_days=5,
            reauth_required=False,
            source="health_check",
            source_kind="cron",
        )
        events = ops_logger.read_events(event_filter="auth_lifecycle_check")
        assert len(events) == 1
        ev = events[0]
        assert ev["event"] == "auth_lifecycle_check"
        assert ev["provider"] == "linkedin"
        assert ev["credential_ref"] == "linkedin_company_access_token"
        assert ev["status"] == "warning"
        assert ev["days_until_expiry"] == 14
        assert ev["warning_days"] == 14
        assert ev["reauth_required"] is False
        assert ev["source"] == "health_check"
        assert "ts" in ev

    def test_strips_sensitive_extra_fields(self, ops_logger):
        ops_logger.auth_lifecycle_check(
            provider="ghost",
            credential_ref="ghost_admin_api_key",
            status="unknown",
            token="SHOULD_NOT_APPEAR",
            secret="ALSO_HIDDEN",
            api_key="NOPE",
            password="NO",
        )
        events = ops_logger.read_events(event_filter="auth_lifecycle_check")
        assert len(events) == 1
        ev = events[0]
        assert "token" not in ev
        assert "secret" not in ev
        assert "api_key" not in ev
        assert "password" not in ev
        assert ev["credential_ref"] == "ghost_admin_api_key"

    def test_details_truncated(self, ops_logger):
        ops_logger.auth_lifecycle_check(
            provider="test",
            credential_ref="test_ref",
            status="ok",
            details="x" * 500,
        )
        events = ops_logger.read_events(event_filter="auth_lifecycle_check")
        assert len(events) == 1
        assert len(events[0]["details"]) == 300

    def test_optional_fields_omitted_when_none(self, ops_logger):
        ops_logger.auth_lifecycle_check(
            provider="test",
            credential_ref="test_ref",
            status="unknown",
        )
        events = ops_logger.read_events(event_filter="auth_lifecycle_check")
        ev = events[0]
        assert "expires_at" not in ev
        assert "days_until_expiry" not in ev
        assert "source" not in ev
        assert "trace_id" not in ev

    def test_compatible_with_read_events_filter(self, ops_logger):
        ops_logger.task_completed("t1", "ping", "system", "none", 10.0)
        ops_logger.auth_lifecycle_check(
            provider="linkedin",
            credential_ref="test",
            status="ok",
        )
        all_events = ops_logger.read_events()
        assert len(all_events) == 2
        auth_events = ops_logger.read_events(event_filter="auth_lifecycle_check")
        assert len(auth_events) == 1
        assert auth_events[0]["event"] == "auth_lifecycle_check"


# ---------------------------------------------------------------------------
# CLI script tests
# ---------------------------------------------------------------------------

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
class TestAuthLifecycleCheckScript:
    def _write_config(self, tmp_path: Path, credentials: list) -> Path:
        import yaml
        config_path = tmp_path / "auth_lifecycle.yaml"
        config_path.write_text(
            yaml.dump({"credentials": credentials}),
            encoding="utf-8",
        )
        return config_path

    def test_dry_run_no_log_written(self, tmp_path):
        from scripts.auth_lifecycle_check import evaluate_credentials, load_config

        config_path = self._write_config(tmp_path, [
            {
                "provider": "linkedin",
                "credential_ref": "test_token",
                "expires_at": (NOW + timedelta(days=30)).isoformat(),
                "warning_days": 14,
                "critical_days": 3,
            },
        ])
        creds = load_config(config_path)
        results = evaluate_credentials(creds, now=NOW)
        assert len(results) == 1
        assert results[0]["status"] == "ok"
        assert results[0]["days_until_expiry"] == 30

    def test_write_mode_creates_events(self, tmp_path):
        from scripts.auth_lifecycle_check import evaluate_credentials, load_config

        config_path = self._write_config(tmp_path, [
            {
                "provider": "ghost",
                "credential_ref": "ghost_admin_api_key",
                "warning_days": 90,
                "critical_days": 30,
            },
            {
                "provider": "linkedin",
                "credential_ref": "linkedin_access_token",
                "expires_at": (NOW + timedelta(days=5)).isoformat(),
                "warning_days": 14,
                "critical_days": 3,
            },
        ])
        creds = load_config(config_path)
        results = evaluate_credentials(creds, now=NOW)
        assert len(results) == 2

        ops = OpsLogger(log_dir=tmp_path)
        for record in results:
            ops.auth_lifecycle_check(**record)

        events = ops.read_events(event_filter="auth_lifecycle_check")
        assert len(events) == 2
        statuses = {ev["credential_ref"]: ev["status"] for ev in events}
        assert statuses["ghost_admin_api_key"] == "unknown"
        assert statuses["linkedin_access_token"] == "warning"

    def test_missing_config_returns_error(self):
        from scripts.auth_lifecycle_check import main
        ret = main(["--config", "/nonexistent/path.yaml"])
        assert ret == 1

    def test_main_dry_run_succeeds(self, tmp_path):
        from scripts.auth_lifecycle_check import main

        config_path = self._write_config(tmp_path, [
            {
                "provider": "test",
                "credential_ref": "test_ref",
                "warning_days": 14,
                "critical_days": 3,
            },
        ])
        ret = main(["--config", str(config_path)])
        assert ret == 0

    def test_main_json_output(self, tmp_path, capsys):
        from scripts.auth_lifecycle_check import main

        config_path = self._write_config(tmp_path, [
            {
                "provider": "test",
                "credential_ref": "test_ref",
                "expires_at": (NOW + timedelta(days=60)).isoformat(),
            },
        ])
        ret = main(["--config", str(config_path), "--json"])
        assert ret == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["status"] == "ok"
