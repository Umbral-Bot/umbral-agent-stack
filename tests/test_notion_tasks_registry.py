"""
Tests for notion.upsert_task relation-aware behavior.
"""

from unittest.mock import MagicMock, patch


def test_handle_notion_upsert_task_resolves_project_and_deliverable_names_and_adds_page_blocks():
    from worker.tasks.notion import handle_notion_upsert_task

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_TASKS_DB_ID = None
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
        mock_cfg.NOTION_TASKS_DB_ID = None
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
        mock_cfg.NOTION_TASKS_DB_ID = None
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


def test_handle_notion_upsert_task_reuses_existing_source_context_when_refreshing():
    from worker.tasks.notion import handle_notion_upsert_task

    existing_task = {
        "id": "task-page-existing",
        "properties": {
            "Source": {"type": "rich_text", "rich_text": [{"plain_text": "notion_poll"}]},
            "Source Kind": {"type": "rich_text", "rich_text": [{"plain_text": "instruction_comment"}]},
            "Trace ID": {"type": "rich_text", "rich_text": [{"plain_text": "trace-kris"}]},
            "Model": {"type": "rich_text", "rich_text": [{"plain_text": "gpt-5.4"}]},
            "Proyecto": {"type": "relation", "relation": [{"id": "project-page-1"}]},
            "Entregable": {"type": "relation", "relation": [{"id": "deliverable-page-1"}]},
        },
    }

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_TASKS_DB_ID = "tasks-db"
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "deliverables-db"
        mock_nc._plain_text_from_rich_text.side_effect = lambda items: "".join(
            piece.get("plain_text", "") for piece in (items or [])
        )
        mock_nc.get_page.side_effect = [
            {
                "id": "project-page-1",
                "url": "https://www.notion.so/project-page-1",
                "icon": {"type": "emoji", "emoji": "\U0001F3AF"},
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Proyecto Embudo Ventas"}]}
                },
            },
            {
                "id": "deliverable-page-1",
                "url": "https://www.notion.so/deliverable-page-1",
                "properties": {
                    "Nombre": {
                        "type": "title",
                        "title": [{"plain_text": "Benchmark parcial de Kris Wojslaw para el embudo"}],
                    }
                },
            },
        ]
        mock_nc.query_database.side_effect = [
            [existing_task],
        ]
        mock_nc.upsert_task.return_value = {"page_id": "task-page-existing", "updated": True}

        result = handle_notion_upsert_task(
            {
                "task_id": "notion-instruction-3265f443",
                "status": "done",
                "team": "Rick",
                "task": "Regularizar cierre y trazabilidad del caso Kris Wojslaw",
            }
        )

    assert result["page_id"] == "task-page-existing"
    kwargs = mock_nc.upsert_task.call_args.kwargs
    assert kwargs["source"] == "notion_poll"
    assert kwargs["source_kind"] == "instruction_comment"
    assert kwargs["trace_id"] == "trace-kris"
    assert kwargs["selected_model"] == "gpt-5.4"
    assert kwargs["project_page_id"] == "project-page-1"
    assert kwargs["deliverable_page_id"] == "deliverable-page-1"
    plain_texts = []
    for block in kwargs["children"]:
        rich_text = next(iter((block.get(k) or {}).get("rich_text", []) for k in block if isinstance(block.get(k), dict)), [])
        plain_texts.extend(piece.get("text", {}).get("content", "") for piece in rich_text)
    assert "Entregable: Benchmark parcial de Kris Wojslaw para el embudo" in plain_texts


def test_handle_notion_upsert_task_infers_project_from_deliverable_relation():
    from worker.tasks.notion import handle_notion_upsert_task

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc:
        mock_cfg.NOTION_TASKS_DB_ID = None
        mock_cfg.NOTION_DELIVERABLES_DB_ID = "deliverables-db"
        mock_nc.get_page.side_effect = [
            {
                "id": "deliverable-page-1",
                "url": "https://www.notion.so/deliverable-page-1",
                "properties": {
                    "Nombre": {
                        "type": "title",
                        "title": [{"plain_text": "Ingeniería inversa del sistema de Ruben Hassid para el embudo"}],
                    },
                    "Proyecto": {
                        "type": "relation",
                        "relation": [{"id": "project-page-1"}],
                    },
                },
            },
            {
                "id": "project-page-1",
                "url": "https://www.notion.so/project-page-1",
                "icon": {"type": "emoji", "emoji": "\U0001F3AF"},
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Proyecto Embudo Ventas"}]}
                },
            },
        ]
        mock_nc.upsert_task.return_value = {"page_id": "task-page-ctx", "updated": True}

        result = handle_notion_upsert_task(
            {
                "task_id": "task-ctx",
                "status": "queued",
                "team": "system",
                "task": "notion_instruction_followup",
                "deliverable_page_id": "deliverable-page-1",
            }
        )

    assert result["page_id"] == "task-page-ctx"
    kwargs = mock_nc.upsert_task.call_args.kwargs
    assert kwargs["deliverable_page_id"] == "deliverable-page-1"
    assert kwargs["project_page_id"] == "project-page-1"
    assert kwargs["icon"] == "\U0001F3AF"


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
            "source": "openclaw_gateway",
            "source_kind": "tool_enqueue",
            "trace_id": "trace-abc",
            "selected_model": "azure_foundry",
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
    assert "Origen: openclaw_gateway" in plain_texts
    assert "Tipo de origen: tool_enqueue" in plain_texts
    assert "Trace ID: trace-abc" in plain_texts
    assert "Modelo seleccionado: azure_foundry" in plain_texts


def test_notion_client_upsert_task_persists_source_trace_and_model():
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

        notion_client.upsert_task(
            task_id="task-900",
            status="done",
            team="ops",
            task="research.web",
            source="openclaw_gateway",
            source_kind="tool_enqueue",
            trace_id="trace-123",
            selected_model="azure_foundry",
        )

    create_payload = mock_client.post.call_args_list[1].kwargs["json"]
    assert create_payload["properties"]["Source"]["rich_text"][0]["text"]["content"] == "openclaw_gateway"
    assert create_payload["properties"]["Source Kind"]["rich_text"][0]["text"]["content"] == "tool_enqueue"
    assert create_payload["properties"]["Trace ID"]["rich_text"][0]["text"]["content"] == "trace-123"
    assert create_payload["properties"]["Model"]["rich_text"][0]["text"]["content"] == "azure_foundry"


def test_notion_client_upsert_task_replaces_page_blocks_on_update():
    from worker import notion_client

    query_response = MagicMock(status_code=200, text="")
    query_response.json.return_value = {"results": [{"id": "task-page-1"}]}

    update_response = MagicMock(status_code=200, text="")
    update_response.json.return_value = {"id": "task-page-1", "url": "https://www.notion.so/task-page-1"}

    mock_client = MagicMock()
    mock_client.post.return_value = query_response
    mock_client.patch.return_value = update_response

    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_client
    mock_cm.__exit__.return_value = None

    with patch("worker.notion_client.config") as mock_cfg, patch(
        "worker.notion_client.httpx.Client", return_value=mock_cm
    ), patch("worker.notion_client._headers", return_value={"Authorization": "Bearer test"}), patch(
        "worker.notion_client.replace_blocks_in_page"
    ) as mock_replace:
        mock_cfg.NOTION_API_KEY = "secret"
        mock_cfg.NOTION_TASKS_DB_ID = "tasks-db-id"

        result = notion_client.upsert_task(
            task_id="task-321",
            status="done",
            team="ops",
            task="notion.upsert_task",
            task_name="Actualizar tarea ligada a entregable",
            project_page_id="project-page-1",
            deliverable_page_id="deliverable-page-1",
            children=[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}],
        )

    assert result["updated"] is True
    mock_replace.assert_called_once_with(
        page_id="task-page-1",
        blocks=[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}],
    )
