from datetime import datetime, timedelta, timezone

from scripts.notion_curate_ops_vps import (
    _db_counts,
    _property_name,
    _resolve_bridge_db_id,
    curate_bridge,
    infer_deliverable_provenance,
    infer_project_name_from_deliverable,
    is_periodic_bridge_review,
    should_archive_task_row,
)


def _task_row(
    *,
    page_id: str = "row-1",
    title: str = "windows.fs.list",
    status: str = "done",
    created: str | None = None,
    project_rel: list[str] | None = None,
    deliverable_rel: list[str] | None = None,
):
    return {
        "id": page_id,
        "properties": {
            "Task": {"type": "title", "title": [{"plain_text": title}]},
            "Status": {"type": "select", "select": {"name": status}},
            "Created": {"type": "date", "date": {"start": created}},
            "Proyecto": {"type": "relation", "relation": [{"id": x} for x in (project_rel or [])]},
            "Entregable": {"type": "relation", "relation": [{"id": x} for x in (deliverable_rel or [])]},
        },
    }


def test_infer_project_name_from_deliverable():
    assert infer_project_name_from_deliverable("Estado real de Freepik en VM") == "Uso de Freepik vía VM"
    assert infer_project_name_from_deliverable(
        "Benchmark Ruben Hassid", next_action="Aplicar al proyecto embudo"
    ) == "Proyecto Embudo Ventas"
    assert (
        infer_project_name_from_deliverable("Perfil maestro del sistema laboral")
        == "Sistema Automatizado de Búsqueda y Postulación Laboral"
    )


def test_infer_deliverable_provenance():
    assert infer_deliverable_provenance("Prueba final de iconos en entregables", "Archivado", "") == "Smoke"
    assert infer_deliverable_provenance("Estado real de Freepik en VM", "Aprobado", "") == "Historico"
    assert (
        infer_deliverable_provenance(
            "Cierre critico del estado real del proyecto embudo",
            "Pendiente revision",
            "",
        )
        == "Manual"
    )
    assert infer_deliverable_provenance("Benchmark Ruben Hassid", "Pendiente revision", "task-123") == "Tarea"


def test_is_periodic_bridge_review():
    assert is_periodic_bridge_review("Revisión periódica 2026-03-10 01:00")
    assert is_periodic_bridge_review("Revision periodica 2026-03-10 01:00")
    assert not is_periodic_bridge_review("Sincronización Mi Perfil -> Perfil operativo Rick completada")


def test_should_archive_task_row_archives_old_unscoped_noise():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=2)).isoformat()
    row = _task_row(created=old)
    assert should_archive_task_row(row, now, keep_recent_unscoped=set()) is True


def test_should_archive_task_row_keeps_recent_unscoped():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=2)).isoformat()
    row = _task_row(page_id="recent-1", created=recent)
    assert should_archive_task_row(row, now, keep_recent_unscoped={"recent-1"}) is False


def test_should_archive_task_row_keeps_project_scoped():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=3)).isoformat()
    row = _task_row(created=old, project_rel=["project-1"])
    assert should_archive_task_row(row, now, keep_recent_unscoped=set()) is False


def test_should_archive_task_row_archives_stale_running_unscoped():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=8)).isoformat()
    row = _task_row(title="research.web", status="running", created=old)
    assert should_archive_task_row(row, now, keep_recent_unscoped=set()) is True


def test_property_name_prefers_explicit_then_type():
    schema = {
        "Task": {"type": "title"},
        "Estado": {"type": "status"},
    }
    assert _property_name(schema, preferred=["Task"], prop_type="title") == "Task"
    assert _property_name(schema, preferred=["Missing"], prop_type="status") == "Estado"


def test_curate_bridge_returns_empty_when_bridge_db_unavailable(monkeypatch):
    monkeypatch.setattr("scripts.notion_curate_ops_vps._bridge_available", lambda: False)
    assert curate_bridge() == []


def test_db_counts_handles_missing_bridge_db(monkeypatch):
    tasks = [_task_row()]
    deliverables = []
    projects = [{"id": "project-1", "properties": {"Nombre": {"type": "title", "title": [{"plain_text": "Proyecto"}]}}}]

    def fake_query(database_id, **kwargs):
        if database_id == "afda99a3666e49f0a2f670cb228ac3ab":
            return tasks
        if database_id == "dd8c27d75c6a462db0920ef16f9720c6":
            return deliverables
        if database_id == "8496ee73-6c7d-43a3-89cf-b9c8825b5dfc":
            raise AssertionError("Bridge DB should not be queried when unavailable")
        return projects

    monkeypatch.setattr("scripts.notion_curate_ops_vps._bridge_available", lambda: False)
    monkeypatch.setattr("scripts.notion_curate_ops_vps._query_db", fake_query)
    counts = _db_counts()
    assert counts["bridge_available"] is False
    assert counts["bridge_total"] == 0
    assert counts["bridge_live"] == 0
    assert counts["bridge_resolved"] == 0


def test_resolve_bridge_db_id_prefers_env(monkeypatch):
    monkeypatch.setattr("scripts.notion_curate_ops_vps.config.NOTION_BRIDGE_DB_ID", "bridge-env")
    monkeypatch.setattr("scripts.notion_curate_ops_vps._find_child_database_id", lambda page_id, title: "bridge-child")
    assert _resolve_bridge_db_id() == "bridge-env"


def test_resolve_bridge_db_id_discovers_child_when_env_missing(monkeypatch):
    monkeypatch.setattr("scripts.notion_curate_ops_vps.config.NOTION_BRIDGE_DB_ID", None)
    monkeypatch.setattr("scripts.notion_curate_ops_vps.config.NOTION_CONTROL_ROOM_PAGE_ID", "control-room")
    monkeypatch.setattr("scripts.notion_curate_ops_vps._find_child_database_id", lambda page_id, title: "bridge-child")
    assert _resolve_bridge_db_id() == "bridge-child"
