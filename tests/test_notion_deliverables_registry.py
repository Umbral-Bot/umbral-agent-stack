"""
Tests for notion.upsert_deliverable handler.
"""

from unittest.mock import patch


def test_upsert_deliverable_requires_name():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    result = handle_notion_upsert_deliverable({})
    assert result["ok"] is False
    assert "name" in result["error"].lower()


def test_upsert_deliverable_no_db_configured():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    with patch("worker.tasks.notion.config") as mock_cfg:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = None
        result = handle_notion_upsert_deliverable({"name": "Deliverable"})

    assert result["ok"] is False
    assert "NOTION_DELIVERABLES_DB_ID" in result["error"]


def test_upsert_deliverable_creates_new_with_normalized_name_due_date_and_blocks():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "db-uuid-456"
        mock_cfg.NOTION_PROJECTS_DB_ID = "projects-db"
        mock_nc.query_database.side_effect = [
            [],
            [],
            [{"id": "project-page-1", "url": "https://www.notion.so/project-page-1"}],
        ]
        mock_nc.create_database_page.return_value = {
            "page_id": "new-deliverable-id",
            "url": "https://www.notion.so/new-deliverable-id",
            "created": True,
        }

        result = handle_notion_upsert_deliverable(
            {
                "name": "benchmark-talana-2026-03-15",
                "project_name": "Proyecto Embudo Ventas",
                "deliverable_type": "Benchmark",
                "review_status": "Pendiente revision",
                "date": "2026-03-15",
                "agent": "Rick",
                "summary": "Resumen",
                "icon": "\U0001F4EC",
            }
        )

    assert result["ok"] is True
    assert result["created"] is True
    assert result["page_id"] == "new-deliverable-id"
    mock_nc.create_database_page.assert_called_once()
    assert mock_nc.create_database_page.call_args.kwargs["icon"] == "\U0001F4EC"
    assert mock_nc.create_database_page.call_args.kwargs["children"]
    created_props = mock_nc.create_database_page.call_args.kwargs["properties"]
    assert created_props["Nombre"]["title"][0]["text"]["content"] == "Benchmark Talana"
    assert created_props["Proyecto"]["relation"][0]["id"] == "project-page-1"
    assert created_props["Fecha limite sugerida"]["date"]["start"] == "2026-03-18"
    assert created_props["Procedencia"]["select"]["name"] == "Manual"


def test_upsert_deliverable_updates_existing_and_replaces_page_blocks():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    existing_page = {"id": "deliverable-id", "url": "https://www.notion.so/deliverable-id", "properties": {}}

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "db-uuid-456"
        mock_cfg.NOTION_PROJECTS_DB_ID = "projects-db"
        mock_nc.query_database.return_value = [existing_page]
        mock_nc.update_page_properties.return_value = {
            "page_id": "deliverable-id",
            "url": "https://www.notion.so/deliverable-id",
            "updated": True,
        }

        result = handle_notion_upsert_deliverable(
            {
                "name": "Benchmark Talana",
                "review_status": "Aprobado",
                "next_action": "Aplicar al embudo",
                "icon": "\U0001F4DD",
            }
        )

    assert result["ok"] is True
    assert result["created"] is False
    assert result["page_id"] == "deliverable-id"
    mock_nc.update_page_properties.assert_called_once()
    assert mock_nc.update_page_properties.call_args.kwargs["icon"] == "\U0001F4DD"
    mock_nc.replace_blocks_in_page.assert_called_once()


def test_upsert_deliverable_inherits_project_icon_when_missing():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "db-uuid-456"
        mock_cfg.NOTION_PROJECTS_DB_ID = "projects-db"
        mock_nc.query_database.side_effect = [
            [],
            [
                {
                    "id": "project-page-1",
                    "url": "https://www.notion.so/project-page-1",
                    "icon": {"type": "emoji", "emoji": "\U0001F3AF"},
                    "properties": {
                        "Nombre": {
                            "type": "title",
                            "title": [{"plain_text": "Proyecto Embudo Ventas"}],
                        }
                    },
                }
            ],
        ]
        mock_nc.create_database_page.return_value = {
            "page_id": "new-deliverable-id",
            "url": "https://www.notion.so/new-deliverable-id",
            "created": True,
        }

        result = handle_notion_upsert_deliverable(
            {
                "name": "Benchmark embudo",
                "project_name": "Proyecto Embudo Ventas",
                "deliverable_type": "Benchmark",
            }
        )

    assert result["ok"] is True
    assert mock_nc.create_database_page.call_args.kwargs["icon"] == "\U0001F3AF"


def test_upsert_deliverable_falls_back_to_original_title_lookup():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    existing_page = {"id": "deliverable-id", "url": "https://www.notion.so/deliverable-id", "properties": {}}

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "db-uuid-456"
        mock_cfg.NOTION_PROJECTS_DB_ID = "projects-db"
        mock_nc.query_database.side_effect = [
            [],
            [existing_page],
        ]
        mock_nc.update_page_properties.return_value = {
            "page_id": "deliverable-id",
            "url": "https://www.notion.so/deliverable-id",
            "updated": True,
        }
        mock_nc.read_page.return_value = {"plain_text": "Already has content"}

        result = handle_notion_upsert_deliverable(
            {
                "name": "Benchmark Talana - 2026-03-10",
                "review_status": "Pendiente revision",
            }
        )

    assert result["ok"] is True
    assert result["created"] is False
    assert mock_nc.query_database.call_count == 2


def test_upsert_deliverable_marks_task_provenance_and_surfaces_it_in_page_blocks():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "db-uuid-456"
        mock_cfg.NOTION_PROJECTS_DB_ID = "projects-db"
        mock_nc.query_database.side_effect = [
            [],
            [
                {
                    "id": "project-page-1",
                    "url": "https://www.notion.so/project-page-1",
                    "icon": {"type": "emoji", "emoji": "\U0001F3AF"},
                    "properties": {
                        "Nombre": {
                            "type": "title",
                            "title": [{"plain_text": "Proyecto Embudo Ventas"}],
                        }
                    },
                }
            ],
        ]
        mock_nc.create_database_page.return_value = {
            "page_id": "new-deliverable-id",
            "url": "https://www.notion.so/new-deliverable-id",
            "created": True,
        }

        result = handle_notion_upsert_deliverable(
            {
                "name": "Cierre critico del embudo",
                "project_name": "Proyecto Embudo Ventas",
                "deliverable_type": "Reporte",
                "review_status": "Pendiente revision",
                "source_task_id": "task-123",
            }
        )

    assert result["ok"] is True
    created_props = mock_nc.create_database_page.call_args.kwargs["properties"]
    assert created_props["Procedencia"]["select"]["name"] == "Tarea"
    assert created_props["Task ID origen"]["rich_text"][0]["text"]["content"] == "task-123"
    children = mock_nc.create_database_page.call_args.kwargs["children"]
    flat_text = []
    for block in children:
        for value in block.values():
            if isinstance(value, dict):
                for item in value.get("rich_text", []):
                    flat_text.append(item.get("text", {}).get("content", ""))
    assert "Procedencia: Tarea" in flat_text
    assert "Task ID origen: task-123" in flat_text
