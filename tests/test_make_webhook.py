"""
Tests for Make.com webhook handler (R4 task 017).

Covers:
- URL validation (only Make.com prefixes allowed)
- Payload validation (must be a dict, required)
- Timeout validation (1-120)
- Successful POST with JSON body
- HTTP error responses (ok=False)
- URLError raises RuntimeError
- TimeoutError raises RuntimeError

Run with:
    python -m pytest tests/test_make_webhook.py -v
"""

import json
import urllib.error
import urllib.request
from io import BytesIO
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.make_webhook import (
    ALLOWED_URL_PREFIXES,
    handle_make_post_webhook,
)


# ======================================================================
# Helpers
# ======================================================================

VALID_URL = "https://hook.make.com/abc123xyz"
VALID_PAYLOAD = {"topic": "test", "report": "hello world"}


def _make_input(
    webhook_url: str = VALID_URL,
    payload: Any = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    if payload is None:
        payload = VALID_PAYLOAD.copy()
    return {
        "webhook_url": webhook_url,
        "payload": payload,
        "timeout": timeout,
    }


class FakeHTTPResponse:
    """Minimal response context-manager for urllib.request.urlopen mock."""

    def __init__(self, status: int = 200, body: str = "Accepted"):
        self.status = status
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ======================================================================
# URL validation
# ======================================================================


class TestURLValidation:
    def test_missing_webhook_url(self):
        with pytest.raises(ValueError, match="webhook_url.*required"):
            handle_make_post_webhook({"payload": {"a": 1}})

    def test_empty_webhook_url(self):
        with pytest.raises(ValueError, match="webhook_url.*required"):
            handle_make_post_webhook({"webhook_url": "", "payload": {"a": 1}})

    def test_whitespace_webhook_url(self):
        with pytest.raises(ValueError, match="webhook_url.*required"):
            handle_make_post_webhook({"webhook_url": "   ", "payload": {"a": 1}})

    @pytest.mark.parametrize(
        "bad_url",
        [
            "https://evil.com/hook",
            "http://hook.make.com/abc",  # http instead of https
            "https://hook.make.com.evil.com/abc",
            "https://example.org/",
            "ftp://hook.make.com/abc",
            "https://hooks.make.com/abc",  # hooks != hook
        ],
    )
    def test_disallowed_urls(self, bad_url: str):
        with pytest.raises(ValueError, match="webhook_url must start with"):
            handle_make_post_webhook(_make_input(webhook_url=bad_url))

    @pytest.mark.parametrize(
        "prefix",
        list(ALLOWED_URL_PREFIXES),
    )
    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_allowed_prefixes(self, mock_urlopen, prefix: str):
        mock_urlopen.return_value = FakeHTTPResponse(200, "OK")
        result = handle_make_post_webhook(_make_input(webhook_url=f"{prefix}test123"))
        assert result["ok"] is True


# ======================================================================
# Payload validation
# ======================================================================


class TestPayloadValidation:
    def test_missing_payload(self):
        with pytest.raises(ValueError, match="payload.*required"):
            handle_make_post_webhook({"webhook_url": VALID_URL})

    def test_payload_none(self):
        with pytest.raises(ValueError, match="payload.*required"):
            handle_make_post_webhook({"webhook_url": VALID_URL, "payload": None})

    def test_payload_not_dict(self):
        with pytest.raises(ValueError, match="payload.*must be a dict"):
            handle_make_post_webhook(_make_input(payload="not a dict"))

    def test_payload_list(self):
        with pytest.raises(ValueError, match="payload.*must be a dict"):
            handle_make_post_webhook(_make_input(payload=[1, 2, 3]))


# ======================================================================
# Timeout validation
# ======================================================================


class TestTimeoutValidation:
    def test_timeout_zero(self):
        with pytest.raises(ValueError, match="timeout.*between 1 and 120"):
            handle_make_post_webhook(_make_input(timeout=0))

    def test_timeout_negative(self):
        with pytest.raises(ValueError, match="timeout.*between 1 and 120"):
            handle_make_post_webhook(_make_input(timeout=-5))

    def test_timeout_too_large(self):
        with pytest.raises(ValueError, match="timeout.*between 1 and 120"):
            handle_make_post_webhook(_make_input(timeout=121))


# ======================================================================
# Successful POST
# ======================================================================


class TestSuccessfulPost:
    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_success_200(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, "Accepted")
        result = handle_make_post_webhook(_make_input())
        assert result == {"ok": True, "status_code": 200, "response": "Accepted"}

    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_request_is_post_with_json(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, "OK")
        handle_make_post_webhook(_make_input())

        # Inspect the Request object passed to urlopen
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        assert isinstance(req, urllib.request.Request)
        assert req.method == "POST"
        assert req.get_header("Content-type") == "application/json"

        body = json.loads(req.data.decode("utf-8"))
        assert body == VALID_PAYLOAD

    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_timeout_passed_to_urlopen(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, "OK")
        handle_make_post_webhook(_make_input(timeout=45))

        _, kwargs = mock_urlopen.call_args
        assert kwargs.get("timeout") == 45

    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_response_truncated_at_2000(self, mock_urlopen):
        long_body = "x" * 5000
        mock_urlopen.return_value = FakeHTTPResponse(200, long_body)
        result = handle_make_post_webhook(_make_input())
        assert len(result["response"]) == 2000

    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_unicode_payload(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, "OK")
        payload = {"topic": "análisis inmobiliario 🏠", "data": "日本語テスト"}
        result = handle_make_post_webhook(_make_input(payload=payload))
        assert result["ok"] is True

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert body["topic"] == "análisis inmobiliario 🏠"


# ======================================================================
# Error handling
# ======================================================================


class TestErrorHandling:
    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_http_error_returns_ok_false(self, mock_urlopen):
        err = urllib.error.HTTPError(
            VALID_URL, 422, "Unprocessable", {}, BytesIO(b"bad input")
        )
        mock_urlopen.side_effect = err
        result = handle_make_post_webhook(_make_input())
        assert result["ok"] is False
        assert result["status_code"] == 422
        assert "bad input" in result["response"]

    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_http_500_error(self, mock_urlopen):
        err = urllib.error.HTTPError(
            VALID_URL, 500, "Internal Server Error", {}, BytesIO(b"server broke")
        )
        mock_urlopen.side_effect = err
        result = handle_make_post_webhook(_make_input())
        assert result["ok"] is False
        assert result["status_code"] == 500

    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_url_error_raises_runtime(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with pytest.raises(RuntimeError, match="Webhook connection failed"):
            handle_make_post_webhook(_make_input())

    @patch("worker.tasks.make_webhook.urllib.request.urlopen")
    def test_timeout_error_raises_runtime(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError()
        with pytest.raises(RuntimeError, match="Webhook timed out"):
            handle_make_post_webhook(_make_input())


# ======================================================================
# Handler registration
# ======================================================================


class TestRegistration:
    def test_handler_registered(self):
        from worker.tasks import TASK_HANDLERS

        assert "make.post_webhook" in TASK_HANDLERS
        assert TASK_HANDLERS["make.post_webhook"] is handle_make_post_webhook
