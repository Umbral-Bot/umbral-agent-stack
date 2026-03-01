"""Tests for Linear integration."""
import pytest
from unittest.mock import patch


class TestLinearTasks:
    def test_create_issue_no_api_key(self):
        from worker.tasks.linear import handle_linear_create_issue
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", None):
            r = handle_linear_create_issue({"title": "Test"})
        assert r["ok"] is False
        assert "LINEAR_API_KEY" in r["error"]

    def test_create_issue_no_title(self):
        from worker.tasks.linear import handle_linear_create_issue
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"):
            r = handle_linear_create_issue({})
        assert r["ok"] is False
        assert "title" in r["error"].lower()

    def test_list_teams_no_api_key(self):
        from worker.tasks.linear import handle_linear_list_teams
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", None):
            r = handle_linear_list_teams({})
        assert r["ok"] is False
        assert r["teams"] == []

    def test_list_teams_returns_teams(self):
        from worker.tasks.linear import handle_linear_list_teams
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.list_teams", return_value=[{"id": "t1", "key": "UMB", "name": "Umbral"}]):
            r = handle_linear_list_teams({})
        assert r["ok"] is True
        assert len(r["teams"]) == 1
        assert r["teams"][0]["key"] == "UMB"
