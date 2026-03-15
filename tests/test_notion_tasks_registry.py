"""
Tests for notion.upsert_task relation-aware behavior.
"""

from unittest.mock import MagicMock, patch


def test_handle_notion_upsert_task_resolves_project_and_deliverable_names():
    from worker.tasks.notion import handle_notion_upsert_task

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "deliverables-db"
        mock_nc.query_database.side_effect = [
            [{"id": "project-page-1", "url": "https://www.notion.so/project-page-1"}],
            [{"id": "deliverable-page-1", "url": "https://www.notion.so/deliverable-page-1"}],
        ]
        mock_nc.upsert_task.return_value = {"page_id": "task-page-1", "updated": True}

        result = handle_notion_upsert_task(
            {
                "task_id": "task-123",
                "status": "running",
                "team": "marketing",
                "task": "Benchmark Ruben",
                "project_name": "Proyecto Embudo Ventas",
                "deliverable_name": "Benchmark Ruben Hassid - sistema contenido y funnel",
            }
        )

    assert result["page_id"] == "task-page-1"
    assert mock_nc.upsert_task.call_args.kwargs["project_page_id"] == "project-page-1"
    assert mock_nc.upsert_task.call_args.kwargs["deliverable_page_id"] == "deliverable-page-1"


def test_handle_notion_upsert_task_prefers_explicit_relation_ids():
    from worker.tasks.notion import handle_notion_upsert_task

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "deliverables-db"
        mock_nc.upsert_task.return_value = {"page_id": "task-page-2", "updated": True}

        result = handle_notion_upsert_task(
            {
                "task_id": "task-456",
                "status": "done",
                "team": "ops",
                "task": "Cerrar deliverable",
                "project_page_id": "project-explicit",
                "deliverable_page_id": "deliverable-explicit",
            }
        )

    assert result["page_id"] == "task-page-2"
    mock_nc.query_database.assert_not_called()
    assert mock_nc.upsert_task.call_args.kwargs["project_page_id"] == "project-explicit"
    assert mock_nc.upsert_task.call_args.kwargs["deliverable_page_id"] == "deliverable-explicit"


def test_notion_client_upsert_task_includes_relation_properties_on_create():
    from worker import notion_client

    query_response = MagicMock(status_code=200, text="")
    query_response.json.return_value = {"results": []}

    create_response = MagicMock(status_code=200, text="")
    create_response.json.return_value = {"id": "new-task-page", "url": "https://www.notion.so/new-task-page"}

    mock_client = MagicMock()
    mock_client.post.side_effect = [query_response, create_response]

    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_client
    mock_cm.__exit__.return_value = None

    with patch("worker.notion_client.config") as mock_cfg, patch(
        "worker.notion_client.httpx.Client", return_value=mock_cm
    ), patch("worker.notion_client._headers", return_value={"Authorization": "Bearer test"}):
        mock_cfg.NOTION_API_KEY = "secret"
        mock_cfg.NOTION_TASKS_DB_ID = "tasks-db-id"

        result = notion_client.upsert_task(
            task_id="task-789",
            status="done",
            team="improvement",
            task="Relacionar entregable",
            project_page_id="project-page-9",
            deliverable_page_id="deliverable-page-9",
        )

    assert result["created"] is True
    create_payload = mock_client.post.call_args_list[1].kwargs["json"]
    assert create_payload["properties"]["Proyecto"]["relation"] == [{"id": "project-page-9"}]
    assert create_payload["properties"]["Entregable"]["relation"] == [{"id": "deliverable-page-9"}]
