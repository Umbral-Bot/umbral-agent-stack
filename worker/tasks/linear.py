"""
Tasks: Linear integration handlers.

- linear.create_issue: crear issue en Linear (con routing de equipo automático)
- linear.list_teams: listar equipos
- linear.update_issue_status: actualizar estado + comentario en un issue
"""

import logging
from typing import Any, Dict

from .. import config
from .. import linear_client
from ..linear_team_router import resolve_team_for_issue, load_teams_config

logger = logging.getLogger("worker.tasks.linear")


def handle_linear_create_issue(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un issue en Linear con equipo y labels resueltos automáticamente.

    Input:
        title (str, required): Título del issue.
        description (str, optional): Descripción.
        team_key (str, optional): Clave del equipo Umbral (ej. "marketing").
                                   Si no se pasa, se infiere del title+description.
        team_id (str, optional): UUID del equipo en Linear. Si no, usa team_name.
        team_name (str, optional): Nombre del equipo en Linear (default "Umbral").
        priority (int, optional): 0=Sin prioridad, 1=Urgente, 2=Alta, 3=Media, 4=Baja.
        add_team_labels (bool, optional, default True): Si adjuntar labels de equipo.

    Returns:
        {
            "ok": True,
            "id": "...", "identifier": "UMB-5", "title": "...", "url": "...",
            "routing": {
                "team_key": "marketing",
                "labels_applied": ["Marketing", "Marketing Supervisor"],
                "supervisor": "Marketing Supervisor",
                "inferred": True,
                "linear_team_id": "...",
            }
        }
    """
    if not config.LINEAR_API_KEY:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    title = (input_data.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "'title' is required"}

    description = input_data.get("description", "")
    priority = input_data.get("priority")
    add_team_labels = input_data.get("add_team_labels", True)
    api_key = config.LINEAR_API_KEY

    # --- Resolver team_id de Linear ---
    team_id = input_data.get("team_id")
    if not team_id:
        team_name = input_data.get("team_name", "Umbral")
        teams = linear_client.list_teams(api_key)
        for t in teams:
            if t.get("name", "").lower() == team_name.lower():
                team_id = t["id"]
                break
        if not team_id and teams:
            team_id = teams[0]["id"]
            logger.warning("[linear.create_issue] team '%s' no encontrado, usando primero: %s", team_name, team_id)

    if not team_id:
        return {"ok": False, "error": "No se pudo resolver team_id de Linear"}

    # --- Routing: equipo Umbral + labels ---
    routing = resolve_team_for_issue(
        team_key=input_data.get("team_key"),
        title=title,
        description=description,
        teams_config=load_teams_config(),
    )

    # --- Crear/buscar labels en Linear ---
    label_ids: list[str] = []
    if add_team_labels and routing["labels"]:
        for label_name, label_color in zip(routing["labels"], routing["label_colors"]):
            lid = linear_client.get_or_create_label(api_key, team_id, label_name, label_color)
            if lid:
                label_ids.append(lid)

    # --- Crear el issue ---
    try:
        issue = linear_client.create_issue(
            api_key=api_key,
            team_id=team_id,
            title=title,
            description=description or None,
            priority=priority,
        )
        # Si hay label_ids, hacer update inmediato (create_issue no acepta labelIds aún)
        if label_ids:
            linear_client.update_issue(api_key, issue["id"], label_ids=label_ids)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    logger.info(
        "[linear.create_issue] %s creado | equipo=%s | labels=%s | inferred=%s",
        issue.get("identifier"), routing["team_key"], routing["labels"], routing["inferred"],
    )

    return {
        "ok": True,
        **issue,
        "routing": {
            "team_key": routing["team_key"],
            "labels_applied": routing["labels"],
            "supervisor": routing["supervisor_display_name"],
            "inferred": routing["inferred"],
            "linear_team_id": team_id,
        },
    }


def handle_linear_update_issue_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza el estado de un issue en Linear y/o agrega un comentario.
    Usado por el Dispatcher al completar una tarea encolada.

    Input:
        issue_id (str, required): UUID del issue en Linear.
        state_name (str, optional): Nombre del workflow state (ej. "Done", "Cancelled").
        comment (str, optional): Comentario a agregar.
        team_id (str, optional): Necesario para resolver state_name → state_id.

    Returns:
        {"ok": True, "update": {...}, "comment": {...}}
    """
    if not config.LINEAR_API_KEY:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    issue_id = (input_data.get("issue_id") or "").strip()
    if not issue_id:
        return {"ok": False, "error": "'issue_id' is required"}

    api_key = config.LINEAR_API_KEY
    state_name = input_data.get("state_name")
    comment = input_data.get("comment")
    team_id = input_data.get("team_id")

    # Resolver state_id desde state_name
    state_id = None
    if state_name and team_id:
        state_id = linear_client.get_state_id_by_name(api_key, team_id, state_name)
    elif state_name and not team_id:
        logger.warning("[linear.update_issue_status] Se pasó state_name sin team_id; no se podrá resolver state_id")

    try:
        result = linear_client.update_issue(
            api_key=api_key,
            issue_id=issue_id,
            state_id=state_id,
            comment=comment,
        )
        logger.info("[linear.update_issue_status] Issue %s actualizado → state=%s", issue_id, state_name)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_linear_list_teams(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista equipos en Linear.

    Input: vacío o {}

    Returns:
        {"ok": True, "teams": [{"id": "...", "name": "Umbral"}, ...]}
    """
    if not config.LINEAR_API_KEY:
        return {"ok": False, "error": "LINEAR_API_KEY not configured", "teams": []}

    try:
        teams = linear_client.list_teams(config.LINEAR_API_KEY)
        return {"ok": True, "teams": teams}
    except Exception as e:
        return {"ok": False, "error": str(e), "teams": []}

