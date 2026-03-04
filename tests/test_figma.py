"""Unit tests for Figma task handlers (worker/tasks/figma.py)."""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests as requests_lib

os.environ.setdefault("WORKER_TOKEN", "test")

from worker.tasks.figma import (
    handle_figma_get_file,
    handle_figma_get_node,
    handle_figma_export_image,
    handle_figma_add_comment,
    handle_figma_list_comments,
)

MOCK_KEY = "figd_test123"


def _http_error(status_code, text="error body"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    err = requests_lib.HTTPError(response=resp)
    err.response = resp
    return err


@pytest.fixture(autouse=True)
def _figma_key():
    """Patch config.FIGMA_API_KEY for all tests; individual tests override if needed."""
    with patch("worker.tasks.figma.config") as cfg:
        cfg.FIGMA_API_KEY = MOCK_KEY
        yield cfg


# ======================================================================
# figma.get_file
# ======================================================================
class TestGetFile:
    @patch("worker.tasks.figma.requests.get")
    def test_ok(self, mock_get):
        mock_get.return_value.json.return_value = {
            "name": "My Design",
            "lastModified": "2026-03-01T10:00:00Z",
            "version": "123",
            "thumbnailUrl": "https://example.com/thumb.png",
            "document": {
                "children": [
                    {"id": "0:1", "name": "Page 1", "type": "CANVAS", "children": [{"id": "1:1"}]},
                    {"id": "0:2", "name": "Page 2", "type": "CANVAS", "children": []},
                ]
            },
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_get_file({"file_key": "abc123"})

        assert result["ok"] is True
        assert result["name"] == "My Design"
        assert result["last_modified"] == "2026-03-01T10:00:00Z"
        assert len(result["pages"]) == 2
        assert result["pages"][0]["name"] == "Page 1"
        assert result["pages"][0]["children_count"] == 1
        mock_get.assert_called_once()

    def test_missing_api_key(self, _figma_key):
        _figma_key.FIGMA_API_KEY = None
        result = handle_figma_get_file({"file_key": "abc123"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY not configured" in result["error"]

    def test_missing_file_key(self):
        result = handle_figma_get_file({})
        assert result["ok"] is False
        assert "'file_key' is required" in result["error"]

    def test_empty_file_key(self):
        result = handle_figma_get_file({"file_key": "  "})
        assert result["ok"] is False
        assert "'file_key' is required" in result["error"]

    @patch("worker.tasks.figma.requests.get")
    def test_http_403(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = _http_error(403, "Forbidden")
        result = handle_figma_get_file({"file_key": "abc123"})
        assert result["ok"] is False
        assert "403" in result["error"]

    @patch("worker.tasks.figma.requests.get")
    def test_http_404(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = _http_error(404, "Not found")
        result = handle_figma_get_file({"file_key": "nonexistent"})
        assert result["ok"] is False
        assert "404" in result["error"]


# ======================================================================
# figma.get_node
# ======================================================================
class TestGetNode:
    @patch("worker.tasks.figma.requests.get")
    def test_ok_single_node(self, mock_get):
        mock_get.return_value.json.return_value = {
            "nodes": {
                "1:2": {
                    "document": {
                        "id": "1:2",
                        "name": "Button",
                        "type": "COMPONENT",
                        "children": [{"id": "1:3"}, {"id": "1:4"}],
                    }
                }
            }
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_get_node({"file_key": "abc123", "node_ids": "1:2"})
        assert result["ok"] is True
        assert "1:2" in result["nodes"]
        assert result["nodes"]["1:2"]["name"] == "Button"
        assert result["nodes"]["1:2"]["children_count"] == 2

    @patch("worker.tasks.figma.requests.get")
    def test_ok_multiple_nodes(self, mock_get):
        mock_get.return_value.json.return_value = {
            "nodes": {
                "1:2": {"document": {"id": "1:2", "name": "A", "type": "FRAME", "children": []}},
                "3:4": {"document": {"id": "3:4", "name": "B", "type": "TEXT", "children": []}},
            }
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_get_node({"file_key": "abc123", "node_ids": ["1:2", "3:4"]})
        assert result["ok"] is True
        assert len(result["nodes"]) == 2
        assert result["nodes"]["3:4"]["type"] == "TEXT"

    def test_missing_node_ids(self):
        result = handle_figma_get_node({"file_key": "abc123"})
        assert result["ok"] is False
        assert "'node_ids' is required" in result["error"]

    def test_missing_api_key(self, _figma_key):
        _figma_key.FIGMA_API_KEY = None
        result = handle_figma_get_node({"file_key": "abc123", "node_ids": "1:2"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY not configured" in result["error"]


# ======================================================================
# figma.export_image
# ======================================================================
class TestExportImage:
    @patch("worker.tasks.figma.requests.get")
    def test_ok_png(self, mock_get):
        mock_get.return_value.json.return_value = {
            "images": {"1:2": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/img/abc"}
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_export_image({
            "file_key": "abc123",
            "node_ids": "1:2",
            "format": "png",
        })
        assert result["ok"] is True
        assert result["format"] == "png"
        assert "1:2" in result["images"]
        assert result["images"]["1:2"].startswith("https://")

    def test_invalid_format(self):
        result = handle_figma_export_image({
            "file_key": "abc123",
            "node_ids": "1:2",
            "format": "gif",
        })
        assert result["ok"] is False
        assert "Invalid format" in result["error"]
        assert "gif" in result["error"]

    def test_missing_node_ids(self):
        result = handle_figma_export_image({"file_key": "abc123"})
        assert result["ok"] is False
        assert "'node_ids' is required" in result["error"]

    @patch("worker.tasks.figma.requests.get")
    def test_ok_svg_with_scale(self, mock_get):
        mock_get.return_value.json.return_value = {
            "images": {"5:6": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/img/svg123"}
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_export_image({
            "file_key": "abc123",
            "node_ids": ["5:6"],
            "format": "svg",
            "scale": 2,
        })
        assert result["ok"] is True
        assert result["format"] == "svg"
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["scale"] == 2


# ======================================================================
# figma.add_comment
# ======================================================================
class TestAddComment:
    @patch("worker.tasks.figma.requests.post")
    def test_ok(self, mock_post):
        mock_post.return_value.json.return_value = {
            "id": "comment_001",
            "message": "Looks good!",
            "created_at": "2026-03-01T12:00:00Z",
            "user": {"handle": "david"},
        }
        mock_post.return_value.raise_for_status = MagicMock()

        result = handle_figma_add_comment({
            "file_key": "abc123",
            "message": "Looks good!",
        })
        assert result["ok"] is True
        assert result["id"] == "comment_001"
        assert result["message"] == "Looks good!"
        assert result["user"] == "david"

    def test_missing_message(self):
        result = handle_figma_add_comment({"file_key": "abc123"})
        assert result["ok"] is False
        assert "'message' is required" in result["error"]

    @patch("worker.tasks.figma.requests.post")
    def test_with_node_id_attaches_client_meta(self, mock_post):
        mock_post.return_value.json.return_value = {
            "id": "comment_002",
            "message": "Check this",
            "created_at": "2026-03-01T13:00:00Z",
            "user": {"handle": "rick"},
        }
        mock_post.return_value.raise_for_status = MagicMock()

        result = handle_figma_add_comment({
            "file_key": "abc123",
            "message": "Check this",
            "node_id": "1:2",
        })
        assert result["ok"] is True
        call_kwargs = mock_post.call_args
        body = call_kwargs[1]["json"]
        assert "client_meta" in body
        assert body["client_meta"]["node_id"] == "1:2"

    def test_missing_api_key(self, _figma_key):
        _figma_key.FIGMA_API_KEY = None
        result = handle_figma_add_comment({
            "file_key": "abc123",
            "message": "Hello",
        })
        assert result["ok"] is False
        assert "FIGMA_API_KEY not configured" in result["error"]


# ======================================================================
# figma.list_comments
# ======================================================================
class TestListComments:
    @patch("worker.tasks.figma.requests.get")
    def test_ok(self, mock_get):
        mock_get.return_value.json.return_value = {
            "comments": [
                {
                    "id": "c1",
                    "message": "First comment",
                    "created_at": "2026-03-01T10:00:00Z",
                    "user": {"handle": "alice"},
                    "resolved_at": None,
                },
                {
                    "id": "c2",
                    "message": "Second comment",
                    "created_at": "2026-03-01T11:00:00Z",
                    "user": {"handle": "bob"},
                    "resolved_at": "2026-03-02T09:00:00Z",
                },
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_list_comments({"file_key": "abc123"})
        assert result["ok"] is True
        assert result["count"] == 2
        assert len(result["comments"]) == 2
        assert result["comments"][0]["user"] == "alice"
        assert result["comments"][1]["resolved_at"] is not None

    def test_missing_file_key(self):
        result = handle_figma_list_comments({})
        assert result["ok"] is False
        assert "'file_key' is required" in result["error"]

    def test_missing_api_key(self, _figma_key):
        _figma_key.FIGMA_API_KEY = None
        result = handle_figma_list_comments({"file_key": "abc123"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY not configured" in result["error"]
