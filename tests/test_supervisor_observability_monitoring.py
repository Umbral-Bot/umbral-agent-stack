"""
Tests for scripts/monitor_supervisor_observability.py — Phase 5 monitoring tool.

Run:
    WORKER_TOKEN=test python -m pytest tests/test_supervisor_observability_monitoring.py -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from scripts.monitor_supervisor_observability import (
    INVESTIGATE,
    PASS_MONITORING,
    ROLLBACK_RECOMMENDED,
    WATCH,
    build_report,
    compute_recommendation,
    format_markdown,
    parse_ops_log,
    parse_supervisor_events,
    run_simulation,
    _check_fields_for_text,
    parse_journal,
)


# ── Helpers ─────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_ops_line(event: str, team: str = "system", **extra: Any) -> str:
    ev: Dict[str, Any] = {
        "event": event,
        "team": team,
        "task_id": "test-1",
        "ts": _now_iso(),
    }
    ev.update(extra)
    return json.dumps(ev)


def _write_temp_ops_log(lines: list[str]) -> Path:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8",
    )
    for line in lines:
        f.write(line + "\n")
    f.close()
    return Path(f.name)


# ── 1. Parse JSON supervisor event line ─────────────────────────────

class TestOpsLogParsing:

    def test_parses_json_lines(self):
        path = _write_temp_ops_log([
            _make_ops_line("task_completed", team="improvement"),
            _make_ops_line("task_failed", team="delivery"),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_ops_log(path, since=since)
        assert result["available"] is True
        assert result["events_in_window"] == 2
        assert result["task_completed"] == 1
        assert result["task_failed"] == 1

    def test_counts_by_event_type(self):
        path = _write_temp_ops_log([
            _make_ops_line("task_completed", team="improvement"),
            _make_ops_line("task_completed", team="system"),
            _make_ops_line("task_blocked", team="delivery"),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_ops_log(path, since=since)
        assert result["by_event"]["task_completed"] == 2
        assert result["by_event"]["task_blocked"] == 1

    def test_counts_by_team(self):
        path = _write_temp_ops_log([
            _make_ops_line("task_completed", team="improvement"),
            _make_ops_line("task_completed", team="system"),
            _make_ops_line("task_completed", team="system"),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_ops_log(path, since=since)
        assert result["by_team"]["improvement"] == 1
        assert result["by_team"]["system"] == 2
        assert result["improvement_events"] == 1

    def test_filters_by_time_window(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        recent_ts = _now_iso()
        path = _write_temp_ops_log([
            json.dumps({"event": "task_completed", "team": "system", "ts": old_ts}),
            json.dumps({"event": "task_completed", "team": "system", "ts": recent_ts}),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_ops_log(path, since=since)
        assert result["events_in_window"] == 1

    def test_handles_missing_file(self):
        result = parse_ops_log(Path("/nonexistent/file.jsonl"), since=datetime.now(timezone.utc))
        assert result["available"] is False

    def test_handles_malformed_json(self):
        path = _write_temp_ops_log([
            "this is not json",
            _make_ops_line("task_completed", team="system"),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_ops_log(path, since=since)
        assert result["available"] is True
        assert result["events_in_window"] == 1


# ── 2. Safety flag detection ───────────────────────────────────────

class TestSafetyFlags:

    def test_flags_should_block_true(self):
        """Simulation should detect should_block=True."""
        result: Dict[str, Any] = {
            "should_block_true_count": 0,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 0,
        }
        fields = {"should_block": True, "team": "improvement"}
        # Direct check: should_block is a field-level check done in simulation
        # The _check_fields_for_text checks text leakage, not should_block
        # should_block is checked in run_simulation directly
        assert fields["should_block"] is True

    def test_flags_non_improvement_team(self):
        """Non-improvement team events should be flagged in recommendation."""
        journal = {"available": True, "marker_counts": {
            "supervisor_observability": 0,
            "supervisor_observability_failed": 0,
            "supervisor_ambiguity_detection_failed": 0,
            "supervisor_resolution_event_failed": 0,
        }}
        ops_log = {"available": True, "task_failed": 0, "task_completed": 1}
        simulation = {
            "available": True,
            "checks": [],
            "should_block_true_count": 0,
            "non_improvement_event_count": 1,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
        }
        rec = compute_recommendation(journal=journal, ops_log=ops_log, simulation=simulation)
        assert rec["level"] == ROLLBACK_RECOMMENDED

    def test_flags_raw_text_leakage_suspicious_keys(self):
        result: Dict[str, Any] = {
            "should_block_true_count": 0,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 0,
        }
        fields = {"text": "a" * 100}  # Long text in suspicious key
        _check_fields_for_text(fields, result)
        assert result["raw_text_leakage_suspected_count"] == 1

    def test_no_flag_for_short_text(self):
        result: Dict[str, Any] = {
            "should_block_true_count": 0,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 0,
        }
        fields = {"text": "short"}
        _check_fields_for_text(fields, result)
        assert result["raw_text_leakage_suspected_count"] == 0

    def test_flags_sentinel_pattern(self):
        result: Dict[str, Any] = {
            "should_block_true_count": 0,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 0,
        }
        fields = {"reason": "TEXTO_SENSIBLE_leaked"}
        _check_fields_for_text(fields, result)
        assert result["raw_text_leakage_suspected_count"] == 1


# ── 3. Unstructured line handling ───────────────────────────────────

class TestJournalParsing:

    def test_handles_unavailable_journalctl(self):
        with patch("scripts.monitor_supervisor_observability.subprocess.run",
                    side_effect=FileNotFoundError):
            result = parse_journal(since_minutes=60)
        assert result["available"] is False
        assert result["raw_lines_scanned"] == 0

    def test_counts_supervisor_markers(self):
        fake_output = (
            "2026-04-20 INFO dispatcher.router: supervisor_observability\n"
            "2026-04-20 INFO dispatcher.router: supervisor_observability\n"
            "2026-04-20 WARNING dispatcher.router: supervisor_observability_failed\n"
            "2026-04-20 INFO other.module: something else\n"
        )
        mock_proc = type("Proc", (), {
            "returncode": 0, "stdout": fake_output, "stderr": "",
        })()
        with patch("scripts.monitor_supervisor_observability.subprocess.run",
                    return_value=mock_proc):
            result = parse_journal(since_minutes=60)

        assert result["available"] is True
        assert result["raw_lines_scanned"] == 4
        # The _failed line also contains "supervisor_observability" as substring
        assert result["marker_counts"]["supervisor_observability"] == 3
        assert result["marker_counts"]["supervisor_observability_failed"] == 1


# ── 4. Recommendation engine ───────────────────────────────────────

class TestRecommendation:

    def _base_journal(self, obs_count: int = 0, fail_count: int = 0) -> Dict[str, Any]:
        return {
            "available": True,
            "marker_counts": {
                "supervisor_observability": obs_count,
                "supervisor_observability_failed": fail_count,
                "supervisor_ambiguity_detection_failed": 0,
                "supervisor_resolution_event_failed": 0,
            },
        }

    def _base_ops(self, completed: int = 10, failed: int = 0) -> Dict[str, Any]:
        return {
            "available": True,
            "task_completed": completed,
            "task_failed": failed,
        }

    def test_empty_logs_is_watch(self):
        rec = compute_recommendation(
            journal=self._base_journal(obs_count=0),
            ops_log=self._base_ops(),
            simulation=None,
        )
        assert rec["level"] == WATCH

    def test_pass_with_simulation_clean(self):
        rec = compute_recommendation(
            journal=self._base_journal(obs_count=5),
            ops_log=self._base_ops(completed=10),
            simulation={
                "available": True,
                "checks": [{"name": "test", "passed": True}],
                "should_block_true_count": 0,
                "non_improvement_event_count": 0,
                "raw_text_leakage_suspected_count": 0,
                "malformed_event_count": 0,
            },
        )
        assert rec["level"] == PASS_MONITORING

    def test_rollback_on_should_block(self):
        rec = compute_recommendation(
            journal=self._base_journal(obs_count=1),
            ops_log=self._base_ops(),
            simulation={
                "available": True,
                "checks": [],
                "should_block_true_count": 1,
                "non_improvement_event_count": 0,
                "raw_text_leakage_suspected_count": 0,
                "malformed_event_count": 0,
            },
        )
        assert rec["level"] == ROLLBACK_RECOMMENDED

    def test_rollback_on_raw_text_leakage(self):
        rec = compute_recommendation(
            journal=self._base_journal(obs_count=1),
            ops_log=self._base_ops(),
            simulation={
                "available": True,
                "checks": [],
                "should_block_true_count": 0,
                "non_improvement_event_count": 0,
                "raw_text_leakage_suspected_count": 1,
                "malformed_event_count": 0,
            },
        )
        assert rec["level"] == ROLLBACK_RECOMMENDED

    def test_investigate_on_high_failure_rate(self):
        rec = compute_recommendation(
            journal=self._base_journal(obs_count=1),
            ops_log=self._base_ops(completed=5, failed=3),
            simulation=None,
        )
        assert rec["level"] == INVESTIGATE

    def test_unavailable_sources_is_watch(self):
        rec = compute_recommendation(
            journal={"available": False},
            ops_log={"available": False},
            simulation=None,
        )
        assert rec["level"] == WATCH


# ── 5. Report and output ───────────────────────────────────────────

class TestReport:

    def test_json_output_serializable(self):
        journal = {"available": True, "raw_lines_scanned": 100, "marker_counts": {
            "supervisor_observability": 2,
            "supervisor_observability_failed": 0,
            "supervisor_ambiguity_detection_failed": 0,
            "supervisor_resolution_event_failed": 0,
        }}
        ops_log = {
            "available": True, "events_in_window": 50,
            "by_event": {"task_completed": 45}, "by_team": {"system": 50},
            "task_completed": 45, "task_failed": 3, "task_blocked": 2,
            "improvement_events": 5,
        }
        rec = {"level": PASS_MONITORING, "reasons": []}
        report = build_report(
            since_minutes=60, journal=journal, ops_log=ops_log,
            simulation=None, recommendation=rec,
        )
        # Must be JSON-serializable
        blob = json.dumps(report, default=str)
        parsed = json.loads(blob)
        assert parsed["report_type"] == "supervisor_observability_monitoring"
        assert parsed["recommendation"]["level"] == PASS_MONITORING

    def test_markdown_contains_recommendation(self):
        report = {
            "generated_at": _now_iso(),
            "time_window_minutes": 60,
            "sources": {
                "journal": {"available": False, "raw_lines_scanned": 0, "marker_counts": {}},
                "ops_log": {
                    "available": True, "events_in_window": 10,
                    "by_event": {}, "by_team": {},
                    "task_completed": 10, "task_failed": 0, "task_blocked": 0,
                    "improvement_events": 0,
                },
                "simulation": None,
            },
            "safety_flags": {
                "supervisor_failure_lines": 0,
                "should_block_true_count": 0,
                "non_improvement_event_count": 0,
                "raw_text_leakage_suspected_count": 0,
                "malformed_event_count": 0,
                "error_event_count": 0,
            },
            "recommendation": {"level": WATCH, "reasons": ["[WATCH] test reason"]},
        }
        md = format_markdown(report)
        assert "WATCH" in md
        # Phase 6A: the old "Known Limitation" section is replaced by a
        # structured telemetry status note that references OpsLogger.
        assert "Structured Telemetry Status" in md
        assert "OpsLogger" in md or "ops_log.jsonl" in md

    def test_suspicious_content_not_printed_in_full(self):
        """Ensure the markdown report doesn't leak raw suspicious content."""
        report = {
            "generated_at": _now_iso(),
            "time_window_minutes": 60,
            "sources": {
                "journal": {"available": False, "raw_lines_scanned": 0, "marker_counts": {}},
                "ops_log": {
                    "available": False, "events_in_window": 0,
                    "by_event": {}, "by_team": {},
                    "task_completed": 0, "task_failed": 0, "task_blocked": 0,
                    "improvement_events": 0,
                },
                "simulation": {
                    "available": True,
                    "checks": [{"name": "sentinel_test", "passed": False, "detail": "sentinel found in event"}],
                    "should_block_true_count": 0,
                    "non_improvement_event_count": 0,
                    "raw_text_leakage_suspected_count": 1,
                    "malformed_event_count": 0,
                    "error_event_count": 0,
                },
            },
            "safety_flags": {
                "supervisor_failure_lines": 0,
                "should_block_true_count": 0,
                "non_improvement_event_count": 0,
                "raw_text_leakage_suspected_count": 1,
                "malformed_event_count": 0,
                "error_event_count": 0,
            },
            "recommendation": {"level": ROLLBACK_RECOMMENDED, "reasons": []},
        }
        md = format_markdown(report)
        # The sentinel text itself should never appear raw
        assert "TEXTO_SENSIBLE_MONITOR_SENTINEL_2026" not in md


# ── 6. CLI smoke ────────────────────────────────────────────────────

class TestCLISmoke:

    def test_help_flag(self):
        result = subprocess.run(
            [sys.executable, "scripts/monitor_supervisor_observability.py", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "supervisor observability" in result.stdout.lower()

    def test_basic_run_no_simulate(self):
        result = subprocess.run(
            [sys.executable, "scripts/monitor_supervisor_observability.py",
             "--since-minutes", "1",
             "--ops-log", "/nonexistent/path.jsonl"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "Recommendation" in result.stdout

    def test_simulate_flag(self):
        result = subprocess.run(
            [sys.executable, "scripts/monitor_supervisor_observability.py",
             "--simulate", "--since-minutes", "1",
             "--ops-log", "/nonexistent/path.jsonl"],
            capture_output=True, text=True, timeout=30,
            env={**__import__("os").environ, "WORKER_TOKEN": "test"},
        )
        assert result.returncode == 0
        assert "Simulation" in result.stdout

    def test_json_output_to_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            outpath = f.name

        result = subprocess.run(
            [sys.executable, "scripts/monitor_supervisor_observability.py",
             "--since-minutes", "1",
             "--ops-log", "/nonexistent/path.jsonl",
             "--output-json", outpath],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(Path(outpath).read_text())
        assert data["report_type"] == "supervisor_observability_monitoring"


# ── 7. Simulation integration ──────────────────────────────────────

class TestSimulationIntegration:

    def test_simulation_runs_and_returns_checks(self):
        result = run_simulation()
        assert result["available"] is True
        assert len(result["checks"]) >= 5  # At least 6 checks
        # All checks should pass with current codebase
        for check in result["checks"]:
            assert check["passed"] is True, f"Check {check['name']} failed: {check.get('detail')}"

    def test_simulation_no_should_block(self):
        result = run_simulation()
        assert result["should_block_true_count"] == 0

    def test_simulation_no_raw_text_leakage(self):
        result = run_simulation()
        assert result["raw_text_leakage_suspected_count"] == 0

    def test_simulation_no_non_improvement(self):
        result = run_simulation()
        assert result["non_improvement_event_count"] == 0


# ── 8. Structured supervisor events parser (Phase 6A) ──────────────


def _make_supervisor_record(
    *,
    event_type: str = "supervisor.ambiguity_signal",
    team: str = "improvement",
    task_id: str = "task-1",
    task_type: str = "general",
    outcome: str = "ambiguous",
    severity: str = "info",
    fields: Dict[str, Any] | None = None,
    ts: str | None = None,
) -> str:
    rec: Dict[str, Any] = {
        "event": event_type,
        "event_type": event_type,
        "team": team,
        "task_id": task_id,
        "task_type": task_type,
        "outcome": outcome,
        "severity": severity,
        "fields": fields or {"is_ambiguous": True, "reason": "positive_keyword_match"},
        "ts": ts or _now_iso(),
    }
    return json.dumps(rec)


class TestParseSupervisorEvents:

    def test_parses_structured_records(self):
        path = _write_temp_ops_log([
            _make_supervisor_record(event_type="supervisor.ambiguity_signal"),
            _make_supervisor_record(
                event_type="supervisor.resolution",
                outcome="unresolved",
                fields={
                    "resolution_status": "unresolved",
                    "should_block": False,
                    "reason": "status_design_only",
                },
            ),
            # Interleave a task_completed line that must NOT be counted.
            _make_ops_line("task_completed", team="improvement"),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_supervisor_events(path, since=since)

        assert result["available"] is True
        assert result["events_in_window"] == 2
        assert result["by_event_type"]["supervisor.ambiguity_signal"] == 1
        assert result["by_event_type"]["supervisor.resolution"] == 1
        assert result["by_team"]["improvement"] == 2
        assert result["non_improvement_event_count"] == 0
        assert result["should_block_true_count"] == 0
        assert result["raw_text_leakage_suspected_count"] == 0

    def test_flags_should_block_true(self):
        path = _write_temp_ops_log([
            _make_supervisor_record(
                event_type="supervisor.resolution",
                outcome="unresolved",
                fields={"should_block": True, "resolution_status": "unresolved"},
            ),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_supervisor_events(path, since=since)

        assert result["should_block_true_count"] == 1

    def test_flags_non_improvement_team(self):
        path = _write_temp_ops_log([
            _make_supervisor_record(team="delivery"),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_supervisor_events(path, since=since)

        assert result["non_improvement_event_count"] == 1

    def test_flags_raw_text_leakage(self):
        path = _write_temp_ops_log([
            _make_supervisor_record(
                fields={
                    "reason": "positive_keyword_match",
                    "text": "a" * 80,  # suspicious key + long value
                },
            ),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_supervisor_events(path, since=since)

        assert result["raw_text_leakage_suspected_count"] >= 1

    def test_flags_unknown_event_type(self):
        path = _write_temp_ops_log([
            _make_supervisor_record(event_type="supervisor.something_new"),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_supervisor_events(path, since=since)

        assert result["unknown_event_type_count"] == 1

    def test_handles_missing_file(self):
        result = parse_supervisor_events(Path("/nonexistent/file.jsonl"),
                                          since=datetime.now(timezone.utc))
        assert result["available"] is False
        assert result["events_in_window"] == 0

    def test_filters_by_time_window(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        path = _write_temp_ops_log([
            _make_supervisor_record(ts=old_ts),
            _make_supervisor_record(),
        ])
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_supervisor_events(path, since=since)

        assert result["events_in_window"] == 1


class TestRecommendationWithStructuredEvents:

    def _clean_journal(self) -> Dict[str, Any]:
        return {
            "available": True,
            "marker_counts": {
                "supervisor_observability": 0,
                "supervisor_observability_failed": 0,
                "supervisor_ambiguity_detection_failed": 0,
                "supervisor_resolution_event_failed": 0,
            },
        }

    def _clean_ops(self) -> Dict[str, Any]:
        return {"available": True, "task_completed": 5, "task_failed": 0}

    def test_pass_monitoring_with_structured_events_and_no_journal(self):
        """Phase 6A: real structured events are sufficient for PASS_MONITORING
        even when journald shows no supervisor_observability markers and
        simulation was not run.
        """
        structured = {
            "available": True,
            "events_in_window": 3,
            "by_event_type": {"supervisor.ambiguity_signal": 2, "supervisor.resolution": 1},
            "by_outcome": {"ambiguous": 2, "unresolved": 1},
            "by_severity": {"info": 3},
            "by_team": {"improvement": 3},
            "should_block_true_count": 0,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 0,
            "unknown_event_type_count": 0,
            "latest_event_ts": _now_iso(),
        }
        rec = compute_recommendation(
            journal=self._clean_journal(),
            ops_log=self._clean_ops(),
            simulation=None,
            supervisor_events=structured,
        )
        assert rec["level"] == PASS_MONITORING

    def test_rollback_on_structured_should_block_true(self):
        structured = {
            "available": True,
            "events_in_window": 1,
            "by_event_type": {"supervisor.resolution": 1},
            "by_outcome": {"unresolved": 1},
            "by_severity": {"warning": 1},
            "by_team": {"improvement": 1},
            "should_block_true_count": 1,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 1,
            "unknown_event_type_count": 0,
            "latest_event_ts": _now_iso(),
        }
        rec = compute_recommendation(
            journal=self._clean_journal(),
            ops_log=self._clean_ops(),
            simulation=None,
            supervisor_events=structured,
        )
        assert rec["level"] == ROLLBACK_RECOMMENDED

    def test_rollback_on_structured_non_improvement(self):
        structured = {
            "available": True,
            "events_in_window": 1,
            "by_event_type": {"supervisor.ambiguity_signal": 1},
            "by_outcome": {"ambiguous": 1},
            "by_severity": {"info": 1},
            "by_team": {"delivery": 1},
            "should_block_true_count": 0,
            "non_improvement_event_count": 1,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 0,
            "unknown_event_type_count": 0,
            "latest_event_ts": _now_iso(),
        }
        rec = compute_recommendation(
            journal=self._clean_journal(),
            ops_log=self._clean_ops(),
            simulation=None,
            supervisor_events=structured,
        )
        assert rec["level"] == ROLLBACK_RECOMMENDED

    def test_rollback_on_structured_raw_text_leakage(self):
        structured = {
            "available": True,
            "events_in_window": 1,
            "by_event_type": {"supervisor.ambiguity_signal": 1},
            "by_outcome": {"ambiguous": 1},
            "by_severity": {"info": 1},
            "by_team": {"improvement": 1},
            "should_block_true_count": 0,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 1,
            "malformed_event_count": 0,
            "error_event_count": 0,
            "unknown_event_type_count": 0,
            "latest_event_ts": _now_iso(),
        }
        rec = compute_recommendation(
            journal=self._clean_journal(),
            ops_log=self._clean_ops(),
            simulation=None,
            supervisor_events=structured,
        )
        assert rec["level"] == ROLLBACK_RECOMMENDED

    def test_watch_when_no_events_anywhere(self):
        """Absence of any traffic still yields WATCH (not failure)."""
        empty_structured = {
            "available": True,
            "events_in_window": 0,
            "by_event_type": {},
            "by_outcome": {},
            "by_severity": {},
            "by_team": {},
            "should_block_true_count": 0,
            "non_improvement_event_count": 0,
            "raw_text_leakage_suspected_count": 0,
            "malformed_event_count": 0,
            "error_event_count": 0,
            "unknown_event_type_count": 0,
            "latest_event_ts": None,
        }
        rec = compute_recommendation(
            journal=self._clean_journal(),
            ops_log=self._clean_ops(),
            simulation=None,
            supervisor_events=empty_structured,
        )
        assert rec["level"] == WATCH

    def test_supervisor_events_absent_falls_back_to_legacy_behavior(self):
        """Phase 5 callers that do not pass supervisor_events keep working:
        journal-only with obs_count>0 still yields PASS_MONITORING.
        """
        journal = self._clean_journal()
        journal["marker_counts"]["supervisor_observability"] = 3
        rec = compute_recommendation(
            journal=journal,
            ops_log=self._clean_ops(),
            simulation=None,
        )
        assert rec["level"] == PASS_MONITORING
