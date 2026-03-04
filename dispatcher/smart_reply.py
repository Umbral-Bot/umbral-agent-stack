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

import logging
import threading
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
            _handle_instruction(comment_text, comment_id, wc)
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


def _handle_instruction(text: str, comment_id: str, wc: WorkerClient) -> None:
    """Confirm instruction received."""
    short_id = comment_id[:8]
    reply = (
        f"{ECHO_PREFIX} Instrucción registrada. "
        f"Procesando configuración. (comment_id={short_id}...)"
    )
    _post_comment(wc, reply)
    logger.info("Instruction acknowledged for comment %s", short_id)


# ── Internal helpers ────────────────────────────────────────────

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
