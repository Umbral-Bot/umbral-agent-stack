"""Unit tests for llm.generate task handler."""

import json
from unittest.mock import patch

import pytest

from worker.tasks.llm import (
    ANTHROPIC_MESSAGES_URL,
    AZURE_OPENAI_DEFAULT_API_VERSION,
    GEMINI_BASE_URL,
    OPENAI_CHAT_COMPLETIONS_URL,
    _detect_provider,
    handle_llm_generate,
)


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _headers_lower(req):
    return {k.lower(): v for k, v in req.header_items()}


# UMBRAL_DISABLE_CLAUDE / OPENCLAW_GATEWAY_TOKEN leak stripping is handled by
# the shared autouse fixture in tests/conftest.py
# (_strip_openclaw_proxy_env_leaks). Tests that need either set use
# monkeypatch.setenv inside the test body (e.g.
# test_detect_provider_claude_respects_disable_flag,
# test_handle_llm_generate_without_model_never_uses_gateway).


def test_handle_llm_generate_requires_prompt():
    with pytest.raises(ValueError, match="prompt"):
        handle_llm_generate({})


def test_handle_llm_generate_without_token_fails_asking_for_the_proxy(monkeypatch):
    """PKG-MACRO-P5-L2-T8: sin OPENCLAW_GATEWAY_TOKEN y sin `model`, NO se cae
    de callado a Gemini — se falla pidiendo exactamente lo que falta.

    Un fallback silencioso a Gemini mandaría el tráfico a un provider que David
    descartó, y el síntoma aparecería como "GOOGLE_API_KEY not configured",
    que apunta al lugar equivocado."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("UMBRAL_DISABLE_CLAUDE", "false")

    with patch("worker.tasks.llm.urllib.request.urlopen") as mock_urlopen:
        with pytest.raises(RuntimeError, match="OPENCLAW_GATEWAY_TOKEN"):
            handle_llm_generate({"prompt": "Resume tendencias de mercado BIM"})

    # Y no intentó Gemini por atrás.
    mock_urlopen.assert_not_called()


def test_handle_llm_generate_claude_disabled_fails_without_falling_back(monkeypatch):
    """Con UMBRAL_DISABLE_CLAUDE activo, openclaw_proxy queda deshabilitado:
    tampoco se cae a Gemini, se falla nombrando el flag."""
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "gw-test-token")
    monkeypatch.setenv("UMBRAL_DISABLE_CLAUDE", "true")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with patch("worker.tasks.llm.urllib.request.urlopen") as mock_urlopen:
        with pytest.raises(RuntimeError, match="UMBRAL_DISABLE_CLAUDE"):
            handle_llm_generate({"prompt": "hola"})
    mock_urlopen.assert_not_called()


def test_handle_llm_generate_without_model_uses_the_proxy(monkeypatch):
    """PKG-MACRO-P5-L2-T8 (decisión de David 2026-08-14): el texto va por la
    sesión de ChatGPT (OAuth) del gateway. Sin `model` ni `selected_model`, y
    con el token presente, la llamada SÍ debe ir al proxy — sin Gemini.

    Invierte el guard de T7: aquel exigía lo contrario, porque en ese momento
    la orden era sacar del gateway a los callers sin modelo.

    UMBRAL_DISABLE_CLAUDE se fija explícito: si llegara truthy, el default
    fallaría por el flag y el test probaría otra cosa."""
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "gw-test-token")
    monkeypatch.setenv("UMBRAL_DISABLE_CLAUDE", "false")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "OK via proxy"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }
    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate({"prompt": "hola"})

    assert result["provider"] == "openclaw_proxy"
    assert result["text"] == "OK via proxy"

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == "http://localhost:18789/v1/chat/completions"
    body = json.loads(req.data.decode("utf-8"))
    assert body["model"] == "openclaw/main"


def test_handle_llm_generate_selected_model_openclaw_proxy_uses_gateway(monkeypatch):
    """Contrapartida del recorte: cuando el dispatcher SÍ inyecta
    selected_model=openclaw_proxy (vía ModelRouter, p.ej. R8 coding/research),
    la llamada sí debe ir al gateway."""
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "gw-test-token")
    monkeypatch.setenv("UMBRAL_DISABLE_CLAUDE", "false")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "OK via proxy"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }
    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "hola", "selected_model": "openclaw_proxy"}
        )

    assert result["provider"] == "openclaw_proxy"
    assert result["model"] == "claude-sonnet-4-6"
    assert result["text"] == "OK via proxy"

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == "http://localhost:18789/v1/chat/completions"
    headers = _headers_lower(req)
    assert headers["authorization"] == "Bearer gw-test-token"
    body = json.loads(req.data.decode("utf-8"))
    # El gateway solo acepta "openclaw"/"openclaw/<agentId>" como model —
    # NUNCA el nombre real del modelo Anthropic (ver _call_openclaw_proxy).
    assert body["model"] == "openclaw/main"
    assert body["messages"][0] == {"role": "user", "content": "hola"}


@pytest.mark.parametrize(
    "model,expected",
    [
        ("gemini-2.5-pro", "gemini"),
        ("gemini-1.5-pro", "gemini"),
        ("unknown-model", "gemini"),
    ],
)
def test_detect_provider_gemini_cases(model, expected, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert _detect_provider(model) == expected


@pytest.mark.parametrize("model", ["gpt-4o", "o1", "o3-mini", "gpt-5.3-codex"])
def test_detect_provider_openai_uses_foundry_when_configured(model, monkeypatch):
    """Con Foundry configurado, modelos OpenAI van a azure_foundry."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key")
    assert _detect_provider(model) == "azure_foundry"


@pytest.mark.parametrize("model", ["gpt-4o", "gpt-5.2", "gpt-5.3-codex"])
def test_detect_provider_openai_falls_to_native_without_foundry(model, monkeypatch):
    """Sin Foundry, cae a OPENAI_API_KEY nativo."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert _detect_provider(model) == "openai"


@pytest.mark.parametrize("model", ["gpt-5.3-codex", "gpt-5.2"])
def test_detect_provider_openai_raises_without_any_key(model, monkeypatch):
    """Sin Foundry ni OPENAI_API_KEY, lanza error (OAuth de ChatGPT Plus no sirve para Worker)."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Azure AI Foundry"):
        _detect_provider(model)


@pytest.mark.parametrize("model", ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"])
def test_detect_provider_claude_uses_anthropic_native(model, monkeypatch):
    """Claude siempre usa ANTHROPIC_API_KEY (token sesión Pro)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert _detect_provider(model) == "anthropic"


@pytest.mark.parametrize("model", ["claude-sonnet-4-6", "claude-opus-4-6"])
def test_detect_provider_claude_raises_without_key(model, monkeypatch):
    """Sin ANTHROPIC_API_KEY, Claude lanza error claro."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        _detect_provider(model)


def test_detect_provider_claude_respects_disable_flag(monkeypatch):
    monkeypatch.setenv("UMBRAL_DISABLE_CLAUDE", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    with pytest.raises(RuntimeError, match="UMBRAL_DISABLE_CLAUDE"):
        _detect_provider("claude-sonnet-4-6")


def test_detect_provider_anthropic_fallback_without_github_token(monkeypatch):
    """Falls back to native Anthropic API when GITHUB_TOKEN absent but ANTHROPIC_API_KEY present."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert _detect_provider("claude-3-5-sonnet") == "anthropic"


def test_handle_llm_generate_success_with_mocked_gemini(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")
    fake_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Oportunidades: digitalizacion BIM."},
                        {"text": " Recomendacion: pilotos por vertical."},
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 22,
            "candidatesTokenCount": 14,
            "totalTokenCount": 36,
        },
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen, patch("worker.tasks.llm.ops_log.llm_usage") as mock_usage:
        result = handle_llm_generate(
            {
                "prompt": "Dame un resumen ejecutivo.",
                # T8: el modelo va explícito. Antes este test dependía de que
                # el default fuera Gemini; ahora el default es openclaw_proxy,
                # y lo que este test prueba es el provider Gemini en sí.
                "model": "gemini-2.5-pro",
                "max_tokens": 256,
                "temperature": 0.4,
                "_task_id": "task-123",
                "_task_type": "analysis",
                "_source": "openclaw_gateway",
                "_source_kind": "tool_enqueue",
                "_usage_component": "llm.generate",
            }
        )

    assert result["provider"] == "gemini"
    assert result["model"] == "gemini-2.5-pro"
    assert "Oportunidades: digitalizacion BIM." in result["text"]
    assert result["usage"]["prompt_tokens"] == 22
    assert result["usage"]["completion_tokens"] == 14
    assert result["usage"]["total_tokens"] == 36

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == f"{GEMINI_BASE_URL}/gemini-2.5-pro:generateContent?key=google-test-key"
    body = json.loads(req.data.decode("utf-8"))
    assert body["generationConfig"]["maxOutputTokens"] == 256
    assert body["generationConfig"]["temperature"] == 0.4
    assert body["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 128
    assert body["contents"][-1]["parts"][0]["text"] == "Dame un resumen ejecutivo."
    mock_usage.assert_called_once()
    usage_kwargs = mock_usage.call_args.kwargs
    assert usage_kwargs["task_id"] == "task-123"
    assert usage_kwargs["source"] == "openclaw_gateway"
    assert usage_kwargs["usage_component"] == "llm.generate"


def test_handle_llm_generate_success_with_mocked_vertex(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY_RICK_UMBRAL", "vertex-test-key")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", "proj-test")
    fake_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Vertex operativo."},
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 18,
            "candidatesTokenCount": 7,
            "totalTokenCount": 25,
        },
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {
                "prompt": "Verifica Vertex.",
                "model": "gemini_vertex",
                "max_tokens": 128,
                "temperature": 0.2,
            }
        )

    assert result["provider"] == "vertex"
    assert result["model"] == "gemini-2.5-flash"
    assert result["text"] == "Vertex operativo."
    assert result["usage"]["total_tokens"] == 25

    req = mock_urlopen.call_args.args[0]
    assert "/publishers/google/models/gemini-2.5-flash:generateContent" in req.full_url
    headers = _headers_lower(req)
    assert headers["x-goog-api-key"] == "vertex-test-key"
    body = json.loads(req.data.decode("utf-8"))
    assert body["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0


def test_handle_llm_generate_vertex31_alias_maps_to_gemini3(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY_RICK_UMBRAL", "vertex-test-key")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", "proj-test")
    fake_payload = {
        "candidates": [{"content": {"parts": [{"text": "Vertex 3 OK."}]}}],
        "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 5, "totalTokenCount": 17},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "Prueba Vertex 3.", "model": "gemini_vertex_31", "max_tokens": 128}
        )

    assert result["provider"] == "vertex"
    assert result["model"] == "gemini-3.1-pro-preview"
    req = mock_urlopen.call_args.args[0]
    assert "https://aiplatform.googleapis.com/" in req.full_url
    assert "/locations/global/publishers/google/models/gemini-3.1-pro-preview:generateContent" in req.full_url


def test_openai_success_with_mocked_urllib(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    # Task 042: strip leaked AZURE_OPENAI_* from ~/.config/openclaw/env so
    # gpt-4o-mini routes to native openai instead of azure_foundry.
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    fake_payload = {
        "choices": [
            {
                "message": {
                    "content": "Resumen OpenAI listo.",
                }
            }
        ],
        "usage": {
            "prompt_tokens": 18,
            "completion_tokens": 9,
            "total_tokens": 27,
        },
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {
                "prompt": "Haz un resumen.",
                "model": "gpt-4o-mini",
                "system": "Eres Rick.",
                "max_tokens": 300,
                "temperature": 0.3,
            }
        )

    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini"
    assert result["text"] == "Resumen OpenAI listo."
    assert result["usage"]["total_tokens"] == 27

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == OPENAI_CHAT_COMPLETIONS_URL
    headers = _headers_lower(req)
    assert headers["authorization"] == "Bearer openai-test-key"
    body = json.loads(req.data.decode("utf-8"))
    assert body["model"] == "gpt-4o-mini"
    assert body["messages"][0] == {"role": "system", "content": "Eres Rick."}
    assert body["messages"][1] == {"role": "user", "content": "Haz un resumen."}


def test_kimi_alias_routes_to_azure_foundry(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key")
    assert _detect_provider("Kimi-K2.5") == "azure_foundry"


def test_anthropic_success_with_mocked_urllib(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    fake_payload = {
        "content": [
            {"type": "text", "text": "Resumen Anthropic."},
            {"type": "text", "text": " Segundo bloque."},
        ],
        "usage": {
            "input_tokens": 12,
            "output_tokens": 8,
        },
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {
                "prompt": "Resume este texto.",
                "model": "claude-3-5-sonnet",
                "system": "Escribe en espanol.",
                "max_tokens": 200,
                "temperature": 0.5,
            }
        )

    assert result["provider"] == "anthropic"
    assert result["model"] == "claude-3-5-sonnet"
    assert result["text"] == "Resumen Anthropic. Segundo bloque."
    assert result["usage"]["prompt_tokens"] == 12
    assert result["usage"]["completion_tokens"] == 8
    assert result["usage"]["total_tokens"] == 20

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == ANTHROPIC_MESSAGES_URL
    headers = _headers_lower(req)
    assert headers["x-api-key"] == "anthropic-test-key"
    assert headers["anthropic-version"] == "2023-06-01"
    body = json.loads(req.data.decode("utf-8"))
    assert body["model"] == "claude-3-5-sonnet"
    assert body["system"] == "Escribe en espanol."
    assert body["messages"][0] == {"role": "user", "content": "Resume este texto."}


def test_missing_all_keys_raises_error_for_openai_model(monkeypatch):
    """Sin Foundry, GITHUB_TOKEN ni OPENAI_API_KEY, lanza error claro."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AZURE_OPENAI"):
        handle_llm_generate({"prompt": "hola", "model": "gpt-4o"})


def test_missing_all_keys_raises_error_for_anthropic_model(monkeypatch):
    """Sin ANTHROPIC_API_KEY ni GITHUB_TOKEN, lanza error claro."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        handle_llm_generate({"prompt": "hola", "model": "claude-sonnet-4-20250514"})


def test_openai_without_foundry_nor_key_raises(monkeypatch):
    """Sin Foundry ni OPENAI_API_KEY, modelos GPT no son accesibles desde el Worker."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Azure AI Foundry"):
        handle_llm_generate({"prompt": "hola", "model": "gpt-5.3-codex"})


def test_claude_without_key_raises(monkeypatch):
    """Sin ANTHROPIC_API_KEY, Claude lanza error claro."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        handle_llm_generate({"prompt": "hola", "model": "claude-sonnet-4-6"})


# ---------------------------------------------------------------------------
# Azure AI Foundry tests
# ---------------------------------------------------------------------------

def test_azure_foundry_detect_provider_priority(monkeypatch):
    """Con Foundry configurado, modelos OpenAI van a azure_foundry."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-test-key")

    assert _detect_provider("gpt-5.3-codex") == "azure_foundry"
    assert _detect_provider("gpt-5.2") == "azure_foundry"
    assert _detect_provider("o3-mini") == "azure_foundry"


def test_azure_foundry_falls_back_to_openai_native(monkeypatch):
    """Sin Foundry pero con OPENAI_API_KEY, cae a openai nativo."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    assert _detect_provider("gpt-5.3-codex") == "openai"


def test_azure_foundry_classic_endpoint(monkeypatch):
    """Azure OpenAI clásico: endpoint .openai.azure.com con deployment en URL."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-123")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.3-codex")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "Respuesta de Azure Foundry (clásico)."}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "Test Foundry", "model": "gpt-5.3-codex", "max_tokens": 100}
        )

    assert result["text"] == "Respuesta de Azure Foundry (clásico)."
    assert result["provider"] == "azure_foundry"
    assert result["usage"]["total_tokens"] == 14

    req = mock_urlopen.call_args.args[0]
    # URL debe contener el deployment y api-version
    assert "openai/deployments/gpt-5.3-codex" in req.full_url
    assert f"api-version={AZURE_OPENAI_DEFAULT_API_VERSION}" in req.full_url
    # Auth debe usar header "api-key" (no Bearer)
    headers = _headers_lower(req)
    assert headers.get("api-key") == "az-key-123"


def test_azure_foundry_hub_endpoint(monkeypatch):
    """AI Foundry Hub: endpoint .services.ai.azure.com (nuevo formato)."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-hub.services.ai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-hub-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.3-codex")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "Respuesta de AI Foundry Hub."}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "Test Foundry Hub", "model": "gpt-5.3-codex"}
        )

    assert result["text"] == "Respuesta de AI Foundry Hub."
    req = mock_urlopen.call_args.args[0]
    # URL debe usar formato /models/{deployment}/ del Hub
    assert "models/gpt-5.3-codex/chat/completions" in req.full_url
    # Body debe incluir "model" para el Hub
    body = json.loads(req.data.decode("utf-8"))
    assert body.get("model") == "gpt-5.3-codex"


def test_azure_foundry_gpt52_uses_max_completion_tokens(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-123")
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "GPT52_OK"}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "Test GPT 5.2", "model": "gpt-5.2", "max_tokens": 100}
        )

    assert result["provider"] == "azure_foundry"
    assert result["text"] == "GPT52_OK"
    req = mock_urlopen.call_args.args[0]
    assert "openai/deployments/gpt-5.2-chat" in req.full_url  # gpt-5.2 alias still maps to gpt-5.2-chat
    body = json.loads(req.data.decode("utf-8"))
    assert "max_tokens" not in body
    assert "temperature" not in body
    assert body["max_completion_tokens"] == 100


def test_azure_foundry_gpt54_uses_max_completion_tokens(monkeypatch):
    """gpt-5.4 en Azure Foundry debe usar max_completion_tokens (no max_tokens)."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-123")
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "GPT54_OK"}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "Test GPT 5.4", "model": "gpt-5.4", "max_tokens": 200}
        )

    assert result["provider"] == "azure_foundry"
    assert result["text"] == "GPT54_OK"
    req = mock_urlopen.call_args.args[0]
    assert "openai/deployments/gpt-5.4" in req.full_url
    body = json.loads(req.data.decode("utf-8"))
    assert "max_tokens" not in body
    assert "temperature" not in body
    assert body["max_completion_tokens"] == 200


def test_azure_foundry_azure_gpt_54_alias_uses_max_completion_tokens(monkeypatch):
    """El alias azure_gpt_54 también debe caer en la rama de max_completion_tokens."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-123")
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "ALIAS_OK"}}],
        "usage": {"prompt_tokens": 4, "completion_tokens": 4, "total_tokens": 8},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        handle_llm_generate(
            {"prompt": "alias GPT 5.4", "model": "azure_gpt_54", "max_tokens": 150}
        )

    req = mock_urlopen.call_args.args[0]
    body = json.loads(req.data.decode("utf-8"))
    assert "max_tokens" not in body
    assert "temperature" not in body
    assert body["max_completion_tokens"] == 150


def test_azure_foundry_gpt53_codex_uses_max_completion_tokens(monkeypatch):
    """gpt-5.3-codex pertenece a la familia gpt-5.x y también debe usar max_completion_tokens."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-123")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.3-codex")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": "CODEX_OK"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 3, "total_tokens": 6},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        handle_llm_generate(
            {"prompt": "Test codex", "model": "gpt-5.3-codex", "max_tokens": 120}
        )

    req = mock_urlopen.call_args.args[0]
    body = json.loads(req.data.decode("utf-8"))
    assert "max_tokens" not in body
    assert "temperature" not in body
    assert body["max_completion_tokens"] == 120


def test_azure_foundry_uses_reasoning_content_when_content_is_empty(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-123")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "Kimi-K2.5")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    fake_payload = {
        "choices": [{"message": {"content": None, "reasoning_content": "KIMI_OK"}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ):
        result = handle_llm_generate(
            {"prompt": "Test Kimi", "model": "kimi_azure", "max_tokens": 100}
        )

    assert result["provider"] == "azure_foundry"
    assert result["text"] == "KIMI_OK"


def test_azure_foundry_missing_keys_raises(monkeypatch):
    """Sin AZURE_OPENAI_API_KEY lanza error descriptivo."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AZURE_OPENAI"):
        handle_llm_generate({"prompt": "test", "model": "gpt-5.3-codex"})


def test_anthropic_always_uses_native_key(monkeypatch):
    """Claude siempre usa ANTHROPIC_API_KEY (token sesión Pro)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-real-key")

    assert _detect_provider("claude-sonnet-4-6") == "anthropic"
    assert _detect_provider("claude-opus-4-6") == "anthropic"
    assert _detect_provider("claude-haiku-4-5") == "anthropic"
