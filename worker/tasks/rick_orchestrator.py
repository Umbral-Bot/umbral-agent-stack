"""Task: rick.orchestrator.triage — Handler v0 (Opción C minimal, task 032).

Triage de mentions @rick desde Notion (vía dispatcher.rick_mention adapter).

Diseño v0 (ver /tmp/032/design.md):
- Pipeline interno hard-coded (NO LLM, NO subagent OpenClaw, NO gateway).
- Comando reconocido: `/health` substring → self-call al worker /health → reply en Notion.
- Comando no reconocido → reply honesto "no implementado en triage v0" (SOUL Regla 22).
- El reply lo postea el handler mismo en `page_id` recibido vía notion_client.add_comment.

Out of scope v0 (defer task 033 post-Vertex-Fase-1 2026-05-14):
- Comandos /status, /version.
- Razonamiento LLM o invocación al subagente rick-orchestrator (Opción A).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import httpx

from .. import notion_client

logger = logging.getLogger("worker.tasks.rick_orchestrator")

_HEALTH_KEYWORDS = ("/health",)
_DEFAULT_WORKER_URL = "http://127.0.0.1:8088"
_HTTP_TIMEOUT_SECONDS = 5.0
_REPLY_MAX_CHARS = 1800


def _classify_command(text: str) -> str:
    """Classify the user's intent. v0: only /health."""
    if not text:
        return "unknown"
    lowered = text.lower()
    if any(kw in lowered for kw in _HEALTH_KEYWORDS):
        return "health"
    return "unknown"


def _format_health_reply(payload: Dict[str, Any]) -> str:
    """Format /health JSON for human-readable Notion reply."""
    pretty = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if len(pretty) > _REPLY_MAX_CHARS:
        pretty = pretty[: _REPLY_MAX_CHARS - 20] + "\n…(truncated)"
    return f"Worker /health response:\n```json\n{pretty}\n```"


def _format_unknown_reply(text: str) -> str:
    snippet = (text or "")[:200]
    return (
        "Comando no reconocido en triage v0. "
        "Comandos disponibles: `/health`. "
        "Razonamiento libre y comandos extendidos: pendiente task 033 (post Vertex Fase 1, 2026-05-14). "
        f"\n\nTexto recibido: `{snippet}`"
    )


def _format_health_error_reply(error: str) -> str:
    return (
        "No pude consultar el worker /health (gap honesto, SOUL Regla 22).\n"
        f"Error: `{error[:300]}`\n"
        "Posibles causas: worker reiniciando, puerto 8088 no escuchando, timeout."
    )


def _self_call_health() -> Dict[str, Any]:
    """GET worker /health (loopback). Returns parsed JSON or raises."""
    base = os.environ.get("WORKER_INTERNAL_URL", _DEFAULT_WORKER_URL).rstrip("/")
    url = f"{base}/health"
    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def handle_rick_orchestrator_triage(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a Rick mention triage envelope (Ola 1b adapter output).

    Expected input keys (from dispatcher/rick_mention.py):
        text (str): Snippet of the comment text (max 500 chars).
        comment_id (str): Notion comment id (used for traceability).
        page_id (str | None): Page where the comment lives — reply target.
        page_kind (str | None): e.g. "control_room".
        author (str | None): Notion user id of the commenter (already allowlisted).
        trace_id (str | None): Trace id for log correlation.

    Returns:
        {
            "command": "health" | "unknown",
            "reply_posted": bool,
            "reply_comment_id": str | None,
            "page_id": str | None,
            "trace_id": str | None,
            "health": dict | None,    # only when command == "health" and self-call ok
            "error": str | None,
        }
    """
    text = str(input_data.get("text") or "")
    page_id = input_data.get("page_id")
    comment_id = input_data.get("comment_id")
    trace_id = input_data.get("trace_id")

    command = _classify_command(text)
    logger.info(
        "rick.orchestrator.triage classify command=%s comment=%s trace=%s",
        command,
        (comment_id or "?")[:8],
        (trace_id or "?")[:8],
    )

    health_payload: Dict[str, Any] | None = None
    error: str | None = None

    if command == "health":
        try:
            health_payload = _self_call_health()
            reply_text = _format_health_reply(health_payload)
        except Exception as exc:  # noqa: BLE001 — gap honesto SOUL Regla 22
            error = f"{type(exc).__name__}: {exc}"
            reply_text = _format_health_error_reply(error)
            logger.warning("rick.orchestrator.triage /health self-call failed: %s", error)
    else:
        reply_text = _format_unknown_reply(text)

    reply_posted = False
    reply_comment_id: str | None = None
    if page_id:
        try:
            reply = notion_client.add_comment(page_id=page_id, text=reply_text)
            reply_posted = True
            if isinstance(reply, dict):
                reply_comment_id = reply.get("comment_id") or reply.get("id")
            logger.info(
                "rick.orchestrator.triage reply posted page=%s reply=%s trace=%s",
                page_id[:8],
                (reply_comment_id or "?")[:8],
                (trace_id or "?")[:8],
            )
        except Exception as exc:  # noqa: BLE001 — gap honesto, NO inventar
            err_msg = f"{type(exc).__name__}: {exc}"
            error = (error + " | " if error else "") + f"reply_failed={err_msg}"
            logger.exception("rick.orchestrator.triage reply post failed: %s", err_msg)
    else:
        error = (error + " | " if error else "") + "no_page_id_in_envelope"
        logger.warning("rick.orchestrator.triage missing page_id in envelope; reply skipped")

    return {
        "command": command,
        "reply_posted": reply_posted,
        "reply_comment_id": reply_comment_id,
        "page_id": page_id,
        "trace_id": trace_id,
        "health": health_payload,
        "error": error,
    }
