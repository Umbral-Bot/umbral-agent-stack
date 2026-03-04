"""Unit tests for llm.generate task handler."""

import json
from unittest.mock import patch

import pytest

from worker.tasks.llm import (
    ANTHROPIC_MESSAGES_URL,
    AZURE_OPENAI_DEFAULT_API_VERSION,
    GEMINI_BASE_URL,
    GITHUB_MODELS_URL,
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


def test_handle_llm_generate_requires_prompt():
    with pytest.raises(ValueError, match="prompt"):
        handle_llm_generate({})


def test_handle_llm_generate_requires_google_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY not configured"):
        handle_llm_generate({"prompt": "Resume tendencias de mercado BIM"})


@pytest.mark.parametrize(
    "model,expected",
    [
        ("gemini-3.1-pro-preview-customtools", "gemini"),
        ("gemini-1.5-pro", "gemini"),
        ("unknown-model", "gemini"),
    ],
)
def test_detect_provider_gemini_cases(model, expected, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert _detect_provider(model) == expected


@pytest.mark.parametrize("model", ["gpt-4o", "o1", "o3-mini", "gpt-4o-mini"])
def test_detect_provider_openai_models_use_github_models(model, monkeypatch):
    """Sin Foundry, GPT usa GitHub Models (GITHUB_TOKEN) sobre OPENAI_API_KEY."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    assert _detect_provider(model) == "github_models"


@pytest.mark.parametrize("model", ["claude-3-5-sonnet", "claude-3-haiku", "claude-sonnet-4-20250514"])
def test_detect_provider_claude_models_use_github_models(model, monkeypatch):
    """Sin ANTHROPIC_API_KEY, Claude usa GitHub Models (sin Foundry)."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    assert _detect_provider(model) == "github_models"


def test_detect_provider_openai_fallback_without_github_token(monkeypatch):
    """Sin Foundry ni GITHUB_TOKEN, cae a OPENAI_API_KEY nativo."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert _detect_provider("gpt-4o") == "openai"


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
    ) as mock_urlopen:
        result = handle_llm_generate(
            {
                "prompt": "Dame un resumen ejecutivo.",
                "max_tokens": 256,
                "temperature": 0.4,
            }
        )

    assert result["model"] == "gemini-3.1-pro-preview-customtools"
    assert "Oportunidades: digitalizacion BIM." in result["text"]
    assert result["usage"]["prompt_tokens"] == 22
    assert result["usage"]["completion_tokens"] == 14
    assert result["usage"]["total_tokens"] == 36

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == f"{GEMINI_BASE_URL}/gemini-3.1-pro-preview-customtools:generateContent?key=google-test-key"
    body = json.loads(req.data.decode("utf-8"))
    assert body["generationConfig"]["maxOutputTokens"] == 256
    assert body["generationConfig"]["temperature"] == 0.4
    assert body["contents"][-1]["parts"][0]["text"] == "Dame un resumen ejecutivo."


def test_openai_success_with_mocked_urllib(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
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


def test_github_models_success_gpt4o(monkeypatch):
    """GitHub Models provider con GPT-4o usando GITHUB_TOKEN (sin Foundry)."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_github_token")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    fake_payload = {
        "choices": [
            {"message": {"content": "Respuesta via GitHub Models."}}
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 7,
            "total_tokens": 17,
        },
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "Hola", "model": "gpt-4o", "max_tokens": 200}
        )

    assert result["model"] == "gpt-4o"
    assert result["text"] == "Respuesta via GitHub Models."
    assert result["usage"]["total_tokens"] == 17

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == GITHUB_MODELS_URL
    headers = _headers_lower(req)
    assert headers["authorization"] == "Bearer ghp_test_github_token"
    body = json.loads(req.data.decode("utf-8"))
    assert body["model"] == "gpt-4o"


def test_github_models_success_claude(monkeypatch):
    """GitHub Models provider con Claude usando GITHUB_TOKEN (sin ANTHROPIC_API_KEY)."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_github_token")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    fake_payload = {
        "choices": [
            {"message": {"content": "Respuesta Claude via GitHub Models."}}
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
    }

    with patch(
        "worker.tasks.llm.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_llm_generate(
            {"prompt": "Resume esto.", "model": "claude-3-5-sonnet-20241022"}
        )

    assert result["model"] == "claude-3-5-sonnet-20241022"
    assert "GitHub Models" in result["text"]
    req = mock_urlopen.call_args.args[0]
    assert req.full_url == GITHUB_MODELS_URL
    headers = _headers_lower(req)
    assert headers["authorization"] == "Bearer ghp_test_github_token"


def test_github_models_missing_token_raises(monkeypatch):
    """Sin GITHUB_TOKEN ni Foundry, lanza error claro."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AZURE_OPENAI"):
        handle_llm_generate({"prompt": "hola", "model": "gpt-4o"})


# ---------------------------------------------------------------------------
# Azure AI Foundry tests
# ---------------------------------------------------------------------------

def test_azure_foundry_detect_provider_priority(monkeypatch):
    """Azure Foundry tiene prioridad sobre GitHub Models para modelos OpenAI."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-test-key")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_also_available")

    # Azure Foundry debe ganar sobre GitHub Models
    assert _detect_provider("gpt-5.3-codex") == "azure_foundry"
    assert _detect_provider("gpt-4o") == "azure_foundry"
    assert _detect_provider("o3-mini") == "azure_foundry"


def test_azure_foundry_falls_back_to_github_models(monkeypatch):
    """Sin Foundry configurado, GPT vuelve a GitHub Models."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fallback")

    assert _detect_provider("gpt-5.3-codex") == "github_models"


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


def test_azure_foundry_missing_keys_raises(monkeypatch):
    """Sin AZURE_OPENAI_API_KEY lanza error descriptivo."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mi-recurso.openai.azure.com")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AZURE_OPENAI"):
        handle_llm_generate({"prompt": "test", "model": "gpt-5.3-codex"})


def test_anthropic_native_priority_over_github_models(monkeypatch):
    """Con ANTHROPIC_API_KEY presente, usa Anthropic nativo (no GitHub Models)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-real-key")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_also_present")

    # Anthropic nativo debe tener prioridad sobre GitHub Models para Claude
    assert _detect_provider("claude-sonnet-4-6") == "anthropic"
    assert _detect_provider("claude-opus-4-6") == "anthropic"
