"""Unit tests for llm.generate task handler."""

import json
from unittest.mock import patch

import pytest

from worker.tasks.llm import GEMINI_BASE_URL, handle_llm_generate


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_handle_llm_generate_requires_prompt():
    with pytest.raises(ValueError, match="prompt"):
        handle_llm_generate({})


def test_handle_llm_generate_requires_google_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY not configured"):
        handle_llm_generate({"prompt": "Resume tendencias de mercado BIM"})


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
        result = handle_llm_generate({"prompt": "Dame un resumen ejecutivo.", "max_tokens": 256, "temperature": 0.4})

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
