"""
Tests for notion.upsert_project handler.
"""

from unittest.mock import patch


def test_upsert_project_requires_name():
    from worker.tasks.notion import handle_notion_upsert_project

    result = handle_notion_upsert_project({})
    assert result["ok"] is False
    assert "name" in result["error"].lower()


def test_upsert_project_no_db_configured():
    from worker.tasks.notion import handle_notion_upsert_project

    with patch("worker.tasks.notion.config") as mock_cfg:
        mock_cfg.NOTION_PROJECTS_DB_ID = None
        result = handle_notion_upsert_project({"name": "My Project"})

    assert result["ok"] is False
    assert "NOTION_PROJECTS_DB_ID" in result["error"]


def test_upsert_project_creates_new_with_page_blocks():
    from worker.tasks.notion import handle_notion_upsert_project

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_PROJECTS_DB_ID = "db-uuid-123"
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "new-page-id",
            "url": "https://www.notion.so/new-page-id",
            "created": True,
        }

        result = handle_notion_upsert_project(
            {
                "name": "Proyecto Embudo Ventas",
                "estado": "Activo",
                "responsable": "David Moreira",
                "icon": "\U0001F4C1",
            }
        )

    assert result["ok"] is True
    assert result["created"] is True
    assert result["page_id"] == "new-page-id"
    mock_nc.create_database_page.assert_called_once()
    assert mock_nc.create_database_page.call_args.kwargs["icon"] == "\U0001F4C1"
    assert mock_nc.create_database_page.call_args.kwargs["children"]
    mock_nc.update_page_properties.assert_not_called()


def test_upsert_project_updates_existing_and_backfills_page_blocks_when_blank():
    from worker.tasks.notion import handle_notion_upsert_project

    existing_page = {"id": "existing-id", "url": "https://www.notion.so/existing-id", "properties": {}}

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_PROJECTS_DB_ID = "db-uuid-123"
        mock_nc.query_database.return_value = [existing_page]
        mock_nc.update_page_properties.return_value = {
            "page_id": "existing-id",
            "url": "https://www.notion.so/existing-id",
            "updated": True,
        }
        mock_nc.read_page.return_value = {"plain_text": ""}

        result = handle_notion_upsert_project(
            {
                "name": "Proyecto Embudo Ventas",
                "estado": "En pausa",
                "open_issues": 3,
                "icon": "\U0001F9ED",
            }
        )

    assert result["ok"] is True
    assert result["created"] is False
    assert result["page_id"] == "existing-id"
    mock_nc.update_page_properties.assert_called_once_with(
        page_id_or_url="existing-id",
        properties=mock_nc.update_page_properties.call_args.kwargs["properties"],
        icon="\U0001F9ED",
    )
    mock_nc.append_blocks_to_page.assert_called_once()
    mock_nc.create_database_page.assert_not_called()


def test_upsert_project_infers_icon_when_missing():
    from worker.tasks.notion import handle_notion_upsert_project

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_PROJECTS_DB_ID = "db-uuid-123"
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "new-page-id",
            "url": "https://www.notion.so/new-page-id",
            "created": True,
        }

        result = handle_notion_upsert_project({"name": "Proyecto Embudo Ventas"})

    assert result["ok"] is True
    assert mock_nc.create_database_page.call_args.kwargs["icon"] == "\U0001F3AF"
