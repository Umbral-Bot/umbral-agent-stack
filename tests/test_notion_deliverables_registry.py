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


def test_upsert_deliverable_creates_new():
    from worker.tasks.notion import handle_notion_upsert_deliverable

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "db-uuid-456"
        mock_cfg.NOTION_PROJECTS_DB_ID = "projects-db"
        mock_nc.query_database.side_effect = [
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
                "name": "Benchmark Talana",
                "project_name": "Proyecto Embudo Ventas",
                "deliverable_type": "Benchmark",
                "review_status": "Pendiente revision",
                "agent": "Rick",
                "summary": "Resumen",
                "icon": "📬",
            }
        )

    assert result["ok"] is True
    assert result["created"] is True
    assert result["page_id"] == "new-deliverable-id"
    mock_nc.create_database_page.assert_called_once()
    assert mock_nc.create_database_page.call_args.kwargs["icon"] == "📬"
    created_props = mock_nc.create_database_page.call_args.kwargs["properties"]
    assert created_props["Proyecto"]["relation"][0]["id"] == "project-page-1"


def test_upsert_deliverable_updates_existing():
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
                "icon": "📝",
            }
        )

    assert result["ok"] is True
    assert result["created"] is False
    assert result["page_id"] == "deliverable-id"
    mock_nc.update_page_properties.assert_called_once()
    assert mock_nc.update_page_properties.call_args.kwargs["icon"] == "📝"


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
                    "icon": {"type": "emoji", "emoji": "🎯"},
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
    assert mock_nc.create_database_page.call_args.kwargs["icon"] == "🎯"
