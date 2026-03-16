from datetime import datetime, timedelta, timezone

from scripts.notion_curate_ops_vps import (
    _property_name,
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
    assert infer_project_name_from_deliverable("Benchmark Ruben Hassid", next_action="Aplicar al proyecto embudo") == "Proyecto Embudo Ventas"
    assert infer_project_name_from_deliverable("Perfil maestro del sistema laboral") == "Sistema Automatizado de Búsqueda y Postulación Laboral"


def test_is_periodic_bridge_review():
    assert is_periodic_bridge_review("Revisión periódica 2026-03-10 01:00")
    assert is_periodic_bridge_review("Revision periodica 2026-03-10 01:00")
    assert not is_periodic_bridge_review("Sincronización Mi Perfil → Perfil operativo Rick completada")


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
