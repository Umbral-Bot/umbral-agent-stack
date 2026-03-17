"""
Intent Classifier — Notion Poller intelligence layer (S5 Hackathon).

Classifies incoming Notion comments into intents and routes them to the
appropriate team.  All functions are pure (no I/O), making them easy to
unit-test without Redis or network calls.

Intents:
    question    — User is asking something (contains "?")
    task        — User wants something done (action verbs)
    instruction — User is configuring / changing system behavior
    echo        — Fallback — cannot classify (backward compat)
"""

from __future__ import annotations

import re
import uuid
import logging
from dataclasses import dataclass
from typing import Optional

from datetime import datetime, timedelta, timezone

logger = logging.getLogger("dispatcher.intent_classifier")

# ── Keyword banks ────────────────────────────────────────────────

# Action verbs → intent "task"
_TASK_VERBS: list[str] = [
    "haz", "crea", "genera", "escribe", "publica", "programa",
    "busca", "investiga", "analiza", "revisa", "diseña", "prepara",
    "envía", "envia", "redacta", "planifica", "ejecuta", "lanza",
    "create", "generate", "write", "publish", "search", "find",
    "research", "analyze", "review", "design", "prepare", "send",
    "draft", "plan", "execute", "launch", "run", "build", "make",
]

# Config verbs → intent "instruction"
_INSTRUCTION_VERBS: list[str] = [
    "configura", "cambia", "actualiza", "activa", "desactiva",
    "modifica", "ajusta", "establece", "define", "setea",
    "corrige", "rehaz", "reabre", "baja", "sube", "marca",
    "configure", "change", "update", "activate", "deactivate",
    "modify", "adjust", "set", "enable", "disable",
    "correct", "reopen", "lower", "raise", "mark",
]

# Team keywords
_TEAM_KEYWORDS: dict[str, list[str]] = {
    "marketing": [
        "marketing", "seo", "social media", "redes sociales", "contenido",
        "content", "copy", "copywriting", "publicidad", "post", "blog",
        "instagram", "twitter", "linkedin", "campaña", "campaign",
    ],
    "advisory": [
        "advisory", "asesoría", "asesoria", "consejo", "advice",
        "financiero", "finanzas", "finance", "lifestyle", "inversión",
        "inversion", "ahorro", "presupuesto", "budget", "portfolio",
        "cartera", "planificación", "planificacion",
    ],
    "improvement": [
        "improvement", "mejora", "ooda", "sota", "self-eval", "evaluación",
        "benchmark", "research", "implementación", "upgrade", "optimizar",
        "optimización", "refactor", "ciclo", "análisis",
    ],
    "lab": [
        "lab", "laboratorio", "experimento", "experiment", "prototipo",
        "prototype", "sandbox", "prueba", "test", "rpa", "automate",
    ],
    "system": [
        "system", "sistema", "infra", "infrastructure", "ping", "health",
        "admin", "deploy", "devops", "ci", "cd", "pipeline", "worker",
        "dispatcher", "redis", "docker",
    ],
}

_TEAM_MENTION_RE = re.compile(
    r"@(" + "|".join(_TEAM_KEYWORDS.keys()) + r")\b",
    re.IGNORECASE,
)

ECHO_PREFIX = "Rick:"


# ── Data structures ──────────────────────────────────────────────

@dataclass(frozen=True)
class IntentResult:
    intent: str          # question | task | instruction | echo | scheduled_task
    confidence: str      # high | medium | low
    run_at: Optional[datetime] = None
    recurrence: Optional[str] = None


# ── Public API ───────────────────────────────────────────────────

def parse_temporal_features(text: str) -> tuple[Optional[datetime], Optional[str]]:
    """
    Lightweight regex parser for temporal instructions.
    Returns (run_at_utc, recurrence_string).
    """
    lower = text.lower()
    now = datetime.now(timezone.utc)
    
    # 1. "en X horas"
    m_hours = re.search(r"en\s+(\d+)\s+horas?", lower)
    if m_hours:
        hours = int(m_hours.group(1))
        return now + timedelta(hours=hours), None
        
    # 2. "en X minutos" / "en X mins"
    m_mins = re.search(r"en\s+(\d+)\s+min", lower)
    if m_mins:
        mins = int(m_mins.group(1))
        return now + timedelta(minutes=mins), None
        
    # 3. "mañana a las HH" or "mañana a las HH:MM"
    m_manana = re.search(r"mañana a las\s+(\d{1,2})(?::(\d{2}))?", lower)
    if m_manana:
        hour = int(m_manana.group(1))
        minute = int(m_manana.group(2)) if m_manana.group(2) else 0
        tomorrow = now + timedelta(days=1)
        # Attempt to create datetime
        try:
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0), None
        except ValueError:
            pass # Invalid hour/minute
            
    # 4. "a las HH" (today)
    m_hoy = re.search(r"(?:hoy )?a las\s+(\d{1,2})(?::(\d{2}))?", lower)
    if m_hoy:
        hour = int(m_hoy.group(1))
        minute = int(m_hoy.group(2)) if m_hoy.group(2) else 0
        try:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1) # If it already passed today, assume tomorrow
            return target, None
        except ValueError:
            pass
            
    # 5. "todos los lunes"
    if "todos los lunes" in lower or "every monday" in lower:
        # Calculate next Monday
        days_ahead = 0 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        return next_monday, "every_monday"
        
    # 6. "todos los días" / "cada día" / "every day"
    if "todos los d" in lower or "cada d" in lower or "every day" in lower:
        tomorrow = now + timedelta(days=1)
        next_day = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        return next_day, "every_day"
        
    return None, None

def classify_intent(text: str) -> IntentResult:
    """
    Classify a comment's intent using simple heuristics.
    """
    if not text or not text.strip():
        return IntentResult(intent="echo", confidence="low")

    cleaned = text.strip()
    
    # Pre-check for temporal intents
    run_at, recurrence = parse_temporal_features(text)
    if run_at or recurrence:
        return IntentResult(
            intent="scheduled_task", 
            confidence="high", 
            run_at=run_at, 
            recurrence=recurrence
        )

    # 1. Question — anywhere in text
    if "?" in cleaned:
        return IntentResult(intent="question", confidence="high")

    lower = cleaned.lower()
    first_word = re.split(r"\s+", lower)[0] if lower else ""

    # 2–3. First word is an action/config verb (high confidence)
    if first_word in _TASK_VERBS:
        return IntentResult(intent="task", confidence="high")
    if first_word in _INSTRUCTION_VERBS:
        return IntentResult(intent="instruction", confidence="high")

    # 4–5. Verb appears anywhere (medium confidence)
    words = set(re.findall(r"\w+", lower))
    if words & set(_TASK_VERBS):
        return IntentResult(intent="task", confidence="medium")
    if words & set(_INSTRUCTION_VERBS):
        return IntentResult(intent="instruction", confidence="medium")

    # 6. Fallback
    return IntentResult(intent="echo", confidence="low")


def route_to_team(text: str) -> str:
    """
    Determine which team should handle the comment.
    """
    if not text:
        return "system"

    match = _TEAM_MENTION_RE.search(text)
    if match:
        return match.group(1).lower()

    text_lower = text.lower()
    scores: dict[str, int] = {}
    for team_key, keywords in _TEAM_KEYWORDS.items():
        score = sum(
            1 for kw in keywords
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
        )
        if score > 0:
            scores[team_key] = score

    if scores:
        best = max(scores, key=lambda k: scores[k])
        logger.debug("Team scores: %s → routed to: %s", scores, best)
        return best

    return "system"


def build_envelope(
    text: str,
    comment_id: str,
    intent: IntentResult,
    team: str,
) -> dict:
    """
    Build a TaskEnvelope based on classified intent and team.
    """
    task_id = str(uuid.uuid4())
    short_id = comment_id[:8] if comment_id else "unknown"

    base = {
        "schema_version": "0.1",
        "task_id": task_id,
        "team": team,
        "source": "notion_poller",
        "source_comment_id": comment_id,
    }
    
    if intent.run_at:
        base["run_at"] = intent.run_at.isoformat()
    if intent.recurrence:
        base["recurrence"] = intent.recurrence

    if intent.intent == "question":
        base["task_type"] = "research"
        base["task"] = "notion.add_comment"
        base["input"] = {
            "text": (
                f"{ECHO_PREFIX} Pregunta recibida. "
                f"Investigando y responderé pronto. "
                f"(comment_id={short_id}...)"
            ),
        }

    elif intent.intent == "task":
        base["task_type"] = "general"
        base["task"] = "notion.add_comment"
        base["input"] = {
            "text": (
                f"{ECHO_PREFIX} Entendido. "
                f"Creé tarea para equipo [{team}]. "
                f"(comment_id={short_id}...)"
            ),
            "original_request": text,
        }

    elif intent.intent == "instruction":
        base["team"] = "system"
        base["task_type"] = "instruction"
        base["task"] = "notion.add_comment"
        base["input"] = {
            "text": (
                f"{ECHO_PREFIX} Instrucción registrada. "
                f"Procesando configuración. "
                f"(comment_id={short_id}...)"
            ),
            "original_request": text,
        }

    elif intent.intent == "scheduled_task":
        base["task_type"] = "general"
        base["task"] = "notion.add_comment"
        base["input"] = {
            "text": (
                f"{ECHO_PREFIX} (Ejecutando tarea programada) "
                f"Equipo [{team}]. Tarea: {text} "
                f"(comment_id={short_id}...)"
            ),
            "original_request": text,
        }

    else:  # echo — backward compat
        base["task_type"] = "general"
        base["task"] = "notion.add_comment"
        base["input"] = {
            "text": f"{ECHO_PREFIX} Recibido. (comment_id={short_id}...)",
        }

    return base
