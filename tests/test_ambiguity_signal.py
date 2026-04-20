"""
Tests for dispatcher/ambiguity_signal.py — passive ambiguity detection.

All tests are pure — no Redis, no network, no mocks, no I/O.
Run with:
    WORKER_TOKEN=test python -m pytest tests/test_ambiguity_signal.py -v
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from dispatcher.ambiguity_signal import AmbiguitySignal, detect_ambiguity_signal


# ── Positive cases (docs/72 §6 #1–#5, #12) ─────────────────────


class TestPositiveSignals:
    """Tasks that should be flagged as ambiguous for improvement team."""

    def test_open_ended_health_review(self):
        """docs/72 §6 #1: open-ended health review."""
        result = detect_ambiguity_signal(
            "revisa la salud del sistema y dime que deberiamos mejorar",
            team="improvement",
        )
        assert result.is_ambiguous is True
        assert result.candidate_for_supervisor_review is True
        assert result.team == "improvement"
        assert result.fallback == "direct"
        assert len(result.matched_terms) > 0

    def test_prioritization_request(self):
        """docs/72 §6 #2: prioritization request."""
        result = detect_ambiguity_signal(
            "prioriza el backlog de mejora continua y dime que sigue",
            team="improvement",
        )
        assert result.is_ambiguous is True
        assert result.candidate_for_supervisor_review is True

    def test_drift_diagnostic(self):
        """docs/72 §6 #3: drift diagnostic."""
        result = detect_ambiguity_signal(
            "detecta drift operativo en el stack y oportunidades de mejora",
            team="improvement",
        )
        assert result.is_ambiguous is True
        assert result.candidate_for_supervisor_review is True

    def test_backlog_review(self):
        """docs/72 §6 #4: backlog review."""
        result = detect_ambiguity_signal(
            "revisa los issues pendientes de Mejora Continua Agent Stack",
            team="improvement",
        )
        assert result.is_ambiguous is True
        assert result.candidate_for_supervisor_review is True

    def test_friction_signal(self):
        """docs/72 §6 #5: friction signal."""
        result = detect_ambiguity_signal(
            "hay friccion en los handoffs, diagnostica donde se esta trabando",
            team="improvement",
        )
        assert result.is_ambiguous is True
        assert result.candidate_for_supervisor_review is True

    def test_process_ooda_improvement_without_handler(self):
        """docs/72 §6 #12: borderline → yes when no explicit handler."""
        result = detect_ambiguity_signal(
            "revisa el proceso OODA de mejora continua y define que sigue",
            team="improvement",
        )
        assert result.is_ambiguous is True
        assert result.candidate_for_supervisor_review is True


# ── Negative cases (docs/72 §4, §6 #6–#11) ─────────────────────


class TestNegativeSignals:
    """Tasks that must NOT be flagged as ambiguous."""

    def test_explicit_ooda_handler_via_task(self):
        """docs/72 §6 #6: explicit handler in task field."""
        result = detect_ambiguity_signal(
            "ejecuta el reporte ooda",
            team="improvement",
            task="system.ooda_report",
        )
        assert result.is_ambiguous is False
        assert result.candidate_for_supervisor_review is False
        assert "handler" in result.reason

    def test_explicit_ooda_handler_in_text(self):
        """docs/72 §6 #6: explicit handler named in text."""
        result = detect_ambiguity_signal(
            "ejecuta system.ooda_report",
            team="improvement",
        )
        assert result.is_ambiguous is False

    def test_explicit_self_eval_handler_via_task(self):
        """docs/72 §6 #7: explicit self_eval handler."""
        result = detect_ambiguity_signal(
            "ejecuta self-eval",
            team="improvement",
            task="system.self_eval",
        )
        assert result.is_ambiguous is False

    def test_explicit_self_eval_in_text(self):
        """docs/72 §6 #7: self_eval mentioned in text."""
        result = detect_ambiguity_signal(
            "ejecuta system.self_eval y dame los resultados",
            team="improvement",
        )
        assert result.is_ambiguous is False

    def test_ping_handler(self):
        """docs/72 §6 #10: ping is always direct."""
        result = detect_ambiguity_signal(
            "ping",
            team="improvement",
            task="ping",
        )
        assert result.is_ambiguous is False

    def test_non_improvement_team(self):
        """docs/72 §4: supervisor only coordinates its own team."""
        result = detect_ambiguity_signal(
            "revisa la salud del sistema y dime que deberiamos mejorar",
            team="delivery",
        )
        assert result.is_ambiguous is False
        assert result.reason == "non_improvement_team"

    def test_non_improvement_team_marketing(self):
        """Non-improvement teams never trigger ambiguity."""
        result = detect_ambiguity_signal(
            "prioriza el backlog",
            team="marketing",
        )
        assert result.is_ambiguous is False

    def test_specific_file_fix(self):
        """docs/72 §6 #8: specific file → concrete scope."""
        result = detect_ambiguity_signal(
            "refactoriza dispatcher/router.py para cambiar TeamRouter.dispatch",
            team="improvement",
        )
        assert result.is_ambiguous is False
        assert "file" in result.reason

    def test_agent_governance(self):
        """docs/72 §6 #11: agent governance is not improvement supervisor scope."""
        result = detect_ambiguity_signal(
            "haz agent-governance y revisa roles del ecosistema de agentes",
            team="improvement",
        )
        assert result.is_ambiguous is False
        assert "governance" in result.reason


# ── Edge cases / safety ──────────────────────────────────────────


class TestSafetyEdgeCases:
    """Empty, None, and edge-case inputs must fail safe."""

    def test_empty_string(self):
        result = detect_ambiguity_signal("", team="improvement")
        assert result.is_ambiguous is False
        assert result.fallback == "direct"

    def test_none_team(self):
        result = detect_ambiguity_signal(
            "revisa la salud del sistema",
            team=None,
        )
        assert result.is_ambiguous is False
        assert result.reason == "non_improvement_team"

    def test_none_text(self):
        # text=None should be handled gracefully
        result = detect_ambiguity_signal(
            None,  # type: ignore[arg-type]
            team="improvement",
        )
        assert result.is_ambiguous is False
        assert result.reason == "empty_input"

    def test_missing_task(self):
        result = detect_ambiguity_signal(
            "",
            team="improvement",
            task=None,
        )
        assert result.is_ambiguous is False
        assert result.fallback == "direct"

    def test_whitespace_only(self):
        result = detect_ambiguity_signal(
            "   \n\t  ",
            team="improvement",
        )
        assert result.is_ambiguous is False


# ── Observability / log fields ───────────────────────────────────


class TestLogFields:
    """to_log_fields must return stable, JSON-serializable dict."""

    def test_log_fields_keys(self):
        result = detect_ambiguity_signal(
            "revisa la salud del sistema",
            team="improvement",
        )
        fields = result.to_log_fields()
        expected_keys = {
            "team", "is_ambiguous", "candidate_for_supervisor_review",
            "reason", "signal_type", "confidence", "matched_terms", "fallback",
        }
        assert set(fields.keys()) == expected_keys

    def test_log_fields_json_serializable(self):
        result = detect_ambiguity_signal(
            "prioriza el backlog de mejora continua",
            team="improvement",
        )
        fields = result.to_log_fields()
        serialized = json.dumps(fields)
        assert isinstance(serialized, str)
        roundtrip = json.loads(serialized)
        assert roundtrip["team"] == "improvement"
        assert roundtrip["is_ambiguous"] is True

    def test_log_fields_negative_case_serializable(self):
        result = detect_ambiguity_signal("ping", team="system", task="ping")
        fields = result.to_log_fields()
        serialized = json.dumps(fields)
        roundtrip = json.loads(serialized)
        assert roundtrip["is_ambiguous"] is False


# ── Purity / determinism ────────────────────────────────────────


class TestPurity:
    """Same inputs must always produce identical outputs."""

    def test_deterministic_positive(self):
        args = dict(text="revisa la salud del sistema", team="improvement")
        r1 = detect_ambiguity_signal(**args)
        r2 = detect_ambiguity_signal(**args)
        r3 = detect_ambiguity_signal(**args)
        assert r1 == r2 == r3

    def test_deterministic_negative(self):
        args = dict(text="refactoriza dispatcher/router.py", team="improvement")
        r1 = detect_ambiguity_signal(**args)
        r2 = detect_ambiguity_signal(**args)
        assert r1 == r2
        assert r1.is_ambiguous is False


# ── Import safety ────────────────────────────────────────────────


class TestImportSafety:
    """The ambiguity signal module must not import runtime dependencies."""

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

    def test_no_forbidden_imports_in_source(self):
        source_path = Path(__file__).resolve().parent.parent / "dispatcher" / "ambiguity_signal.py"
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
                    f"ambiguity_signal.py imports '{imported}' which is forbidden "
                    f"(matches '{forbidden}')"
                )


# ── Runtime invariance ───────────────────────────────────────────


class TestRuntimeInvariance:
    """Service worker loop and intent classifier must not consume the
    ambiguity_signal detector. ``dispatcher/router.py`` is the designated
    integration point for the observability-only wiring slice and is
    validated by ``tests/test_supervisor_runtime_observability_wiring.py``.
    """

    @pytest.mark.parametrize(
        "relative_path",
        [
            "dispatcher/service.py",
            "dispatcher/intent_classifier.py",
        ],
    )
    def test_runtime_files_do_not_import_ambiguity_signal(self, relative_path):
        root = Path(__file__).resolve().parent.parent
        source = (root / relative_path).read_text(encoding="utf-8")
        assert "ambiguity_signal" not in source, (
            f"{relative_path} imports ambiguity_signal — this module must remain "
            f"passive for non-router runtime code"
        )
