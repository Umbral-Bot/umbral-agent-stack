from unittest.mock import MagicMock, patch


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
@patch(
    "worker.notion_client.config.NOTION_GRANOLA_DB_ID",
    "dd181874-b894-4120-a41f-e1e0a98577b8",
)
def test_create_transcript_page_supports_real_granola_schema(
    mock_require_notion, mock_client_cls
):
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
            "Trazabilidad": {"type": "rich_text"},
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
        traceability_text="granola_document_id=doc-123\ningest_path=granola.process_transcript",
    )

    assert result == {"page_id": "page-1", "url": "https://www.notion.so/page-1"}
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["properties"]["Título"]["title"][0]["text"]["content"] == "Reunión con Cliente X"
    assert payload["properties"]["Estado"]["select"]["name"] == "Pendiente"
    assert payload["properties"]["Fecha de transcripción"]["date"]["start"] == "2026-03-09"
    assert payload["properties"]["Tags"]["multi_select"][0]["name"] == "granola"
    assert "Fecha que Rick pasó a Notion" in payload["properties"]
    assert "Fecha que el agente procesó" in payload["properties"]
    assert (
        payload["properties"]["Trazabilidad"]["rich_text"][0]["text"]["content"]
        == "granola_document_id=doc-123\ningest_path=granola.process_transcript"
    )


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
@patch("worker.notion_client.config.NOTION_GRANOLA_DB_ID", "db-123")
def test_create_transcript_page_supports_legacy_schema(
    mock_require_notion, mock_client_cls
):
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
