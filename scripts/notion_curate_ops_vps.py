#!/usr/bin/env python3
"""
Curacion operativa incremental de Notion.

- Normaliza entregables huerfanos hacia proyectos.
- Vincula entregables con su tarea origen cuando existe Task ID origen.
- Asegura propiedades de procedencia en la DB de Tareas.
- Archiva ruido tecnico viejo de Tareas en lotes acotados.
- Archiva items resueltos viejos de Bandeja Puente.

Uso:
  source ~/.config/openclaw/env
  .venv/bin/python scripts/notion_curate_ops_vps.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from worker import config, notion_client

BRIDGE_DB_ID = "8496ee73-6c7d-43a3-89cf-b9c8825b5dfc"
SNAPSHOT_PATH = Path("docs/audits/notion-curation-snapshot-2026-03-16.json")

TASK_NOISE_PREFIXES = (
    "windows.fs.",
    "ping",
    "notion.poll_comments",
    "notion.read_page",
    "notion.read_database",
    "notion.search_databases",
)

DELIVERABLE_PROJECT_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("freepik",), "Uso de Freepik vía VM"),
    (("rpa gui", "gui"), "Autonomía RPA GUI en VM"),
    (("navegador", "browser vm"), "Control de Navegador VM"),
    (("laboral", "postulaci", "oportunidades laborales"), "Sistema Automatizado de Búsqueda y Postulación Laboral"),
    (("editorial", "multicanal"), "Sistema Editorial Automatizado Umbral"),
    (("granola", "transcrip"), "Proyecto Granola"),
    (("embudo", "veritasium", "ruben", "linkedin", "landing"), "Proyecto Embudo Ventas"),
    (("mejora continua", "ooda", "drift"), "Auditoría Mejora Continua — Umbral Agent Stack"),
]


def _headers() -> dict[str, str]:
    return notion_client._headers()  # type: ignore[attr-defined]


def _api(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.request(
            method,
            f"{notion_client.NOTION_BASE_URL}{path}",
            headers=_headers(),
            json=payload,
            params=params,
        )
    return notion_client._check_response(resp, path)  # type: ignore[attr-defined]


def _db_schema(database_id: str) -> dict[str, dict[str, Any]]:
    data = _api("GET", f"/databases/{database_id}")
    return data.get("properties", {}) or {}


def _property_name(
    schema: dict[str, dict[str, Any]],
    *,
    preferred: list[str] | tuple[str, ...] = (),
    prop_type: str | None = None,
) -> str | None:
    for name in preferred:
        if name in schema:
            return name
    if prop_type:
        for name, meta in schema.items():
            if meta.get("type") == prop_type:
                return name
    return None


def _query_db(
    database_id: str,
    *,
    filter_payload: dict[str, Any] | None = None,
    sorts: list[dict[str, Any]] | None = None,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_cursor: str | None = None
    while True:
        payload: dict[str, Any] = {"page_size": page_size}
        if filter_payload:
            payload["filter"] = filter_payload
        if sorts:
            payload["sorts"] = sorts
        if next_cursor:
            payload["start_cursor"] = next_cursor
        data = _api("POST", f"/databases/{database_id}/query", payload=payload)
        results.extend(data.get("results", []))
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
    return results


def _plain(prop: dict[str, Any] | None) -> Any:
    if not isinstance(prop, dict):
        return None
    typ = prop.get("type")
    if typ == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if typ == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if typ == "select":
        return (prop.get("select") or {}).get("name")
    if typ == "status":
        return (prop.get("status") or {}).get("name")
    if typ == "date":
        return (prop.get("date") or {}).get("start")
    if typ == "relation":
        return [x.get("id") for x in prop.get("relation", [])]
    if typ == "number":
        return prop.get("number")
    if typ == "checkbox":
        return prop.get("checkbox")
    return None


def infer_project_name_from_deliverable(name: str, summary: str = "", next_action: str = "") -> str | None:
    haystack = f"{name} {summary} {next_action}".lower()
    for hints, project_name in DELIVERABLE_PROJECT_HINTS:
        if any(hint in haystack for hint in hints):
            return project_name
    return None


def is_periodic_bridge_review(title: str) -> bool:
    lowered = title.lower()
    return lowered.startswith("revisión periódica") or lowered.startswith("revision periodica")


def _parse_created(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def should_archive_task_row(
    row: dict[str, Any],
    now: datetime,
    *,
    keep_recent_unscoped: set[str],
    task_prop: str = "Task",
    status_prop: str = "Status",
    created_prop: str = "Created",
    project_prop: str = "Proyecto",
    deliverable_prop: str = "Entregable",
) -> bool:
    props = row.get("properties", {})
    page_id = row.get("id", "")
    if page_id in keep_recent_unscoped:
        return False

    project_rel = _plain(props.get(project_prop)) or []
    deliverable_rel = _plain(props.get(deliverable_prop)) or []
    if project_rel or deliverable_rel:
        return False

    title = (_plain(props.get(task_prop)) or "").strip().lower()
    status = (_plain(props.get(status_prop)) or "").strip().lower()
    created_dt = _parse_created(_plain(props.get(created_prop)))

    if created_dt is None:
        return title.startswith(TASK_NOISE_PREFIXES) or status in {"done", "blocked", "failed"}

    age = now - created_dt
    if age >= timedelta(days=1):
        return True
    if status == "running" and age >= timedelta(hours=2):
        return True
    if status in {"done", "blocked", "failed"} and age >= timedelta(hours=8):
        return True
    if status in {"done", "blocked", "failed"} and title.startswith(TASK_NOISE_PREFIXES):
        return True
    return False


def _project_lookup() -> dict[str, str]:
    rows = _query_db(config.NOTION_PROJECTS_DB_ID)
    mapping: dict[str, str] = {}
    for row in rows:
        name = (_plain(row.get("properties", {}).get("Nombre")) or "").strip()
        if name:
            mapping[name] = row["id"]
    return mapping


def ensure_task_schema() -> list[str]:
    db_id = config.NOTION_TASKS_DB_ID
    if not db_id:
        return []
    schema = _db_schema(db_id)
    additions: dict[str, Any] = {}
    for name in ("Source", "Source Kind", "Trace ID"):
        if name not in schema:
            additions[name] = {"rich_text": {}}
    if additions:
        _api("PATCH", f"/databases/{db_id}", payload={"properties": additions})
    return list(additions.keys())


def normalize_orphan_deliverables() -> list[dict[str, Any]]:
    project_ids = _project_lookup()
    rows = _query_db(config.NOTION_DELIVERABLES_DB_ID)
    updates: list[dict[str, Any]] = []
    for row in rows:
        props = row.get("properties", {})
        if _plain(props.get("Proyecto")):
            continue
        name = _plain(props.get("Nombre")) or ""
        summary = _plain(props.get("Resumen")) or ""
        next_action = _plain(props.get("Siguiente accion")) or ""
        inferred = infer_project_name_from_deliverable(name, summary, next_action)
        if not inferred:
            continue
        project_page_id = project_ids.get(inferred)
        if not project_page_id:
            continue
        notion_client.update_page_properties(
            page_id_or_url=row["id"],
            properties={"Proyecto": {"relation": [{"id": project_page_id}]}}
        )
        updates.append({"deliverable_id": row["id"], "name": name, "project_name": inferred})
    return updates


def backfill_deliverable_task_origins(batch_size: int = 100) -> list[dict[str, Any]]:
    tasks = _query_db(config.NOTION_TASKS_DB_ID)
    by_task_id: dict[str, str] = {}
    for row in tasks:
        task_id = (_plain(row.get("properties", {}).get("Task ID")) or "").strip()
        if task_id:
            by_task_id[task_id] = row["id"]

    updates: list[dict[str, Any]] = []
    deliverables = _query_db(config.NOTION_DELIVERABLES_DB_ID)
    for row in deliverables:
        if len(updates) >= batch_size:
            break
        props = row.get("properties", {})
        if _plain(props.get("Tareas origen")):
            continue
        task_id = (_plain(props.get("Task ID origen")) or "").strip()
        if not task_id:
            continue
        task_page_id = by_task_id.get(task_id)
        if not task_page_id:
            continue
        notion_client.update_page_properties(
            page_id_or_url=row["id"],
            properties={"Tareas origen": {"relation": [{"id": task_page_id}]}}
        )
        updates.append(
            {
                "deliverable_id": row["id"],
                "deliverable_name": _plain(props.get("Nombre")) or "",
                "task_id": task_id,
                "task_page_id": task_page_id,
            }
        )
    return updates


def curate_tasks(batch_size: int = 180, keep_recent_unscoped_count: int = 4) -> list[dict[str, Any]]:
    rows = _query_db(
        config.NOTION_TASKS_DB_ID,
        sorts=[{"timestamp": "created_time", "direction": "descending"}],
    )
    now = datetime.now(timezone.utc)
    task_schema = _db_schema(config.NOTION_TASKS_DB_ID)
    task_prop = _property_name(task_schema, preferred=["Task"], prop_type="title") or "Task"
    status_prop = _property_name(task_schema, preferred=["Status"], prop_type="select") or "Status"
    created_prop = _property_name(task_schema, preferred=["Created"], prop_type="date") or "Created"
    project_prop = _property_name(task_schema, preferred=["Proyecto"], prop_type="relation") or "Proyecto"
    deliverable_prop = _property_name(task_schema, preferred=["Entregable"], prop_type="relation") or "Entregable"

    unscoped_sorted = [
        row for row in rows
        if not (_plain(row.get("properties", {}).get(project_prop)) or [])
        and not (_plain(row.get("properties", {}).get(deliverable_prop)) or [])
    ]
    keep_recent_unscoped = {row["id"] for row in unscoped_sorted[:keep_recent_unscoped_count]}

    archived: list[dict[str, Any]] = []
    for row in rows:
        if len(archived) >= batch_size:
            break
        if should_archive_task_row(
            row,
            now,
            keep_recent_unscoped=keep_recent_unscoped,
            task_prop=task_prop,
            status_prop=status_prop,
            created_prop=created_prop,
            project_prop=project_prop,
            deliverable_prop=deliverable_prop,
        ):
            _api("PATCH", f"/pages/{row['id']}", payload={"archived": True})
            props = row.get("properties", {})
            archived.append(
                {
                    "id": row["id"],
                    "title": _plain(props.get(task_prop)) or "",
                    "status": _plain(props.get(status_prop)) or "",
                    "created": _plain(props.get(created_prop)),
                }
            )
    return archived


def curate_bridge(batch_size: int = 150, keep_recent_resolved: int = 10) -> list[dict[str, Any]]:
    schema = _db_schema(BRIDGE_DB_ID)
    title_prop = _property_name(schema, preferred=["Ítem"], prop_type="title")
    status_prop = _property_name(schema, preferred=["Estado"], prop_type="status")
    last_move_prop = _property_name(schema, preferred=["Último movimiento"], prop_type="date")
    notes_prop = _property_name(schema, preferred=["Notas"], prop_type="rich_text")

    rows = _query_db(
        BRIDGE_DB_ID,
        sorts=[{"property": last_move_prop or "Último movimiento", "direction": "descending"}] if last_move_prop else None,
    )
    resolved_rows = []
    for row in rows:
        props = row.get("properties", {})
        title = (_plain(props.get(title_prop or "")) or "").strip()
        status = (_plain(props.get(status_prop or "")) or "").strip()
        if status == "Resuelto":
            resolved_rows.append(row)

    keep_ids = {row["id"] for row in resolved_rows[:keep_recent_resolved]}
    archived: list[dict[str, Any]] = []
    for row in resolved_rows:
        if len(archived) >= batch_size:
            break
        if row["id"] in keep_ids:
            continue
        props = row.get("properties", {})
        title = (_plain(props.get(title_prop or "")) or "").strip()
        last_move = _plain(props.get(last_move_prop or "")) if last_move_prop else None
        notes = (_plain(props.get(notes_prop or "")) or "") if notes_prop else ""
        _api("PATCH", f"/pages/{row['id']}", payload={"archived": True})
        archived.append(
            {
                "id": row["id"],
                "title": title,
                "last_move": last_move,
                "notes": notes[:240],
            }
        )
    return archived


def _db_counts() -> dict[str, Any]:
    tasks = _query_db(config.NOTION_TASKS_DB_ID)
    deliverables = _query_db(config.NOTION_DELIVERABLES_DB_ID)
    bridge = _query_db(BRIDGE_DB_ID)
    projects = _query_db(config.NOTION_PROJECTS_DB_ID)

    unlinked_tasks = 0
    for row in tasks:
        props = row.get("properties", {})
        if not (_plain(props.get("Proyecto")) or []) and not (_plain(props.get("Entregable")) or []):
            unlinked_tasks += 1
    bridge_live = 0
    bridge_resolved = 0
    for row in bridge:
        status = (_plain(row.get("properties", {}).get("Estado")) or "").strip()
        if status == "Resuelto":
            bridge_resolved += 1
        else:
            bridge_live += 1

    pending_deliverables = 0
    deliverables_without_task_origin = 0
    for row in deliverables:
        props = row.get("properties", {})
        if (_plain(props.get("Estado revision")) or "") in {"Pendiente revision", "Aprobado con ajustes"}:
            pending_deliverables += 1
        if not (_plain(props.get("Tareas origen")) or []):
            deliverables_without_task_origin += 1

    return {
        "projects_total": len(projects),
        "tasks_total": len(tasks),
        "tasks_unlinked": unlinked_tasks,
        "deliverables_total": len(deliverables),
        "deliverables_pending_review": pending_deliverables,
        "deliverables_without_task_origin": deliverables_without_task_origin,
        "bridge_total": len(bridge),
        "bridge_live": bridge_live,
        "bridge_resolved": bridge_resolved,
    }


def write_snapshot(snapshot: dict[str, Any]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def _snapshot_base() -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts_before": _db_counts(),
        "schema_updates": [],
        "deliverables_normalized": [],
        "deliverable_task_origins_backfilled": [],
        "tasks_archived": [],
        "bridge_archived": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-batch", type=int, default=180)
    parser.add_argument("--bridge-batch", type=int, default=150)
    parser.add_argument("--deliverable-batch", type=int, default=100)
    args = parser.parse_args(argv)

    snapshot = _snapshot_base()
    write_snapshot(snapshot)

    snapshot["schema_updates"] = ensure_task_schema()
    write_snapshot(snapshot)

    snapshot["deliverables_normalized"] = normalize_orphan_deliverables()
    write_snapshot(snapshot)

    snapshot["deliverable_task_origins_backfilled"] = backfill_deliverable_task_origins(batch_size=args.deliverable_batch)
    write_snapshot(snapshot)

    snapshot["tasks_archived"] = curate_tasks(batch_size=args.task_batch)
    write_snapshot(snapshot)

    snapshot["bridge_archived"] = curate_bridge(batch_size=args.bridge_batch)
    snapshot["counts_after"] = _db_counts()
    write_snapshot(snapshot)

    print(
        json.dumps(
            {
                "ok": True,
                "schema_updates": snapshot["schema_updates"],
                "deliverables_normalized": len(snapshot["deliverables_normalized"]),
                "deliverable_task_origins_backfilled": len(snapshot["deliverable_task_origins_backfilled"]),
                "tasks_archived": len(snapshot["tasks_archived"]),
                "bridge_archived": len(snapshot["bridge_archived"]),
                "counts_after": snapshot["counts_after"],
                "snapshot": str(SNAPSHOT_PATH),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
