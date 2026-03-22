"""
Tasks: Linear integration handlers.

- linear.create_issue: crear issue en Linear (con routing de equipo automático)
- linear.list_teams: listar equipos
- linear.update_issue_status: actualizar estado + comentario en un issue
- linear.list_projects: listar proyectos
- linear.create_project: crear proyecto
- linear.attach_issue_to_project: asociar issue a proyecto
- linear.list_project_issues: listar issues de un proyecto
- linear.create_project_update: publicar update de estado en un proyecto
- linear.publish_agent_stack_followup: publicar pendiente interno al proyecto canonico de Agent Stack
- linear.claim_agent_stack_issue: tomar una issue del proyecto canonico por agente
- linear.list_agent_stack_issues: listar issues del proyecto canonico de Agent Stack
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

_AGENT_STACK_BASE_LABELS = [
    ("Agent Stack", "#2563EB"),
    ("Mejora Continua", "#7C3AED"),
]
_AGENT_STACK_PROJECT_NAME = "Mejora Continua Agent Stack"
_AGENT_STACK_PROJECT_ALIASES = (
    _AGENT_STACK_PROJECT_NAME,
    "Auditor\u00eda Mejora Continua \u2014 Umbral Agent Stack",
    "Auditoria Mejora Continua - Umbral Agent Stack",
)
_AGENT_STACK_PROJECT_DESCRIPTION = (
    "Proyecto can\u00f3nico para la mejora continua de Umbral Agent Stack, con foco en drift "
    "operativo, follow-ups de auditor\u00eda, deuda t\u00e9cnica y consistencia entre repo y "
    "operaci\u00f3n real."
)
_AGENT_STACK_PROJECT_CONTENT = (
    "Objetivo: revisar qu\u00e9 est\u00e1 definido en repo, qu\u00e9 workflows y agentes deben "
    "evaluar continuamente el sistema, qu\u00e9 ocurre hoy en Linear, Notion, dashboard, cron "
    "y artefactos, y dejar el estado real con gaps accionables y seguimiento trazable.\n\n"
    "Usar este proyecto para: worker, dispatcher, OpenClaw, Redis, Tailscale, VPS o VM, "
    "Notion y Linear del propio stack, drift operativo y follow-ups internos.\n\n"
    "No usar este proyecto para: proyectos de cliente, entregables de negocio o iniciativas "
    "tem\u00e1ticas de Rick fuera del stack."
)
_AGENT_STACK_KIND_LABELS = {
    "analysis_followup": ("Analysis Follow-up", "#F59E0B"),
    "operational_debt": ("Operational Debt", "#DC2626"),
    "human_review": ("Human Review", "#059669"),
    "drift": ("Drift", "#EA580C"),
}
_AGENT_STACK_ALLOWED_AGENT_CANONICAL = {
    "codex": "Codex",
    "cursor": "Cursor",
    "antigravity": "Antigravity",
    "github copilot": "GitHub Copilot",
    "github-copilot": "GitHub Copilot",
    "rick": "Rick",
    "openclaw": "OpenClaw",
}


def _allowed_agent_names() -> dict[str, str]:
    configured = {}
    raw = getattr(config, "LINEAR_AGENT_STACK_ALLOWED_AGENTS", "") or ""
    for item in raw.split(","):
        key = item.strip().lower()
        if not key:
            continue
        configured[key] = _AGENT_STACK_ALLOWED_AGENT_CANONICAL.get(key, item.strip())
    return configured or dict(_AGENT_STACK_ALLOWED_AGENT_CANONICAL)


def _canonical_agent_name(agent_name: str) -> str | None:
    key = (agent_name or "").strip().lower()
    if not key:
        return None
    return _allowed_agent_names().get(key)


def _agent_label(agent_name: str) -> tuple[str, str]:
    return (f"Agente: {agent_name}", "#0F766E")


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


def _resolve_agent_stack_team_id(api_key: str) -> str | None:
    explicit_team_id = (getattr(config, "LINEAR_AGENT_STACK_TEAM_ID", None) or "").strip()
    if explicit_team_id:
        return explicit_team_id
    return _resolve_linear_team_id(
        api_key,
        {"team_name": getattr(config, "LINEAR_AGENT_STACK_TEAM_NAME", "Umbral")},
    )


def _find_project_by_names(api_key: str, names: list[str]) -> Dict[str, Any] | None:
    seen: set[str] = set()
    for raw_name in names:
        name = (raw_name or "").strip()
        if not name:
            continue
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        project = linear_client.get_project_by_name(api_key, name)
        if project:
            return project
    return None


def _resolve_agent_stack_project(api_key: str) -> Dict[str, Any]:
    explicit_project_id = (getattr(config, "LINEAR_AGENT_STACK_PROJECT_ID", None) or "").strip()
    if explicit_project_id:
        return linear_client.get_project(api_key, explicit_project_id)

    project_name = (getattr(config, "LINEAR_AGENT_STACK_PROJECT_NAME", _AGENT_STACK_PROJECT_NAME) or "").strip()
    project = _find_project_by_names(
        api_key,
        [project_name, _AGENT_STACK_PROJECT_NAME, *_AGENT_STACK_PROJECT_ALIASES],
    )
    if project:
        return project

    team_id = _resolve_agent_stack_team_id(api_key)
    if not team_id:
        raise RuntimeError("No se pudo resolver el team de Linear para Agent Stack")

    return linear_client.create_project(
        api_key=api_key,
        name=project_name or _AGENT_STACK_PROJECT_NAME,
        team_ids=[team_id],
        description=_AGENT_STACK_PROJECT_DESCRIPTION,
        content=_AGENT_STACK_PROJECT_CONTENT,
        icon="🛠️",
        color="#2563EB",
    )


def _issue_description_for_agent_stack(input_data: Dict[str, Any]) -> str:
    lines = [
        "Ambito: Umbral Agent Stack",
        f"Tipo: {(input_data.get('kind') or 'analysis_followup').strip() if input_data.get('kind') else 'analysis_followup'}",
    ]
    summary = (input_data.get("summary") or "").strip()
    evidence = (input_data.get("evidence") or "").strip()
    impact = (input_data.get("impact") or "").strip()
    next_action = (input_data.get("next_action") or "").strip()
    source_ref = (input_data.get("source_ref") or "").strip()
    requested_by = (input_data.get("requested_by") or "David").strip()

    if summary:
        lines.extend(["", "Resumen", summary])
    if evidence:
        lines.extend(["", "Evidencia", evidence])
    if impact:
        lines.extend(["", "Impacto", impact])
    if next_action:
        lines.extend(["", "Siguiente accion", next_action])
    if source_ref:
        lines.extend(["", "Origen", source_ref])

    lines.extend(["", f"Solicitado por: {requested_by}"])
    return "\n".join(lines).strip()


def _ensure_label_ids(
    api_key: str,
    team_id: str,
    labels: list[tuple[str, str]],
) -> list[str]:
    label_ids: list[str] = []
    for label_name, label_color in labels:
        label_id = linear_client.get_or_create_label(api_key, team_id, label_name, label_color)
        if label_id and label_id not in label_ids:
            label_ids.append(label_id)
    return label_ids


def _resolve_issue_for_agent_stack(
    api_key: str,
    input_data: Dict[str, Any],
    *,
    project: Dict[str, Any],
) -> Dict[str, Any]:
    issue_id = (input_data.get("issue_id") or "").strip()
    identifier = (input_data.get("identifier") or "").strip()

    if issue_id:
        issue = linear_client.get_issue(api_key, issue_id)
    elif identifier:
        issue = linear_client.get_issue_by_identifier(api_key, identifier)
        if not issue:
            raise RuntimeError(f"No existe issue con identifier '{identifier}'")
    else:
        raise RuntimeError("Provide issue_id or identifier")

    issue_project_id = ((issue.get("project") or {}).get("id") or "").strip()
    if issue_project_id != project["id"]:
        raise RuntimeError("La issue no pertenece al proyecto canonico de Agent Stack")
    return issue


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
        return {"ok": False, "error": "state_name provided but team_id missing; state not updated"}

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


_HEALTH_VALID = {"onTrack", "atRisk", "offTrack"}


def handle_linear_create_project_update(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publica un update de estado en un proyecto de Linear.

    Input:
        body (str, required): texto del update (markdown soportado).
        project_id (str, optional): UUID del proyecto.
        project_name (str, optional): nombre del proyecto.
        health (str, optional): onTrack | atRisk | offTrack (default: onTrack).

    Returns:
        {"ok": True, "projectUpdate": {...}} o {"ok": False, "error": "..."}

    Nota: La API pública de Linear soporta `projectUpdateCreate` en todos los planes.
    Si el workspace no tiene acceso, se devolverá {"ok": False, "error": "..."}.
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    body = (input_data.get("body") or "").strip()
    if not body:
        return {"ok": False, "error": "'body' is required"}

    health = (input_data.get("health") or "onTrack").strip()
    if health not in _HEALTH_VALID:
        return {"ok": False, "error": f"'health' must be one of {sorted(_HEALTH_VALID)}"}

    try:
        project = _resolve_project(api_key, input_data)
        if not project:
            return {
                "ok": False,
                "error": "Could not resolve Linear project. Provide project_id or project_name.",
            }
        result = linear_client.create_project_update(
            api_key=api_key,
            project_id=project["id"],
            body=body,
            health=health,
        )
        logger.info(
            "[linear.create_project_update] project=%s health=%s",
            project.get("name"), health,
        )
        return {"ok": True, "project": {"id": project["id"], "name": project.get("name")}, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_linear_publish_agent_stack_followup(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publica un pendiente interno de Umbral Agent Stack en el proyecto canónico
    'Mejora Continua Agent Stack'. No sirve para proyectos de cliente ni frentes externos.

    Input:
        title (str, required)
        summary/evidence/impact/next_action/source_ref/requested_by (str, optional)
        kind (str, optional): analysis_followup | operational_debt | human_review | drift
        priority (int, optional)
        designated_agent (str, optional): codex | cursor | antigravity | github copilot | rick | openclaw
        state_name (str, optional): si se quiere mover de inmediato al workflow state indicado

    Returns:
        {"ok": True, "issue": {...}, "project": {...}, "designated_agent": "..."}
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    title = (input_data.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "'title' is required"}

    try:
        project = _resolve_agent_stack_project(api_key)
        team_id = _resolve_agent_stack_team_id(api_key)
        if not team_id:
            return {"ok": False, "error": "No se pudo resolver team_id de Linear para Agent Stack"}

        kind = (input_data.get("kind") or "analysis_followup").strip()
        labels = list(_AGENT_STACK_BASE_LABELS)
        if kind in _AGENT_STACK_KIND_LABELS:
            labels.append(_AGENT_STACK_KIND_LABELS[kind])

        designated_agent = None
        if input_data.get("designated_agent"):
            designated_agent = _canonical_agent_name(str(input_data.get("designated_agent")))
            if not designated_agent:
                allowed = ", ".join(sorted(_allowed_agent_names().values()))
                return {"ok": False, "error": f"designated_agent invalido. Allowed: {allowed}"}
            labels.append(_agent_label(designated_agent))

        description = _issue_description_for_agent_stack(input_data)
        issue = linear_client.create_issue(
            api_key=api_key,
            team_id=team_id,
            title=f"[Agent Stack] {title}",
            description=description,
            priority=input_data.get("priority"),
        )
        attach = linear_client.attach_issue_to_project(api_key, issue["id"], project["id"])
        label_ids = _ensure_label_ids(api_key, team_id, labels)

        state_name = (input_data.get("state_name") or "").strip()
        state_id = linear_client.get_state_id_by_name(api_key, team_id, state_name) if state_name else None
        update_result = linear_client.update_issue(
            api_key=api_key,
            issue_id=issue["id"],
            state_id=state_id,
            label_ids=label_ids,
        )
        return {
            "ok": True,
            "issue": {
                **issue,
                "project": attach.get("issue", {}).get("project"),
            },
            "project": {"id": project["id"], "name": project.get("name"), "url": project.get("url")},
            "labels_applied": [name for name, _ in labels],
            "designated_agent": designated_agent,
            "update": update_result.get("update"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_linear_claim_agent_stack_issue(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Marca una issue del proyecto canónico de Agent Stack como tomada por un agente.

    Input:
        issue_id (str, optional) or identifier (str, optional)
        agent_name (str, required): codex | cursor | antigravity | github copilot | rick | openclaw
        state_name (str, optional): workflow target (default: In Progress)
        comment (str, optional)

    Returns:
        {"ok": True, "issue": {...}, "claimed_by": "..."}
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured"}

    agent_name = _canonical_agent_name(str(input_data.get("agent_name") or ""))
    if not agent_name:
        allowed = ", ".join(sorted(_allowed_agent_names().values()))
        return {"ok": False, "error": f"'agent_name' is required and must be one of: {allowed}"}

    try:
        project = _resolve_agent_stack_project(api_key)
        issue = _resolve_issue_for_agent_stack(api_key, input_data, project=project)
        team_id = ((issue.get("team") or {}).get("id") or "").strip() or _resolve_agent_stack_team_id(api_key)
        if not team_id:
            return {"ok": False, "error": "No se pudo resolver team_id de Linear para la issue"}

        existing_labels = []
        for item in ((issue.get("labels") or {}).get("nodes") or []):
            label_id = item.get("id")
            if label_id:
                existing_labels.append(label_id)
        agent_label_ids = _ensure_label_ids(api_key, team_id, [_agent_label(agent_name)])
        merged_label_ids = list(dict.fromkeys(existing_labels + agent_label_ids))

        state_name = (input_data.get("state_name") or "In Progress").strip()
        state_id = linear_client.get_state_id_by_name(api_key, team_id, state_name) if state_name else None
        comment = (input_data.get("comment") or "").strip()
        comment_block = (
            f"Tomada por: {agent_name}\n"
            f"Proyecto: {project.get('name')}\n"
            f"Siguiente paso: {comment or 'Tomar ownership del siguiente slice y dejar trazabilidad.'}"
        )
        result = linear_client.update_issue(
            api_key=api_key,
            issue_id=issue["id"],
            state_id=state_id,
            label_ids=merged_label_ids,
            comment=comment_block,
        )
        refreshed = linear_client.get_issue(api_key, issue["id"])
        return {
            "ok": True,
            "issue": refreshed,
            "project": {"id": project["id"], "name": project.get("name"), "url": project.get("url")},
            "claimed_by": agent_name,
            "update": result.get("update"),
            "comment": result.get("comment"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_linear_list_agent_stack_issues(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista issues del proyecto canónico de Agent Stack, opcionalmente filtradas por agente.

    Input:
        limit (int, optional)
        agent_name (str, optional)
        only_unclaimed (bool, optional)

    Returns:
        {"ok": True, "project": {...}, "issues": [...]}
    """
    api_key = _linear_api_key()
    if not api_key:
        return {"ok": False, "error": "LINEAR_API_KEY not configured", "issues": []}

    try:
        project = _resolve_agent_stack_project(api_key)
        issues = linear_client.list_project_issues(api_key, project["id"], limit=int(input_data.get("limit", 50)))
        wanted_agent = None
        if input_data.get("agent_name"):
            wanted_agent = _canonical_agent_name(str(input_data.get("agent_name")))
            if not wanted_agent:
                allowed = ", ".join(sorted(_allowed_agent_names().values()))
                return {"ok": False, "error": f"agent_name invalido. Allowed: {allowed}", "issues": []}

        filtered = []
        for issue in issues:
            label_names = [str(item.get("name", "")).strip() for item in ((issue.get("labels") or {}).get("nodes") or [])]
            has_agent = next((label for label in label_names if label.startswith("Agente: ")), None)
            if wanted_agent and has_agent != f"Agente: {wanted_agent}":
                continue
            if input_data.get("only_unclaimed") and has_agent:
                continue
            filtered.append(
                {
                    "id": issue.get("id"),
                    "identifier": issue.get("identifier"),
                    "title": issue.get("title"),
                    "url": issue.get("url"),
                    "state": (issue.get("state") or {}).get("name"),
                    "assignee": ((issue.get("assignee") or {}).get("name") or ""),
                    "agent_label": has_agent or "",
                    "labels": label_names,
                }
            )

        return {
            "ok": True,
            "project": {"id": project["id"], "name": project.get("name"), "url": project.get("url")},
            "issues": filtered,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "issues": []}

