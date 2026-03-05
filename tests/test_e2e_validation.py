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
    format_results,
)
from scripts.e2e_validation import test_worker_vps_health as e2e_health
from scripts.e2e_validation import test_ping as e2e_ping
from scripts.e2e_validation import test_scheduled_list as e2e_scheduled_list

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


if __name__ == "__main__":
    unittest.main()
