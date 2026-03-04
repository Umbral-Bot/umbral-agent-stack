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
    "configure", "change", "update", "activate", "deactivate",
    "modify", "adjust", "set", "enable", "disable",
]

# Team keywords — same vocabulary as linear_team_router._TEAM_KEYWORDS
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

# Direct mention patterns: @marketing, @advisory, etc.
_TEAM_MENTION_RE = re.compile(
    r"@(" + "|".join(_TEAM_KEYWORDS.keys()) + r")\b",
    re.IGNORECASE,
)

ECHO_PREFIX = "Rick:"


# ── Data structures ──────────────────────────────────────────────

@dataclass(frozen=True)
class IntentResult:
    intent: str          # question | task | instruction | echo
    confidence: str      # high | medium | low


# ── Public API ───────────────────────────────────────────────────

def classify_intent(text: str) -> IntentResult:
    """
    Classify a comment's intent using simple heuristics.

    Priority:
        1. Contains '?' → question (high confidence)
        2. Starts with action verb → task
        3. Starts with config verb → instruction
        4. Contains action verb anywhere → task (medium)
        5. Contains config verb anywhere → instruction (medium)
        6. Fallback → echo
    """
    if not text or not text.strip():
        return IntentResult(intent="echo", confidence="low")

    cleaned = text.strip()

    # 1. Question — anywhere in text
    if "?" in cleaned:
        return IntentResult(intent="question", confidence="high")

    lower = cleaned.lower()
    # Extract first word for verb-first detection
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

    Priority:
        1. Direct @mention  → that team
        2. Keyword scoring   → highest-scoring team
        3. Fallback          → "system"
    """
    if not text:
        return "system"

    # 1. Direct @mention
    match = _TEAM_MENTION_RE.search(text)
    if match:
        return match.group(1).lower()

    # 2. Keyword scoring (same algorithm as linear_team_router.infer_team_from_text)
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

    # 3. Fallback
    return "system"


def build_envelope(
    text: str,
    comment_id: str,
    intent: IntentResult,
    team: str,
) -> dict:
    """
    Build a TaskEnvelope based on classified intent and team.

    Returns a dict ready to be passed to TaskQueue.enqueue().
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

    if intent.intent == "question":
        # Acknowledge the question and mark as pending research
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
        # Route the task to the detected team
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

    else:  # echo — backward compat
        base["task_type"] = "general"
        base["task"] = "notion.add_comment"
        base["input"] = {
            "text": f"{ECHO_PREFIX} Recibido. (comment_id={short_id}...)",
        }

    return base
