"""
Tests for linear.create_project_update handler and linear_client.create_project_update.
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Handler tests
# ---------------------------------------------------------------------------

def test_create_project_update_no_api_key():
    from worker.tasks.linear import handle_linear_create_project_update

    with patch("worker.tasks.linear._linear_api_key", return_value=None):
        result = handle_linear_create_project_update({"body": "Update text", "project_name": "Test"})

    assert result["ok"] is False
    assert "LINEAR_API_KEY" in result["error"]


def test_create_project_update_no_body():
    from worker.tasks.linear import handle_linear_create_project_update

    with patch("worker.tasks.linear._linear_api_key", return_value="fake-key"):
        result = handle_linear_create_project_update({"project_name": "Test"})

    assert result["ok"] is False
    assert "body" in result["error"].lower()


def test_create_project_update_no_project():
    from worker.tasks.linear import handle_linear_create_project_update

    with patch("worker.tasks.linear._linear_api_key", return_value="fake-key"), \
         patch("worker.tasks.linear._resolve_project", return_value=None):

        result = handle_linear_create_project_update({"body": "Update"})

    assert result["ok"] is False
    assert "project" in result["error"].lower()


def test_create_project_update_success():
    from worker.tasks.linear import handle_linear_create_project_update

    fake_project = {"id": "proj-uuid", "name": "My Project", "url": "https://linear.app/umbral/project/test"}
    fake_update = {
        "success": True,
        "projectUpdate": {"id": "upd-uuid", "url": "https://linear.app/...", "createdAt": "2026-03-09T00:00:00Z"},
    }

    with patch("worker.tasks.linear._linear_api_key", return_value="fake-key"), \
         patch("worker.tasks.linear._resolve_project", return_value=fake_project), \
         patch("worker.tasks.linear.linear_client.create_project_update", return_value=fake_update):

        result = handle_linear_create_project_update({
            "body": "Sprint R21 completado — arquitectura web v1 lista.",
            "project_name": "My Project",
            "health": "onTrack",
        })

    assert result["ok"] is True
    assert result["project"]["id"] == "proj-uuid"
    assert "success" in result


# ---------------------------------------------------------------------------
# linear_client unit test
# ---------------------------------------------------------------------------

def test_linear_client_create_project_update_calls_gql():
    from worker import linear_client

    with patch.object(linear_client, "_gql") as mock_gql:
        mock_gql.return_value = {
            "projectUpdateCreate": {
                "success": True,
                "projectUpdate": {"id": "upd-1", "url": "https://...", "createdAt": "2026-03-09"},
            }
        }
        result = linear_client.create_project_update(
            api_key="fake", project_id="proj-1", body="Body text", health="atRisk"
        )

    mock_gql.assert_called_once()
    call_vars = mock_gql.call_args[0][2]
    assert call_vars["input"]["projectId"] == "proj-1"
    assert call_vars["input"]["body"] == "Body text"
    assert call_vars["input"]["health"] == "atRisk"
    assert result["success"] is True
