"""
Tests for _escalate_failure_to_linear in dispatcher/service.py.

Verifies that failed tasks are correctly escalated to Linear with
proper priority mapping, and that guard conditions prevent duplicate
or recursive issue creation.

Run: python -m pytest tests/test_dispatcher_escalation.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import unittest

import dispatcher.service as service
from dispatcher.service import _escalate_failure_to_linear
from tests.conftest import worker_run_envelope
from worker.sanitize import sanitize_input


@pytest.fixture
def mock_wc():
    """WorkerClient mock."""
    wc = MagicMock()
    wc.base_url = "http://worker.test:8088"
    wc.run = MagicMock(
        return_value={
            "ok": True,
            "result": {
                "ok": True,
                "issue": {"id": "issue-42", "identifier": "UMB-42"},
            },
        }
    )
    return wc


def _make_envelope(**overrides) -> dict:
    """Build a minimal envelope for testing."""
    base = {
        "task_id": "abc12345-6789-0000-0000-000000000000",
        "task": "llm.generate",
        "team": "system",
        "task_type": "coding",
        "trace_id": "trace-123",
        "source": "openclaw_gateway",
        "source_kind": "tool_enqueue",
        "input": {},
    }
    base.update(overrides)
    return base


# ── Core: creates issue with correct data ──────────────────────


class TestEscalateCreatesIssue:

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_creates_linear_issue_on_failure(self, mock_wc):
        """_escalate_failure_to_linear creates a Linear issue with correct fields."""
        envelope = _make_envelope(task_type="coding")
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="abc12345-dead-beef",
            task="llm.generate",
            team="system",
            error="TimeoutError: model took too long",
        )

        mock_wc.run.assert_called_once()
        args = mock_wc.run.call_args
        assert args[0][0] == "linear.publish_agent_stack_followup"

        payload = args[0][1]
        assert "Task fallida" in payload["title"]
        assert "abc12345" not in payload["title"]
        assert "llm.generate" in payload["summary"]
        assert "TimeoutError" in payload["evidence"]
        assert payload["kind"] == "operational_debt"
        assert payload["priority"] == 2  # coding → 2
        assert payload["source_ref"] == "openclaw_gateway / tool_enqueue"
        assert payload["auto_generated"] is True
        assert payload["dedupe_key"]
        assert payload["dedupe_window_hours"] == 24
        assert "worker_endpoint=http://worker.test:8088" in payload["evidence"]
        assert "error_class=timeout" in payload["evidence"]

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_error_truncated_to_500_chars(self, mock_wc):
        """Long error messages are truncated in the description."""
        long_error = "x" * 1000
        envelope = _make_envelope()
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="trunc-test",
            task="llm.generate",
            team="system",
            error=long_error,
        )
        payload = mock_wc.run.call_args[0][1]
        assert long_error[:500] in payload["evidence"]
        assert long_error[:501] not in payload["evidence"]

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_includes_selected_model_and_retry_context(self, mock_wc):
        envelope = _make_envelope(
            selected_model="gpt-4o-mini",
            retry_count=2,
        )
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="ctx-test",
            task="llm.generate",
            team="system",
            error="ConnectError: connection refused",
        )

        payload = mock_wc.run.call_args[0][1]
        assert "selected_model=gpt-4o-mini" in payload["evidence"]
        assert "retry_count=2" in payload["evidence"]
        assert payload["selected_model"] == "gpt-4o-mini"
        assert payload["retry_count"] == 2
        assert payload["error_class"] == "connect_error"

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_http_400_followup_payload_is_sanitize_safe(self, mock_wc):
        envelope = _make_envelope(task="diagnostic.synthetic_fail_v3", task_type="general")
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="smoke-test",
            task="diagnostic.synthetic_fail_v3",
            team="system",
            error=(
                "Client error '400 Bad Request' for url 'http://127.0.0.1:8088/run'\n"
                "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400"
            ),
        )

        payload = mock_wc.run.call_args[0][1]
        assert payload["error_class"] == "http_400"
        assert "`system`" not in payload["summary"]
        assert "`http_400`" not in payload["summary"]
        sanitize_input(payload)


# ── Guard: no duplicate if linear_issue_id exists ──────────────


class TestEscalateGuardConditions:

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_no_issue_if_linear_issue_id_present(self, mock_wc):
        """Skip if envelope already has a linear_issue_id (avoid duplicates)."""
        envelope = _make_envelope(linear_issue_id="LIN-99")
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="dup-test",
            task="llm.generate",
            team="system",
            error="some error",
        )
        mock_wc.run.assert_not_called()

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_no_issue_for_linear_tasks(self, mock_wc):
        """Skip for linear.* tasks to avoid infinite recursion."""
        envelope = _make_envelope(task="linear.create_issue")
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="recurse-test",
            task="linear.create_issue",
            team="system",
            error="some error",
        )
        mock_wc.run.assert_not_called()

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_no_issue_for_linear_update(self, mock_wc):
        """Also skip for linear.update_issue_status."""
        envelope = _make_envelope(task="linear.update_issue_status")
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="recurse-test2",
            task="linear.update_issue_status",
            team="system",
            error="some error",
        )
        mock_wc.run.assert_not_called()

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", False)
    def test_no_issue_when_env_disabled(self, mock_wc):
        """Skip when ESCALATE_FAILURES_TO_LINEAR=false."""
        envelope = _make_envelope()
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="disabled-test",
            task="llm.generate",
            team="system",
            error="some error",
        )
        mock_wc.run.assert_not_called()

    @patch("dispatcher.service.ESCALATE_ONLY_CANONICAL", True)
    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_no_issue_for_non_canonical_source(self, mock_wc):
        envelope = _make_envelope(source="sim_daily", source_kind="cron")
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="noise-test",
            task="research.web",
            team="system",
            error="quota",
        )
        mock_wc.run.assert_not_called()


# ── Priority mapping ───────────────────────────────────────────


class TestEscalatePriorityMapping:

    @pytest.mark.parametrize(
        "task_type,expected_priority",
        [
            ("critical", 1),
            ("coding", 2),
            ("ms_stack", 2),
            ("general", 3),
            ("writing", 3),
            ("research", 3),
            ("light", 4),
            ("unknown_type", 3),  # fallback default
        ],
    )
    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_priority_mapping(self, mock_wc, task_type, expected_priority):
        """Each task_type maps to the correct Linear priority."""
        envelope = _make_envelope(task_type=task_type)
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="prio-test",
            task="llm.generate",
            team="system",
            error="err",
        )
        payload = mock_wc.run.call_args[0][1]
        assert payload["priority"] == expected_priority, (
            f"task_type={task_type}: expected priority {expected_priority}, got {payload['priority']}"
        )


# ── Resilience: wc.run failure does not raise ──────────────────


class TestEscalateResilience:

    @patch("dispatcher.service.ESCALATE_TO_LINEAR", True)
    def test_wc_run_exception_swallowed(self, mock_wc):
        """If wc.run raises, _escalate_failure_to_linear does not propagate."""
        mock_wc.run.side_effect = Exception("Linear API down")
        envelope = _make_envelope()
        # Should NOT raise
        _escalate_failure_to_linear(
            wc=mock_wc,
            envelope=envelope,
            task_id="resilient-test",
            task="llm.generate",
            team="system",
            error="some error",
        )
        mock_wc.run.assert_called_once()


# ── Resumen del resultado en las notificaciones (PKG-MACRO-P5-L3-T1) ──
# Las dos líneas que arman el resumen (service.py:349 para Linear, :767 para
# Notion) pasaron a usar worker_payload. Es salida visible para David, así que
# los cinco casos quedan fijados: cuatro preservan exactamente lo de antes y el
# quinto es el único cambio deliberado.

class TestResultSummaryUnwrap(unittest.TestCase):

    def _comment_for(self, result):
        wc = MagicMock()
        envelope = {"linear_issue_id": "LIN-1", "task": "composite.research_report", "team": "lab"}
        service._notify_linear_completion(wc, envelope, True, result=result)
        wc.run.assert_called_once()
        return wc.run.call_args[0][1]["comment"]

    def test_payload_is_summarized_not_the_envelope(self):
        """El caso que importa: se resume el payload, no el sobre que lo envuelve.

        El assert va contra `task_id`, que sólo existe en el sobre: mirar que
        aparezca el texto del reporte no alcanza, porque también aparece cuando
        se vuelca el sobre entero.
        """
        comment = self._comment_for(worker_run_envelope({"report": "informe real", "sources": 3}))
        self.assertIn("informe real", comment)
        self.assertNotIn("task_id", comment)

    def test_envelope_without_result_key_is_summarized_whole(self):
        """Preservado: sin clave result, se resume lo que haya."""
        self.assertIn("algo", self._comment_for({"algo": "suelto"}))

    def test_non_dict_result_is_stringified(self):
        """Preservado: un result no-dict se sigue mostrando tal cual."""
        self.assertIn("texto plano", self._comment_for("texto plano"))

    def test_non_dict_payload_keeps_its_content(self):
        """Preservado: si el payload no es dict, no se pierde su contenido.

        worker_payload devuelve {} ahí; el `or result` evita que el comentario
        quede en "{}" y se resume el sobre, que es donde vive el texto.
        """
        self.assertIn("contenido", self._comment_for(worker_run_envelope("contenido")))

    def test_empty_payload_falls_back_to_the_envelope(self):
        """ÚNICO cambio deliberado: antes decía "{}", ahora resume el sobre.

        Un "{}" a secas no le dice nada a nadie; el sobre al menos trae el task.
        """
        comment = self._comment_for(worker_run_envelope({}))
        self.assertIn("llm.generate", comment)
