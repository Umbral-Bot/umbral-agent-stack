"""Tests for worker.tasks.rick_orchestrator (task 032).

Cubre:
- Comando /health → self-call mocked, JSON formateado, reply posteado.
- Comando desconocido → reply honesto SOUL Regla 22 (NO inventa JSON).
- Self-call falla → reply honesto con error real, no inventado.
- Envelope sin page_id → no crash, devuelve gap en `error`.
- Validación enums Team.RICK_ORCHESTRATOR + TaskType.TRIAGE aceptados (smoke contra HB del task 031).
- Handler registrado en TASK_HANDLERS.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import httpx
import pytest

from worker.models import TaskEnvelope, Team, TaskType
from worker.tasks import TASK_HANDLERS
from worker.tasks.rick_orchestrator import (
    RICK_REPLY_PREFIX,
    _classify_command,
    _format_health_error_reply,
    _format_health_reply,
    _format_unknown_reply,
    _with_prefix,
    handle_rick_orchestrator_triage,
)


# Fields that must NEVER appear in a David-facing reply (internal catalog/telemetry).
_LEAK_MARKERS = (
    "tasks_registered",
    "tasks_in_memory",
    "```json",
    "Worker /health response",
    "notion.write_transcript",  # a real handler name — proves no catalog echo
    "127.0.0.1",
    ":8088",
)


def _assert_no_leak(text: str) -> None:
    for marker in _LEAK_MARKERS:
        assert marker not in text, f"reply leaked internal marker: {marker!r}"


# ---------------------------------------------------------------------------
# Enum extension (HB fix from task 031)
# ---------------------------------------------------------------------------


def test_team_enum_includes_rick_orchestrator() -> None:
    assert Team("rick-orchestrator") is Team.RICK_ORCHESTRATOR


def test_task_type_enum_includes_triage() -> None:
    assert TaskType("triage") is TaskType.TRIAGE


def test_envelope_accepts_rick_orchestrator_triage_payload() -> None:
    """Reproduces the exact envelope shape produced by dispatcher/rick_mention.py
    that triggered HTTP 400 in task 031 — should now validate cleanly."""
    body = {
        "task_id": "abc123",
        "task": "rick.orchestrator.triage",
        "team": "rick-orchestrator",
        "task_type": "triage",
        "trace_id": "trace1",
        "input": {
            "kind": "notion.comment.mention",
            "comment_id": "c1",
            "page_id": "p1",
            "page_kind": "control_room",
            "author": "u1",
            "text": "@rick ping worker /health",
        },
    }
    env = TaskEnvelope.from_run_payload(body)
    assert env.team is Team.RICK_ORCHESTRATOR
    assert env.task_type is TaskType.TRIAGE
    assert env.task == "rick.orchestrator.triage"


# ---------------------------------------------------------------------------
# Handler registration (HC fix from task 031)
# ---------------------------------------------------------------------------


def test_handler_registered_in_task_handlers() -> None:
    assert "rick.orchestrator.triage" in TASK_HANDLERS
    assert TASK_HANDLERS["rick.orchestrator.triage"] is handle_rick_orchestrator_triage


# ---------------------------------------------------------------------------
# Command classifier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", [
    "@rick ping worker /health",
    "/HEALTH ahora",
    "hola @rick podés correr /health y devolverme json?",
])
def test_classify_command_health(text: str) -> None:
    assert _classify_command(text) == "health"


@pytest.mark.parametrize("text", [
    "",
    "@rick hola",
    "@rick generame un reporte de marketing",
    "/status",
])
def test_classify_command_unknown(text: str) -> None:
    assert _classify_command(text) == "unknown"


# ---------------------------------------------------------------------------
# Reply formatting (verifies SOUL Regla 22 — no fabricación)
# ---------------------------------------------------------------------------


def test_format_health_reply_sane_is_summary_without_catalog() -> None:
    """A3: healthy reply is a stable human summary, NOT the raw /health payload."""
    payload = {
        "ok": True,
        "version": "0.4.0",
        "ts": 123,
        "tasks_in_memory": 445,
        "tasks_registered": ["ping", "notion.write_transcript", "llm.generate"],
    }
    reply = _format_health_reply(payload)
    assert reply.startswith(RICK_REPLY_PREFIX)
    assert "Worker OK" in reply
    assert "3 handlers" in reply  # count only, never the names
    _assert_no_leak(reply)


def test_format_health_reply_degraded() -> None:
    """A3: ok=false renders as 'degradado', still no catalog leak."""
    payload = {"ok": False, "tasks_registered": ["ping"], "llm": False}
    reply = _format_health_reply(payload)
    assert "Worker degradado" in reply
    assert "LLM degradado" in reply
    assert "1 handlers" in reply
    _assert_no_leak(reply)


def test_format_health_reply_llm_field_summarized_coarsely() -> None:
    payload = {"ok": True, "tasks_registered": [], "llm_ok": True}
    reply = _format_health_reply(payload)
    assert "LLM operativo" in reply
    _assert_no_leak(reply)


def test_format_health_error_reply_hides_internals() -> None:
    """A3: health error surfaces only the error class, no URL/port/config."""
    reply = _format_health_error_reply("ConnectError: Connection refused to http://127.0.0.1:8088")
    assert reply.startswith(RICK_REPLY_PREFIX)
    assert "gap honesto" in reply.lower()
    assert "ConnectError" in reply
    _assert_no_leak(reply)


def test_with_prefix_is_idempotent() -> None:
    """A3 anti-loop: prefix applied once, never duplicated."""
    once = _with_prefix("Worker OK · 3 handlers · LLM desconocido")
    twice = _with_prefix(once)
    assert once == twice
    assert once.count(RICK_REPLY_PREFIX) == 1
    # An already-prefixed string is left untouched.
    assert _with_prefix("Rick: hola").count(RICK_REPLY_PREFIX) == 1


def test_format_unknown_reply_is_honest_gap() -> None:
    reply = _format_unknown_reply("@rick hacé algo raro")
    assert reply.startswith(RICK_REPLY_PREFIX)
    # Debe declarar el gap explícitamente — NO inventar respuesta.
    assert "no reconocido" in reply.lower()
    assert "/health" in reply
    assert "task 033" in reply  # referencia explícita a la deuda
    _assert_no_leak(reply)


# ---------------------------------------------------------------------------
# Handler integration (with mocks — no network, no Notion writes)
# ---------------------------------------------------------------------------


@patch("worker.tasks.rick_orchestrator.notion_client")
@patch("worker.tasks.rick_orchestrator.httpx.Client")
def test_triage_health_command_returns_json_and_posts_reply(
    mock_httpx_client: MagicMock, mock_notion: MagicMock,
) -> None:
    fake_response = MagicMock()
    fake_response.json.return_value = {"ok": True, "version": "0.4.0", "ts": 1}
    fake_response.raise_for_status.return_value = None
    mock_httpx_client.return_value.__enter__.return_value.get.return_value = fake_response
    mock_notion.add_comment.return_value = {"comment_id": "newCmt123"}

    result = handle_rick_orchestrator_triage({
        "text": "@rick ping worker /health",
        "comment_id": "origCmt",
        "page_id": "pageABC",
        "trace_id": "trace42",
    })

    assert result["command"] == "health"
    assert result["reply_posted"] is True
    assert result["reply_comment_id"] == "newCmt123"
    assert result["health"] == {"ok": True, "version": "0.4.0", "ts": 1}
    assert result["error"] is None
    # Reply posteado al page_id del envelope, saneado y con prefijo anti-loop.
    mock_notion.add_comment.assert_called_once()
    kwargs = mock_notion.add_comment.call_args.kwargs
    assert kwargs["page_id"] == "pageABC"
    assert kwargs["text"].startswith(RICK_REPLY_PREFIX)
    assert "Worker OK" in kwargs["text"]
    _assert_no_leak(kwargs["text"])


@patch("worker.tasks.rick_orchestrator.notion_client")
@patch("worker.tasks.rick_orchestrator.httpx.Client")
def test_triage_unknown_command_returns_honest_gap(
    mock_httpx_client: MagicMock, mock_notion: MagicMock,
) -> None:
    mock_notion.add_comment.return_value = {"comment_id": "gapReply"}

    result = handle_rick_orchestrator_triage({
        "text": "@rick generame un análisis de marketing",
        "comment_id": "origCmt",
        "page_id": "pageABC",
        "trace_id": "trace42",
    })

    assert result["command"] == "unknown"
    assert result["reply_posted"] is True
    assert result["health"] is None
    # Self-call al worker NO debe ocurrir para comandos unknown.
    mock_httpx_client.assert_not_called()
    posted_text = mock_notion.add_comment.call_args.kwargs["text"]
    assert posted_text.startswith(RICK_REPLY_PREFIX)
    assert "no reconocido" in posted_text.lower()
    # NO inventa JSON ni respuesta falsa.
    _assert_no_leak(posted_text)


@patch("worker.tasks.rick_orchestrator.notion_client")
@patch("worker.tasks.rick_orchestrator.httpx.Client")
def test_triage_health_self_call_failure_returns_honest_error(
    mock_httpx_client: MagicMock, mock_notion: MagicMock,
) -> None:
    mock_httpx_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
        "Connection refused"
    )
    mock_notion.add_comment.return_value = {"comment_id": "errReply"}

    result = handle_rick_orchestrator_triage({
        "text": "/health please",
        "comment_id": "origCmt",
        "page_id": "pageABC",
        "trace_id": "trace42",
    })

    assert result["command"] == "health"
    assert result["health"] is None
    assert result["error"] is not None
    assert "ConnectError" in result["error"]
    # Reply se postea con el tipo de error REAL, saneado (sin URL/puerto/config).
    posted_text = mock_notion.add_comment.call_args.kwargs["text"]
    assert posted_text.startswith(RICK_REPLY_PREFIX)
    assert "gap honesto" in posted_text.lower()
    assert "ConnectError" in posted_text
    _assert_no_leak(posted_text)


@patch("worker.tasks.rick_orchestrator.notion_client")
def test_triage_no_page_id_returns_gap_without_crash(mock_notion: MagicMock) -> None:
    result = handle_rick_orchestrator_triage({
        "text": "@rick generame algo",
        "comment_id": "origCmt",
        "page_id": None,
        "trace_id": "trace42",
    })
    assert result["reply_posted"] is False
    assert result["error"] is not None
    assert "no_page_id" in result["error"]
    mock_notion.add_comment.assert_not_called()
