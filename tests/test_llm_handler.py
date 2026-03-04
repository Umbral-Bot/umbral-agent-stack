"""Unit tests for llm.generate task handler."""

import json
from unittest.mock import patch

import pytest

from worker.tasks.llm import (
    ANTHROPIC_MESSAGES_URL,
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
        ("gemini-2.5-flash", "gemini"),
        ("gpt-4o", "openai"),
        ("o1", "openai"),
        ("o3-mini", "openai"),
        ("claude-3-5-sonnet", "anthropic"),
        ("unknown-model", "gemini"),
    ],
)
def test_detect_provider_cases(model, expected):
    assert _detect_provider(model) == expected


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

    assert result["model"] == "gemini-2.5-flash"
    assert "Oportunidades: digitalizacion BIM." in result["text"]
    assert result["usage"]["prompt_tokens"] == 22
    assert result["usage"]["completion_tokens"] == 14
    assert result["usage"]["total_tokens"] == 36

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == f"{GEMINI_BASE_URL}/gemini-2.5-flash:generateContent?key=google-test-key"
    body = json.loads(req.data.decode("utf-8"))
    assert body["generationConfig"]["maxOutputTokens"] == 256
    assert body["generationConfig"]["temperature"] == 0.4
    assert body["contents"][-1]["parts"][0]["text"] == "Dame un resumen ejecutivo."


def test_openai_success_with_mocked_urllib(monkeypatch):
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


def test_missing_openai_api_key_raises_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not configured"):
        handle_llm_generate({"prompt": "hola", "model": "gpt-4o"})


def test_missing_anthropic_api_key_raises_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not configured"):
        handle_llm_generate({"prompt": "hola", "model": "claude-sonnet-4-20250514"})
