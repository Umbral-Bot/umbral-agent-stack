"""
Tests for notion.upsert_bridge_item behavior.
"""

from unittest.mock import patch


def test_handle_notion_upsert_bridge_item_creates_page_with_rich_schema():
    from worker.tasks.notion import handle_notion_upsert_bridge_item

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc, patch("worker.tasks.notion._maybe_trigger_openclaw_panel_refresh") as mock_refresh:
        mock_cfg.NOTION_BRIDGE_DB_ID = "bridge-db"
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "bridge-page-1",
            "url": "https://www.notion.so/bridge-page-1",
            "created": True,
        }

        result = handle_notion_upsert_bridge_item(
            {
                "name": "Regularizar benchmark de Kris",
                "status": "En curso",
                "project_name": "Proyecto Embudo Ventas",
                "priority": "Alta",
                "source": "Entregable",
                "notes": "Caso parcial en revisión.",
                "next_action": "Definir si se cierra como parcial o se reabre con evidencia real.",
                "last_move_date": "2026-03-17",
                "link": "https://www.notion.so/bridge-page-1",
                "icon": "🎯",
            }
        )

    assert result["ok"] is True
    assert result["created"] is True
    payload = mock_nc.create_database_page.call_args.kwargs
    assert payload["database_id_or_url"] == "bridge-db"
    assert payload["icon"] == "🎯"
    assert payload["properties"]["Ítem"]["title"][0]["text"]["content"] == "Regularizar benchmark de Kris"
    assert payload["properties"]["Estado"]["status"]["name"] == "En curso"
    assert payload["properties"]["Proyecto"]["rich_text"][0]["text"]["content"] == "Proyecto Embudo Ventas"
    assert payload["properties"]["Prioridad"]["select"]["name"] == "Alta"
    assert payload["properties"]["Origen"]["select"]["name"] == "Entregable"
    assert payload["properties"]["Siguiente acción"]["rich_text"][0]["text"]["content"].startswith("Definir si se cierra")
    assert payload["children"]
    mock_refresh.assert_called_once_with("bridge_item_upsert", source="notion.upsert_bridge_item")


def test_handle_notion_upsert_bridge_item_updates_existing_page_and_replaces_blocks():
    from worker.tasks.notion import handle_notion_upsert_bridge_item

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc, patch(
        "worker.tasks.notion._ensure_page_blocks"
    ) as mock_ensure, patch("worker.tasks.notion._maybe_trigger_openclaw_panel_refresh") as mock_refresh:
        mock_cfg.NOTION_BRIDGE_DB_ID = "bridge-db"
        mock_nc.query_database.return_value = [{"id": "bridge-page-existing"}]
        mock_nc.update_page_properties.return_value = {
            "page_id": "bridge-page-existing",
            "url": "https://www.notion.so/bridge-page-existing",
            "updated": True,
        }

        result = handle_notion_upsert_bridge_item(
            {
                "name": "Responder comentario de Ruben",
                "status": "Esperando",
                "project_name": "Proyecto Embudo Ventas",
                "priority": "Media",
                "source": "Rick",
                "notes": "Pendiente respuesta de validación.",
                "next_action": "Confirmar entregable derivado y dejarlo ligado a tarea.",
            }
        )

    assert result["ok"] is True
    assert result["created"] is False
    update_kwargs = mock_nc.update_page_properties.call_args.kwargs
    assert update_kwargs["page_id_or_url"] == "bridge-page-existing"
    assert update_kwargs["properties"]["Estado"]["status"]["name"] == "Esperando"
    assert update_kwargs["properties"]["Origen"]["select"]["name"] == "Rick"
    mock_ensure.assert_called_once()
    ensure_kwargs = mock_ensure.call_args.kwargs
    assert ensure_kwargs["page_id"] == "bridge-page-existing"
    assert ensure_kwargs["force_replace"] is True
    mock_refresh.assert_called_once_with("bridge_item_upsert", source="notion.upsert_bridge_item")


def test_handle_notion_upsert_bridge_item_falls_back_to_local_title_match_when_filter_misses():
    from worker.tasks.notion import handle_notion_upsert_bridge_item

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc, patch(
        "worker.tasks.notion._ensure_page_blocks"
    ) as mock_ensure:
        mock_cfg.NOTION_BRIDGE_DB_ID = "bridge-db"
        mock_nc._plain_text_from_rich_text.side_effect = lambda items: "".join(
            piece.get("plain_text", "") for piece in (items or [])
        )
        mock_nc.query_database.side_effect = [
            [],
            [
                {
                    "id": "bridge-page-existing",
                    "properties": {
                        "Ítem": {
                            "type": "title",
                            "title": [{"plain_text": "Responder comentario de Ruben"}],
                        }
                    },
                }
            ],
        ]
        mock_nc.update_page_properties.return_value = {
            "page_id": "bridge-page-existing",
            "url": "https://www.notion.so/bridge-page-existing",
            "updated": True,
        }

        result = handle_notion_upsert_bridge_item(
            {
                "name": "Responder comentario de Ruben",
                "status": "En curso",
                "project_name": "Proyecto Embudo Ventas",
            }
        )

    assert result["ok"] is True
    assert result["created"] is False
    assert mock_nc.query_database.call_count == 2
    mock_ensure.assert_called_once()


def test_handle_notion_upsert_bridge_item_updates_explicit_page_id_without_query():
    from worker.tasks.notion import handle_notion_upsert_bridge_item

    with patch("worker.tasks.notion.config") as mock_cfg, patch("worker.tasks.notion.notion_client") as mock_nc, patch(
        "worker.tasks.notion._ensure_page_blocks"
    ) as mock_ensure:
        mock_cfg.NOTION_BRIDGE_DB_ID = "bridge-db"
        mock_nc.update_page_properties.return_value = {
            "page_id": "bridge-page-explicit",
            "url": "https://www.notion.so/bridge-page-explicit",
            "updated": True,
        }

        result = handle_notion_upsert_bridge_item(
            {
                "page_id": "bridge-page-explicit",
                "name": "Responder comentario de Ruben",
                "status": "Resuelto",
            }
        )

    assert result["ok"] is True
    assert result["created"] is False
    mock_nc.query_database.assert_not_called()
    assert mock_nc.update_page_properties.call_args.kwargs["page_id_or_url"] == "bridge-page-explicit"
    mock_ensure.assert_called_once()
