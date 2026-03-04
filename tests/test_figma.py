"""Unit tests for worker/tasks/figma.py handlers."""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

os.environ.setdefault("WORKER_TOKEN", "test")

from worker.tasks.figma import (
    handle_figma_get_file,
    handle_figma_get_node,
    handle_figma_export_image,
    handle_figma_add_comment,
    handle_figma_list_comments,
)


def _mock_config(api_key="figd_test123"):
    cfg = MagicMock()
    cfg.FIGMA_API_KEY = api_key
    return cfg


def _http_error(status_code, body="error body"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = body
    return requests.HTTPError(response=resp)


# ---------------------------------------------------------------------------
# figma.get_file
# ---------------------------------------------------------------------------
class TestFigmaGetFile:
    @patch("worker.tasks.figma.requests.get")
    @patch("worker.tasks.figma.config")
    def test_ok(self, mock_config, mock_get):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_get.return_value.json.return_value = {
            "name": "Design System",
            "lastModified": "2026-03-01T10:00:00Z",
            "version": "v42",
            "thumbnailUrl": "https://example.com/thumb.png",
            "document": {
                "children": [
                    {"id": "0:1", "name": "Page 1", "type": "CANVAS", "children": [{}, {}]},
                    {"id": "0:2", "name": "Page 2", "type": "CANVAS", "children": []},
                ]
            },
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_get_file({"file_key": "abc123"})

        assert result["ok"] is True
        assert result["name"] == "Design System"
        assert len(result["pages"]) == 2
        assert result["pages"][0]["children_count"] == 2
        assert result["pages"][1]["children_count"] == 0
        assert result["version"] == "v42"

    @patch("worker.tasks.figma.config")
    def test_no_api_key(self, mock_config):
        mock_config.FIGMA_API_KEY = None

        result = handle_figma_get_file({"file_key": "abc123"})

        assert result["ok"] is False
        assert "FIGMA_API_KEY not configured" in result["error"]

    @patch("worker.tasks.figma.config")
    def test_no_file_key(self, mock_config):
        mock_config.FIGMA_API_KEY = "figd_test123"

        result = handle_figma_get_file({})

        assert result["ok"] is False
        assert "file_key" in result["error"]

    @patch("worker.tasks.figma.config")
    def test_empty_file_key(self, mock_config):
        mock_config.FIGMA_API_KEY = "figd_test123"

        result = handle_figma_get_file({"file_key": "  "})

        assert result["ok"] is False
        assert "file_key" in result["error"]

    @patch("worker.tasks.figma.requests.get")
    @patch("worker.tasks.figma.config")
    def test_http_403(self, mock_config, mock_get):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_get.return_value.raise_for_status.side_effect = _http_error(403, "Forbidden")

        result = handle_figma_get_file({"file_key": "abc123"})

        assert result["ok"] is False
        assert "403" in result["error"]

    @patch("worker.tasks.figma.requests.get")
    @patch("worker.tasks.figma.config")
    def test_http_404(self, mock_config, mock_get):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_get.return_value.raise_for_status.side_effect = _http_error(404, "Not Found")

        result = handle_figma_get_file({"file_key": "nonexistent"})

        assert result["ok"] is False
        assert "404" in result["error"]


# ---------------------------------------------------------------------------
# figma.get_node
# ---------------------------------------------------------------------------
class TestFigmaGetNode:
    @patch("worker.tasks.figma.requests.get")
    @patch("worker.tasks.figma.config")
    def test_ok_single_node(self, mock_config, mock_get):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_get.return_value.json.return_value = {
            "nodes": {
                "1:2": {
                    "document": {
                        "id": "1:2",
                        "name": "Button",
                        "type": "COMPONENT",
                        "children": [{"id": "1:3"}],
                    }
                }
            }
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = handle_figma_get_node({"file_key": "abc123", "node_ids": "1:2"})

        assert result["ok"] is True
        assert "1:2" in result["nodes"]
        assert result["nodes"]["1:2"]["name"] == "Button"
        assert result["nodes"]["1:2"]["children_count"] == 1

    @patch("worker.tasks.figma.requests.get")
    @patch("worker.tasks.figma.config")
    def test_ok_multiple_nodes(self, mock_config, mock_get):
        mock_config.FIGMA_API_KEY = "figd_test123"
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

    @patch("worker.tasks.figma.config")
    def test_no_node_ids(self, mock_config):
        mock_config.FIGMA_API_KEY = "figd_test123"

        result = handle_figma_get_node({"file_key": "abc123"})

        assert result["ok"] is False
        assert "node_ids" in result["error"]


# ---------------------------------------------------------------------------
# figma.export_image
# ---------------------------------------------------------------------------
class TestFigmaExportImage:
    @patch("worker.tasks.figma.requests.get")
    @patch("worker.tasks.figma.config")
    def test_ok_png(self, mock_config, mock_get):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_get.return_value.json.return_value = {
            "images": {"1:2": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/img123.png"}
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

    @patch("worker.tasks.figma.config")
    def test_invalid_format(self, mock_config):
        mock_config.FIGMA_API_KEY = "figd_test123"

        result = handle_figma_export_image({
            "file_key": "abc123",
            "node_ids": "1:2",
            "format": "gif",
        })

        assert result["ok"] is False
        assert "Invalid format" in result["error"]

    @patch("worker.tasks.figma.config")
    def test_no_node_ids(self, mock_config):
        mock_config.FIGMA_API_KEY = "figd_test123"

        result = handle_figma_export_image({"file_key": "abc123"})

        assert result["ok"] is False
        assert "node_ids" in result["error"]


# ---------------------------------------------------------------------------
# figma.add_comment
# ---------------------------------------------------------------------------
class TestFigmaAddComment:
    @patch("worker.tasks.figma.requests.post")
    @patch("worker.tasks.figma.config")
    def test_ok(self, mock_config, mock_post):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_post.return_value.json.return_value = {
            "id": "comment_42",
            "message": "Looks good!",
            "created_at": "2026-03-01T12:00:00Z",
            "user": {"handle": "rick"},
        }
        mock_post.return_value.raise_for_status = MagicMock()

        result = handle_figma_add_comment({
            "file_key": "abc123",
            "message": "Looks good!",
        })

        assert result["ok"] is True
        assert result["id"] == "comment_42"
        assert result["user"] == "rick"

    @patch("worker.tasks.figma.config")
    def test_no_message(self, mock_config):
        mock_config.FIGMA_API_KEY = "figd_test123"

        result = handle_figma_add_comment({"file_key": "abc123"})

        assert result["ok"] is False
        assert "message" in result["error"]

    @patch("worker.tasks.figma.requests.post")
    @patch("worker.tasks.figma.config")
    def test_with_node_id_attaches_client_meta(self, mock_config, mock_post):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_post.return_value.json.return_value = {
            "id": "comment_99",
            "message": "Review this",
            "created_at": "2026-03-01T13:00:00Z",
            "user": {"handle": "david"},
        }
        mock_post.return_value.raise_for_status = MagicMock()

        handle_figma_add_comment({
            "file_key": "abc123",
            "message": "Review this",
            "node_id": "5:10",
        })

        call_kwargs = mock_post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert "client_meta" in body
        assert body["client_meta"]["node_id"] == "5:10"


# ---------------------------------------------------------------------------
# figma.list_comments
# ---------------------------------------------------------------------------
class TestFigmaListComments:
    @patch("worker.tasks.figma.requests.get")
    @patch("worker.tasks.figma.config")
    def test_ok(self, mock_config, mock_get):
        mock_config.FIGMA_API_KEY = "figd_test123"
        mock_get.return_value.json.return_value = {
            "comments": [
                {
                    "id": "c1",
                    "message": "First",
                    "created_at": "2026-03-01T10:00:00Z",
                    "user": {"handle": "alice"},
                    "resolved_at": None,
                },
                {
                    "id": "c2",
                    "message": "Second",
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
        assert result["comments"][0]["user"] == "alice"
        assert result["comments"][1]["resolved_at"] is not None

    @patch("worker.tasks.figma.config")
    def test_no_file_key(self, mock_config):
        mock_config.FIGMA_API_KEY = "figd_test123"

        result = handle_figma_list_comments({})

        assert result["ok"] is False
        assert "file_key" in result["error"]
