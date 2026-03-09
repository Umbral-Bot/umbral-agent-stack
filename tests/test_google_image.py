"""Unit tests for google.image.generate task handler."""

import base64
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from worker.tasks.google_image import DEFAULT_MODEL, handle_google_image_generate


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_missing_prompt_raises():
    with pytest.raises(ValueError, match="'prompt' is required"):
        handle_google_image_generate({})


def test_invalid_n_raises():
    with pytest.raises(ValueError, match="'n' must be between 1 and 4"):
        handle_google_image_generate({"prompt": "hola", "n": 0})


def test_missing_google_key_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY_NANO", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Google image API no configurada"):
        handle_google_image_generate({"prompt": "hola"})


@patch("worker.tasks.google_image.urllib.request.urlopen")
def test_successful_generation_saves_images(mock_urlopen, monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_API_KEY_NANO", "nano-test-key")
    image_bytes = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            }
                        }
                    ]
                }
            }
        ]
    }
    mock_urlopen.return_value = _DummyResponse(payload)

    result = handle_google_image_generate(
        {
            "prompt": "Arquitectura editorial",
            "n": 2,
            "output_dir": str(tmp_path),
            "filename_prefix": "editorial",
        }
    )

    assert result["ok"] is True
    assert result["count"] == 2
    assert result["model"] == DEFAULT_MODEL
    assert len(result["images"]) == 2
    for item in result["images"]:
        path = Path(item["output_path"])
        assert path.exists()
        assert path.read_bytes() == image_bytes
        assert item["mime_type"] == "image/png"

    req = mock_urlopen.call_args.args[0]
    body = json.loads(req.data.decode("utf-8"))
    assert body["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
    assert body["contents"][0]["parts"][0]["text"] == "Arquitectura editorial"


@patch("worker.tasks.google_image.urllib.request.urlopen")
def test_return_b64_includes_payload(mock_urlopen, monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_API_KEY_NANO", "nano-test-key")
    image_bytes = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 16)
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            }
                        }
                    ]
                }
            }
        ]
    }
    mock_urlopen.return_value = _DummyResponse(payload)

    result = handle_google_image_generate(
        {
            "prompt": "Portada",
            "return_b64": True,
            "output_dir": str(tmp_path),
        }
    )

    assert "b64_json" in result["images"][0]
    assert result["images"][0]["size_bytes"] == len(image_bytes)


def test_handler_registered():
    from worker.tasks import TASK_HANDLERS

    assert "google.image.generate" in TASK_HANDLERS
