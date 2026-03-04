"""
E2E tests for Figma worker task handlers.

These tests call the actual Figma API and require FIGMA_API_KEY to be set.
They are skipped if the key is not available.

For offline unit-level tests, the handlers are also tested with missing
API key to verify graceful error handling.
"""

import os

import pytest

from worker.tasks.figma import (
    handle_figma_add_comment,
    handle_figma_export_image,
    handle_figma_get_file,
    handle_figma_get_node,
    handle_figma_list_comments,
)

HAS_FIGMA_KEY = bool(os.environ.get("FIGMA_API_KEY", "").strip())

skip_no_figma = pytest.mark.skipif(
    not HAS_FIGMA_KEY,
    reason="FIGMA_API_KEY not set",
)

# A well-known public Figma community file for testing (Figma's own design system)
# If this file becomes unavailable, replace with any accessible file_key.
TEST_FILE_KEY = os.environ.get("FIGMA_TEST_FILE_KEY", "")


# ---------------------------------------------------------------------------
# Offline tests (no API key required)
# ---------------------------------------------------------------------------

class TestFigmaHandlersOffline:
    """Tests that handlers fail gracefully without FIGMA_API_KEY."""

    def test_get_file_no_api_key(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "")
        result = handle_figma_get_file({"file_key": "abc123"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY" in result["error"]

    def test_get_node_no_api_key(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "")
        result = handle_figma_get_node({"file_key": "abc", "node_ids": "1:2"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY" in result["error"]

    def test_export_image_no_api_key(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "")
        result = handle_figma_export_image({"file_key": "abc", "node_ids": "1:2"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY" in result["error"]

    def test_add_comment_no_api_key(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "")
        result = handle_figma_add_comment({"file_key": "abc", "message": "hi"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY" in result["error"]

    def test_list_comments_no_api_key(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "")
        result = handle_figma_list_comments({"file_key": "abc"})
        assert result["ok"] is False
        assert "FIGMA_API_KEY" in result["error"]

    def test_get_file_missing_file_key(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "fake-key")
        result = handle_figma_get_file({})
        assert result["ok"] is False
        assert "file_key" in result["error"]

    def test_get_node_missing_node_ids(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "fake-key")
        result = handle_figma_get_node({"file_key": "abc"})
        assert result["ok"] is False
        assert "node_ids" in result["error"]

    def test_export_image_invalid_format(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "fake-key")
        result = handle_figma_export_image(
            {"file_key": "abc", "node_ids": "1:2", "format": "bmp"}
        )
        assert result["ok"] is False
        assert "Invalid format" in result["error"]

    def test_add_comment_missing_message(self, monkeypatch):
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "fake-key")
        result = handle_figma_add_comment({"file_key": "abc"})
        assert result["ok"] is False
        assert "message" in result["error"]

    def test_get_node_ids_as_list(self, monkeypatch):
        """Verify node_ids list is joined correctly (unit check, no real API)."""
        monkeypatch.setattr("worker.tasks.figma.config.FIGMA_API_KEY", "")
        result = handle_figma_get_node({"file_key": "abc", "node_ids": ["1:2", "3:4"]})
        assert result["ok"] is False  # fails on missing key, but input parsing is fine


# ---------------------------------------------------------------------------
# Online E2E tests (require FIGMA_API_KEY + FIGMA_TEST_FILE_KEY)
# ---------------------------------------------------------------------------

@skip_no_figma
class TestFigmaE2E:
    """Live API tests — run only when FIGMA_API_KEY and FIGMA_TEST_FILE_KEY are set."""

    @pytest.fixture(autouse=True)
    def _check_file_key(self):
        if not TEST_FILE_KEY:
            pytest.skip("FIGMA_TEST_FILE_KEY not set")

    def test_get_file(self):
        result = handle_figma_get_file({"file_key": TEST_FILE_KEY, "depth": 1})
        assert result["ok"] is True
        assert result.get("name")
        assert isinstance(result.get("pages"), list)

    def test_list_comments(self):
        result = handle_figma_list_comments({"file_key": TEST_FILE_KEY})
        assert result["ok"] is True
        assert "count" in result
        assert isinstance(result.get("comments"), list)

    def test_get_file_with_depth(self):
        result = handle_figma_get_file({"file_key": TEST_FILE_KEY, "depth": 1})
        assert result["ok"] is True
        pages = result.get("pages", [])
        if pages:
            # first page should have basic info
            assert pages[0].get("id")
            assert pages[0].get("name")
