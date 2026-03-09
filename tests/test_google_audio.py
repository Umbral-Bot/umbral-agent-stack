"""Unit tests for google.audio.generate task handler."""

import base64
import json
import struct
from unittest.mock import patch

import pytest

from worker.tasks.google_audio import (
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    _detect_sample_rate,
    handle_google_audio_generate,
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


class TestGoogleAudioValidation:
    def test_missing_text_raises(self):
        with pytest.raises(ValueError, match="'text' is required"):
            handle_google_audio_generate({})

    def test_missing_google_key_returns_error(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        result = handle_google_audio_generate({"text": "Hola"})
        assert result["ok"] is False
        assert "no configurada" in result["error"]

    def test_detect_sample_rate_from_mime_type(self):
        assert _detect_sample_rate("audio/L16;codec=pcm;rate=24000") == 24000
        assert _detect_sample_rate("audio/L16") == 24000


class TestGoogleAudioGenerate:
    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")

    @patch("worker.tasks.google_audio.urllib.request.urlopen")
    def test_successful_generation(self, mock_urlopen):
        pcm = b"\x00\x01" * 2400
        fake_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/L16;codec=pcm;rate=24000",
                                    "data": base64.b64encode(pcm).decode("ascii"),
                                }
                            }
                        ]
                    }
                }
            ],
            "usageMetadata": {"totalTokenCount": 61},
        }
        mock_urlopen.return_value = _DummyResponse(fake_payload)

        result = handle_google_audio_generate({"text": "Hola Rick"})

        assert result["voice"] == DEFAULT_VOICE
        assert result["model"] == DEFAULT_MODEL
        assert result["duration_seconds"] == 0.1
        assert result["audio_size_bytes"] > len(pcm)
        wav_bytes = base64.b64decode(result["audio_b64"])
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"
        sample_rate = struct.unpack("<I", wav_bytes[24:28])[0]
        assert sample_rate == 24000

    @patch("worker.tasks.google_audio.urllib.request.urlopen")
    def test_custom_voice_instructions_and_output_path(self, mock_urlopen, tmp_path):
        pcm = b"\x00" * 480
        fake_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/L16;codec=pcm;rate=16000",
                                    "data": base64.b64encode(pcm).decode("ascii"),
                                }
                            }
                        ]
                    }
                }
            ],
            "usageMetadata": {"totalTokenCount": 33},
        }
        mock_urlopen.return_value = _DummyResponse(fake_payload)
        out_file = str(tmp_path / "google_tts.wav")

        result = handle_google_audio_generate(
            {
                "text": "Hola",
                "voice": "Puck",
                "instructions": "Habla con energia.",
                "output_path": out_file,
            }
        )

        assert result["voice"] == "Puck"
        assert result["output_path"] == out_file
        with open(out_file, "rb") as f:
            content = f.read()
        assert content[:4] == b"RIFF"
        sample_rate = struct.unpack("<I", content[24:28])[0]
        assert sample_rate == 16000

        req = mock_urlopen.call_args.args[0]
        body = json.loads(req.data.decode("utf-8"))
        assert body["systemInstruction"]["parts"][0]["text"] == "Habla con energia."
        assert body["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] == "Puck"

    @patch("worker.tasks.google_audio.urllib.request.urlopen")
    def test_missing_inline_data_raises(self, mock_urlopen):
        mock_urlopen.return_value = _DummyResponse({"candidates": [{"content": {"parts": [{"text": "No audio"}]}}]})
        with pytest.raises(RuntimeError, match="No audio inlineData"):
            handle_google_audio_generate({"text": "Hola"})
