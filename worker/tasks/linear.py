"""
Tasks: Linear integration handlers.

- linear.create_issue: crear issue en Linear (con routing de equipo automático)
- linear.list_teams: listar equipos
- linear.update_issue_status: actualizar estado + comentario en un issue
- linear.list_projects: listar proyectos
- linear.create_project: crear proyecto
- linear.attach_issue_to_project: asociar issue a proyecto
- linear.list_project_issues: listar issues de un proyecto
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict

from .. import config
from .. import linear_client
from ..linear_team_router import resolve_team_for_issue, load_teams_config


def _linear_api_key() -> str | None:
    """Return LINEAR_API_KEY from config or from ~/.config/openclaw/env (VPS/cron)."""
    key = (config.LINEAR_API_KEY or "").strip()
    if key:
        return key
    if os.name == "nt":
        return None
    candidates = [
        Path(os.environ.get("HOME", "")) / ".config/openclaw/env",
        Path("/home/rick/.config/openclaw/env"),  # VPS cuando HOME no está definido
    ]
    env_file = None
    for p in candidates:
        if p.exists():
            env_file = p
            break
    if not env_file:
        return None
    # Última aparición de LINEAR_API_KEY gana (por si hay duplicados en el archivo)
    value = None
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k.startswith("export "):
            k = k[7:].strip()
        if k == "LINEAR_API_KEY":
            value = v.strip().strip('"').strip("'").replace("\r", "") or None
    return value

logger = logging.getLogger("worker.tasks.linear")


def _resolve_linear_team_id(
    api_key: str,
    input_data: Dict[str, Any],
) -> str | None:
    """Resolve a Linear team UUID from input or default to the Umbral team."""
    team_id = input_data.get("team_id")
    if team_id:
        return str(team_id)

    team_name = input_data.get("team_name", "Umbral")
    teams = linear_client.list_teams(api_key)
    for team in teams:
        if team.get("name", "").lower() == str(team_name).lower():
            return team["id"]

    if teams:
        fallback = teams[0]["id"]
        logger.warning(
            "[linear] team '%s' no encontrado, usando primero: %s",
            team_name,
            fallback,
        )
        return fallback
    return None


def _resolve_project(
    api_key: str,
    input_data: Dict[str, Any],
    *,
    team_id: str | None = None,
) -> Dict[str, Any] | None:
    """
    Resolve a Linear project from explicit project_id or project_name.

    If create_project_if_missing=true and a team_id is available, creates the project.
    """
    project_id = (input_data.get("project_id") or "").strip()
    if project_id:
        return linear_client.get_project(api_key, project_id)

    project_name = (input_data.get("project_name") or "").strip()
    if not project_name:
        return None

    project = linear_client.get_project_by_name(api_key, project_name)
    if project:
        return project

    if not input_data.get("create_project_if_missing"):
        return None

    if not team_id:
        raise RuntimeError(
            "Cannot create Linear project without a resolved team_id. "
            "Provide team_id/team_name or disable create_project_if_missing."
        )

    return linear_client.create_project(
        api_key=api_key,
        name=project_name,
        team_ids=[team_id],
        description=input_data.get("project_description") or input_data.get("project_summary"),
        content=input_data.get("project_content"),
        lead_id=input_data.get("project_lead_id"),
        start_date=input_data.get("project_start_date"),
        target_date=input_data.get("project_target_date"),
        priority=input_data.get("project_priority"),
        icon=input_data.get("project_icon"),
        color=input_data.get("project_color"),
    )


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
        project_id (str, optional): UUID del proyecto de Linear al que debe quedar asociado.
        project_name (str, optional): Nombre del proyecto de Linear. Puede crearse si no existe.
        create_project_if_missing (bool, optional): Crear el proyecto si no existe.
        project_description (str, optional): Descripción corta del proyecto si hay que crearlo.
        project_content (str, optional): Contenido largo del proyecto si hay que crearlo.
        project_start_date (str, optional): Fecha inicio YYYY-MM-DD para proyecto nuevo.
        project_target_date (str, optional): Fecha objetivo YYYY-MM-DD para proyecto nuevo.

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
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    title = (input_data.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "'title' is required"}

    description = input_data.get("description", "")
    priority = input_data.get("priority")
    add_team_labels = input_data.get("add_team_labels", True)

    # --- Resolver team_id de Linear ---
    team_id = _resolve_linear_team_id(api_key, input_data)

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

        project = _resolve_project(api_key, input_data, team_id=team_id)
        attached = None
        if project:
            attached = linear_client.attach_issue_to_project(api_key, issue["id"], project["id"])
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
        "project": (
            {
                "id": attached["issue"]["project"]["id"],
                "name": attached["issue"]["project"]["name"],
                "url": attached["issue"]["project"]["url"],
            }
            if attached and attached.get("issue", {}).get("project")
            else None
        ),
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
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    issue_id = (input_data.get("issue_id") or "").strip()
    if not issue_id:
        return {"ok": False, "error": "'issue_id' is required"}
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
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured", "teams": []}

    try:
        teams = linear_client.list_teams(api_key)
        return {"ok": True, "teams": teams}
    except Exception as e:
        return {"ok": False, "error": str(e), "teams": []}


def handle_linear_list_projects(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista proyectos en Linear.

    Input:
        query (str, optional): filtro case-insensitive por nombre.
        limit (int, optional): máximo de proyectos a devolver (default 50).

    Returns:
        {"ok": True, "projects": [...]}
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured", "projects": []}

    try:
        projects = linear_client.list_projects(
            api_key,
            limit=int(input_data.get("limit", 50)),
            query=input_data.get("query"),
        )
        return {"ok": True, "projects": projects}
    except Exception as e:
        return {"ok": False, "error": str(e), "projects": []}


def handle_linear_create_project(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un proyecto en Linear o retorna el existente por nombre.

    Input:
        name (str, required): nombre del proyecto.
        team_id (str, optional): UUID del equipo.
        team_name (str, optional): nombre del equipo (default Umbral).
        if_exists_return (bool, optional, default True): si existe por nombre, retornarlo.
        description/content/lead_id/start_date/target_date/priority/icon/color: campos opcionales.

    Returns:
        {"ok": True, "project": {...}, "created": bool}
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    name = (input_data.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "'name' is required"}

    if input_data.get("if_exists_return", True):
        existing = linear_client.get_project_by_name(api_key, name)
        if existing:
            return {"ok": True, "project": existing, "created": False}

    team_id = _resolve_linear_team_id(api_key, input_data)
    if not team_id:
        return {"ok": False, "error": "No se pudo resolver team_id de Linear"}

    try:
        project = linear_client.create_project(
            api_key=api_key,
            name=name,
            team_ids=[team_id],
            description=input_data.get("description"),
            content=input_data.get("content"),
            lead_id=input_data.get("lead_id"),
            start_date=input_data.get("start_date"),
            target_date=input_data.get("target_date"),
            priority=input_data.get("priority"),
            icon=input_data.get("icon"),
            color=input_data.get("color"),
        )
        return {"ok": True, "project": project, "created": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_linear_attach_issue_to_project(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asocia un issue existente a un proyecto de Linear.

    Input:
        issue_id (str, required): UUID del issue.
        project_id (str, optional): UUID del proyecto.
        project_name (str, optional): nombre del proyecto.
        create_project_if_missing (bool, optional): crear proyecto si no existe.
        team_id/team_name + project_*: usados si hay que crear el proyecto.

    Returns:
        {"ok": True, "issue": {...}, "project": {...}}
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    issue_id = (input_data.get("issue_id") or "").strip()
    if not issue_id:
        return {"ok": False, "error": "'issue_id' is required"}

    try:
        project = _resolve_project(api_key, input_data)
        if not project and input_data.get("create_project_if_missing"):
            team_id = _resolve_linear_team_id(api_key, input_data)
            project = _resolve_project(api_key, input_data, team_id=team_id)
        if not project:
            return {
                "ok": False,
                "error": "Could not resolve Linear project. Provide project_id or project_name, or enable create_project_if_missing.",
            }
        result = linear_client.attach_issue_to_project(api_key, issue_id, project["id"])
        return {"ok": True, **result, "project": project}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_linear_list_project_issues(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista issues asociadas a un proyecto de Linear.

    Input:
        project_id (str, optional): UUID del proyecto.
        project_name (str, optional): nombre del proyecto.
        limit (int, optional): máximo de issues a devolver.

    Returns:
        {"ok": True, "project": {...}, "issues": [...]}
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured", "issues": []}

    try:
        project = _resolve_project(api_key, input_data)
        if not project:
            return {
                "ok": False,
                "error": "Could not resolve Linear project. Provide project_id or project_name.",
                "issues": [],
            }
        issues = linear_client.list_project_issues(
            api_key,
            project["id"],
            limit=int(input_data.get("limit", 50)),
        )
        return {"ok": True, "project": project, "issues": issues}
    except Exception as e:
        return {"ok": False, "error": str(e), "issues": []}

