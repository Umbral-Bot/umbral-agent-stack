"""Unit tests for n8n task handlers."""

from unittest.mock import patch

import pytest

from worker.tasks.n8n import (
    handle_n8n_create_workflow,
    handle_n8n_get_workflow,
    handle_n8n_list_workflows,
    handle_n8n_post_webhook,
    handle_n8n_update_workflow,
)


def test_list_workflows_requires_config():
    with patch("worker.tasks.n8n.config") as mock_cfg:
        mock_cfg.N8N_URL = None
        mock_cfg.N8N_API_KEY = None
        result = handle_n8n_list_workflows({})
    assert result["ok"] is False
    assert "N8N_URL" in result["error"]


def test_list_workflows_success_filters_query():
    with patch("worker.tasks.n8n.config") as mock_cfg, \
         patch("worker.tasks.n8n.n8n_client.list_workflows") as mock_list:
        mock_cfg.N8N_URL = "https://n8n.local"
        mock_cfg.N8N_API_KEY = "key"
        mock_list.return_value = {
            "data": [
                {"id": "1", "name": "Editorial Capture"},
                {"id": "2", "name": "CRM Sync"},
            ]
        }
        result = handle_n8n_list_workflows({"query": "editorial"})
    assert result["ok"] is True
    assert result["count"] == 1
    assert result["workflows"][0]["id"] == "1"


def test_get_workflow_requires_id():
    with pytest.raises(ValueError, match="'workflow_id' is required"):
        handle_n8n_get_workflow({"workflow_id": ""})


def test_get_workflow_success():
    with patch("worker.tasks.n8n.config") as mock_cfg, \
         patch("worker.tasks.n8n.n8n_client.get_workflow") as mock_get:
        mock_cfg.N8N_URL = "https://n8n.local"
        mock_cfg.N8N_API_KEY = "key"
        mock_get.return_value = {"id": "wf-1", "name": "Editorial Flow"}
        result = handle_n8n_get_workflow({"workflow_id": "wf-1"})
    assert result["ok"] is True
    assert result["workflow"]["name"] == "Editorial Flow"


def test_create_workflow_requires_payload():
    with pytest.raises(ValueError, match="'workflow' must be a non-empty object"):
        handle_n8n_create_workflow({"workflow": None})


def test_create_workflow_success():
    with patch("worker.tasks.n8n.config") as mock_cfg, \
         patch("worker.tasks.n8n.n8n_client.create_workflow") as mock_create:
        mock_cfg.N8N_URL = "https://n8n.local"
        mock_cfg.N8N_API_KEY = "key"
        mock_create.return_value = {"id": "wf-1", "name": "Editorial Flow"}
        result = handle_n8n_create_workflow({"workflow": {"name": "Editorial Flow", "nodes": [], "connections": {}}})
    assert result["ok"] is True
    assert result["workflow"]["id"] == "wf-1"


def test_update_workflow_requires_payload():
    with pytest.raises(ValueError, match="'workflow' must be a non-empty object"):
        handle_n8n_update_workflow({"workflow_id": "wf-1", "workflow": None})


def test_update_workflow_success():
    with patch("worker.tasks.n8n.config") as mock_cfg, \
         patch("worker.tasks.n8n.n8n_client.update_workflow") as mock_update:
        mock_cfg.N8N_URL = "https://n8n.local"
        mock_cfg.N8N_API_KEY = "key"
        mock_update.return_value = {"id": "wf-1", "name": "Editorial Flow v2"}
        result = handle_n8n_update_workflow(
            {"workflow_id": "wf-1", "workflow": {"name": "Editorial Flow v2", "nodes": [], "connections": {}}}
        )
    assert result["ok"] is True
    assert result["workflow"]["name"] == "Editorial Flow v2"


def test_post_webhook_requires_path_or_url():
    with pytest.raises(ValueError, match="Either 'webhook_path' or 'webhook_url' is required"):
        handle_n8n_post_webhook({"payload": {}})


def test_post_webhook_success():
    with patch("worker.tasks.n8n.config") as mock_cfg, \
         patch("worker.tasks.n8n.n8n_client.post_webhook") as mock_post:
        mock_cfg.N8N_URL = "https://n8n.local"
        mock_cfg.N8N_API_KEY = "key"
        mock_post.return_value = {"ok": True, "status_code": 200, "response": {"received": True}}
        result = handle_n8n_post_webhook({"webhook_path": "/webhook/editorial", "payload": {"x": 1}})
    assert result["ok"] is True
    assert result["status_code"] == 200


def test_handlers_registered():
    from worker.tasks import TASK_HANDLERS

    assert "n8n.list_workflows" in TASK_HANDLERS
    assert "n8n.get_workflow" in TASK_HANDLERS
    assert "n8n.create_workflow" in TASK_HANDLERS
    assert "n8n.update_workflow" in TASK_HANDLERS
    assert "n8n.post_webhook" in TASK_HANDLERS
