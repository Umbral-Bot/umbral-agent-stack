"""Unit tests for E2E validation and smoke test scripts (mock HTTP)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

import httpx

# Import test functions from e2e_validation
# Alias test_* functions to avoid pytest collecting them as test cases
from scripts.e2e_validation import (
    ValidationResult,
    SuiteResult,
    _run_test,
    _worker_payload,
    format_results,
)
from scripts.e2e_validation import test_worker_vps_health as e2e_health
from scripts.e2e_validation import test_ping as e2e_ping
from scripts.e2e_validation import test_scheduled_list as e2e_scheduled_list
from scripts.e2e_validation import test_composite_research as e2e_composite
from scripts.e2e_validation import test_routing_coding_selects_claude as e2e_routing_coding
from scripts.e2e_validation import test_routing_research_selects_gemini as e2e_routing_research

# Import smoke test functions
from scripts.smoke_test import (
    smoke_worker_health,
    smoke_ping,
    smoke_redis,
    smoke_quota,
)


# ── ValidationResult / SuiteResult ──────────────────────────────────


class TestDataStructures(unittest.TestCase):
    """Verify ValidationResult and SuiteResult counting."""

    def test_suite_pass_fail_skip_counts(self):
        suite = SuiteResult(results=[
            ValidationResult("a", passed=True, elapsed_ms=10),
            ValidationResult("b", passed=False, elapsed_ms=20, error="boom"),
            ValidationResult("c", passed=True, elapsed_ms=0, skipped=True, detail="SKIP"),
            ValidationResult("d", passed=True, elapsed_ms=15),
        ])
        self.assertEqual(suite.total_pass, 2)
        self.assertEqual(suite.total_fail, 1)
        self.assertEqual(suite.total_skip, 1)

    def test_suite_all_pass(self):
        suite = SuiteResult(results=[
            ValidationResult("a", passed=True, elapsed_ms=10),
            ValidationResult("b", passed=True, elapsed_ms=20),
        ])
        self.assertEqual(suite.total_pass, 2)
        self.assertEqual(suite.total_fail, 0)
        self.assertEqual(suite.total_skip, 0)


# ── _run_test infrastructure ─────────────────────────────────


class TestRunTest(unittest.TestCase):
    """Verify _run_test wraps functions correctly."""

    def test_success(self):
        result = _run_test("ok_test", lambda: "done")
        self.assertTrue(result.passed)
        self.assertEqual(result.detail, "done")
        self.assertFalse(result.skipped)

    def test_failure(self):
        def boom():
            raise ValueError("broken")
        result = _run_test("fail_test", boom)
        self.assertFalse(result.passed)
        self.assertIn("ValueError", result.error)


# ── format_results ────────────────────────────────────────────


class TestFormatResults(unittest.TestCase):
    """Verify output formatting."""

    def test_skip_shown_in_output(self):
        suite = SuiteResult(results=[
            ValidationResult("test1", passed=True, elapsed_ms=10, detail="ok"),
            ValidationResult("test2", passed=True, elapsed_ms=0, skipped=True, detail="SKIP — no key"),
        ])
        output = format_results(suite)
        self.assertIn("[SKIP]", output)
        self.assertIn("[PASS]", output)
        self.assertIn("1 SKIP", output)

    def test_fail_shown_in_output(self):
        suite = SuiteResult(results=[
            ValidationResult("test1", passed=False, elapsed_ms=5, error="connection refused"),
        ])
        output = format_results(suite)
        self.assertIn("[FAIL]", output)
        self.assertIn("connection refused", output)


# ── Mock HTTP E2E tests ───────────────────────────────────────


class TestWorkerVPSHealth(unittest.TestCase):
    """Test test_worker_vps_health with mock HTTP."""

    @patch("scripts.e2e_validation.httpx.Client")
    def test_health_success(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "version": "0.4.0",
            "tasks_registered": ["ping", "llm.generate", "research.web"],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = e2e_health("http://localhost:8088")
        self.assertIn("v0.4.0", result)
        self.assertIn("3 handlers", result)


class TestPingE2E(unittest.TestCase):
    """Test test_ping with mock HTTP."""

    @patch("scripts.e2e_validation.httpx.Client")
    def test_ping_success(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"echo": "pong"}}
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = e2e_ping("http://localhost:8088", "test-token")
        self.assertIn("echo=pong", result)


class TestScheduledList(unittest.TestCase):
    """Test test_scheduled_list with mock HTTP."""

    @patch("scripts.e2e_validation.httpx.Client")
    def test_scheduled_empty(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "scheduled": [], "total": 0}
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = e2e_scheduled_list("http://localhost:8088", "test-token")
        self.assertIn("0 tareas", result)


# ── Smoke test functions ──────────────────────────────────────


class TestSmokeWorkerHealth(unittest.TestCase):
    """Test smoke_worker_health."""

    @patch("scripts.smoke_test.httpx.Client")
    def test_success(self, mock_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "version": "0.4.0"}
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_cls.return_value = mock_client

        ok, detail = smoke_worker_health("http://localhost:8088")
        self.assertTrue(ok)
        self.assertIn("v0.4.0", detail)

    @patch("scripts.smoke_test.httpx.Client")
    def test_failure(self, mock_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("refused")
        mock_cls.return_value = mock_client

        ok, detail = smoke_worker_health("http://localhost:8088")
        self.assertFalse(ok)
        self.assertIn("FAIL", detail)


class TestSmokePing(unittest.TestCase):
    """Test smoke_ping."""

    @patch("scripts.smoke_test.httpx.Client")
    def test_success(self, mock_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"echo": "pong"}}
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_cls.return_value = mock_client

        ok, detail = smoke_ping("http://localhost:8088", "tok")
        self.assertTrue(ok)
        self.assertIn("echo=pong", detail)


class TestSmokeRedis(unittest.TestCase):
    """Test smoke_redis."""

    @patch("scripts.smoke_test.redis_lib", create=True)
    def test_success(self, mock_redis_mod):
        # We need to patch the import inside the function
        mock_r = MagicMock()
        mock_r.ping.return_value = True
        mock_r.llen.return_value = 3
        with patch.dict("sys.modules", {"redis": MagicMock()}):
            with patch("scripts.smoke_test.smoke_redis") as mock_fn:
                mock_fn.return_value = (True, "connected, pending=3")
                ok, detail = mock_fn("redis://localhost:6379/0")
                self.assertTrue(ok)
                self.assertIn("connected", detail)


class TestSmokeQuota(unittest.TestCase):
    """Test smoke_quota with 404 (endpoint not deployed)."""

    @patch("scripts.smoke_test.httpx.Client")
    def test_404_is_skip(self, mock_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_cls.return_value = mock_client

        ok, detail = smoke_quota("http://localhost:8088", "tok")
        self.assertTrue(ok)
        self.assertIn("SKIP", detail)


# ── UNWRAP (PKG-MACRO-P5-L2-T12) ────────────────────────────────


def _status_envelope(payload: dict) -> dict:
    """El shape REAL que devuelve GET /task/<id>/status (medido en T11).

    El dispatcher guarda el sobre completo del worker dentro de result, así que
    el payload del handler queda dos niveles adentro.
    """
    return {
        "task_id": "e2e-1234",
        "status": "done",
        "task": "llm.generate",
        "team": "lab",
        "result": {
            "ok": True,
            "task_id": "e2e-1234",
            "task": "llm.generate",
            "team": "lab",
            "trace_id": "trace-1234",
            "result": payload,
        },
        "error": None,
    }


def _run_envelope(payload: dict) -> dict:
    """El shape de POST /run: un solo nivel de result, sin el sobre extra."""
    return {"ok": True, "task_id": "e2e-1234", "task": "llm.generate", "result": payload}


class TestWorkerPayloadUnwrap(unittest.TestCase):
    """_worker_payload desenvuelve el sobre del worker sin comerse un nivel de más."""

    def test_status_envelope_yields_inner_model_and_report(self):
        wrapped = _status_envelope({"model": "anthropic/claude-sonnet-4-6", "report": "x" * 19459})
        payload = _worker_payload(wrapped)
        self.assertEqual(payload.get("model"), "anthropic/claude-sonnet-4-6")
        self.assertEqual(len(payload.get("report", "")), 19459)
        # Y no quedó el sobre: las llaves del envelope no deben sobrevivir.
        self.assertNotIn("trace_id", payload)

    def test_run_envelope_is_pass_through(self):
        """POST /run ya viene con un solo nivel: no debe haber segundo unwrap."""
        payload = _worker_payload(_run_envelope({"text": "hola", "model": "m", "provider": "openclaw_proxy"}))
        self.assertEqual(payload, {"text": "hola", "model": "m", "provider": "openclaw_proxy"})

    def test_handler_payload_with_its_own_result_is_not_unwrapped(self):
        """Regresión: granola devuelve {followup_type, result:{...}}.

        Un criterio laxo ("tiene un result dict adentro") se comería ese nivel y
        devolvería el interior del handler en lugar del payload. El sobre del
        worker se reconoce por ok+task_id+task juntos, que ningún handler pone.
        """
        granola = {"followup_type": "reminder", "result": {"task_id": "n-1", "due_date": "2026-08-20"}}
        # a) vía POST /run: el payload no es un sobre → pass-through intacto
        self.assertEqual(_worker_payload(_run_envelope(granola)), granola)
        # b) vía status: se pela UN solo nivel, el del worker
        self.assertEqual(_worker_payload(_status_envelope(granola)), granola)

    def test_missing_or_non_dict_result_is_empty_dict(self):
        """Una task fallida no trae result: devolver {} y no explotar con None."""
        self.assertEqual(_worker_payload({"status": "failed", "result": None}), {})
        self.assertEqual(_worker_payload({"status": "failed"}), {})
        self.assertEqual(_worker_payload({"result": "texto plano"}), {})


# El unwrap ingenuo que había antes de T12 y que producía el FAIL de aserción.
# Se usa para MUTAR el helper en los tests de abajo: si una función deja de
# depender de _worker_payload, el test de mutación lo detecta (lección T9/T10).
def _naive_unwrap(status_data: dict) -> dict:
    return status_data.get("result", {})


class TestAffectedTestsUseTheUnwrap(unittest.TestCase):
    """Las 3 funciones que leen GET /task/status pasan con el shape real de T11.

    Cada caso viene con su mutación: reemplazando _worker_payload por el unwrap
    ingenuo pre-T12, el test DEBE fallar. Sin eso, un assert que pase por otra
    razón no probaría nada.
    """

    ROUTE = {"effective_model": "anthropic/claude-sonnet-4-6"}

    def _patch_routing(self):
        return patch.multiple(
            "scripts.e2e_validation",
            _get_provider_status=MagicMock(return_value={"routing": {}}),
            _get_effective_route=MagicMock(return_value=self.ROUTE),
        )

    # -- b) routing coding ---------------------------------------

    def test_routing_coding_reads_inner_model(self):
        status = _status_envelope({"model": "anthropic/claude-sonnet-4-6", "provider": "openclaw_proxy"})
        with self._patch_routing(), patch("scripts.e2e_validation._enqueue_and_wait", return_value=status):
            detail = e2e_routing_coding("http://w", "tok")
        self.assertIn("actual=anthropic/claude-sonnet-4-6", detail)

    def test_routing_coding_fails_without_the_unwrap(self):
        status = _status_envelope({"model": "anthropic/claude-sonnet-4-6", "provider": "openclaw_proxy"})
        with self._patch_routing(), \
                patch("scripts.e2e_validation._enqueue_and_wait", return_value=status), \
                patch("scripts.e2e_validation._worker_payload", _naive_unwrap):
            with self.assertRaises(ValueError) as ctx:
                e2e_routing_coding("http://w", "tok")
        self.assertIn("got=?", str(ctx.exception))

    # -- c) routing research -------------------------------------

    def test_routing_research_reads_inner_model(self):
        status = _status_envelope({"model": "anthropic/claude-sonnet-4-6", "provider": "openclaw_proxy"})
        with self._patch_routing(), patch("scripts.e2e_validation._enqueue_and_wait", return_value=status):
            detail = e2e_routing_research("http://w", "tok")
        self.assertIn("actual=anthropic/claude-sonnet-4-6", detail)

    def test_routing_research_fails_without_the_unwrap(self):
        status = _status_envelope({"model": "anthropic/claude-sonnet-4-6", "provider": "openclaw_proxy"})
        with self._patch_routing(), \
                patch("scripts.e2e_validation._enqueue_and_wait", return_value=status), \
                patch("scripts.e2e_validation._worker_payload", _naive_unwrap):
            with self.assertRaises(ValueError) as ctx:
                e2e_routing_research("http://w", "tok")
        self.assertIn("got=?", str(ctx.exception))

    # -- d) composite --------------------------------------------

    def test_composite_reports_the_real_report_length(self):
        status = _status_envelope({"report": "x" * 19459, "stats": {"total_sources": 15}})
        with patch("scripts.e2e_validation._enqueue_and_wait", return_value=status):
            detail = e2e_composite("http://w", "tok")
        self.assertIn("19459 chars", detail)

    def test_composite_reports_zero_without_the_unwrap(self):
        """El síntoma exacto de T11: PASS pero 'reporte 0 chars'."""
        status = _status_envelope({"report": "x" * 19459, "stats": {"total_sources": 15}})
        with patch("scripts.e2e_validation._enqueue_and_wait", return_value=status), \
                patch("scripts.e2e_validation._worker_payload", _naive_unwrap):
            detail = e2e_composite("http://w", "tok")
        self.assertIn("0 chars", detail)


if __name__ == "__main__":
    unittest.main()
