"""
Linear Team Router
==================
Mapea equipos/supervisores de config/teams.yaml a entidades de Linear:

- team_key → label names (ej. "Marketing", "Marketing Supervisor")
- instrucción de texto libre → equipo inferido (keyword scoring)
- Función principal: resolve_team_for_issue()

El router NO llama a la API de Linear; solo resuelve metadatos.
El cliente (linear_client) usa esos metadatos para crear/buscar labels.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger("worker.linear_team_router")

_TEAMS_CONFIG_PATH = Path(__file__).parent.parent / "config" / "teams.yaml"

# Keywords por equipo para inferencia desde texto libre (español + inglés)
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

# Colores en Linear para cada equipo
TEAM_LABEL_COLORS: dict[str, str] = {
    "marketing":   "#F59E0B",   # amber
    "advisory":    "#3B82F6",   # blue
    "improvement": "#8B5CF6",   # violet
    "lab":         "#10B981",   # emerald
    "system":      "#6B7280",   # gray
}
SUPERVISOR_LABEL_COLOR = "#EF4444"  # red — supervisor labels destacan


def load_teams_config() -> dict:
    """Carga config/teams.yaml y retorna el dict completo."""
    with open(_TEAMS_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def infer_team_from_text(text: str) -> Optional[str]:
    """
    Infiere el team_key a partir de texto libre (título + descripción).
    Retorna el equipo con mayor score de keywords, o None si no hay match.
    """
    if not text:
        return None

    text_lower = text.lower()
    scores: dict[str, int] = {}

    for team_key, keywords in _TEAM_KEYWORDS.items():
        score = sum(
            1 for kw in keywords
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
        )
        if score > 0:
            scores[team_key] = score

    if not scores:
        return None

    best = max(scores, key=lambda k: scores[k])
    logger.debug("[TeamRouter] Scores: %s → inferred: %s", scores, best)
    return best


def get_team_labels(team_key: str, teams_config: Optional[dict] = None) -> list[str]:
    """
    Retorna los label names de Linear para un equipo.
    Primer label: nombre del equipo capitalizado (ej. "Marketing").
    Segundo label: nombre del supervisor tal cual en teams.yaml, si existe.
    """
    if teams_config is None:
        teams_config = load_teams_config()

    teams = teams_config.get("teams", {})
    team = teams.get(team_key)
    if not team:
        return []

    labels: list[str] = []

    # Label del equipo
    labels.append(team_key.capitalize())

    # Label del supervisor (ya viene como display name en teams.yaml, ej. "Marketing Supervisor")
    supervisor = team.get("supervisor")
    if supervisor:
        labels.append(supervisor)

    return labels


def get_supervisor_display_name(team_key: str, teams_config: Optional[dict] = None) -> Optional[str]:
    """Retorna el display name del supervisor para un equipo, o None."""
    if teams_config is None:
        teams_config = load_teams_config()

    teams = teams_config.get("teams", {})
    team = teams.get(team_key)
    if not team:
        return None
    return team.get("supervisor") or None


def resolve_team_for_issue(
    team_key: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    teams_config: Optional[dict] = None,
) -> dict:
    """
    Resuelve todos los metadatos de equipo para crear un issue en Linear.

    Prioridad:
      1. team_key explícito
      2. Inferencia desde title + description

    Retorna:
        {
            "team_key": str | None,
            "labels": list[str],          # ej. ["Marketing", "Marketing Supervisor"]
            "label_colors": list[str],    # un color por label
            "supervisor_display_name": str | None,
            "inferred": bool,
        }
    """
    if teams_config is None:
        teams_config = load_teams_config()

    inferred = False
    resolved_key = team_key

    if not resolved_key:
        combined = " ".join(filter(None, [title, description]))
        resolved_key = infer_team_from_text(combined)
        if resolved_key:
            inferred = True
            logger.info("[TeamRouter] Equipo inferido: '%s'", resolved_key)

    if not resolved_key:
        logger.warning("[TeamRouter] No se pudo resolver equipo — issue sin labels de equipo")
        return {
            "team_key": None,
            "labels": [],
            "label_colors": [],
            "supervisor_display_name": None,
            "inferred": False,
        }

    labels = get_team_labels(resolved_key, teams_config)
    supervisor = get_supervisor_display_name(resolved_key, teams_config)

    # Colores: primero el del equipo, luego el del supervisor
    team_color = TEAM_LABEL_COLORS.get(resolved_key, "#6B7280")
    label_colors = [team_color] + [SUPERVISOR_LABEL_COLOR] * (len(labels) - 1)

    return {
        "team_key": resolved_key,
        "labels": labels,
        "label_colors": label_colors,
        "supervisor_display_name": supervisor,
        "inferred": inferred,
    }
