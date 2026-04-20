"""
Tests for supervisor config consistency validation.

Validates that config/teams.yaml and config/supervisors.yaml stay aligned:
label matches, team existence, valid enum values, active-requires-target.
All tests are pure — no Redis, no network, no I/O beyond reading config files.

Run with:
    WORKER_TOKEN=test python -m pytest tests/test_supervisor_config_consistency.py -v
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dispatcher.supervisor_resolution import (
    SupervisorConfigIssue,
    load_supervisor_registry,
    resolve_supervisor,
    validate_supervisor_config_consistency,
)
from dispatcher.team_config import get_team_capabilities


# ── Helpers ──────────────────────────────────────────────────────


def _issue_codes(issues: tuple[SupervisorConfigIssue, ...]) -> list[str]:
    return [i.code for i in issues]


def _errors(issues: tuple[SupervisorConfigIssue, ...]) -> list[SupervisorConfigIssue]:
    return [i for i in issues if i.severity == "error"]


def _warnings(issues: tuple[SupervisorConfigIssue, ...]) -> list[SupervisorConfigIssue]:
    return [i for i in issues if i.severity == "warning"]


# ── Real config validation ───────────────────────────────────────


class TestRealConfig:
    """Validate the real config files produce zero errors."""

    def test_real_config_has_zero_errors(self):
        teams_config = {"teams": get_team_capabilities()}
        registry = load_supervisor_registry()
        issues = validate_supervisor_config_consistency(teams_config, registry)

        errors = _errors(issues)
        assert errors == [], f"Real config has errors: {errors}"

        # improvement label must match
        warnings = _warnings(issues)
        warning_teams = [w.team for w in warnings]
        # marketing and advisory have supervisors in teams.yaml but no registry entry
        # this is expected as warnings, not errors
        for w in warnings:
            assert w.code == "team_supervisor_missing_registry_entry"

        # improvement must NOT be in warnings (it has a registry entry)
        assert "improvement" not in warning_teams


# ── Drift detection ──────────────────────────────────────────────


class TestDriftDetection:
    """Synthetic cases for drift between teams.yaml and supervisors.yaml."""

    def test_unknown_registry_team(self):
        teams_config = {"teams": {"improvement": {"supervisor": "S"}}}
        registry = {"supervisors": {
            "improvement": {"label": "S", "type": "none", "status": "design_only", "fallback": "direct"},
            "unknown_team": {"label": "X", "type": "none", "status": "disabled", "fallback": "direct"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert "registry_team_missing_from_teams_config" in _issue_codes(issues)
        assert any(i.team == "unknown_team" for i in issues)

    def test_label_mismatch(self):
        teams_config = {"teams": {"improvement": {"supervisor": "Mejora Continua Supervisor"}}}
        registry = {"supervisors": {
            "improvement": {"label": "Wrong Label", "type": "openclaw_agent", "status": "design_only", "fallback": "direct"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert "supervisor_label_mismatch" in _issue_codes(issues)

    def test_team_supervisor_missing_registry_entry(self):
        teams_config = {"teams": {
            "improvement": {"supervisor": "Mejora Continua Supervisor"},
            "marketing": {"supervisor": "Marketing Supervisor"},
        }}
        registry = {"supervisors": {}}  # empty registry
        issues = validate_supervisor_config_consistency(teams_config, registry)

        codes = _issue_codes(issues)
        assert "team_supervisor_missing_registry_entry" in codes
        # must be warnings, not errors
        assert len(_errors(issues)) == 0
        assert len(_warnings(issues)) == 2

    def test_invalid_status(self):
        teams_config = {"teams": {"improvement": {"supervisor": "S"}}}
        registry = {"supervisors": {
            "improvement": {"label": "S", "type": "none", "status": "enabled", "fallback": "direct"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert "invalid_supervisor_status" in _issue_codes(issues)

    def test_invalid_type(self):
        teams_config = {"teams": {"improvement": {"supervisor": "S"}}}
        registry = {"supervisors": {
            "improvement": {"label": "S", "type": "agent", "status": "design_only", "fallback": "direct"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert "invalid_supervisor_type" in _issue_codes(issues)

    def test_invalid_fallback_rejects_orchestrator(self):
        """Fallback 'orchestrator' must be rejected — safety rule: no fallback to orchestrator."""
        teams_config = {"teams": {"improvement": {"supervisor": "S"}}}
        registry = {"supervisors": {
            "improvement": {"label": "S", "type": "none", "status": "design_only", "fallback": "orchestrator"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert "invalid_supervisor_fallback" in _issue_codes(issues)

    def test_active_missing_target(self):
        teams_config = {"teams": {"improvement": {"supervisor": "S"}}}
        registry = {"supervisors": {
            "improvement": {"label": "S", "type": "openclaw_agent", "status": "active", "fallback": "direct"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert "active_supervisor_missing_target" in _issue_codes(issues)

    def test_design_only_with_target_accepted(self):
        teams_config = {"teams": {"improvement": {"supervisor": "S"}}}
        registry = {"supervisors": {
            "improvement": {
                "label": "S", "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "design_only", "fallback": "direct",
            },
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert len(_errors(issues)) == 0

    def test_disabled_without_target_accepted(self):
        teams_config = {"teams": {"lab": {"supervisor": None}}}
        registry = {"supervisors": {
            "lab": {"label": None, "type": "none", "status": "disabled", "fallback": "direct"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert len(_errors(issues)) == 0

    def test_manual_owner_and_none_variants_accepted(self):
        teams_config = {"teams": {
            "team_a": {"supervisor": "A"},
            "team_b": {"supervisor": "B"},
        }}
        registry = {"supervisors": {
            "team_a": {"label": "A", "type": "manual_owner", "target": "david", "status": "design_only", "fallback": "manual"},
            "team_b": {"label": "B", "type": "none", "status": "disabled", "fallback": "disabled"},
        }}
        issues = validate_supervisor_config_consistency(teams_config, registry)
        assert len(_errors(issues)) == 0


# ── Purity and import safety ────────────────────────────────────


class TestPurityAndImports:
    """The module must remain pure and not import runtime dependencies."""

    _FORBIDDEN_IMPORTS = [
        "dispatcher.router",
        "dispatcher.service",
        "worker",
        "client",
        "redis",
        "openclaw",
        "requests",
        "httpx",
    ]

    def test_no_forbidden_imports_in_supervisor_resolution(self):
        source_path = Path(__file__).resolve().parent.parent / "dispatcher" / "supervisor_resolution.py"
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
                    f"supervisor_resolution.py imports '{imported}' which is forbidden "
                    f"(matches '{forbidden}')"
                )

    @pytest.mark.parametrize(
        "relative_path",
        [
            "dispatcher/service.py",
            "dispatcher/intent_classifier.py",
        ],
    )
    def test_runtime_files_do_not_import_supervisor_resolution(self, relative_path):
        """Phase 5 invariance: service worker loop and intent classifier must
        not consume the supervisor resolver or the config validator.
        ``dispatcher/router.py`` is the designated integration point for the
        observability-only wiring slice and is validated by
        ``tests/test_supervisor_runtime_observability_wiring.py``. The
        consistency validator itself remains passive — it is not called from
        runtime, only from operational tooling and tests.
        """
        root = Path(__file__).resolve().parent.parent
        source = (root / relative_path).read_text(encoding="utf-8")
        assert "supervisor_resolution" not in source
        assert "validate_supervisor_config" not in source


# ── Resolver unchanged ───────────────────────────────────────────


class TestResolverUnchanged:
    """Adding validation must not change existing resolver behavior."""

    def test_improvement_still_resolves_design_only(self):
        teams_config = {"teams": get_team_capabilities()}
        registry = load_supervisor_registry()
        resolution = resolve_supervisor(
            "improvement", teams_config=teams_config, registry=registry,
        )
        assert resolution.resolution_status == "unresolved"
        assert resolution.reason == "status_design_only"
        assert resolution.fallback == "direct"
        assert resolution.should_block is False
