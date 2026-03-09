"""
Tasks: n8n workflow management and webhook triggering.

- n8n.list_workflows: list workflows from the configured n8n instance
- n8n.get_workflow: fetch a workflow definition by ID
- n8n.create_workflow: create a workflow from raw JSON
- n8n.update_workflow: update a workflow from raw JSON
- n8n.post_webhook: invoke an n8n webhook on the configured instance
"""

from __future__ import annotations

from typing import Any, Dict

from .. import config, n8n_client


def _require_n8n_url() -> str | None:
    url = (config.N8N_URL or "").strip()
    return url or None


def _require_n8n_api_key() -> str | None:
    key = (config.N8N_API_KEY or "").strip()
    return key or None


def handle_n8n_list_workflows(input_data: Dict[str, Any]) -> Dict[str, Any]:
    if not _require_n8n_url():
        return {"ok": False, "error": "N8N_URL not configured"}
    if not _require_n8n_api_key():
        return {"ok": False, "error": "N8N_API_KEY not configured"}

    limit = int(input_data.get("limit", 100))
    if limit < 1 or limit > 250:
        raise ValueError("'limit' must be between 1 and 250")

    query = str(input_data.get("query") or "").strip().lower()
    active = input_data.get("active")
    if active is not None and not isinstance(active, bool):
        raise ValueError("'active' must be a boolean when provided")

    result = n8n_client.list_workflows(
        active=active,
        limit=limit,
        timeout=int(input_data.get("timeout", 30)),
    )
    workflows = result.get("data", result) if isinstance(result, dict) else result
    if not isinstance(workflows, list):
        workflows = [workflows]

    if query:
        workflows = [
            wf for wf in workflows
            if query in str(wf.get("name", "")).lower()
        ]

    return {
        "ok": True,
        "count": len(workflows),
        "workflows": workflows,
    }


def handle_n8n_get_workflow(input_data: Dict[str, Any]) -> Dict[str, Any]:
    workflow_id = str(input_data.get("workflow_id") or "").strip()
    if not workflow_id:
        raise ValueError("'workflow_id' is required")

    if not _require_n8n_url():
        return {"ok": False, "error": "N8N_URL not configured"}
    if not _require_n8n_api_key():
        return {"ok": False, "error": "N8N_API_KEY not configured"}

    result = n8n_client.get_workflow(
        workflow_id,
        timeout=int(input_data.get("timeout", 30)),
    )
    return {"ok": True, "workflow": result}


def handle_n8n_create_workflow(input_data: Dict[str, Any]) -> Dict[str, Any]:
    workflow = input_data.get("workflow")
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("'workflow' must be a non-empty object")

    if not _require_n8n_url():
        return {"ok": False, "error": "N8N_URL not configured"}
    if not _require_n8n_api_key():
        return {"ok": False, "error": "N8N_API_KEY not configured"}

    result = n8n_client.create_workflow(
        workflow,
        timeout=int(input_data.get("timeout", 30)),
    )
    return {"ok": True, "workflow": result}


def handle_n8n_update_workflow(input_data: Dict[str, Any]) -> Dict[str, Any]:
    workflow_id = str(input_data.get("workflow_id") or "").strip()
    if not workflow_id:
        raise ValueError("'workflow_id' is required")

    workflow = input_data.get("workflow")
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("'workflow' must be a non-empty object")

    if not _require_n8n_url():
        return {"ok": False, "error": "N8N_URL not configured"}
    if not _require_n8n_api_key():
        return {"ok": False, "error": "N8N_API_KEY not configured"}

    result = n8n_client.update_workflow(
        workflow_id,
        workflow,
        timeout=int(input_data.get("timeout", 30)),
    )
    return {"ok": True, "workflow": result}


def handle_n8n_post_webhook(input_data: Dict[str, Any]) -> Dict[str, Any]:
    webhook_path = str(input_data.get("webhook_path") or "").strip()
    webhook_url = str(input_data.get("webhook_url") or "").strip()
    if not webhook_path and not webhook_url:
        raise ValueError("Either 'webhook_path' or 'webhook_url' is required")

    payload = input_data.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("'payload' must be an object")

    timeout = int(input_data.get("timeout", 30))
    if timeout < 1 or timeout > 120:
        raise ValueError("'timeout' must be between 1 and 120")

    if not _require_n8n_url():
        return {"ok": False, "error": "N8N_URL not configured"}

    return n8n_client.post_webhook(
        webhook_path=webhook_path or None,
        webhook_url=webhook_url or None,
        payload=payload,
        timeout=timeout,
    )
