"""Tests for openclaw_proxy provider — Claude via OpenClaw gateway."""

import json
import os
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("WORKER_TOKEN", "test")


def _mock_urlopen_ok(content="Hola desde Claude", usage=None):
    """Build a mock response for urllib.request.urlopen — success."""
    body = {
        "choices": [{"message": {"content": content}}],
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    resp = MagicMock()
    resp.read.return_value = json.dumps(body).encode()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _env_without(*keys):
    """Return os.environ copy without specific keys."""
    return {k: v for k, v in os.environ.items() if k not in keys}


# ---------------------------------------------------------------------------
# _call_openclaw_proxy
# ---------------------------------------------------------------------------
class TestCallOpenclawProxy:

    def test_missing_token_returns_error(self):
        from worker.tasks.llm import _call_openclaw_proxy
        with patch.dict(os.environ, _env_without("OPENCLAW_GATEWAY_TOKEN"), clear=True):
            result = _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-sonnet-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="",
            )
        assert result["ok"] is False
        assert "OPENCLAW_GATEWAY_TOKEN" in result["error"]

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_successful_call(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("Hola desde Claude")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok123"}):
            result = _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-sonnet-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="",
            )
        assert result["text"] == "Hola desde Claude"
        assert result["model"] == "anthropic/claude-sonnet-4-6"
        assert result["provider"] == "openclaw_proxy"
        assert result["usage"]["total_tokens"] == 15

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_http_error_raises(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        exc = urllib.error.HTTPError(
            url="http://localhost:18789/v1/chat/completions",
            code=429, msg="Too Many Requests",
            hdrs=MagicMock(), fp=BytesIO(b"Rate limit exceeded"),
        )
        mock_urlopen.side_effect = exc
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            with pytest.raises(RuntimeError, match="OpenClaw proxy error 429"):
                _call_openclaw_proxy(
                    prompt="Hola", model="anthropic/claude-sonnet-4-6",
                    max_tokens=1024, temperature=0.7, system_prompt="",
                )

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_connection_refused(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            with pytest.raises(RuntimeError, match="unreachable"):
                _call_openclaw_proxy(
                    prompt="Hola", model="anthropic/claude-sonnet-4-6",
                    max_tokens=1024, temperature=0.7, system_prompt="",
                )

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_no_choices_raises(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        resp = MagicMock()
        resp.read.return_value = json.dumps({"choices": []}).encode()
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            with pytest.raises(RuntimeError, match="No choices"):
                _call_openclaw_proxy(
                    prompt="Hola", model="anthropic/claude-sonnet-4-6",
                    max_tokens=1024, temperature=0.7, system_prompt="",
                )

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_custom_gateway_url(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        env = {"OPENCLAW_GATEWAY_TOKEN": "tok", "OPENCLAW_GATEWAY_URL": "http://10.0.0.5:9999"}
        with patch.dict(os.environ, env):
            result = _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-sonnet-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="",
            )
        # Verify the URL used in the Request
        req_obj = mock_urlopen.call_args[0][0]
        assert "10.0.0.5:9999" in req_obj.full_url
        assert result["text"] == "ok"

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_bearer_token_header(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "secret-abc"}):
            _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-sonnet-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="",
            )
        req_obj = mock_urlopen.call_args[0][0]
        assert req_obj.get_header("Authorization") == "Bearer secret-abc"

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_system_prompt_sent(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-sonnet-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="Eres Rick.",
            )
        req_obj = mock_urlopen.call_args[0][0]
        body = json.loads(req_obj.data.decode())
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][0]["content"] == "Eres Rick."
        assert body["messages"][1]["role"] == "user"

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_max_tokens_and_temperature(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-sonnet-4-6",
                max_tokens=4096, temperature=0.3, system_prompt="",
            )
        req_obj = mock_urlopen.call_args[0][0]
        body = json.loads(req_obj.data.decode())
        assert body["max_tokens"] == 4096
        assert body["temperature"] == 0.3

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_model_forwarded_in_payload(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-opus-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="",
            )
        req_obj = mock_urlopen.call_args[0][0]
        body = json.loads(req_obj.data.decode())
        assert body["model"] == "anthropic/claude-opus-4-6"


# ---------------------------------------------------------------------------
# _detect_provider — Claude routing
# ---------------------------------------------------------------------------
class TestDetectProviderClaude:

    def test_claude_with_openclaw_token(self):
        from worker.tasks.llm import _detect_provider
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            assert _detect_provider("claude-sonnet-4-6") == "openclaw_proxy"

    def test_claude_with_anthropic_key_no_openclaw(self):
        from worker.tasks.llm import _detect_provider
        env = _env_without("OPENCLAW_GATEWAY_TOKEN")
        env["ANTHROPIC_API_KEY"] = "ak"
        with patch.dict(os.environ, env, clear=True):
            assert _detect_provider("claude-sonnet-4-6") == "anthropic"

    def test_claude_openclaw_takes_priority(self):
        """When both OPENCLAW_GATEWAY_TOKEN and ANTHROPIC_API_KEY exist, prefer openclaw_proxy."""
        from worker.tasks.llm import _detect_provider
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok", "ANTHROPIC_API_KEY": "ak"}):
            assert _detect_provider("claude-sonnet-4-6") == "openclaw_proxy"

    def test_claude_no_credentials_raises(self):
        from worker.tasks.llm import _detect_provider
        env = _env_without("OPENCLAW_GATEWAY_TOKEN", "ANTHROPIC_API_KEY")
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="OPENCLAW_GATEWAY_TOKEN"):
                _detect_provider("claude-sonnet-4-6")

    def test_gemini_unchanged(self):
        from worker.tasks.llm import _detect_provider
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "gk"}):
            assert _detect_provider("gemini-3.1-pro-preview") == "gemini"

    def test_gpt_with_azure(self):
        from worker.tasks.llm import _detect_provider
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "ak",
        }):
            assert _detect_provider("gpt-5.2") == "azure_foundry"


# ---------------------------------------------------------------------------
# handle_llm_generate integration — openclaw_proxy
# ---------------------------------------------------------------------------
class TestHandleLlmGenerateOpenClaw:

    @patch("worker.tasks.llm.trace_llm_call")
    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_auto_detect_claude_via_openclaw(self, mock_urlopen, mock_trace):
        from worker.tasks.llm import handle_llm_generate
        mock_urlopen.return_value = _mock_urlopen_ok("Claude says hi")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            result = handle_llm_generate({
                "prompt": "Hello Claude",
                "model": "claude-sonnet-4-6",
            })
        assert result["text"] == "Claude says hi"
        assert result["provider"] == "openclaw_proxy"

    @patch("worker.tasks.llm.trace_llm_call")
    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_anthropic_prefix_model(self, mock_urlopen, mock_trace):
        from worker.tasks.llm import handle_llm_generate
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            result = handle_llm_generate({
                "prompt": "Test",
                "model": "anthropic/claude-opus-4-6",
            })
        # Model with anthropic/ prefix should also get claude detection
        assert result["provider"] == "openclaw_proxy"

    @patch("worker.tasks.llm.trace_llm_call")
    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_tracing_called(self, mock_urlopen, mock_trace):
        from worker.tasks.llm import handle_llm_generate
        mock_urlopen.return_value = _mock_urlopen_ok("traced")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            handle_llm_generate({
                "prompt": "Trace me",
                "model": "claude-sonnet-4-6",
            })
        mock_trace.assert_called_once()
        call_kwargs = mock_trace.call_args
        assert call_kwargs.kwargs.get("provider") == "openclaw_proxy" or \
               (len(call_kwargs.args) > 1 and call_kwargs.args[1] == "openclaw_proxy")


# ---------------------------------------------------------------------------
# model_router.py entries
# ---------------------------------------------------------------------------
class TestModelRouterOpenClaw:

    def test_provider_env_requirements(self):
        from dispatcher.model_router import _PROVIDER_ENV_REQUIREMENTS
        assert "openclaw_proxy" in _PROVIDER_ENV_REQUIREMENTS
        assert "OPENCLAW_GATEWAY_TOKEN" in _PROVIDER_ENV_REQUIREMENTS["openclaw_proxy"]

    def test_openclaw_provider_detection(self):
        from dispatcher.model_router import get_configured_providers
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            providers = get_configured_providers()
        assert "openclaw_proxy" in providers


# ---------------------------------------------------------------------------
# service.py PROVIDER_MODEL_MAP
# ---------------------------------------------------------------------------
class TestServiceProviderModelMap:

    def test_openclaw_claude_models_in_map(self):
        from dispatcher.service import PROVIDER_MODEL_MAP
        assert PROVIDER_MODEL_MAP.get("openclaw_claude_pro") == "anthropic/claude-sonnet-4-6"
        assert PROVIDER_MODEL_MAP.get("openclaw_claude_opus") == "anthropic/claude-opus-4-6"
        assert PROVIDER_MODEL_MAP.get("openclaw_claude_haiku") == "anthropic/claude-haiku-4-5"

    def test_original_claude_models_still_present(self):
        from dispatcher.service import PROVIDER_MODEL_MAP
        assert PROVIDER_MODEL_MAP.get("claude_pro") == "claude-sonnet-4-6"
        assert PROVIDER_MODEL_MAP.get("claude_opus") == "claude-opus-4-6"
        assert PROVIDER_MODEL_MAP.get("claude_haiku") == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# PROVIDERS dict
# ---------------------------------------------------------------------------
class TestProvidersDict:

    def test_openclaw_proxy_registered(self):
        from worker.tasks.llm import PROVIDERS
        assert "openclaw_proxy" in PROVIDERS
        assert callable(PROVIDERS["openclaw_proxy"])

    def test_all_original_providers_still_present(self):
        from worker.tasks.llm import PROVIDERS
        for p in ("gemini", "vertex", "azure_foundry", "openai", "anthropic"):
            assert p in PROVIDERS, f"Provider '{p}' missing from PROVIDERS dict"
