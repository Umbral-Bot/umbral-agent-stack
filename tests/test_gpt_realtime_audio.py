"""Tests para scripts/test_gpt_realtime_audio.py — audio gpt-realtime (cursor-api-david)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_TEXT = "Hola, este es un audio de prueba para el proyecto de Rick"
OUTPUT_REL = "assets/audio/rick_audio_prueba.wav"


class TestGptRealtimeAudioScript:
    """Test test_gpt_realtime_audio.py con mock del handler."""

    def test_success_saves_to_repo_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://cursor-api-david.cognitiveservices.azure.com")
        # Redirect repo root to tmp_path so we don't write in repo during test
        assets_audio = tmp_path / "assets" / "audio"
        assets_audio.mkdir(parents=True)

        mock_result = {
            "audio_b64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=",
            "audio_size_bytes": 100,
            "duration_seconds": 2.5,
            "transcript": AUDIO_TEXT,
            "voice": "alloy",
            "deployment": "gpt-realtime",
        }

        with patch("scripts.test_gpt_realtime_audio._REPO_ROOT", tmp_path):
            with patch("worker.tasks.azure_audio.handle_azure_audio_generate", return_value=mock_result) as mock_handler:
                from scripts.test_gpt_realtime_audio import main

                assert main() == 0
                call_args = mock_handler.call_args[0][0]
                assert call_args["text"] == AUDIO_TEXT
                assert call_args["deployment"] == "gpt-realtime"
                assert "rick_audio_prueba.wav" in call_args["output_path"]

    def test_no_api_key_returns_1(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        from scripts.test_gpt_realtime_audio import main

        assert main() == 1

    def test_handler_error_returns_1(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        (tmp_path / "assets" / "audio").mkdir(parents=True)

        with patch("scripts.test_gpt_realtime_audio._REPO_ROOT", tmp_path):
            with patch("worker.tasks.azure_audio.handle_azure_audio_generate", return_value={"error": "Azure no configurado"}):
                from scripts.test_gpt_realtime_audio import main

                assert main() == 1


class TestGptRealtimeConstants:
    """Constantes del script."""

    def test_audio_text(self):
        from scripts.test_gpt_realtime_audio import AUDIO_TEXT

        assert "Rick" in AUDIO_TEXT
        assert "audio de prueba" in AUDIO_TEXT

    def test_default_endpoint(self):
        from scripts.test_gpt_realtime_audio import DEFAULT_ENDPOINT

        assert "cursor-api-david.cognitiveservices.azure.com" in DEFAULT_ENDPOINT

    def test_output_path_in_repo(self):
        from scripts.test_gpt_realtime_audio import OUTPUT_REL_PATH

        assert OUTPUT_REL_PATH == "assets/audio/rick_audio_prueba.wav"
