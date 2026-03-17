"""
Smart Notion Reply Pipeline — generates real answers to Control Room questions.

Instead of just acknowledging ("Investigando..."), this module:
1. Runs research.web via Worker to gather context
2. Uses llm.generate to synthesize a coherent answer
3. Posts the answer back as a Notion comment

Falls back gracefully:
- research fails → answer with LLM only (no web context)
- LLM fails → post the old-style acknowledgment template
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
import threading
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from client.worker_client import WorkerClient
from dispatcher.queue import TaskQueue
from dispatcher.scheduler import TaskScheduler
from dispatcher.intent_classifier import IntentResult, build_envelope
from dispatcher.workflow_engine import WorkflowEngine

logger = logging.getLogger("dispatcher.smart_reply")

# ── Workflow engine (lazy singleton) ────────────────────────────

_workflow_engine: Optional[WorkflowEngine] = None


def _get_workflow_engine(wc: WorkerClient) -> WorkflowEngine:
    """Return a (lazily initialized) WorkflowEngine singleton."""
    global _workflow_engine
    if _workflow_engine is None:
        from pathlib import Path

        config_path = Path(__file__).resolve().parent.parent / "config" / "team_workflows.yaml"
        _workflow_engine = WorkflowEngine(config_path, wc)
        logger.info("WorkflowEngine initialized (teams: %s)", _workflow_engine.get_teams())
    else:
        # Update worker client in case it changed
        _workflow_engine.wc = wc
    return _workflow_engine

ECHO_PREFIX = "Rick:"
_RESEARCH_TIMEOUT = 15.0  # seconds for research.web call
_LLM_TIMEOUT = 20.0       # seconds for llm.generate call
_MAX_RESEARCH_RESULTS = 3

# ── System prompt for answer synthesis ──────────────────────────

_ANSWER_SYSTEM_PROMPT = (
    "Eres Rick, asistente operativo de Umbral Group. "
    "Responde de forma concisa, profesional y útil. "
    "Si tienes datos de búsqueda web, úsalos como contexto pero sintetiza — "
    "no copies textualmente. Responde en el mismo idioma que la pregunta. "
    "Máximo 3 párrafos."
)

_TASK_PLAN_SYSTEM_PROMPT = (
    "Eres Rick, asistente operativo de Umbral Group. "
    "Te piden ejecutar una tarea. Descompón la tarea en 2-5 pasos concretos y accionables. "
    "Responde en el mismo idioma que la solicitud. Sé breve y directo."
)


# ── Public API ──────────────────────────────────────────────────

def handle_smart_reply(
    comment_text: str,
    comment_id: str,
    intent_obj: IntentResult,
    team: str,
    wc: WorkerClient,
    queue: TaskQueue,
    scheduler: TaskScheduler,
) -> None:
    """
    Generate a smart reply and post it to Notion.

    Runs in the caller's thread (the poller loop). If the whole pipeline
    takes too long the caller can wrap this in a thread with a timeout.

    Args:
        comment_text: The original comment text from Notion.
        comment_id: Notion comment ID.
        intent_obj: Classified IntentResult.
        team: Target team.
        wc: WorkerClient for calling the Worker API.
        queue: TaskQueue for enqueueing sub-tasks.
        scheduler: TaskScheduler for enqueueing scheduled tasks.
    """
    short_id = comment_id[:8] if comment_id else "unknown"
    intent = intent_obj.intent
    logger.info("Smart reply for [%s] comment %s: %.60s", intent, short_id, comment_text)

    try:
        if intent == "question":
            _handle_question(comment_text, comment_id, team, wc)
        elif intent == "task":
            _handle_task(comment_text, comment_id, team, wc, queue)
        elif intent == "scheduled_task":
            _handle_scheduled_task(comment_text, comment_id, team, wc, scheduler, intent_obj)
        elif intent == "instruction":
            _handle_instruction(comment_text, comment_id, team, wc)
        else:
            # echo — just acknowledge
            _post_comment(wc, f"{ECHO_PREFIX} Recibido. (comment_id={short_id}...)")
    except Exception:
        logger.exception("Smart reply pipeline failed for comment %s, posting fallback", short_id)
        _post_fallback(wc, comment_id, intent)


# ── Intent handlers ─────────────────────────────────────────────

def _handle_scheduled_task(
    text: str, comment_id: str, team: str, wc: WorkerClient, scheduler: TaskScheduler, intent_obj: IntentResult
) -> None:
    short_id = comment_id[:8]
    
    # Generate envelope
    envelope = build_envelope(text, comment_id, intent_obj, team)
    
    scheduler.schedule(envelope, intent_obj.run_at)
    
    # Format a nice reply
    recurrence_str = f" (Recurrencia: {intent_obj.recurrence})" if intent_obj.recurrence else ""
    time_str = intent_obj.run_at.strftime("%Y-%m-%d %H:%M UTC")
    
    reply = (
        f"{ECHO_PREFIX} Tarea programada para el {time_str}{recurrence_str}.\n\n"
        f"(comment_id={short_id}...)"
    )
    _post_comment(wc, reply)
    logger.info("Scheduled task posted and scheduled for %s, comment %s", time_str, short_id)

def _handle_question(text: str, comment_id: str, team: str, wc: WorkerClient) -> None:
    """Research + LLM → answer."""
    short_id = comment_id[:8]

    # 1. Try web research
    research_context = _do_research(wc, text)

    # 2. Build prompt
    if research_context:
        prompt = (
            f"Pregunta del usuario: {text}\n\n"
            f"Contexto de búsqueda web:\n{research_context}\n\n"
            f"Genera una respuesta informada basada en este contexto."
        )
    else:
        prompt = (
            f"Pregunta del usuario: {text}\n\n"
            f"No tengo resultados de búsqueda web. "
            f"Responde con tu conocimiento general."
        )

    # 3. Generate answer
    answer = _do_llm_generate(wc, prompt, _ANSWER_SYSTEM_PROMPT)
    if not answer:
        _post_fallback(wc, comment_id, "question")
        return

    # 4. Post answer
    # If the answer is too long (e.g. composite research report), create a dedicated page
    if len(answer) > 1500 or answer.count("\n") > 15:
        # Title based on the prompt/question
        title = f"Respuesta a: {text[:60]}"
        if len(text) > 60:
            title += "..."
            
        try:
            page_res = wc.run("notion.create_report_page", {
                "title": title,
                "content": answer,
                "metadata": {
                    "source": "smart_reply",
                    "original_question": text[:200]
                }
            })
            page_url = page_res.get("result", {}).get("page_url", "")
            if page_url:
                reply = f"{ECHO_PREFIX} He generado un informe detallado para tu consulta. Puedes leerlo aquí: {page_url}\n\n(comment_id={short_id}...)"
            else:
                reply = f"{ECHO_PREFIX} {answer[:1900]}...\n\n(comment_id={short_id}...)"
        except Exception:
            logger.exception("Failed to create report page for long answer, falling back to comment")
            reply = f"{ECHO_PREFIX} {answer[:1900]}...\n\n(comment_id={short_id}...)"
    else:
        # Short answer fits in a comment
        reply = f"{ECHO_PREFIX} {answer}\n\n(comment_id={short_id}...)"
        
    _post_comment(wc, reply)
    logger.info("Smart reply posted for question %s (research=%s, length=%d)", short_id, bool(research_context), len(answer))


def _handle_task(
    text: str, comment_id: str, team: str, wc: WorkerClient, queue: TaskQueue
) -> None:
    """Execute team workflow if available, else LLM plan + enqueue."""
    short_id = comment_id[:8]

    # --- Try workflow engine first ---
    engine = _get_workflow_engine(wc)
    if engine.has_workflow(team):
        _handle_task_with_workflow(text, comment_id, team, wc, engine)
        return

    # --- Fallback: LLM plan + enqueue (original behavior) ---
    prompt = f"Tarea solicitada: {text}\n\nDescompón en pasos concretos."
    plan = _do_llm_generate(wc, prompt, _TASK_PLAN_SYSTEM_PROMPT)

    if not plan:
        _post_fallback(wc, comment_id, "task")
        return

    reply = (
        f"{ECHO_PREFIX} Plan para equipo [{team}]:\n\n"
        f"{plan}\n\n"
        f"Procesando... (comment_id={short_id}...)"
    )
    _post_comment(wc, reply)

    # Enqueue the original task for the team to execute
    import uuid
    envelope = {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": team,
        "source": "smart_reply",
        "source_comment_id": comment_id,
        "task_type": "general",
        "task": "notion.add_comment",
        "input": {"original_request": text, "plan": plan},
    }
    queue.enqueue(envelope)
    logger.info("Task plan posted and enqueued for team [%s], comment %s", team, short_id)


def _handle_task_with_workflow(
    text: str,
    comment_id: str,
    team: str,
    wc: WorkerClient,
    engine: WorkflowEngine,
) -> None:
    """Execute a team workflow and post the result."""
    short_id = comment_id[:8]
    workflow_name = engine.get_default_workflow(team)

    # Extract a topic from the comment text (first 120 chars as topic)
    topic = text.strip()[:120]

    _post_comment(
        wc,
        f"{ECHO_PREFIX} Ejecutando workflow [{workflow_name}] para equipo [{team}]... (comment_id={short_id}...)",
    )

    context = {
        "topic": topic,
        "text": text,
        "team": team,
    }

    result = engine.execute_workflow(team, workflow_name, context)

    if result["ok"]:
        final = result.get("final_result", "")
        steps_info = f"{result['steps_completed']}/{result['steps_total']} pasos completados"

        if final and len(final) > 1500:
            # Long result → try Notion page
            try:
                page_res = wc.run("notion.create_report_page", {
                    "title": f"[{team}] Workflow: {workflow_name} — {topic[:60]}",
                    "content": final,
                    "metadata": {
                        "source": "workflow_engine",
                        "team": team,
                        "workflow": workflow_name,
                    },
                })
                page_url = page_res.get("result", {}).get("page_url", "")
                if page_url:
                    reply = (
                        f"{ECHO_PREFIX} Workflow [{workflow_name}] completado ({steps_info}).\n"
                        f"Resultado detallado: {page_url}\n\n(comment_id={short_id}...)"
                    )
                else:
                    reply = f"{ECHO_PREFIX} Workflow [{workflow_name}] completado ({steps_info}).\n\n{final[:1900]}\n\n(comment_id={short_id}...)"
            except Exception:
                logger.exception("Failed to create report page for workflow result")
                reply = f"{ECHO_PREFIX} Workflow [{workflow_name}] completado ({steps_info}).\n\n{final[:1900]}\n\n(comment_id={short_id}...)"
        elif final:
            reply = (
                f"{ECHO_PREFIX} Workflow [{workflow_name}] completado ({steps_info}).\n\n"
                f"{final}\n\n(comment_id={short_id}...)"
            )
        else:
            reply = f"{ECHO_PREFIX} Workflow [{workflow_name}] completado ({steps_info}). (comment_id={short_id}...)"

        _post_comment(wc, reply)
    else:
        error = result.get("error", "unknown error")
        reply = (
            f"{ECHO_PREFIX} Workflow [{workflow_name}] para [{team}] terminó con errores: "
            f"{error}\n\n(comment_id={short_id}...)"
        )
        _post_comment(wc, reply)

    logger.info(
        "Workflow '%s' for team '%s': ok=%s, %d/%d steps",
        workflow_name, team, result["ok"],
        result["steps_completed"], result["steps_total"],
    )


def _handle_instruction(text: str, comment_id: str, team: str, wc: WorkerClient) -> None:
    """Confirm instruction received and register a follow-up task in Notion."""
    short_id = comment_id[:8]
    reply = (
        f"{ECHO_PREFIX} Instrucción registrada. "
        f"Procesando configuración. (comment_id={short_id}...)"
    )
    _post_comment(wc, reply)
    telegram_sent = False
    try:
        wc.run(
            "notion.upsert_task",
            {
                "task_id": f"notion-instruction-{short_id}",
                "status": "queued",
                "team": team or "system",
                "task": "notion_instruction_followup",
                "task_name": f"Instrucción desde Notion: {text[:90]}",
                "input_summary": text,
                "result_summary": "Pendiente de seguimiento desde Control Room y runtime principal",
                "source": "notion_poll",
                "source_kind": "instruction_comment",
                "trace_id": comment_id,
            },
        )
    except Exception:
        logger.warning("Failed to register Notion instruction task for %s", short_id, exc_info=True)
    try:
        telegram_sent = _handoff_instruction_to_rick(text=text, comment_id=comment_id)
    except Exception:
        logger.warning("Failed to hand off instruction %s to Rick", short_id, exc_info=True)
    if telegram_sent:
        try:
            wc.run(
                "notion.upsert_task",
                {
                    "task_id": f"notion-instruction-{short_id}",
                    "status": "in_progress",
                    "team": team or "system",
                    "task": "notion_instruction_followup",
                    "task_name": f"Instrucción desde Notion: {text[:90]}",
                    "input_summary": text,
                    "result_summary": "Seguimiento inyectado al runtime principal de Rick",
                    "source": "notion_poll",
                    "source_kind": "instruction_comment",
                    "trace_id": comment_id,
                },
            )
        except Exception:
            logger.warning("Failed to annotate mirrored instruction task for %s", short_id, exc_info=True)
    logger.info("Instruction acknowledged for comment %s", short_id)


# ── Internal helpers ────────────────────────────────────────────

def _is_external_reference_instruction(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "http://",
        "https://",
        "linkedin.com",
        "post",
        "publicaci",
        "newsletter",
        "referencia",
        "benchmark",
        "perfil",
        "funnel",
        "landing",
        "youtube",
    )
    return any(marker in lowered for marker in markers)


def _build_instruction_message(text: str, comment_id: str) -> str:
    short_id = comment_id[:8]
    lines = [
        "Rick: seguimiento activo desde Control Room.",
        f"Referencia interna: notion-instruction-{short_id}",
        f"Instruccion: {text.strip()}",
        "",
        "Esto no queda cerrado solo con registro en Notion.",
    ]
    if _is_external_reference_instruction(text):
        lines.extend(
            [
                "Si es una referencia externa o URL concreta, debes reabrir el caso en tu canal principal y cerrarlo solo cuando exista:",
                "- evidencia real con tools sobre la fuente principal;",
                "- separacion entre evidencia, inferencia e hipotesis;",
                "- artefacto y trazabilidad proporcional en proyecto/entregable si aplica;",
                "- lenguaje de certeza coherente con la traza real.",
                "- si persistes en Notion para un proyecto activo, usa notion.upsert_deliverable; no cierres solo con notion.create_report_page;",
                "- si ya dejaste una pagina suelta en Control Room/OpenClaw, regularizala con entregable y luego archivala con notion.update_page_properties(archived=true).",
                "- no marques el caso como cerrado hasta que la tarea quede enlazada a Proyecto y Entregable, y el entregable quede enlazado a Proyecto y Tareas origen/Task ID origen coherente.",
            ]
        )
    else:
        lines.extend(
            [
                "Ejecuta el follow-up en tu canal principal y vuelve con trazabilidad real, no solo con confirmacion.",
                "- usa tools antes de responder;",
                "- deja artefacto o update proporcional si afecta proyecto activo;",
                "- cierra la tarea solo cuando el trabajo este realmente hecho.",
            ]
        )
    return "\n".join(lines)


def _load_openclaw_session_store() -> dict[str, Any]:
    override = os.environ.get("OPENCLAW_MAIN_SESSION_STORE", "").strip()
    if override:
        store_path = pathlib.Path(override)
    else:
        store_path = pathlib.Path.home() / ".openclaw" / "agents" / "main" / "sessions" / "sessions.json"
    if not store_path.exists():
        logger.info("OpenClaw session store not found at %s", store_path)
        return {}
    try:
        data = json.loads(store_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        logger.warning("Failed to read OpenClaw session store at %s", store_path, exc_info=True)
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_rick_main_session_id() -> str | None:
    forced = os.environ.get("OPENCLAW_MAIN_TELEGRAM_SESSION_ID", "").strip()
    if forced:
        return forced

    sessions = _load_openclaw_session_store()
    if not sessions:
        return None

    agent_id = os.environ.get("OPENCLAW_MAIN_AGENT_ID", "main").strip() or "main"
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        or os.environ.get("TELEGRAM_ALLOWLIST_ID", "").strip()
        or "1813248373"
    )
    preferred_key = f"agent:{agent_id}:telegram:slash:{chat_id}"

    preferred = sessions.get(preferred_key)
    if isinstance(preferred, dict):
        preferred_session_id = preferred.get("sessionId")
        if isinstance(preferred_session_id, str) and preferred_session_id.strip():
            return preferred_session_id.strip()

    candidates: list[tuple[int, str]] = []
    for session_key, payload in sessions.items():
        if not isinstance(payload, dict):
            continue
        origin = payload.get("origin") or {}
        if not isinstance(origin, dict):
            origin = {}
        provider = str(origin.get("provider") or "").strip().lower()
        from_id = str(origin.get("from") or "")
        to_id = str(origin.get("to") or "")
        if provider != "telegram":
            continue
        if chat_id not in session_key and chat_id not in from_id and chat_id not in to_id:
            continue
        session_id = str(payload.get("sessionId") or "").strip()
        if not session_id:
            continue
        updated_at = payload.get("updatedAt")
        try:
            sort_key = int(updated_at)
        except (TypeError, ValueError):
            sort_key = 0
        candidates.append((sort_key, session_id))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _run_openclaw_agent(message: str, session_id: str) -> bool:
    openclaw_bin = os.environ.get("OPENCLAW_BIN", "").strip() or str(pathlib.Path.home() / ".npm-global" / "bin" / "openclaw")
    cmd = [
        openclaw_bin,
        "agent",
        "--session-id",
        session_id,
        "--message",
        message,
        "--json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except Exception:
        logger.warning("OpenClaw agent handoff failed", exc_info=True)
        return False
    if result.returncode != 0:
        logger.warning(
            "OpenClaw agent handoff returned rc=%s stdout=%r stderr=%r",
            result.returncode,
            result.stdout[:1000],
            result.stderr[:1000],
        )
        return False
    logger.info("OpenClaw agent handoff succeeded for session %s", session_id)
    return True


def _send_telegram_message(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or os.environ.get("TELEGRAM_ALLOWLIST_ID", "1813248373").strip()
    if not token or not chat_id:
        logger.info("Telegram mirror skipped: missing TELEGRAM_BOT_TOKEN or chat id")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        logger.warning("Telegram mirror request failed", exc_info=True)
        return False
    if not data.get("ok"):
        logger.warning("Telegram mirror API error: %s", data)
        return False
    return True


def _handoff_instruction_to_rick(text: str, comment_id: str) -> bool:
    message = _build_instruction_message(text=text, comment_id=comment_id)
    session_id = _resolve_rick_main_session_id()
    if session_id and _run_openclaw_agent(message=message, session_id=session_id):
        return True
    return _send_telegram_message(message)


def _do_research(wc: WorkerClient, query: str) -> Optional[str]:
    """Call research.web and return formatted context, or None on failure."""
    try:
        result = wc.run("research.web", {
            "query": query,
            "count": _MAX_RESEARCH_RESULTS,
            "search_depth": "basic",
        })
        results = result.get("result", {}).get("results", [])
        if not results:
            logger.info("Research returned 0 results for: %.40s", query)
            return None

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            url = r.get("url", "")
            lines.append(f"{i}. {title}\n   {snippet}\n   Fuente: {url}")
        context = "\n\n".join(lines)
        logger.info("Research returned %d results for: %.40s", len(results), query)
        return context
    except Exception:
        logger.warning("Research failed for: %.40s", query, exc_info=True)
        return None


def _do_llm_generate(wc: WorkerClient, prompt: str, system: str) -> Optional[str]:
    """Call llm.generate and return the text, or None on failure."""
    try:
        result = wc.run("llm.generate", {
            "prompt": prompt,
            "system": system,
            "max_tokens": 800,
            "temperature": 0.5,
        })
        text = result.get("result", {}).get("text", "")
        if text:
            logger.info("LLM generated %d chars", len(text))
        return text or None
    except Exception:
        logger.warning("LLM generate failed", exc_info=True)
        return None


def _post_comment(wc: WorkerClient, text: str) -> None:
    """Post a comment to Notion Control Room via Worker."""
    try:
        wc.run("notion.add_comment", {"text": text})
    except Exception:
        logger.error("Failed to post comment to Notion", exc_info=True)


def _post_fallback(wc: WorkerClient, comment_id: str, intent: str) -> None:
    """Post the old-style acknowledgment when the smart pipeline fails."""
    short_id = comment_id[:8] if comment_id else "unknown"
    fallbacks = {
        "question": f"{ECHO_PREFIX} Pregunta recibida. Investigando y responderé pronto. (comment_id={short_id}...)",
        "task": f"{ECHO_PREFIX} Entendido. Tarea registrada. (comment_id={short_id}...)",
        "scheduled_task": f"{ECHO_PREFIX} Tarea programada registrada. (comment_id={short_id}...)",
        "instruction": f"{ECHO_PREFIX} Instrucción registrada. (comment_id={short_id}...)",
    }
    text = fallbacks.get(intent, f"{ECHO_PREFIX} Recibido. (comment_id={short_id}...)")
    _post_comment(wc, text)
    logger.info("Fallback reply posted for %s [%s]", short_id, intent)
