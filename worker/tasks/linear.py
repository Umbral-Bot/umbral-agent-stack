"""
Tasks: Linear integration handlers.

- linear.create_issue: crear issue en Linear
- linear.list_teams: listar equipos
"""

from typing import Any, Dict

from .. import config
from .. import linear_client


def handle_linear_create_issue(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un issue en Linear.

    Input:
        title (str, required): Título del issue.
        team_id (str, optional): ID del equipo. Si no se pasa, usa team_key.
        team_key (str, optional): Clave del equipo (ej. "UMB"). Usar si no hay team_id.
        description (str, optional): Descripción del issue.
        assignee_id (str, optional): ID del usuario asignado.
        priority (int, optional): 0=Sin prioridad, 1=Urgente, 2=Alta, 3=Media, 4=Baja.

    Returns:
        {"ok": True, "id": "...", "identifier": "UMB-5", "title": "...", "url": "..."}
    """
    if not config.LINEAR_API_KEY:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    title = input_data.get("title")
    if not title:
        return {"ok": False, "error": "'title' is required"}

    team_id = input_data.get("team_id")
    team_key = input_data.get("team_key")

    if not team_id and team_key:
        team = linear_client.get_team_by_key(config.LINEAR_API_KEY, team_key)
        if not team:
            return {"ok": False, "error": f"Team key '{team_key}' not found"}
        team_id = team["id"]
    elif not team_id:
        # Usar el primer equipo disponible
        teams = linear_client.list_teams(config.LINEAR_API_KEY)
        if not teams:
            return {"ok": False, "error": "No teams found in Linear workspace"}
        team_id = teams[0]["id"]

    try:
        issue = linear_client.create_issue(
            api_key=config.LINEAR_API_KEY,
            team_id=team_id,
            title=title,
            description=input_data.get("description"),
            assignee_id=input_data.get("assignee_id"),
            priority=input_data.get("priority"),
        )
        return {"ok": True, **issue}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_linear_list_teams(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista equipos en Linear.

    Input: vacío o {}

    Returns:
        {"ok": True, "teams": [{"id": "...", "key": "UMB", "name": "Umbral"}, ...]}
    """
    if not config.LINEAR_API_KEY:
        return {"ok": False, "error": "LINEAR_API_KEY not configured", "teams": []}

    try:
        teams = linear_client.list_teams(config.LINEAR_API_KEY)
        return {"ok": True, "teams": teams}
    except Exception as e:
        return {"ok": False, "error": str(e), "teams": []}
