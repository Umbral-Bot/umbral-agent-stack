"""
Tests for the Copilot Agent — Phase 4.

Validates:
- Azure BYOK provider config generation
- MCP server config generation
- System message generation
- Agent initialization and environment validation
- Config shapes match SDK expectations

Run:
    python -m pytest tests/test_copilot_agent.py -v
"""

import os
import sys
from unittest.mock import patch

import pytest

# copilot SDK is an optional dependency (not in worker/requirements.txt,
# only in pyproject.toml). Skip the entire module if not installed.
pytest.importorskip("copilot", reason="github-copilot-sdk not installed")

from copilot_agent.agent import (
    UmbralCopilotAgent,
    _get_azure_provider_config,
    _get_mcp_server_config,
    _get_system_message,
    _REPO_ROOT,
)


# ---------------------------------------------------------------------------
# Azure BYOK provider config
# ---------------------------------------------------------------------------


class TestAzureProviderConfig:
    def test_valid_config(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://my-resource.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "sk-test-123")
        config = _get_azure_provider_config()
        assert config["type"] == "azure"
        assert config["base_url"] == "https://my-resource.openai.azure.com"
        assert config["api_key"] == "sk-test-123"
        assert config["azure"]["api_version"] == "2024-12-01-preview"

    def test_missing_endpoint_raises(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "sk-test-123")
        with pytest.raises(EnvironmentError, match="AZURE_OPENAI_ENDPOINT"):
            _get_azure_provider_config()

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://my-resource.openai.azure.com")
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="AZURE_OPENAI_API_KEY"):
            _get_azure_provider_config()

    def test_empty_endpoint_raises(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "sk-test")
        with pytest.raises(EnvironmentError):
            _get_azure_provider_config()


# ---------------------------------------------------------------------------
# MCP server config
# ---------------------------------------------------------------------------


class TestMCPServerConfig:
    def test_config_shape(self, monkeypatch):
        monkeypatch.setenv("WORKER_TOKEN", "test-token")
        monkeypatch.setenv("WORKER_URL", "http://localhost:8088")
        config = _get_mcp_server_config()
        assert "umbral-worker" in config
        srv = config["umbral-worker"]
        assert srv["type"] == "stdio"
        assert srv["command"] == sys.executable
        assert "-m" in srv["args"]
        assert "mcp_server" in srv["args"]
        assert srv["env"]["WORKER_TOKEN"] == "test-token"
        assert srv["env"]["WORKER_URL"] == "http://localhost:8088"

    def test_cwd_is_repo_root(self, monkeypatch):
        monkeypatch.setenv("WORKER_TOKEN", "x")
        config = _get_mcp_server_config()
        assert config["umbral-worker"]["cwd"] == str(_REPO_ROOT)

    def test_default_worker_url(self, monkeypatch):
        monkeypatch.delenv("WORKER_URL", raising=False)
        monkeypatch.setenv("WORKER_TOKEN", "x")
        config = _get_mcp_server_config()
        assert config["umbral-worker"]["env"]["WORKER_URL"] == "http://localhost:8088"


# ---------------------------------------------------------------------------
# System message
# ---------------------------------------------------------------------------


class TestSystemMessage:
    def test_has_text(self):
        msg = _get_system_message()
        assert "text" in msg
        assert "Rick" in msg["text"]
        assert "85" in msg["text"]
        assert "umbral-worker" in msg["text"]


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class TestUmbralCopilotAgent:
    def test_default_model(self):
        agent = UmbralCopilotAgent()
        assert agent.model == "gpt-5.4"

    def test_custom_model(self):
        agent = UmbralCopilotAgent(model="gpt-4.1")
        assert agent.model == "gpt-4.1"

    def test_run_without_start_raises(self):
        agent = UmbralCopilotAgent()
        import asyncio
        with pytest.raises(RuntimeError, match="not started"):
            asyncio.get_event_loop().run_until_complete(agent.run("test"))

    def test_stop_without_start_is_safe(self):
        agent = UmbralCopilotAgent()
        import asyncio
        # Should not raise
        asyncio.get_event_loop().run_until_complete(agent.stop())

    def test_context_manager_protocol(self):
        """Agent supports async context manager."""
        assert hasattr(UmbralCopilotAgent, "__aenter__")
        assert hasattr(UmbralCopilotAgent, "__aexit__")
