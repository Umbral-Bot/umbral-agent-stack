"""
Tests for notion.upsert_task relation-aware behavior.
"""

from unittest.mock import MagicMock, patch


def test_handle_notion_upsert_task_resolves_project_and_deliverable_names_and_adds_page_blocks():
    from worker.tasks.notion import handle_notion_upsert_task

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "deliverables-db"
        mock_nc.query_database.side_effect = [
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
            [{"id": "deliverable-page-1", "url": "https://www.notion.so/deliverable-page-1"}],
        ]
        mock_nc.upsert_task.return_value = {"page_id": "task-page-1", "updated": True}

        result = handle_notion_upsert_task(
            {
                "task_id": "task-123",
                "status": "running",
                "team": "marketing",
                "task": "Benchmark Ruben",
                "task_name": "Analizar benchmark de Ruben para el embudo",
                "project_name": "Proyecto Embudo Ventas",
                "deliverable_name": "Benchmark Ruben Hassid - sistema contenido y funnel",
            }
        )

    assert result["page_id"] == "task-page-1"
    assert mock_nc.upsert_task.call_args.kwargs["project_page_id"] == "project-page-1"
    assert mock_nc.upsert_task.call_args.kwargs["deliverable_page_id"] == "deliverable-page-1"
    assert mock_nc.upsert_task.call_args.kwargs["icon"] == "\U0001F3AF"
    assert mock_nc.upsert_task.call_args.kwargs["task_name"] == "Analizar benchmark de Ruben para el embudo"
    assert mock_nc.upsert_task.call_args.kwargs["children"]


def test_handle_notion_upsert_task_prefers_explicit_relation_ids():
    from worker.tasks.notion import handle_notion_upsert_task

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "deliverables-db"
        mock_nc.get_page.return_value = {
            "id": "project-explicit",
            "url": "https://www.notion.so/project-explicit",
            "icon": {"type": "emoji", "emoji": "\U0001F504"},
            "properties": {
                "Nombre": {
                    "type": "title",
                    "title": [{"plain_text": "Auditoria Mejora Continua"}],
                }
            },
        }
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
    assert mock_nc.upsert_task.call_args.kwargs["icon"] == "\U0001F504"


def test_handle_notion_upsert_task_infers_icon_from_text_without_project():
    from worker.tasks.notion import handle_notion_upsert_task

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "deliverables-db"
        mock_nc.upsert_task.return_value = {"page_id": "task-page-3", "updated": True}

        result = handle_notion_upsert_task(
            {
                "task_id": "task-789",
                "status": "queued",
                "team": "ops",
                "task": "Preparar blog editorial",
            }
        )

    assert result["page_id"] == "task-page-3"
    assert mock_nc.upsert_task.call_args.kwargs["icon"] == "\u270d\ufe0f"


def test_notion_client_upsert_task_includes_relation_properties_icon_and_children_on_create():
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
            task_name="Relacionar entregable del proyecto",
            project_page_id="project-page-9",
            deliverable_page_id="deliverable-page-9",
            icon="\U0001F3AF",
            children=[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}],
        )

    assert result["created"] is True
    create_payload = mock_client.post.call_args_list[1].kwargs["json"]
    assert create_payload["properties"]["Task"]["title"][0]["text"]["content"] == "Relacionar entregable del proyecto"
    assert create_payload["properties"]["Proyecto"]["relation"] == [{"id": "project-page-9"}]
    assert create_payload["properties"]["Entregable"]["relation"] == [{"id": "deliverable-page-9"}]
    assert create_payload["icon"] == {"type": "emoji", "emoji": "\U0001F3AF"}
    assert create_payload["children"] == [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}]


def test_build_task_page_blocks_show_human_name_and_technical_task():
    from worker.tasks.notion import _build_task_page_blocks

    blocks = _build_task_page_blocks(
        {
            "task_id": "task-900",
            "status": "running",
            "team": "ops",
            "task": "notion.upsert_task",
            "task_name": "Registrar tarea de smoke ligada al embudo",
        },
        project_context={"name": "Proyecto Embudo Ventas"},
        deliverable_name="Benchmark del sistema de contenido y funnel de Ruben Hassid",
    )

    plain_texts = []
    for block in blocks:
        rich_text = next(iter((block.get(k) or {}).get("rich_text", []) for k in block if isinstance(block.get(k), dict)), [])
        plain_texts.extend(piece.get("text", {}).get("content", "") for piece in rich_text)

    assert "Registrar tarea de smoke ligada al embudo" in plain_texts
    assert "Task técnico: notion.upsert_task" in plain_texts
