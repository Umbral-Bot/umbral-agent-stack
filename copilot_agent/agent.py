"""
Copilot Agent — BYOK agentic orchestrator using GitHub Copilot SDK.

Uses Azure OpenAI as the LLM provider (BYOK — Bring Your Own Key) and
connects to the Umbral MCP server for Worker tools.

Architecture:
    CopilotClient (SDK subprocess)
      → Session (Azure BYOK provider)
         → MCP server (stdio) → Worker HTTP API → 85 task handlers

Env vars:
    AZURE_OPENAI_ENDPOINT  — Azure OpenAI endpoint (required)
    AZURE_OPENAI_API_KEY   — Azure OpenAI API key (required)
    WORKER_TOKEN           — Worker API token (for MCP server)
    WORKER_URL             — Worker URL (default: http://localhost:8088)
    GITHUB_TOKEN           — GitHub PAT for Copilot SDK auth (optional for BYOK)
    COPILOT_SDK_LOG_LEVEL  — SDK log level (default: warn)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

from copilot import CopilotClient, CopilotSession, SubprocessConfig

logger = logging.getLogger("copilot_agent")

# Repo root for MCP server path
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _get_azure_provider_config() -> dict[str, Any]:
    """Build Azure OpenAI BYOK provider config."""
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
    if not endpoint or not api_key:
        raise EnvironmentError(
            "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set for BYOK mode."
        )
    return {
        "type": "azure",
        "base_url": endpoint,
        "api_key": api_key,
        "azure": {
            "api_version": "2024-12-01-preview",
        },
    }


def _get_mcp_server_config() -> dict[str, dict[str, Any]]:
    """Build MCP server config pointing to our local mcp_server."""
    worker_token = os.environ.get("WORKER_TOKEN", "")
    worker_url = os.environ.get("WORKER_URL", "http://localhost:8088")
    python_exe = sys.executable

    return {
        "umbral-worker": {
            "type": "stdio",
            "command": python_exe,
            "args": ["-m", "mcp_server"],
            "cwd": str(_REPO_ROOT),
            "env": {
                "WORKER_TOKEN": worker_token,
                "WORKER_URL": worker_url,
            },
        }
    }


def _get_system_message() -> dict[str, Any]:
    """Build Rick's system message for the Copilot session."""
    return {
        "text": (
            "Sos Rick, el agente operativo de Umbral BIM. "
            "Tenés acceso a 85 herramientas del Worker que cubren: "
            "Notion, Linear, Gmail, Google Calendar, Figma, n8n, Make, "
            "investigación web, generación LLM, documentos, audio, imágenes, "
            "browser automation, Windows desktop, y más. "
            "Usá las herramientas del MCP server 'umbral-worker' para ejecutar tareas. "
            "Respondé en español salvo que el usuario pida otro idioma. "
            "Sé conciso y orientado a la acción."
        ),
    }


class UmbralCopilotAgent:
    """
    High-level agent that wraps the Copilot SDK with Azure BYOK + MCP tools.

    Usage:
        agent = UmbralCopilotAgent()
        await agent.start()
        result = await agent.run("Listá las tareas pendientes en Linear")
        await agent.stop()
    """

    def __init__(
        self,
        model: str = "gpt-5.4",
        log_level: str = "warn",
    ):
        self.model = model
        self._log_level = os.environ.get("COPILOT_SDK_LOG_LEVEL", log_level)
        self._client: Optional[CopilotClient] = None
        self._session: Optional[CopilotSession] = None

    async def start(self) -> None:
        """Initialize Copilot client and create a session with BYOK + MCP."""
        github_token = os.environ.get("GITHUB_TOKEN", "")
        config = SubprocessConfig(
            log_level=self._log_level,
            github_token=github_token or None,
            use_stdio=True,
        )

        self._client = CopilotClient(config=config, auto_start=True)
        await self._client.start()

        provider = _get_azure_provider_config()
        mcp_servers = _get_mcp_server_config()

        self._session = await self._client.create_session(
            model=self.model,
            provider=provider,
            mcp_servers=mcp_servers,
            system_message=_get_system_message(),
            on_permission_request=lambda ctx: True,  # auto-approve tool calls
        )
        logger.info("Copilot session started (model=%s, BYOK=Azure, MCP=umbral-worker)", self.model)

    async def run(self, prompt: str, timeout: float = 120.0) -> dict[str, Any]:
        """
        Send a prompt to the agent and wait for the response.

        Returns dict with:
            - text: the agent's text response
            - tool_calls: list of tools invoked (if any)
            - raw_event: the raw SessionEvent
        """
        if not self._session:
            raise RuntimeError("Agent not started. Call start() first.")

        event = await self._session.send_and_wait(prompt, timeout=timeout)

        if event is None:
            return {"text": "", "tool_calls": [], "raw_event": None, "error": "timeout"}

        text = ""
        tool_calls = []
        raw = event

        # Extract text from event
        if hasattr(event, "content"):
            text = str(event.content)
        elif hasattr(event, "data") and isinstance(event.data, dict):
            text = event.data.get("content", "")
            tool_calls = event.data.get("tool_calls", [])

        return {
            "text": text,
            "tool_calls": tool_calls,
            "raw_event": raw,
        }

    async def stop(self) -> None:
        """Tear down session and client."""
        if self._session:
            try:
                await self._session.destroy()
            except Exception:
                pass
            self._session = None
        if self._client:
            try:
                await self._client.stop()
            except Exception:
                pass
            self._client = None
        logger.info("Copilot agent stopped.")

    async def __aenter__(self) -> "UmbralCopilotAgent":
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()
