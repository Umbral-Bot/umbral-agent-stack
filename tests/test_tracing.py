"""Tests for worker.tracing Langfuse integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

import worker.tracing as tracing
from worker.tasks.llm import handle_llm_generate


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


@pytest.fixture(autouse=True)
def _reset_tracing_state(monkeypatch):
    monkeypatch.setattr(tracing, "_langfuse", None)
    monkeypatch.setattr(tracing, "_langfuse_initialized", False)


def test_tracing_disabled_without_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    assert tracing._get_langfuse() is None


def test_trace_llm_call_with_mock_langfuse(monkeypatch):
    fake_trace = MagicMock()
    fake_langfuse = MagicMock()
    fake_langfuse.trace.return_value = fake_trace
    monkeypatch.setattr(tracing, "_get_langfuse", lambda: fake_langfuse)

    tracing.trace_llm_call(
        model="gpt-4o-mini",
        provider="openai",
        prompt="hola",
        system="Eres Rick",
        response_text="ok",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        duration_ms=123.4,
        task_id="t-123",
        task_type="general",
    )

    fake_langfuse.trace.assert_called_once()
    trace_kwargs = fake_langfuse.trace.call_args.kwargs
    assert trace_kwargs["name"] == "llm.generate"
    assert trace_kwargs["metadata"]["provider"] == "openai"

    fake_trace.generation.assert_called_once()
    gen_kwargs = fake_trace.generation.call_args.kwargs
    assert gen_kwargs["name"] == "openai/gpt-4o-mini"
    assert gen_kwargs["usage"]["input"] == 10
    assert gen_kwargs["usage"]["output"] == 5
    assert gen_kwargs["usage"]["total"] == 15


def test_llm_generate_works_with_tracing_hook(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")
    fake_payload = {
        "candidates": [{"content": {"parts": [{"text": "respuesta"}]}}],
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3, "totalTokenCount": 8},
    }

    with (
        patch("worker.tasks.llm.urllib.request.urlopen", return_value=_DummyResponse(fake_payload)),
        patch("worker.tasks.llm.trace_llm_call") as mock_trace,
    ):
        result = handle_llm_generate({"prompt": "hola", "model": "gemini-2.5-flash"})

    assert result["text"] == "respuesta"
    mock_trace.assert_called_once()


def test_llm_generate_works_when_tracing_raises(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")
    fake_payload = {
        "candidates": [{"content": {"parts": [{"text": "respuesta"}]}}],
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3, "totalTokenCount": 8},
    }

    with (
        patch("worker.tasks.llm.urllib.request.urlopen", return_value=_DummyResponse(fake_payload)),
        patch("worker.tasks.llm.trace_llm_call", side_effect=RuntimeError("lf down")),
    ):
        result = handle_llm_generate({"prompt": "hola", "model": "gemini-2.5-flash"})

    assert result["text"] == "respuesta"
