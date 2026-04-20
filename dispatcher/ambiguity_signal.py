"""
Pure passive ambiguity signal detector for improvement-team tasks.

Implements the detection logic defined in docs/72-ambiguous-improvement-task-detection.md.
This module is deliberately passive: it is not imported by dispatcher routing, service,
or intent classifier. It produces an AmbiguitySignal dataclass that future runtime
wiring can consume, but today nothing calls it outside of tests.

Safety invariants:
- Only team "improvement" can produce is_ambiguous=True.
- Explicit handlers (system.ooda_report, system.self_eval, ping) always return False.
- No side effects, no I/O, no external imports.
- Deterministic: same inputs always produce same output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

# ── Keyword families from docs/72 §5 ────────────────────────────

_POSITIVE_FAMILIES: dict[str, list[str]] = {
    "general_improvement": [
        "mejora continua", "mejora del sistema", "mejorar el stack",
        "improvement cycle",
    ],
    "health_review": [
        "salud del sistema", "system health", "cómo estamos",
        "como estamos", "estado general", "health check interno",
        "salud del stack",
    ],
    "backlog_prioritization": [
        "backlog", "qué sigue", "que sigue", "priorizar mejoras",
        "next improvement", "pendientes de mejora", "prioriza",
        "priorización", "priorizacion",
    ],
    "friction_drift": [
        "fricción", "friccion", "drift", "friction",
        "sistema roto", "something broken", "qué falla", "que falla",
        "se está trabando", "se esta trabando",
    ],
    "ooda_nonspecific": [
        "ciclo ooda", "ooda review", "revisión ooda", "revision ooda",
        "proceso ooda",
    ],
    "selfeval_nonspecific": [
        "evaluar calidad", "quality review", "cómo lo estamos haciendo",
        "como lo estamos haciendo",
    ],
    "diagnostic": [
        "diagnostica", "diagnóstico", "diagnostico",
        "detecta drift", "oportunidades de mejora",
    ],
}

# Explicit handlers that must always route direct (docs/72 §4).
_EXPLICIT_HANDLERS: set[str] = {
    "system.ooda_report",
    "system.self_eval",
    "ping",
}

# Handler keywords in text that signal an explicit handler request.
_HANDLER_TEXT_PATTERNS: list[str] = [
    "system.ooda_report", "ooda_report",
    "system.self_eval", "self_eval",
]

# Negative signals: specific file/module targets or governance scope (docs/72 §4).
_NEGATIVE_FILE_RE = re.compile(
    r"(?:refactoriza|fix|arregla|modifica|cambia|edita|crea)\s+"
    r"(?:el archivo|el fichero|el módulo|el modulo|)?\s*"
    r"[\w/\\]+\.(?:py|yaml|yml|json|md|toml|cfg|txt|js|ts)",
    re.IGNORECASE,
)

_GOVERNANCE_KEYWORDS: list[str] = [
    "agent-governance", "agent governance",
    "roles del ecosistema", "ecosystem roles",
    "gobernanza de agentes",
]


@dataclass(frozen=True)
class AmbiguitySignal:
    """Detection result prepared for future observability/logging."""

    team: str | None
    is_ambiguous: bool
    candidate_for_supervisor_review: bool
    reason: str
    signal_type: str
    confidence: float
    matched_terms: tuple[str, ...]
    fallback: str = "direct"

    def to_log_fields(self) -> dict[str, Any]:
        """Return stable fields for logs/telemetry without side effects."""
        return {
            "team": self.team,
            "is_ambiguous": self.is_ambiguous,
            "candidate_for_supervisor_review": self.candidate_for_supervisor_review,
            "reason": self.reason,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "matched_terms": self.matched_terms,
            "fallback": self.fallback,
        }


def detect_ambiguity_signal(
    text: str,
    *,
    team: str | None = None,
    task: str | None = None,
    task_type: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AmbiguitySignal:
    """
    Detect whether a task for the improvement team is ambiguous.

    Returns an AmbiguitySignal with is_ambiguous=True only when:
    - team is "improvement"
    - no explicit handler is specified
    - the text matches positive keyword families from docs/72
    - no negative signals (specific file targets, governance scope) are present

    For any other team, empty input, or explicit handler: returns is_ambiguous=False.
    """
    team_key = team if isinstance(team, str) and team.strip() else None
    safe_text = text if isinstance(text, str) else ""
    safe_task = task if isinstance(task, str) and task.strip() else None

    # Gate 1: empty/missing input → safe false
    if not safe_text.strip() and not safe_task:
        return _not_ambiguous(team_key, reason="empty_input")

    # Gate 2: non-improvement team → always false
    if team_key != "improvement":
        return _not_ambiguous(team_key, reason="non_improvement_team")

    # Gate 3: explicit handler in task field → direct routing
    if safe_task and safe_task.strip() in _EXPLICIT_HANDLERS:
        return _not_ambiguous(
            team_key, reason="explicit_handler", signal_type="handler_match",
        )

    lower = safe_text.lower()

    # Gate 4: explicit handler mentioned in text
    for pattern in _HANDLER_TEXT_PATTERNS:
        if pattern in lower:
            return _not_ambiguous(
                team_key, reason="explicit_handler_in_text",
                signal_type="handler_match",
            )

    # Gate 5: specific file/module target → concrete scope, not ambiguous
    if _NEGATIVE_FILE_RE.search(lower):
        return _not_ambiguous(
            team_key, reason="specific_file_target",
            signal_type="negative_file",
        )

    # Gate 6: agent governance scope → not improvement supervisor's domain
    for kw in _GOVERNANCE_KEYWORDS:
        if kw in lower:
            return _not_ambiguous(
                team_key, reason="governance_scope",
                signal_type="negative_governance",
            )

    # Positive matching: scan keyword families
    matched_families: list[str] = []
    matched_terms: list[str] = []

    for family, keywords in _POSITIVE_FAMILIES.items():
        for kw in keywords:
            if kw in lower:
                if family not in matched_families:
                    matched_families.append(family)
                matched_terms.append(kw)

    if matched_families:
        confidence = min(0.9, 0.5 + 0.1 * len(matched_families))
        signal_type = matched_families[0] if len(matched_families) == 1 else "multi_signal"
        return AmbiguitySignal(
            team=team_key,
            is_ambiguous=True,
            candidate_for_supervisor_review=True,
            reason="positive_keyword_match",
            signal_type=signal_type,
            confidence=confidence,
            matched_terms=tuple(matched_terms),
            fallback="direct",
        )

    # No positive signals matched → not ambiguous
    return _not_ambiguous(team_key, reason="no_positive_signal")


def _not_ambiguous(
    team: str | None,
    *,
    reason: str,
    signal_type: str = "none",
) -> AmbiguitySignal:
    return AmbiguitySignal(
        team=team,
        is_ambiguous=False,
        candidate_for_supervisor_review=False,
        reason=reason,
        signal_type=signal_type,
        confidence=0.0,
        matched_terms=(),
        fallback="direct",
    )
