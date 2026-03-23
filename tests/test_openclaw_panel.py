from scripts import openclaw_panel_vps
from scripts.openclaw_panel_vps import _build_panel_blocks, validate_openclaw_shell


def test_build_panel_blocks_use_summary_table_and_operational_tables():
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
                "review": "Pendiente revisión",
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
                "project": "Proyecto Embudo Ventas",
                "priority": "Alta",
                "next_action": "Resolver revisión humana del benchmark y dejar siguiente tarea.",
            }
        ],
        "due_items": [
            {
                "due_date": "2026-03-18",
                "name": "Cierre crítico del estado real del proyecto embudo",
                "project_name": "Proyecto Embudo Ventas",
                "review": "Pendiente revisión",
            }
        ],
    }

    blocks = _build_panel_blocks(snapshot)
    types = [b["type"] for b in blocks]
    assert types.count("column_list") == 0
    assert types.count("table") == 5
    assert types.count("toggle") == 1
    assert blocks[1]["type"] == "callout"
    assert blocks[2]["type"] == "heading_3"
    assert openclaw_panel_vps._extract_text(blocks[2]) == "Lectura rápida"
    summary_table_text = str(blocks[3])
    assert "Entregables" in summary_table_text
    assert "3 por revisar" in summary_table_text
    assert "1 con ajustes" in summary_table_text


def test_primary_focus_prioritizes_first_pending_deliverable():
    snapshot = {
        "summary": {
            "pending_deliverables": 1,
            "deliverables_adjustments": 0,
            "projects_attention": 0,
            "bridge_live": 0,
            "bridge_available": True,
            "due_items": 1,
        },
        "pending_deliverables": [
            {
                "name": "Benchmark parcial de Kris Wojslaw para el embudo",
                "project_name": "Proyecto Embudo Ventas",
                "review": "Pendiente revisión",
                "due_date": "2026-03-18",
                "next_action": "Verificar evidencia real antes de aprobar.",
            }
        ],
        "projects_attention": [],
        "bridge_live": [],
        "due_items": [],
    }

    focus = openclaw_panel_vps._primary_focus(snapshot)
    assert focus["title"] == "Prioridad inmediata"
    assert "Entregable:" in focus["body"]
    assert "Proyecto:" in focus["body"]
    assert "Kris Wojslaw" in focus["body"]
    assert focus["emoji"] == "🎯"


def test_primary_focus_bridge_uses_project_and_next_action():
    snapshot = {
        "summary": {
            "pending_deliverables": 0,
            "deliverables_adjustments": 0,
            "projects_attention": 0,
            "bridge_live": 1,
            "bridge_available": True,
            "due_items": 0,
        },
        "pending_deliverables": [],
        "projects_attention": [],
        "bridge_live": [
            {
                "title": "Responder comentario de validación",
                "status": "Esperando",
                "project": "Proyecto Embudo Ventas",
                "priority": "Alta",
                "next_action": "Confirmar si se deriva a entregable o se cierra como parcial.",
                "notes": "Caso Kris en revisión.",
            }
        ],
        "due_items": [],
    }

    focus = openclaw_panel_vps._primary_focus(snapshot)
    assert focus["title"] == "Coordinación viva"
    assert "Item:" in focus["body"]
    assert "Proyecto Embudo Ventas" in focus["body"]
    assert "Confirmar si se deriva" in focus["body"]
    assert focus["emoji"] == "📮"


def test_synchronize_summary_callout_updates_first_callout_after_summary(monkeypatch):
    snapshot = {
        "summary": {
            "pending_deliverables": 1,
            "deliverables_adjustments": 0,
            "projects_attention": 0,
            "bridge_live": 0,
            "bridge_available": True,
            "due_items": 1,
        },
        "pending_deliverables": [
            {
                "name": "Benchmark del sistema de contenido y funnel de Ruben Hassid",
                "project_name": "Proyecto Embudo Ventas",
                "review": "Pendiente revisión",
                "due_date": "2026-03-16",
                "next_action": "Revisar y decidir si se integra o se archiva.",
            }
        ],
        "projects_attention": [],
        "bridge_live": [],
        "due_items": [],
    }
    children = [
        {"id": "root", "type": "callout", "callout": {"rich_text": []}},
        {
            "id": "summary",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Resumen ejecutivo", "text": {"content": "Resumen ejecutivo"}}]},
        },
        {"id": "focus", "type": "callout", "callout": {"rich_text": [{"plain_text": "Viejo", "text": {"content": "Viejo"}}]}},
        {
            "id": "next",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Lectura rápida", "text": {"content": "Lectura rápida"}}]},
        },
    ]
    updates = []

    monkeypatch.setattr(
        openclaw_panel_vps,
        "_update_block_text",
        lambda block, text, emoji=None: updates.append((block["id"], text, emoji)),
    )

    openclaw_panel_vps._synchronize_summary_callout(children, snapshot)
    assert updates
    assert updates[0][0] == "focus"
    assert "Ruben Hassid" in updates[0][1]
    assert updates[0][2] == "🎯"


def test_validate_openclaw_shell_requires_anchor_and_databases():
    children = [
        {"id": "a", "type": "callout", "callout": {"rich_text": []}},
        {
            "id": "h1",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Resumen ejecutivo", "text": {"content": "Resumen ejecutivo"}}]},
        },
        {
            "id": "h2",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Lectura rápida", "text": {"content": "Lectura rápida"}}]},
        },
        {
            "id": "h3",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Entregables por revisar", "text": {"content": "Entregables por revisar"}}]},
        },
        {
            "id": "h4",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Proyectos que requieren atención", "text": {"content": "Proyectos que requieren atención"}}]
            },
        },
        {
            "id": "h5",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bandeja viva", "text": {"content": "Bandeja viva"}}]},
        },
        {
            "id": "h6",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Próximos vencimientos", "text": {"content": "Próximos vencimientos"}}]},
        },
        {
            "id": "b",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Bases operativas y paneles", "text": {"content": "Bases operativas y paneles"}}]
            },
        },
        {"id": "c", "type": "child_database", "child_database": {"title": "Proyectos"}},
        {"id": "d", "type": "child_database", "child_database": {"title": "Tareas"}},
        {"id": "e", "type": "child_database", "child_database": {"title": "Entregables"}},
    ]
    result = validate_openclaw_shell(children)
    assert result["ok"] is True
    assert result["child_databases_after_anchor"] == 3
    assert result["required_headings_present"] is True
    assert result["quick_access_present"] is False


def test_validate_openclaw_shell_fails_with_residual_child_page():
    children = [
        {"id": "a", "type": "callout", "callout": {"rich_text": []}},
        {
            "id": "h1",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Resumen ejecutivo", "text": {"content": "Resumen ejecutivo"}}]},
        },
        {
            "id": "h2",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Lectura rápida", "text": {"content": "Lectura rápida"}}]},
        },
        {
            "id": "h3",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Entregables por revisar", "text": {"content": "Entregables por revisar"}}]},
        },
        {
            "id": "h4",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Proyectos que requieren atención", "text": {"content": "Proyectos que requieren atención"}}]
            },
        },
        {
            "id": "h5",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bandeja viva", "text": {"content": "Bandeja viva"}}]},
        },
        {
            "id": "h6",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Próximos vencimientos", "text": {"content": "Próximos vencimientos"}}]},
        },
        {
            "id": "b",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Bases operativas y paneles", "text": {"content": "Bases operativas y paneles"}}]
            },
        },
        {"id": "c", "type": "child_database", "child_database": {"title": "Proyectos"}},
        {"id": "d", "type": "child_database", "child_database": {"title": "Tareas"}},
        {"id": "e", "type": "child_database", "child_database": {"title": "Entregables"}},
        {"id": "page-1", "type": "child_page", "child_page": {"title": "Benchmark parcial - Kris Wojslaw"}},
    ]
    result = validate_openclaw_shell(children)
    assert result["ok"] is False
    assert result["residual_child_pages"] == 1


def test_validate_openclaw_shell_allows_dashboard_rick_child_page():
    children = [
        {"id": "a", "type": "callout", "callout": {"rich_text": []}},
        {
            "id": "h1",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Resumen ejecutivo", "text": {"content": "Resumen ejecutivo"}}]},
        },
        {
            "id": "h2",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Lectura rápida", "text": {"content": "Lectura rápida"}}]},
        },
        {
            "id": "h3",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Entregables por revisar", "text": {"content": "Entregables por revisar"}}]},
        },
        {
            "id": "h4",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Proyectos que requieren atención", "text": {"content": "Proyectos que requieren atención"}}]
            },
        },
        {
            "id": "h5",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bandeja viva", "text": {"content": "Bandeja viva"}}]},
        },
        {
            "id": "h6",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Próximos vencimientos", "text": {"content": "Próximos vencimientos"}}]},
        },
        {
            "id": "b",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Bases operativas y paneles", "text": {"content": "Bases operativas y paneles"}}]
            },
        },
        {"id": "c", "type": "child_database", "child_database": {"title": "Proyectos"}},
        {"id": "d", "type": "child_database", "child_database": {"title": "Tareas"}},
        {"id": "e", "type": "child_database", "child_database": {"title": "Entregables"}},
        {"id": "page-1", "type": "child_page", "child_page": {"title": "Dashboard Rick"}},
    ]
    result = validate_openclaw_shell(children)
    assert result["ok"] is True
    assert result["residual_child_pages"] == 0
    assert result["quick_access_present"] is True


def test_validate_openclaw_shell_allows_supervisor_alert_page_child():
    children = [
        {"id": "a", "type": "callout", "callout": {"rich_text": []}},
        {
            "id": "h1",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Resumen ejecutivo", "text": {"content": "Resumen ejecutivo"}}]},
        },
        {
            "id": "h2",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Lectura rápida", "text": {"content": "Lectura rápida"}}]},
        },
        {
            "id": "h3",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Entregables por revisar", "text": {"content": "Entregables por revisar"}}]},
        },
        {
            "id": "h4",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Proyectos que requieren atención", "text": {"content": "Proyectos que requieren atención"}}]
            },
        },
        {
            "id": "h5",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bandeja viva", "text": {"content": "Bandeja viva"}}]},
        },
        {
            "id": "h6",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Próximos vencimientos", "text": {"content": "Próximos vencimientos"}}]},
        },
        {
            "id": "b",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Bases operativas y paneles", "text": {"content": "Bases operativas y paneles"}}]
            },
        },
        {"id": "c", "type": "child_database", "child_database": {"title": "Proyectos"}},
        {"id": "d", "type": "child_database", "child_database": {"title": "Tareas"}},
        {"id": "e", "type": "child_database", "child_database": {"title": "Entregables"}},
        {"id": "page-2", "type": "child_page", "child_page": {"title": "Alertas del Supervisor"}},
    ]
    result = validate_openclaw_shell(children)
    assert result["ok"] is True
    assert result["residual_child_pages"] == 0
    assert result["quick_access_present"] is True


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


def test_build_operational_snapshot_sorts_by_urgency(monkeypatch):
    projects_result = [
        {
            "id": "proj-1",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Proyecto Bajo"}]},
                "Bloqueos": {"type": "rich_text", "rich_text": []},
                "Siguiente acción": {"type": "rich_text", "rich_text": []},
                "Tareas": {"type": "relation", "relation": []},
                "Issues abiertas": {"type": "number", "number": 1},
            },
        },
        {
            "id": "proj-2",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Proyecto Crítico"}]},
                "Bloqueos": {"type": "rich_text", "rich_text": [{"plain_text": "Bloqueado"}]},
                "Siguiente acción": {"type": "rich_text", "rich_text": []},
                "Tareas": {"type": "relation", "relation": [{"id": "task-1"}]},
                "Issues abiertas": {"type": "number", "number": 9},
            },
        },
    ]
    deliverables_result = [
        {
            "id": "del-1",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Entrega tardía"}]},
                "Estado revision": {"type": "status", "status": {"name": "Aprobado con ajustes"}},
                "Proyecto": {"type": "relation", "relation": [{"id": "proj-1"}]},
                "Fecha limite sugerida": {"type": "date", "date": {"start": "2026-03-20"}},
                "Siguiente accion": {"type": "rich_text", "rich_text": []},
            },
        },
        {
            "id": "del-2",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Entrega urgente"}]},
                "Estado revision": {"type": "status", "status": {"name": "Pendiente revision"}},
                "Proyecto": {"type": "relation", "relation": [{"id": "proj-2"}]},
                "Fecha limite sugerida": {"type": "date", "date": {"start": "2026-03-17"}},
                "Siguiente accion": {"type": "rich_text", "rich_text": []},
            },
        },
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
    assert snapshot["pending_deliverables"][0]["name"] == "Entrega urgente"
    assert snapshot["projects_attention"][0]["name"] == "Proyecto Crítico"


def test_build_operational_snapshot_prefers_pending_review_over_adjustments(monkeypatch):
    projects_result = [
        {
            "id": "proj-1",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Proyecto A"}]},
                "Bloqueos": {"type": "rich_text", "rich_text": []},
                "Siguiente acción": {"type": "rich_text", "rich_text": []},
                "Tareas": {"type": "relation", "relation": [{"id": "task-1"}]},
                "Issues abiertas": {"type": "number", "number": 0},
            },
        }
    ]
    deliverables_result = [
        {
            "id": "del-older-adjustment",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Ajuste atrasado"}]},
                "Estado revision": {"type": "status", "status": {"name": "Aprobado con ajustes"}},
                "Proyecto": {"type": "relation", "relation": [{"id": "proj-1"}]},
                "Fecha limite sugerida": {"type": "date", "date": {"start": "2026-03-11"}},
                "Siguiente accion": {"type": "rich_text", "rich_text": []},
            },
        },
        {
            "id": "del-pending",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Decisión pendiente"}]},
                "Estado revision": {"type": "status", "status": {"name": "Pendiente revision"}},
                "Proyecto": {"type": "relation", "relation": [{"id": "proj-1"}]},
                "Fecha limite sugerida": {"type": "date", "date": {"start": "2026-03-18"}},
                "Siguiente accion": {"type": "rich_text", "rich_text": []},
            },
        },
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
    assert snapshot["pending_deliverables"][0]["name"] == "Decisión pendiente"


def test_tidy_navigation_sections_inserts_navigation_heading(monkeypatch):
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
            "id": "heading-nav",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"plain_text": "Bases operativas y paneles", "text": {"content": "Bases operativas y paneles"}}]
            },
        },
        {"id": "page-1", "type": "child_page", "child_page": {"title": "Dashboard Rick"}},
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
    assert openclaw_panel_vps._extract_text(inserted[0]) == "Bases operativas y paneles"


def test_is_residual_child_page_matches_known_generated_titles():
    assert openclaw_panel_vps._is_residual_child_page(
        {"id": "a", "type": "child_page", "child_page": {"title": "OODA Weekly Report - 2026-03-16"}}
    )
    assert openclaw_panel_vps._is_residual_child_page(
        {
            "id": "b",
            "type": "child_page",
            "child_page": {"title": "[improvement] Workflow: self_improvement_cycle - SIM Daily Report"},
        }
    )
    assert not openclaw_panel_vps._is_residual_child_page(
        {"id": "c", "type": "child_page", "child_page": {"title": "Dashboard Rick"}}
    )
    assert not openclaw_panel_vps._is_residual_child_page(
        {"id": "d", "type": "child_page", "child_page": {"title": "Alertas del Supervisor"}}
    )


def test_cleanup_openclaw_residuals_archives_generated_pages_and_empty_paragraphs(monkeypatch):
    archived = []
    deleted = []
    monkeypatch.setattr(openclaw_panel_vps, "_archive_pages", lambda page_ids: archived.extend(page_ids))
    monkeypatch.setattr(openclaw_panel_vps, "_delete_blocks", lambda block_ids: deleted.extend(block_ids))

    cleaned = openclaw_panel_vps._cleanup_openclaw_residuals(
        [
            {"id": "keep-1", "type": "child_page", "child_page": {"title": "Dashboard Rick"}},
            {"id": "keep-2", "type": "child_page", "child_page": {"title": "Alertas del Supervisor"}},
            {"id": "res-1", "type": "child_page", "child_page": {"title": "OODA Weekly Report - 2026-03-16"}},
            {"id": "res-2", "type": "child_page", "child_page": {"title": "[improvement] Workflow: self_improvement_cycle - SIM Daily Report"}},
            {"id": "blank-1", "type": "paragraph", "paragraph": {"rich_text": []}},
            {"id": "blank-2", "type": "paragraph", "paragraph": {"rich_text": []}},
        ]
    )

    assert archived == ["res-1", "res-2"]
    assert deleted == ["blank-1", "blank-2"]
    assert cleaned == 4


def test_rename_navigation_pages_uses_canonical_titles(monkeypatch):
    children = [
        {"id": "dash-id", "type": "child_page", "child_page": {"title": "Dashboard viejo"}},
        {"id": "alert-id", "type": "child_page", "child_page": {"title": "Dashboard Rick"}},
        {"id": "other-id", "type": "child_page", "child_page": {"title": "Otra página"}},
    ]
    renamed = []

    monkeypatch.setattr(openclaw_panel_vps.config, "NOTION_DASHBOARD_PAGE_ID", "dash-id")
    monkeypatch.setattr(openclaw_panel_vps, "SUPERVISOR_ALERT_PAGE_ID", "alert-id")
    monkeypatch.setattr(openclaw_panel_vps, "_update_page_title", lambda page_id, title: renamed.append((page_id, title)))

    count = openclaw_panel_vps._rename_navigation_pages(children)

    assert count == 2
    assert renamed == [
        ("dash-id", "Dashboard Rick"),
        ("alert-id", "Alertas del Supervisor"),
    ]


def test_canonical_nav_page_title_tolerates_hyphenless_env_ids(monkeypatch):
    monkeypatch.setattr(openclaw_panel_vps.config, "NOTION_DASHBOARD_PAGE_ID", "3265f443fb5c816d9ce8c5d6cf075f9c")
    monkeypatch.setattr(openclaw_panel_vps, "SUPERVISOR_ALERT_PAGE_ID", "0fd13978b220498e9465b4fb2efc5f4a")

    assert (
        openclaw_panel_vps._canonical_nav_page_title(
            "3265f443-fb5c-816d-9ce8-c5d6cf075f9c",
            "Dashboard viejo",
        )
        == "Dashboard Rick"
    )
    assert (
        openclaw_panel_vps._canonical_nav_page_title(
            "0fd13978-b220-498e-9465-b4fb2efc5f4a",
            "Dashboard Rick",
        )
        == "Alertas del Supervisor"
    )


def test_remove_stale_blocks_archives_child_pages_and_deletes_normal_blocks(monkeypatch):
    archived = []
    deleted = []
    monkeypatch.setattr(openclaw_panel_vps, "_archive_pages", lambda page_ids: archived.extend(page_ids))
    monkeypatch.setattr(openclaw_panel_vps, "_delete_blocks", lambda block_ids: deleted.extend(block_ids))

    removed = openclaw_panel_vps._remove_stale_blocks(
        [
            {"id": "page-1", "type": "child_page", "child_page": {"title": "Residual page"}},
            {"id": "table-1", "type": "table", "table": {}},
            {"id": "db-1", "type": "child_database", "child_database": {"title": "Keep db"}},
        ]
    )

    assert archived == ["page-1"]
    assert deleted == ["table-1"]
    assert removed == 2


def test_delete_blocks_ignores_already_archived_or_missing(monkeypatch):
    class FakeResponse:
        def __init__(self, status_code, text=""):
            self.status_code = status_code
            self.text = text

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def patch(self, url, headers=None, json=None):
            if url.endswith("/block-a"):
                return FakeResponse(400, "{\"message\":\"Can't edit block that is archived.\"}")
            if url.endswith("/block-b"):
                return FakeResponse(404, '{"code":"object_not_found"}')
            return FakeResponse(200, "{}")

    monkeypatch.setattr(openclaw_panel_vps, "_api_client", lambda: FakeClient())
    monkeypatch.setattr(openclaw_panel_vps, "_headers", lambda: {})
    monkeypatch.setattr(openclaw_panel_vps.notion_client, "_check_response", lambda resp, op: {"ok": True})

    openclaw_panel_vps._delete_blocks(["block-a", "block-b", "block-c"])


def test_refresh_openclaw_panel_skips_when_fingerprint_unchanged(monkeypatch, tmp_path):
    children = [
        {"id": "a", "type": "callout", "callout": {"rich_text": []}},
        {
            "id": "h1",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Resumen ejecutivo", "text": {"content": "Resumen ejecutivo"}}]},
        },
        {
            "id": "h2",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Lectura rápida", "text": {"content": "Lectura rápida"}}]},
        },
        {
            "id": "h3",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Entregables por revisar", "text": {"content": "Entregables por revisar"}}]},
        },
        {
            "id": "h4",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Proyectos que requieren atención", "text": {"content": "Proyectos que requieren atención"}}]},
        },
        {
            "id": "h5",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bandeja viva", "text": {"content": "Bandeja viva"}}]},
        },
        {
            "id": "h6",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Próximos vencimientos", "text": {"content": "Próximos vencimientos"}}]},
        },
        {
            "id": "b",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Bases operativas y paneles", "text": {"content": "Bases operativas y paneles"}}]},
        },
        {"id": "c", "type": "child_database", "child_database": {"title": "Proyectos"}},
        {"id": "d", "type": "child_database", "child_database": {"title": "Tareas"}},
        {"id": "e", "type": "child_database", "child_database": {"title": "Entregables"}},
    ]
    snapshot = {
        "generated_at": "2026-03-23 12:00 UTC",
        "summary": {
            "pending_deliverables": 0,
            "deliverables_adjustments": 0,
            "projects_attention": 0,
            "bridge_live": 0,
            "bridge_available": True,
            "due_items": 0,
        },
        "pending_deliverables": [],
        "projects_attention": [],
        "bridge_live": [],
        "due_items": [],
    }
    fingerprint = openclaw_panel_vps._snapshot_fingerprint(snapshot)
    events = []

    monkeypatch.setattr(openclaw_panel_vps, "OPENCLAW_PAGE_ID", "openclaw-page")
    monkeypatch.setattr(openclaw_panel_vps, "_FINGERPRINT_PATH", tmp_path / "fp.txt")
    monkeypatch.setattr(openclaw_panel_vps, "_DIRTY_FLAG_PATH", tmp_path / "dirty.json")
    monkeypatch.setattr(openclaw_panel_vps, "_list_children", lambda page_id: children)
    monkeypatch.setattr(openclaw_panel_vps, "_build_operational_snapshot", lambda bridge_db_id=None: snapshot)
    monkeypatch.setattr(openclaw_panel_vps.ops_log, "system_activity", lambda *args, **kwargs: events.append((args, kwargs)))
    (tmp_path / "fp.txt").write_text(fingerprint, encoding="utf-8")

    result = openclaw_panel_vps.refresh_openclaw_panel(trigger="test.skip")

    assert result["updated"] is False
    assert result["skipped"] is True
    assert result["reason"] == "fingerprint_unchanged"
    assert events
    assert events[0][0][2] == "skipped"


def test_trigger_openclaw_panel_refresh_marks_dirty_when_panel_not_ready(monkeypatch, tmp_path):
    monkeypatch.setattr(openclaw_panel_vps, "_DIRTY_FLAG_PATH", tmp_path / "dirty.json")
    monkeypatch.setattr(openclaw_panel_vps, "_openclaw_panel_ready", lambda: False)

    result = openclaw_panel_vps.trigger_openclaw_panel_refresh(
        "project_upsert",
        source="notion.upsert_project",
    )

    assert result["triggered"] is False
    assert result["reason"] == "openclaw_panel_not_ready"
    assert not (tmp_path / "dirty.json").exists()
