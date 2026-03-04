"""Unit tests for azure.audio.generate task handler."""

import asyncio
import base64
import json
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.tasks.azure_audio import (
    DEFAULT_API_VERSION,
    DEFAULT_DEPLOYMENT,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_VOICE,
    SUPPORTED_VOICES,
    _pcm16_to_wav,
    handle_azure_audio_generate,
)


# ---------------------------------------------------------------------------
# WAV helper tests
# ---------------------------------------------------------------------------
class TestPcm16ToWav:
    def test_empty_pcm(self):
        wav = _pcm16_to_wav(b"")
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        # data chunk size should be 0
        data_idx = wav.index(b"data")
        size = struct.unpack("<I", wav[data_idx + 4 : data_idx + 8])[0]
        assert size == 0

    def test_known_pcm_data(self):
        pcm = b"\x00\x01" * 100  # 200 bytes = 100 samples
        wav = _pcm16_to_wav(pcm, sample_rate=24000)
        data_idx = wav.index(b"data")
        size = struct.unpack("<I", wav[data_idx + 4 : data_idx + 8])[0]
        assert size == 200
        assert wav[data_idx + 8 :] == pcm

    def test_sample_rate_in_header(self):
        pcm = b"\x00" * 48
        wav = _pcm16_to_wav(pcm, sample_rate=16000)
        # sample rate is at offset 24 in WAV
        sr = struct.unpack("<I", wav[24:28])[0]
        assert sr == 16000


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------
class TestHandleAzureAudioValidation:
    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="'text' is required"):
            handle_azure_audio_generate({"text": ""})

    def test_missing_text_raises(self):
        with pytest.raises(ValueError, match="'text' is required"):
            handle_azure_audio_generate({})

    def test_invalid_voice_raises(self):
        with pytest.raises(ValueError, match="Unsupported voice"):
            handle_azure_audio_generate({"text": "Hola", "voice": "darth_vader"})

    def test_missing_endpoint_returns_error(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        result = handle_azure_audio_generate({"text": "Hola", "voice": "alloy"})
        assert result["ok"] is False
        assert "no configurado" in result["error"]

    def test_missing_api_key_returns_error(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        result = handle_azure_audio_generate({"text": "Hola", "voice": "alloy"})
        assert result["ok"] is False
        assert "no configurado" in result["error"]


# ---------------------------------------------------------------------------
# Successful generation (mocked WebSocket)
# ---------------------------------------------------------------------------
class TestHandleAzureAudioGenerate:
    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-123")

    def _build_ws_mock(self, pcm_data: bytes, transcript: str = "Hola Rick"):
        """Build a mock websocket that replays a typical Realtime API session."""
        audio_b64 = base64.b64encode(pcm_data).decode()
        messages = [
            json.dumps({"type": "session.created"}),
            json.dumps({"type": "session.updated", "session": {"voice": "alloy"}}),
            json.dumps({"type": "conversation.item.created", "item": {}}),
            json.dumps({"type": "conversation.item.created", "item": {}}),
            json.dumps({"type": "response.audio.delta", "delta": audio_b64}),
            json.dumps({"type": "response.audio_transcript.done", "transcript": transcript}),
            json.dumps({
                "type": "response.done",
                "response": {
                    "status": "completed",
                    "usage": {
                        "total_tokens": 100,
                        "input_tokens": 20,
                        "output_tokens": 80,
                        "output_token_details": {"text_tokens": 10, "audio_tokens": 70},
                    },
                },
            }),
        ]
        ws_mock = AsyncMock()
        ws_mock.recv = AsyncMock(side_effect=messages)
        ws_mock.send = AsyncMock()
        ws_mock.__aenter__ = AsyncMock(return_value=ws_mock)
        ws_mock.__aexit__ = AsyncMock(return_value=False)
        return ws_mock

    @patch("worker.tasks.azure_audio._websockets")
    def test_successful_generation(self, mock_ws_module):
        pcm = b"\x00\x01" * 2400  # 4800 bytes = 0.1s at 24kHz mono 16bit
        ws_mock = self._build_ws_mock(pcm, transcript="Hola Rick")
        mock_ws_module.connect = MagicMock(return_value=ws_mock)

        result = handle_azure_audio_generate({"text": "Di hola Rick"})

        assert result["transcript"] == "Hola Rick"
        assert result["voice"] == "alloy"
        assert result["deployment"] == DEFAULT_DEPLOYMENT
        assert result["audio_size_bytes"] > len(pcm)  # WAV header adds bytes
        assert result["duration_seconds"] == 0.1
        assert "audio_b64" in result
        # Decode and verify WAV
        wav_bytes = base64.b64decode(result["audio_b64"])
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"
        assert result["usage"]["total_tokens"] == 100

    @patch("worker.tasks.azure_audio._websockets")
    def test_custom_voice_and_instructions(self, mock_ws_module):
        pcm = b"\x00" * 480
        ws_mock = self._build_ws_mock(pcm, transcript="test")
        mock_ws_module.connect = MagicMock(return_value=ws_mock)

        result = handle_azure_audio_generate({
            "text": "Prueba con coral",
            "voice": "coral",
            "instructions": "Habla en espanol mexicano.",
        })

        assert result["voice"] == "coral"
        # Verify session.update included instructions
        sent_calls = ws_mock.send.call_args_list
        session_msg = json.loads(sent_calls[0][0][0])
        assert session_msg["type"] == "session.update"
        assert "Habla en espanol" in session_msg["session"]["instructions"]

    @patch("worker.tasks.azure_audio._websockets")
    def test_output_path_saves_file(self, mock_ws_module, tmp_path):
        pcm = b"\x00\x01" * 100
        ws_mock = self._build_ws_mock(pcm)
        mock_ws_module.connect = MagicMock(return_value=ws_mock)

        out_file = str(tmp_path / "test_output.wav")
        result = handle_azure_audio_generate({
            "text": "Audio a disco",
            "output_path": out_file,
        })

        assert result["output_path"] == out_file
        with open(out_file, "rb") as f:
            content = f.read()
        assert content[:4] == b"RIFF"
        assert len(content) == result["audio_size_bytes"]

    @patch("worker.tasks.azure_audio._websockets")
    def test_websocket_url_format(self, mock_ws_module):
        pcm = b"\x00" * 48
        ws_mock = self._build_ws_mock(pcm)
        mock_ws_module.connect = MagicMock(return_value=ws_mock)

        handle_azure_audio_generate({"text": "test"})

        call_args = mock_ws_module.connect.call_args
        url = call_args[0][0]
        assert url.startswith("wss://test.openai.azure.com/openai/realtime")
        assert "deployment=gpt-realtime" in url
        assert f"api-version={DEFAULT_API_VERSION}" in url
        headers = call_args[1]["additional_headers"]
        assert headers["api-key"] == "test-key-123"

    @patch("worker.tasks.azure_audio._websockets")
    def test_custom_deployment(self, mock_ws_module):
        pcm = b"\x00" * 48
        ws_mock = self._build_ws_mock(pcm)
        mock_ws_module.connect = MagicMock(return_value=ws_mock)

        result = handle_azure_audio_generate({
            "text": "test",
            "deployment": "my-custom-realtime",
        })

        assert result["deployment"] == "my-custom-realtime"
        url = mock_ws_module.connect.call_args[0][0]
        assert "deployment=my-custom-realtime" in url


class TestHandleAzureAudioErrors:
    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-123")

    @patch("worker.tasks.azure_audio._websockets")
    def test_websocket_error_during_session(self, mock_ws_module):
        error_messages = [
            json.dumps({"type": "error", "error": {"message": "Invalid deployment"}}),
        ]
        ws_mock = AsyncMock()
        ws_mock.recv = AsyncMock(side_effect=error_messages)
        ws_mock.send = AsyncMock()
        ws_mock.__aenter__ = AsyncMock(return_value=ws_mock)
        ws_mock.__aexit__ = AsyncMock(return_value=False)
        mock_ws_module.connect = MagicMock(return_value=ws_mock)

        with pytest.raises(RuntimeError, match="Session error"):
            handle_azure_audio_generate({"text": "test"})

    @patch("worker.tasks.azure_audio._websockets")
    def test_response_error_event(self, mock_ws_module):
        messages = [
            json.dumps({"type": "session.updated", "session": {"voice": "alloy"}}),
            json.dumps({"type": "conversation.item.created", "item": {}}),
            json.dumps({"type": "error", "error": {"message": "Rate limited"}}),
        ]
        ws_mock = AsyncMock()
        ws_mock.recv = AsyncMock(side_effect=messages)
        ws_mock.send = AsyncMock()
        ws_mock.__aenter__ = AsyncMock(return_value=ws_mock)
        ws_mock.__aexit__ = AsyncMock(return_value=False)
        mock_ws_module.connect = MagicMock(return_value=ws_mock)

        with pytest.raises(RuntimeError, match="Realtime API error"):
            handle_azure_audio_generate({"text": "test"})


# ---------------------------------------------------------------------------
# Supported voices constant test
# ---------------------------------------------------------------------------
def test_supported_voices_includes_common():
    assert "alloy" in SUPPORTED_VOICES
    assert "echo" in SUPPORTED_VOICES
    assert "shimmer" in SUPPORTED_VOICES
    assert len(SUPPORTED_VOICES) >= 7


def test_default_constants():
    assert DEFAULT_DEPLOYMENT == "gpt-realtime"
    assert DEFAULT_VOICE == "alloy"
    assert DEFAULT_SAMPLE_RATE == 24000
    assert "2025" in DEFAULT_API_VERSION
