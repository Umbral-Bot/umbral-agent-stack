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

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_explicit_agent_id_overrides_global_route_without_mutating_env(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        env = {"OPENCLAW_GATEWAY_TOKEN": "tok", "OPENCLAW_GATEWAY_AGENT": "main"}
        with patch.dict(os.environ, env):
            _call_openclaw_proxy(
                prompt="Hola", model="rick-editorial", max_tokens=1024,
                temperature=0.2, system_prompt="", agent_id="rick-editorial",
            )
            assert os.environ["OPENCLAW_GATEWAY_AGENT"] == "main"
        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body["model"] == "openclaw/rick-editorial"


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
# PKG-MACRO-P5-L2-T8 — el texto va por el proxy (OAuth de ChatGPT), sin Gemini
# ---------------------------------------------------------------------------
class TestTextGoesThroughProxy:
    """T8 invierte el recorte de T7 por decisión de David (2026-08-14): el
    texto sale por la sesión de ChatGPT (OAuth) que vive en el gateway, vía
    `openclaw_proxy`. Sin Gemini.

    Lo que T7 protegía sigue importando, pero se resuelve con timeouts (≥90s,
    también en este pack) y no disparando en ráfaga, no sacando el tráfico del
    gateway.

    Los tests usan las funciones REALES, no literales copiados a mano."""

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_composite_report_generation_uses_proxy(self, mock_urlopen):
        """El payload real de composite, sin modelo inyectado, va al proxy."""
        from worker.tasks.composite import _build_report_generation_payload
        from worker.tasks.llm import handle_llm_generate

        mock_urlopen.return_value = _mock_urlopen_ok("reporte")
        payload = _build_report_generation_payload(
            topic="proptech", research_data="datos", language="es"
        )
        env = _env_without("GOOGLE_API_KEY")
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        env["UMBRAL_DISABLE_CLAUDE"] = "false"
        with patch.dict(os.environ, env, clear=True):
            result = handle_llm_generate(payload)

        assert result["provider"] == "openclaw_proxy"
        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body["model"] == "openclaw/main"

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_composite_honours_dispatcher_routed_model(self, mock_urlopen):
        """T8 paso 3: si el dispatcher inyectó un modelo, composite lo HONRA
        (antes lo descartaba y sus sub-llamadas caían en el default)."""
        from worker.tasks import composite

        mock_urlopen.return_value = _mock_urlopen_ok("reporte")
        composite._ACTIVE_CONTEXT.clear()
        composite._ACTIVE_CONTEXT["model"] = "anthropic/claude-sonnet-4-6"
        composite._ACTIVE_CONTEXT["selected_model"] = "openclaw_proxy"
        try:
            payload = composite._build_report_generation_payload(
                topic="t", research_data="d", language="es"
            )
            assert payload["model"] == "anthropic/claude-sonnet-4-6"
            assert payload["selected_model"] == "openclaw_proxy"
        finally:
            composite._ACTIVE_CONTEXT.clear()

    def test_composite_without_routed_model_sends_no_model_key(self):
        """Sin inyección del dispatcher (llamada directa, no encolada), el
        payload no lleva modelo y aplica el default de handle_llm_generate."""
        from worker.tasks import composite

        composite._ACTIVE_CONTEXT.clear()
        payload = composite._build_report_generation_payload(
            topic="t", research_data="d", language="es"
        )
        assert "model" not in payload
        assert "selected_model" not in payload

    @patch("worker.tasks.composite.handle_research_web")
    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_composite_query_generation_uses_proxy(self, mock_urlopen, _mock_web):
        """`_generate_queries` arma su payload inline; se lo ejercita de verdad
        porque es la PRIMERA llamada LLM del pipeline."""
        from worker.tasks.composite import _generate_queries

        mock_urlopen.return_value = _mock_urlopen_ok("1. una\n2. dos\n3. tres")
        env = _env_without("GOOGLE_API_KEY")
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        env["UMBRAL_DISABLE_CLAUDE"] = "false"
        with patch.dict(os.environ, env, clear=True):
            _generate_queries("proptech", 3)

        mock_urlopen.assert_called()
        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body["model"] == "openclaw/main"

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_no_gemini_call_when_token_present(self, mock_urlopen):
        """Guard explícito de la decisión 'sin Gemini': ninguna llamada por
        defecto puede terminar en generativelanguage.googleapis.com."""
        from worker.tasks.llm import handle_llm_generate

        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        env = _env_without()
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        env["UMBRAL_DISABLE_CLAUDE"] = "false"
        env["GOOGLE_API_KEY"] = "no-deberia-usarse"
        with patch.dict(os.environ, env, clear=True):
            result = handle_llm_generate({"prompt": "hola"})

        assert result["provider"] == "openclaw_proxy"
        url = mock_urlopen.call_args[0][0].full_url
        assert "googleapis.com" not in url
        assert "18789" in url

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


# ---------------------------------------------------------------------------
# PKG-MACRO-P5-L2-T10 — WINDOW: timeout del proxy por llamada
# ---------------------------------------------------------------------------
class TestProxyTimeoutWindow:
    """El urlopen contra el gateway va SIEMPRE por debajo del timeout de su
    caller (regla T8). Como los callers no son todos iguales, el valor es por
    llamada y no global: subir el default a 225s dejaría a smart_reply (120s)
    cortando antes que el proxy — el anti-patrón que T8 arregló."""

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_default_timeout_is_used_when_no_override(self, mock_urlopen):
        from worker.tasks.llm import _call_openclaw_proxy, PROXY_DEFAULT_TIMEOUT_S
        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "tok"}):
            _call_openclaw_proxy(
                prompt="Hola", model="anthropic/claude-sonnet-4-6",
                max_tokens=16, temperature=0.7, system_prompt="",
            )
        assert mock_urlopen.call_args.kwargs["timeout"] == PROXY_DEFAULT_TIMEOUT_S

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_composite_payload_carries_the_wide_window(self, mock_urlopen):
        """El payload real de composite pide la ventana ancha, y esa ventana
        llega hasta el urlopen."""
        from worker.tasks.composite import _build_report_generation_payload
        from worker.tasks.llm import handle_llm_generate, PROXY_COMPOSITE_TIMEOUT_S

        mock_urlopen.return_value = _mock_urlopen_ok("reporte")
        payload = _build_report_generation_payload(
            topic="t", research_data="d", language="es"
        )
        assert payload["_proxy_timeout_s"] == PROXY_COMPOSITE_TIMEOUT_S

        env = _env_without("GOOGLE_API_KEY")
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        env["UMBRAL_DISABLE_CLAUDE"] = "false"
        with patch.dict(os.environ, env, clear=True):
            handle_llm_generate(payload)
        assert mock_urlopen.call_args.kwargs["timeout"] == PROXY_COMPOSITE_TIMEOUT_S

    @patch("worker.tasks.llm.urllib.request.urlopen")
    def test_plain_llm_generate_keeps_the_default_window(self, mock_urlopen):
        """Una llm.generate normal (smart_reply/digest) NO hereda la ventana
        ancha: sigue con el default, por debajo de sus 120s."""
        from worker.tasks.llm import handle_llm_generate, PROXY_DEFAULT_TIMEOUT_S

        mock_urlopen.return_value = _mock_urlopen_ok("ok")
        env = _env_without("GOOGLE_API_KEY")
        env["OPENCLAW_GATEWAY_TOKEN"] = "tok"
        env["UMBRAL_DISABLE_CLAUDE"] = "false"
        with patch.dict(os.environ, env, clear=True):
            handle_llm_generate({"prompt": "hola"})
        assert mock_urlopen.call_args.kwargs["timeout"] == PROXY_DEFAULT_TIMEOUT_S
