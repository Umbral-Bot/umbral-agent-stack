import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from worker import notion_client
from worker.tasks.notion import handle_notion_read_database


@patch("worker.tasks.notion.notion_client.read_database")
def test_handle_notion_read_database_success(mock_read_database):
    mock_read_database.return_value = {
        "database_id": "2b45f443-fb5c-8154-8f22-de9978f2a039",
        "title": "Fuentes",
        "schema": {"Name": "title", "URL": "url"},
        "items": [{"title": "Gartner", "properties": {"URL": "https://www.gartner.com/"}}],
    }

    result = handle_notion_read_database(
        {
            "database_id_or_url": "https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
            "max_items": 25,
        }
    )

    assert result["title"] == "Fuentes"
    mock_read_database.assert_called_once_with(
        database_id_or_url="https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
        max_items=25,
        filter=None,
    )


def test_handle_notion_read_database_requires_database():
    with pytest.raises(ValueError, match="'database_id_or_url' is required"):
        handle_notion_read_database({})


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_read_database_returns_schema_and_items(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import read_database

    db_response = MagicMock()
    db_response.status_code = 200
    db_response.json.return_value = {
        "id": "2b45f443-fb5c-8154-8f22-de9978f2a039",
        "url": "https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
        "title": [{"plain_text": "Fuentes"}],
        "properties": {
            "Name": {"type": "title"},
            "URL": {"type": "url"},
            "Prioridad": {"type": "select"},
        },
    }
    query_response = MagicMock()
    query_response.status_code = 200
    query_response.json.return_value = {
        "results": [
            {
                "id": "page-1",
                "url": "https://www.notion.so/item-1",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Gartner"}]},
                    "URL": {"type": "url", "url": "https://www.gartner.com/"},
                    "Prioridad": {"type": "select", "select": {"name": "Alta"}},
                },
            }
        ],
        "has_more": False,
    }

    mock_client = MagicMock()
    mock_client.request.side_effect = [db_response, query_response]
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = read_database(
        "https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
        max_items=20,
    )

    assert result["title"] == "Fuentes"
    assert result["database_id"] == "2b45f443-fb5c-8154-8f22-de9978f2a039"
    assert result["schema"] == {"Name": "title", "URL": "url", "Prioridad": "select"}
    assert result["count"] == 1
    assert result["items"][0]["title"] == "Gartner"
    assert result["items"][0]["properties"]["URL"] == "https://www.gartner.com/"
    assert result["items"][0]["properties"]["Prioridad"] == "Alta"


DATABASE_ID = "2b45f443-fb5c-8154-8f22-de9978f2a039"
TRANSPORT_ERRORS = [
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.WriteError,
]


@pytest.fixture
def mock_notion_http(monkeypatch):
    monkeypatch.setattr(notion_client.config, "require_notion_core", lambda: None)
    monkeypatch.setattr(notion_client, "_headers", lambda: {})
    sleep = MagicMock()
    monkeypatch.setattr(notion_client.time, "sleep", sleep)

    def install(handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(notion_client.httpx, "Client", lambda **kwargs: client)
        return client

    return install, sleep


def _read_database_response(request):
    if request.method == "GET":
        return httpx.Response(200, json={
            "id": DATABASE_ID,
            "title": [{"plain_text": "Fuentes"}],
            "properties": {"Name": {"type": "title"}},
        })
    return httpx.Response(200, json={"results": [], "has_more": False})


@pytest.mark.parametrize("method", ["GET", "POST"], ids=["metadata", "query"])
@pytest.mark.parametrize("error_type", TRANSPORT_ERRORS)
def test_read_database_recovers_transport_error(mock_notion_http, method, error_type):
    install, sleep = mock_notion_http
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == method and sum(r.method == method for r in requests) == 1:
            raise error_type("simulated disconnect", request=request)
        return _read_database_response(request)

    install(handle)
    filter_body = {"property": "Name", "title": {"contains": "Gartner"}}
    result = notion_client.read_database(DATABASE_ID, max_items=20, filter=filter_body)

    assert result == {
        "database_id": DATABASE_ID,
        "url": "",
        "title": "Fuentes",
        "schema": {"Name": "title"},
        "items": [],
        "count": 0,
        "has_more": False,
        "max_items": 20,
    }
    assert [r.method for r in requests] == (
        ["GET", "GET", "POST"] if method == "GET" else ["GET", "POST", "POST"]
    )
    for request in requests:
        suffix = "/query" if request.method == "POST" else ""
        assert request.url.path == f"/v1/databases/{DATABASE_ID}{suffix}"
        if request.method == "POST":
            assert json.loads(request.content) == {"page_size": 20, "filter": filter_body}
    sleep.assert_called_once_with(1.0)


@pytest.mark.parametrize("method", ["GET", "POST"], ids=["metadata", "query"])
@pytest.mark.parametrize("error_type", TRANSPORT_ERRORS)
def test_read_database_transport_retry_is_bounded(mock_notion_http, method, error_type):
    install, sleep = mock_notion_http
    requests = []
    error = error_type("persistent simulated disconnect")

    def handle(request):
        requests.append(request.method)
        if request.method == method:
            raise error
        return _read_database_response(request)

    install(handle)
    with pytest.raises(error_type) as exc_info:
        notion_client.read_database(DATABASE_ID)

    assert exc_info.value is error
    assert requests == (["GET"] * 5 if method == "GET" else ["GET"] + ["POST"] * 5)
    assert [call.args[0] for call in sleep.call_args_list] == [1.0, 2.0, 4.0, 8.0]


@pytest.mark.parametrize("method", ["GET", "POST"], ids=["metadata", "query"])
@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
def test_read_database_does_not_retry_client_error(mock_notion_http, method, status_code):
    install, sleep = mock_notion_http
    requests = []

    def handle(request):
        requests.append(request.method)
        if request.method == method:
            return httpx.Response(status_code, json={"message": "simulated API error"})
        return _read_database_response(request)

    install(handle)
    with pytest.raises(RuntimeError, match=rf"Notion API error \({status_code}\)"):
        notion_client.read_database(DATABASE_ID)

    assert requests == (["GET"] if method == "GET" else ["GET", "POST"])
    sleep.assert_not_called()


@pytest.mark.parametrize("method", ["GET", "POST"], ids=["metadata", "query"])
def test_read_database_preserves_retry_after(mock_notion_http, method):
    install, sleep = mock_notion_http
    requests = []

    def handle(request):
        requests.append(request.method)
        if request.method == method and requests.count(method) == 1:
            return httpx.Response(429, headers={"Retry-After": "3.5"})
        return _read_database_response(request)

    install(handle)
    assert notion_client.read_database(DATABASE_ID)["title"] == "Fuentes"
    assert requests == (
        ["GET", "GET", "POST"] if method == "GET" else ["GET", "POST", "POST"]
    )
    sleep.assert_called_once_with(3.5)


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("error_type", TRANSPORT_ERRORS)
def test_request_does_not_retry_transport_by_default(mock_notion_http, method, error_type):
    install, sleep = mock_notion_http
    handler = MagicMock(side_effect=error_type("simulated disconnect"))

    with install(handler) as client:
        with pytest.raises(error_type):
            notion_client._request_with_backoff(
                client, method, "https://api.notion.com/v1/pages/test-page",
                context="default transport behavior", headers={},
            )

    handler.assert_called_once()
    sleep.assert_not_called()
