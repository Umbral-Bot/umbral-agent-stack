"""
Tests for dispatcher/supervisor_observability.py — passive event builders.

All tests are pure — no Redis, no network, no logging, no I/O.
Run with:
    WORKER_TOKEN=test python -m pytest tests/test_supervisor_observability.py -v
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from dispatcher.supervisor_observability import (
    SupervisorObservabilityEvent,
    build_ambiguity_signal_event,
    build_config_validation_event,
    build_supervisor_noop_event,
    build_supervisor_resolution_event,
)
from dispatcher.supervisor_resolution import (
    SupervisorConfigIssue,
    SupervisorResolution,
    load_supervisor_registry,
    resolve_supervisor,
    validate_supervisor_config_consistency,
)
from dispatcher.ambiguity_signal import AmbiguitySignal, detect_ambiguity_signal
from dispatcher.team_config import get_team_capabilities

EXPECTED_TOP_KEYS = {
    "event_type", "team", "task_id", "task_type",
    "outcome", "severity", "fields",
}


# ── Resolution events ────────────────────────────────────────────


class TestResolutionEvents:
    """Events from SupervisorResolution results."""

    def test_real_design_only_resolution(self):
        """Current real case: improvement is design_only."""
        teams_config = {"teams": get_team_capabilities()}
        registry = load_supervisor_registry()
        resolution = resolve_supervisor(
            "improvement", teams_config=teams_config, registry=registry,
        )
        event = build_supervisor_resolution_event(
            resolution, task_id="test-123", task_type="research",
        )
        assert event.event_type == "supervisor.resolution"
        assert event.outcome == "unresolved"
        assert event.severity == "info"
        assert event.team == "improvement"
        assert event.task_id == "test-123"
        assert event.fields["should_block"] is False
        assert event.fields["fallback"] == "direct"
        assert event.fields["reason"] == "status_design_only"

    def test_resolved_synthetic(self):
        """Synthetic resolved case."""
        resolution = SupervisorResolution(
            team="improvement",
            supervisor_label="Mejora Continua Supervisor",
            resolution_status="resolved",
            target_type="openclaw_agent",
            target="improvement-supervisor",
            fallback="direct",
            fallback_used=False,
            should_block=False,
            reason="target_available",
        )
        event = build_supervisor_resolution_event(resolution)
        assert event.outcome == "resolved"
        assert event.severity == "info"
        assert event.fields["target"] == "improvement-supervisor"

    def test_target_unavailable_warning(self):
        """Unavailable target should produce warning severity."""
        resolution = SupervisorResolution(
            team="improvement",
            supervisor_label="S",
            resolution_status="unresolved",
            target_type="openclaw_agent",
            target="improvement-supervisor",
            fallback="direct",
            fallback_used=True,
            should_block=False,
            reason="target_unavailable",
        )
        event = build_supervisor_resolution_event(resolution)
        assert event.outcome == "unresolved"
        assert event.severity == "warning"

    def test_not_ready_warning(self):
        """Not-ready target should produce warning severity."""
        resolution = SupervisorResolution(
            team="improvement",
            supervisor_label="S",
            resolution_status="not_ready",
            target_type="openclaw_agent",
            target="improvement-supervisor",
            fallback="direct",
            fallback_used=True,
            should_block=False,
            reason="target_availability_unknown",
        )
        event = build_supervisor_resolution_event(resolution)
        assert event.outcome == "unresolved"
        assert event.severity == "warning"


# ── Ambiguity signal events ──────────────────────────────────────


class TestAmbiguitySignalEvents:
    """Events from AmbiguitySignal results."""

    def test_ambiguous_signal(self):
        signal = detect_ambiguity_signal(
            "revisa la salud del sistema y dime que deberiamos mejorar",
            team="improvement",
        )
        event = build_ambiguity_signal_event(
            signal, task_id="amb-1", task_type="general",
        )
        assert event.event_type == "supervisor.ambiguity_signal"
        assert event.outcome == "ambiguous"
        assert event.severity == "info"
        assert event.team == "improvement"
        assert len(event.fields.get("matched_terms", ())) > 0

    def test_not_ambiguous_explicit_handler(self):
        signal = detect_ambiguity_signal(
            "ejecuta system.ooda_report",
            team="improvement",
        )
        event = build_ambiguity_signal_event(signal)
        assert event.outcome == "not_ambiguous"
        assert event.severity == "debug"

    def test_not_ambiguous_wrong_team(self):
        signal = detect_ambiguity_signal(
            "revisa la salud del sistema",
            team="marketing",
        )
        event = build_ambiguity_signal_event(signal)
        assert event.outcome == "not_ambiguous"
        assert event.severity == "debug"


# ── Config validation events ─────────────────────────────────────


class TestConfigValidationEvents:
    """Events from config validation results."""

    def test_valid_empty_issues(self):
        event = build_config_validation_event(())
        assert event.event_type == "supervisor.config_validation"
        assert event.outcome == "valid"
        assert event.severity == "info"
        assert event.fields["issue_count"] == 0
        assert event.fields["error_count"] == 0
        assert event.fields["warning_count"] == 0

    def test_warnings_only(self):
        """Real config produces warnings for marketing/advisory."""
        teams_config = {"teams": get_team_capabilities()}
        registry = load_supervisor_registry()
        issues = validate_supervisor_config_consistency(teams_config, registry)
        event = build_config_validation_event(issues)
        assert event.outcome == "warning"
        assert event.severity == "warning"
        assert event.fields["error_count"] == 0
        assert event.fields["warning_count"] >= 2

    def test_errors_present(self):
        error_issue = SupervisorConfigIssue(
            team="fake",
            severity="error",
            code="registry_team_missing_from_teams_config",
            message="test error",
        )
        event = build_config_validation_event([error_issue])
        assert event.outcome == "error"
        assert event.severity == "error"
        assert event.fields["error_count"] == 1
        assert len(event.fields["issues"]) == 1
        assert event.fields["issues"][0]["code"] == "registry_team_missing_from_teams_config"


# ── Noop events ──────────────────────────────────────────────────


class TestNoopEvents:

    def test_noop_event(self):
        event = build_supervisor_noop_event(
            team="improvement",
            reason="runtime_not_wired",
            task_id="noop-1",
        )
        assert event.event_type == "supervisor.noop"
        assert event.outcome == "noop"
        assert event.severity == "debug"
        assert event.fields["reason"] == "runtime_not_wired"
        assert event.team == "improvement"


# ── JSON serialization ───────────────────────────────────────────


class TestSerialization:
    """All events must produce JSON-serializable log records."""

    @pytest.mark.parametrize("builder", [
        lambda: build_supervisor_resolution_event(
            resolve_supervisor(
                "improvement",
                teams_config={"teams": get_team_capabilities()},
                registry=load_supervisor_registry(),
            ),
        ),
        lambda: build_ambiguity_signal_event(
            detect_ambiguity_signal("revisa la salud del sistema", team="improvement"),
        ),
        lambda: build_config_validation_event(()),
        lambda: build_supervisor_noop_event(team="lab", reason="no_supervisor"),
    ])
    def test_json_serializable(self, builder):
        event = builder()
        record = event.to_log_record()
        serialized = json.dumps(record)
        roundtrip = json.loads(serialized)
        assert isinstance(roundtrip, dict)


# ── Stable keys ──────────────────────────────────────────────────


class TestStableKeys:

    @pytest.mark.parametrize("builder", [
        lambda: build_supervisor_resolution_event(
            SupervisorResolution(
                team="t", supervisor_label="S",
                resolution_status="unresolved", reason="test",
            ),
        ),
        lambda: build_ambiguity_signal_event(
            AmbiguitySignal(
                team="t", is_ambiguous=False,
                candidate_for_supervisor_review=False,
                reason="test", signal_type="none",
                confidence=0.0, matched_terms=(),
            ),
        ),
        lambda: build_config_validation_event([]),
        lambda: build_supervisor_noop_event(team="t", reason="test"),
    ])
    def test_top_level_keys(self, builder):
        record = builder().to_log_record()
        assert set(record.keys()) == EXPECTED_TOP_KEYS


# ── No raw text leakage ─────────────────────────────────────────


class TestNoTextLeakage:

    def test_resolution_event_no_raw_text(self):
        resolution = SupervisorResolution(
            team="improvement", supervisor_label="S",
            resolution_status="unresolved", reason="test",
        )
        event = build_supervisor_resolution_event(
            resolution, task_id="t1", task_type="general",
        )
        serialized = json.dumps(event.to_log_record())
        # No raw task input text should appear
        assert "revisa la salud" not in serialized
        assert "original_request" not in serialized

    def test_ambiguity_event_no_raw_text(self):
        text = "revisa la salud del sistema y dime que deberiamos mejorar"
        signal = detect_ambiguity_signal(text, team="improvement")
        event = build_ambiguity_signal_event(signal, task_id="t2")
        serialized = json.dumps(event.to_log_record())
        assert text not in serialized


# ── Purity / determinism ────────────────────────────────────────


class TestPurity:

    def test_deterministic_resolution_event(self):
        resolution = SupervisorResolution(
            team="improvement", supervisor_label="S",
            resolution_status="unresolved", reason="status_design_only",
        )
        r1 = build_supervisor_resolution_event(resolution).to_log_record()
        r2 = build_supervisor_resolution_event(resolution).to_log_record()
        assert r1 == r2

    def test_deterministic_ambiguity_event(self):
        signal = detect_ambiguity_signal(
            "prioriza el backlog de mejora continua",
            team="improvement",
        )
        r1 = build_ambiguity_signal_event(signal).to_log_record()
        r2 = build_ambiguity_signal_event(signal).to_log_record()
        assert r1 == r2


# ── Import safety ────────────────────────────────────────────────


class TestImportSafety:

    _FORBIDDEN_IMPORTS = [
        "dispatcher.router",
        "dispatcher.service",
        "worker",
        "client",
        "redis",
        "openclaw",
        "requests",
        "httpx",
        "logging",
        "os",
    ]

    def test_no_forbidden_imports(self):
        source_path = (
            Path(__file__).resolve().parent.parent
            / "dispatcher"
            / "supervisor_observability.py"
        )
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.append(node.module)

        for forbidden in self._FORBIDDEN_IMPORTS:
            for imported in imported_names:
                assert not imported.startswith(forbidden), (
                    f"supervisor_observability.py imports '{imported}' "
                    f"which is forbidden (matches '{forbidden}')"
                )


# ── Runtime invariance ───────────────────────────────────────────


class TestRuntimeInvariance:

    @pytest.mark.parametrize("relative_path", [
        "dispatcher/service.py",
        "dispatcher/intent_classifier.py",
    ])
    def test_runtime_files_do_not_import_supervisor_observability(self, relative_path):
        """Phase 5 invariance: service worker loop and intent classifier must
        not consume ``supervisor_observability``. ``dispatcher/router.py`` is
        the designated integration point for the non-blocking observability
        wiring slice and is validated by
        ``tests/test_supervisor_runtime_observability_wiring.py``.
        """
        root = Path(__file__).resolve().parent.parent
        source = (root / relative_path).read_text(encoding="utf-8")
        assert "supervisor_observability" not in source


# ── Existing modules unchanged ───────────────────────────────────


class TestExistingUnchanged:

    def test_resolver_still_design_only(self):
        teams_config = {"teams": get_team_capabilities()}
        registry = load_supervisor_registry()
        resolution = resolve_supervisor(
            "improvement", teams_config=teams_config, registry=registry,
        )
        assert resolution.resolution_status == "unresolved"
        assert resolution.reason == "status_design_only"
        assert resolution.should_block is False

    def test_ambiguity_still_detects_positive(self):
        signal = detect_ambiguity_signal(
            "revisa la salud del sistema",
            team="improvement",
        )
        assert signal.is_ambiguous is True

    def test_ambiguity_still_detects_negative(self):
        signal = detect_ambiguity_signal(
            "ejecuta system.ooda_report",
            team="improvement",
        )
        assert signal.is_ambiguous is False
