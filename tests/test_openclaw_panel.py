from scripts import openclaw_panel_vps
from scripts.openclaw_panel_vps import _build_panel_blocks, validate_openclaw_shell


def test_build_panel_blocks_use_tables_and_summary_cards():
    snapshot = {
        "generated_at": "2026-03-16 09:00 UTC",
        "summary": {
            "pending_deliverables": 3,
            "deliverables_adjustments": 1,
            "projects_attention": 2,
            "bridge_live": 1,
            "bridge_available": True,
            "due_items": 2,
        },
        "pending_deliverables": [
            {
                "name": "Cierre crítico del estado real del proyecto embudo",
                "project_name": "Proyecto Embudo Ventas",
                "review": "Pendiente revision",
                "due_date": "2026-03-18",
            }
        ],
        "projects_attention": [
            {
                "name": "Proyecto Embudo Ventas",
                "open_issues": 2,
                "task_count": 1,
                "blockers": "Falta definir captura real del CTA.",
                "next_action": "",
            }
        ],
        "bridge_live": [
            {
                "title": "Validar flujo editorial",
                "status": "En curso",
                "last_move": "2026-03-16",
                "notes": "Pendiente revisión humana.",
            }
        ],
        "due_items": [
            {
                "due_date": "2026-03-18",
                "name": "Cierre crítico del estado real del proyecto embudo",
                "project_name": "Proyecto Embudo Ventas",
                "review": "Pendiente revision",
            }
        ],
    }

    blocks = _build_panel_blocks(snapshot)
    types = [b["type"] for b in blocks]
    assert "column_list" in types
    assert types.count("table") == 4
    assert "bulleted_list_item" not in types


def test_validate_openclaw_shell_requires_anchor_and_databases():
    children = [
        {"id": "a", "type": "callout", "callout": {"rich_text": []}},
        {"id": "b", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Bases operativas"}]}},
        {"id": "c", "type": "child_database", "child_database": {"title": "Proyectos"}},
        {"id": "d", "type": "child_database", "child_database": {"title": "Tareas"}},
        {"id": "e", "type": "child_database", "child_database": {"title": "Entregables"}},
    ]
    result = validate_openclaw_shell(children)
    assert result["ok"] is True
    assert result["child_databases_after_anchor"] == 3


def test_validate_openclaw_shell_fails_without_anchor():
    children = [
        {"id": "a", "type": "callout", "callout": {"rich_text": []}},
    ]
    result = validate_openclaw_shell(children)
    assert result["ok"] is False


def test_find_child_database_id_by_title():
    children = [
        {"id": "a", "type": "child_database", "child_database": {"title": "Bandeja Puente"}},
        {"id": "b", "type": "child_database", "child_database": {"title": "Proyectos"}},
    ]
    assert openclaw_panel_vps._find_child_database_id(children, "Bandeja Puente") == "a"
    assert openclaw_panel_vps._find_child_database_id(children, "No existe") is None


def test_build_operational_snapshot_tolerates_missing_bridge(monkeypatch):
    projects_result = [
        {
            "id": "proj-1",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Proyecto Embudo Ventas"}]},
                "Bloqueos": {"type": "rich_text", "rich_text": []},
                "Siguiente acción": {"type": "rich_text", "rich_text": []},
                "Tareas": {"type": "relation", "relation": [{"id": "task-1"}]},
                "Issues abiertas": {"type": "number", "number": 0},
            },
        }
    ]
    deliverables_result = [
        {
            "id": "del-1",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Entregable principal"}]},
                "Estado revision": {"type": "status", "status": {"name": "Pendiente revision"}},
                "Proyecto": {"type": "relation", "relation": [{"id": "proj-1"}]},
                "Fecha limite sugerida": {"type": "date", "date": {"start": "2026-03-18"}},
                "Siguiente accion": {"type": "rich_text", "rich_text": []},
            },
        }
    ]

    def fake_query(database_id, filter_payload=None, page_size=50):
        if database_id == "projects-db":
            return projects_result
        if database_id == "deliverables-db":
            return deliverables_result
        raise AssertionError(f"unexpected database id: {database_id}")

    monkeypatch.setattr(openclaw_panel_vps.config, "NOTION_PROJECTS_DB_ID", "projects-db")
    monkeypatch.setattr(openclaw_panel_vps.config, "NOTION_DELIVERABLES_DB_ID", "deliverables-db")
    monkeypatch.setattr(openclaw_panel_vps, "_query_db", fake_query)

    snapshot = openclaw_panel_vps._build_operational_snapshot(bridge_db_id=None)
    assert snapshot["summary"]["pending_deliverables"] == 1
    assert snapshot["summary"]["bridge_live"] == 0
    assert snapshot["summary"]["bridge_available"] is False


def test_tidy_navigation_sections_inserts_quick_access_heading(monkeypatch):
    initial_children = [
        {"id": "callout-1", "type": "callout", "callout": {"rich_text": []}},
        {"id": "divider-1", "type": "divider", "divider": {}},
        {"id": "page-1", "type": "child_page", "child_page": {"title": "Dashboard Rick"}},
        {
            "id": "heading-1",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bases operativas", "text": {"content": "Bases operativas"}}]},
        },
    ]
    updated_children = [
        {"id": "callout-1", "type": "callout", "callout": {"rich_text": []}},
        {"id": "divider-1", "type": "divider", "divider": {}},
        {
            "id": "heading-quick",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Accesos rapidos", "text": {"content": "Accesos rapidos"}}]},
        },
        {"id": "page-1", "type": "child_page", "child_page": {"title": "Dashboard Rick"}},
        {
            "id": "heading-1",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bases operativas", "text": {"content": "Bases operativas"}}]},
        },
    ]
    inserted = []

    def fake_insert_after(page_id, after_block_id, blocks):
        inserted.extend(blocks)

    monkeypatch.setattr(openclaw_panel_vps, "_insert_after", fake_insert_after)
    monkeypatch.setattr(openclaw_panel_vps, "_list_children", lambda page_id: updated_children)
    monkeypatch.setattr(openclaw_panel_vps, "_update_block_text", lambda block, text, emoji=None: None)

    openclaw_panel_vps._tidy_navigation_sections("page-root", initial_children)
    assert inserted
    assert inserted[0]["type"] == "heading_3"
