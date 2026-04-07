from unittest.mock import MagicMock, patch


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
@patch("worker.notion_client.config.NOTION_GRANOLA_DB_ID", "dd181874-b894-4120-a41f-e1e0a98577b8")
def test_create_transcript_page_supports_real_granola_schema(mock_require_notion, mock_client_cls):
    from worker.notion_client import create_transcript_page

    schema_response = MagicMock()
    schema_response.status_code = 200
    schema_response.json.return_value = {
        "id": "dd181874-b894-4120-a41f-e1e0a98577b8",
        "properties": {
            "Título": {"type": "title"},
            "Estado": {"type": "select"},
            "Fecha de transcripción": {"type": "date"},
            "Fecha que Rick pasó a Notion": {"type": "date"},
            "Fecha que el agente procesó": {"type": "date"},
            "Tags": {"type": "multi_select"},
        },
    }
    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.return_value = {
        "id": "page-1",
        "url": "https://www.notion.so/page-1",
    }

    mock_client = MagicMock()
    mock_client.get.return_value = schema_response
    mock_client.post.return_value = create_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = create_transcript_page(
        title="Reunión con Cliente X",
        content="Hola\n" * 10,
        source="granola",
        date="2026-03-09",
    )

    assert result == {"page_id": "page-1", "url": "https://www.notion.so/page-1"}
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["properties"]["Título"]["title"][0]["text"]["content"] == "Reunión con Cliente X"
    assert payload["properties"]["Estado"]["select"]["name"] == "Pendiente"
    assert payload["properties"]["Fecha de transcripción"]["date"]["start"] == "2026-03-09"
    assert payload["properties"]["Tags"]["multi_select"][0]["name"] == "granola"
    assert "Fecha que Rick pasó a Notion" in payload["properties"]
    assert "Fecha que el agente procesó" in payload["properties"]


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
@patch("worker.notion_client.config.NOTION_GRANOLA_DB_ID", "db-123")
def test_create_transcript_page_supports_legacy_schema(mock_require_notion, mock_client_cls):
    from worker.notion_client import create_transcript_page

    schema_response = MagicMock()
    schema_response.status_code = 200
    schema_response.json.return_value = {
        "id": "db-123",
        "properties": {
            "Name": {"type": "title"},
            "Source": {"type": "select"},
            "Date": {"type": "date"},
        },
    }
    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.return_value = {
        "id": "page-legacy",
        "url": "https://www.notion.so/page-legacy",
    }

    mock_client = MagicMock()
    mock_client.get.return_value = schema_response
    mock_client.post.return_value = create_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = create_transcript_page(
        title="Legacy meeting",
        content="Body",
        source="granola",
        date="2026-03-09",
    )

    assert result["page_id"] == "page-legacy"
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "Legacy meeting"
    assert payload["properties"]["Source"]["select"]["name"] == "granola"
    assert payload["properties"]["Date"]["date"]["start"] == "2026-03-09"


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
@patch("worker.notion_client.config.NOTION_GRANOLA_DB_ID", "dd181874-b894-4120-a41f-e1e0a98577b8")
def test_create_transcript_page_seeds_v2_raw_contract_fields(mock_require_notion, mock_client_cls):
    from worker.notion_client import create_transcript_page

    schema_response = MagicMock()
    schema_response.status_code = 200
    schema_response.json.return_value = {
        "id": "dd181874-b894-4120-a41f-e1e0a98577b8",
        "properties": {
            "Título": {"type": "title"},
            "Estado": {"type": "select"},
            "Estado agente": {"type": "select"},
            "Accion agente": {"type": "select"},
            "Dominio propuesto": {"type": "select"},
            "Tipo propuesto": {"type": "select"},
            "Destino canonico": {"type": "select"},
            "Resumen agente": {"type": "rich_text"},
            "Log del agente": {"type": "rich_text"},
            "URL artefacto": {"type": "url"},
            "Trazabilidad": {"type": "rich_text"},
            "Estado revision": {"type": "select"},
            "Reprocesar tras revision": {"type": "checkbox"},
        },
    }
    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.return_value = {
        "id": "page-v2",
        "url": "https://www.notion.so/page-v2",
    }

    mock_client = MagicMock()
    mock_client.get.return_value = schema_response
    mock_client.post.return_value = create_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = create_transcript_page(
        title="ReuniÃ³n V2",
        content="Body",
        source="granola",
        date="2026-03-09",
    )

    assert result == {"page_id": "page-v2", "url": "https://www.notion.so/page-v2"}
    payload = mock_client.post.call_args.kwargs["json"]
    props = payload["properties"]
    assert payload["properties"]["Título"]["title"][0]["text"]["content"] == "ReuniÃ³n V2"
    assert props["Estado agente"]["select"]["name"] == "Pendiente"
    assert props["Accion agente"]["select"]["name"] == "Sin accion"
    assert props["Dominio propuesto"]["select"]["name"] == "Mixto"
    assert props["Tipo propuesto"]["select"]["name"] == "Reunión"
    assert props["Destino canonico"]["select"]["name"] == "Ignorar"
    assert "Ingesta raw desde Granola" in props["Resumen agente"]["rich_text"][0]["text"]["content"]
    assert "flujo V2 directo pendiente" in props["Log del agente"]["rich_text"][0]["text"]["content"]
    assert props["URL artefacto"]["url"] is None
    assert "capitalization_mode=notion_ai_raw_direct_v2" in props["Trazabilidad"]["rich_text"][0]["text"]["content"]
    assert props["Estado revision"]["select"]["name"] == "No aplica"
    assert props["Reprocesar tras revision"]["checkbox"] is False
