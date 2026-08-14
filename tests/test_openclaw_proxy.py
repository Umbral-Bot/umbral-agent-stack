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


@pytest.fixture(autouse=True)
def _strip_umbral_disable_claude(monkeypatch):
    """Task 042: worker.config._load_openclaw_env() runs at conftest import
    time and ingests ~/.config/openclaw/env, which on the VPS sets
    UMBRAL_DISABLE_CLAUDE=true. That leaks into every test process and
    short-circuits Claude routing in worker.tasks.llm._detect_provider.
    Strip the var by default; tests that explicitly need it set use
    patch.dict / monkeypatch.setenv inside the test body.
    """
    monkeypatch.delenv("UMBRAL_DISABLE_CLAUDE", raising=False)


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
    def test_gateway_receives_openclaw_routing_alias_not_raw_model(self, mock_urlopen):
        """PKG-MACRO-P5-L2-T5: el gateway (endpoint OpenAI-compatible) hace su
        propio ruteo de modelo interno y rechaza con 400 cualquier `model` que
        no sea "openclaw" o "openclaw/<agentId>" (verificado en vivo contra
        127.0.0.1:18789). El payload saliente NUNCA debe llevar el nombre real
        del modelo Anthropic — eso solo se preserva en el valor de retorno
        (ver test_successful_call: result["model"])."""
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}, clear=False):
            os.environ.pop("OPENCLAW_GATEWAY_AGENT", None)
            _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-opus-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="",
            )
        req_obj = mock_urlopen.call_args[0][0]
        body = json.loads(req_obj.data.decode())
        assert body["model"] == "openclaw/main"

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_gateway_agent_env_var_overrides_default(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        env = {"OPENCLAW_GATEWAY_TOKEN": "tok", "OPENCLAW_GATEWAY_AGENT": "rick-communication-director"}
        with patch.dict(os.environ, env):
            _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-opus-4-6",
                max_tokens=1024, temperature=0.7, system_prompt="",
            )
        req_obj = mock_urlopen.call_args[0][0]
        body = json.loads(req_obj.data.decode())
        assert body["model"] == "openclaw/rick-communication-director"


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
            assert _detect_provider("gemini-2.5-pro") == "gemini"

    def test_gpt_with_azure(self):
        from worker.tasks.llm import _detect_provider
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "ak",
        }):
            assert _detect_provider("gpt-5.2") == "azure_foundry"

    def test_openclaw_proxy_alias_resolves_to_claude(self):
        """PKG-MACRO-P5-L2-T5: MODEL_ALIASES["openclaw_proxy"] must exist —
        config/quota_policy.yaml's fallback_chain and dispatcher's
        ModelRouter/PROVIDER_MODEL_MAP can legitimately hand the worker a bare
        "openclaw_proxy" as `selected_model` (the same alias pattern every
        other provider key in MODEL_ALIASES supports); without an entry it
        silently fell through _detect_provider's catch-all to "gemini"."""
        from worker.tasks.llm import MODEL_ALIASES, _resolve_model_alias
        assert "openclaw_proxy" in MODEL_ALIASES
        assert _resolve_model_alias("openclaw_proxy") == "claude-sonnet-4-6"

    @patch("worker.tasks.llm.trace_llm_call")
    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_selected_model_openclaw_proxy_routes_through_gateway(self, mock_urlopen, mock_trace):
        """End-to-end: selected_model="openclaw_proxy" (no "model" key — the
        Dispatcher's documented backward-compat shape) with ONLY
        OPENCLAW_GATEWAY_TOKEN configured must reach the gateway, not raise
        GOOGLE_API_KEY not configured."""
        from worker.tasks.llm import handle_llm_generate
        mock_urlopen.return_value = _mock_urlopen_ok("via gateway")
        env = _env_without("ANTHROPIC_API_KEY", "GOOGLE_API_KEY")
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        with patch.dict(os.environ, env, clear=True):
            result = handle_llm_generate({"prompt": "hola", "selected_model": "openclaw_proxy"})
        assert result["provider"] == "openclaw_proxy"
        assert result["text"] == "via gateway"


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

    def test_openclaw_proxy_model_in_map(self):
        from dispatcher.service import PROVIDER_MODEL_MAP
        assert PROVIDER_MODEL_MAP.get("openclaw_proxy") == "anthropic/claude-sonnet-4-6"

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


# ---------------------------------------------------------------------------
# PKG-MACRO-P5-L2-T7 — recorte del default: los callers sin modelo NO van al gateway
# ---------------------------------------------------------------------------
class TestDefaultScopedAwayFromGateway:
    """Fija el recorte de T7 sobre los callers REALES que no pasan por el
    ModelRouter del dispatcher. Antes de T7, con OPENCLAW_GATEWAY_TOKEN
    presente (que es el estado vivo del VPS desde T4), estos caminos se
    reenrutaban solos al gateway: ~36s y ~27k tokens de prompt por llamada
    (medición real contra `openclaw/main`, §7.3/§9.2), con riesgo de
    saturarlo — ya lo tumbó una vez.

    Los tests piden el payload a las funciones REALES (no a un literal
    copiado a mano), así que si alguien le agrega un `model` a cualquiera de
    los tres callers, estos tests fallan."""

    def test_composite_report_payload_has_no_model_key(self):
        """Guardia estructural sobre `_build_report_generation_payload`: hoy no
        manda ninguna clave que seleccione modelo, así que cae en DEFAULT_MODEL.

        Se miran SOLO las claves que deciden el modelo — no todos los valores:
        el payload lleva metadata de tracing (`_source`, que en runtime vale
        "openclaw_gateway") que no tiene nada que ver con el ruteo.

        Si alguien agrega acá un passthrough del modelo ruteado por el
        dispatcher (`composite.` sí está en LLM_TASK_PREFIXES, así que sería
        legítimo), este test va a fallar — a propósito: que sea una decisión
        consciente, no un accidente, porque hoy manda composite al gateway."""
        from worker.tasks.composite import _build_report_generation_payload
        payload = _build_report_generation_payload(
            topic="t", research_data="d", language="es"
        )
        assert "model" not in payload
        assert "selected_model" not in payload

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_composite_report_generation_never_hits_gateway(self, mock_urlopen):
        """El payload real de composite.research_report, con el token presente,
        no debe abrir NINGUNA conexión al gateway."""
        from worker.tasks.composite import _build_report_generation_payload
        from worker.tasks.llm import handle_llm_generate

        payload = _build_report_generation_payload(
            topic="proptech", research_data="datos", language="es"
        )
        env = _env_without("GOOGLE_API_KEY")
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        env.pop("UMBRAL_DISABLE_CLAUDE", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="GOOGLE_API_KEY not configured"):
                handle_llm_generate(payload)
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.composite.handle_research_web")
    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_composite_query_generation_never_hits_gateway(self, mock_urlopen, _mock_web):
        """`_generate_queries` arma su payload inline (no vía un builder), así
        que se lo ejercita de verdad — es la PRIMERA llamada LLM del pipeline."""
        from worker.tasks.composite import _generate_queries

        env = _env_without("GOOGLE_API_KEY")
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        env.pop("UMBRAL_DISABLE_CLAUDE", None)
        with patch.dict(os.environ, env, clear=True):
            # Falla o devuelve fallback, pero NUNCA debe tocar el gateway.
            try:
                _generate_queries("proptech", 3)
            except Exception:
                pass
        mock_urlopen.assert_not_called()

    def test_smart_reply_real_caller_sends_no_model(self):
        """Vincula el guard al caller REAL: dispatcher/smart_reply.py::
        _do_llm_generate. Si alguien le agrega un `model`, esto falla."""
        from unittest.mock import MagicMock
        from dispatcher.smart_reply import _do_llm_generate

        wc = MagicMock()
        wc.run.return_value = {"result": {"text": "ok"}}
        _do_llm_generate(wc, prompt="Respondé a David.", system="Sos Rick.")

        task, payload = wc.run.call_args.args[0], wc.run.call_args.args[1]
        assert task == "llm.generate"
        assert "model" not in payload
        assert "selected_model" not in payload

    def test_daily_digest_real_caller_sends_no_model(self):
        """Idem para scripts/daily_digest.py::generate_llm_summary."""
        from unittest.mock import MagicMock
        from scripts.daily_digest import generate_llm_summary

        wc = MagicMock()
        wc.run.return_value = {"result": {"text": "resumen"}}
        generate_llm_summary("reporte", wc)

        task, payload = wc.run.call_args.args[0], wc.run.call_args.args[1]
        assert task == "llm.generate"
        assert "model" not in payload
        assert "selected_model" not in payload
