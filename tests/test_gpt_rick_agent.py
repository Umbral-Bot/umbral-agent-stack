"""Tests para scripts/test_gpt_rick_agent.py — acceso al agente Gpt-Rick (Azure AI Foundry)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestGptRickAgentScript:
    """Test test_gpt_rick_agent.py con mock HTTP."""

    def test_success_returns_0(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"output_text": "París"}
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("GPT_RICK_API_KEY", raising=False)

        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_resp
            from scripts.test_gpt_rick_agent import main

            assert main() == 0

    def test_success_output_structure_alternative(self, monkeypatch):
        """Respuesta con estructura output[] en lugar de output_text."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "output": [{"content": [{"type": "output_text", "text": "París"}]}],
        }
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("GPT_RICK_API_KEY", raising=False)

        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_resp
            from scripts.test_gpt_rick_agent import main

            assert main() == 0

    def test_401_returns_1(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "bad-key")

        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_resp
            from scripts.test_gpt_rick_agent import main

            assert main() == 1

    def test_no_api_key_returns_1(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GPT_RICK_API_KEY", raising=False)

        from scripts.test_gpt_rick_agent import main

        assert main() == 1

    def test_prefers_gpt_rick_api_key(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"output_text": "OK"}
        monkeypatch.setenv("GPT_RICK_API_KEY", "rick-key")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-key")

        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_resp
            from scripts.test_gpt_rick_agent import main

            assert main() == 0
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["headers"]["api-key"] == "rick-key"


class TestGptRickUrls:
    """URLs de los endpoints documentados."""

    def test_responses_url_default(self):
        from scripts.test_gpt_rick_agent import RESPONSES_URL

        assert "cursor-api-david.services.ai.azure.com" in RESPONSES_URL
        assert "rick-api-david-project" in RESPONSES_URL
        assert "Gpt-Rick" in RESPONSES_URL
        assert "responses" in RESPONSES_URL
        assert "2025-11-15-preview" in RESPONSES_URL

    def test_activity_protocol_url_default(self):
        from scripts.test_gpt_rick_agent import ACTIVITY_PROTOCOL_URL

        assert "activityprotocol" in ACTIVITY_PROTOCOL_URL
        assert "rick-api-david-project" in ACTIVITY_PROTOCOL_URL
        assert "Gpt-Rick" in ACTIVITY_PROTOCOL_URL
