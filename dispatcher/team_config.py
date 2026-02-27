"""
Dispatcher — Carga de configuración de equipos (S3).

Lee config/teams.yaml si existe; si no, usa capacidades por defecto.
Cada equipo puede tener: supervisor, description, requires_vm, roles, notion_page_id.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("dispatcher.team_config")

# Default (mismo que router.TEAM_CAPABILITIES) por si no hay YAML
DEFAULT_TEAM_CAPABILITIES = {
    "marketing": {
        "description": "Estrategia y ejecución digital",
        "requires_vm": False,
        "roles": ["supervisor", "seo", "social_media", "copywriting"],
        "supervisor": "Marketing Supervisor",
        "notion_page_id": None,
    },
    "advisory": {
        "description": "Asesoría personal y financiera",
        "requires_vm": False,
        "roles": ["supervisor", "financial", "lifestyle"],
        "supervisor": "Asesoría Personal Supervisor",
        "notion_page_id": None,
    },
    "improvement": {
        "description": "Mejora continua del sistema (OODA)",
        "requires_vm": True,
        "roles": ["supervisor", "sota_research", "self_evaluation", "implementation"],
        "supervisor": "Mejora Continua Supervisor",
        "notion_page_id": None,
    },
    "lab": {
        "description": "Experimentos y pruebas",
        "requires_vm": True,
        "roles": ["researcher"],
        "supervisor": None,
        "notion_page_id": None,
    },
    "system": {
        "description": "Tareas internas del sistema",
        "requires_vm": False,
        "roles": ["ping", "health", "admin"],
        "supervisor": None,
        "notion_page_id": None,
    },
}


def _find_teams_yaml() -> str | None:
    """Ruta a config/teams.yaml: env TEAMS_CONFIG_PATH, o repo root (parent de dispatcher)."""
    path = os.environ.get("TEAMS_CONFIG_PATH")
    if path and os.path.isfile(path):
        return path
    # Repo root = parent of dispatcher package
    repo_root = Path(__file__).resolve().parent.parent
    candidate = repo_root / "config" / "teams.yaml"
    if candidate.is_file():
        return str(candidate)
    return None


def get_team_capabilities() -> Dict[str, Dict[str, Any]]:
    """
    Carga equipos desde config/teams.yaml si existe; si no, devuelve DEFAULT_TEAM_CAPABILITIES.
    El dict devuelto tiene la forma { team_id: { description, requires_vm, roles, supervisor?, notion_page_id? } }.
    """
    path = _find_teams_yaml()
    if not path:
        logger.debug("No config/teams.yaml found, using defaults")
        return dict(DEFAULT_TEAM_CAPABILITIES)

    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed, using default team capabilities")
        return dict(DEFAULT_TEAM_CAPABILITIES)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s. Using defaults.", path, e)
        return dict(DEFAULT_TEAM_CAPABILITIES)

    teams = data.get("teams") if isinstance(data, dict) else None
    if not teams or not isinstance(teams, dict):
        logger.warning("teams.yaml has no 'teams' dict, using defaults")
        return dict(DEFAULT_TEAM_CAPABILITIES)

    out = {}
    for team_id, info in teams.items():
        if not isinstance(info, dict):
            continue
        out[team_id] = {
            "description": info.get("description", ""),
            "requires_vm": bool(info.get("requires_vm", True)),
            "roles": info.get("roles") or [],
            "supervisor": info.get("supervisor"),
            "notion_page_id": info.get("notion_page_id"),
        }
    if out:
        logger.info("Loaded %d teams from %s", len(out), path)
    return out if out else dict(DEFAULT_TEAM_CAPABILITIES)
