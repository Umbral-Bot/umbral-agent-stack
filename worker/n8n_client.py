"""
Minimal n8n REST client helpers for workflow discovery and webhook triggering.

Official docs:
- API auth: https://docs.n8n.io/api/authentication/
- Workflow management: https://docs.n8n.io/api/
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

from . import config


def _base_url() -> str:
    base = (config.N8N_URL or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("N8N_URL not configured")
    return base


def _api_key() -> str:
    key = (config.N8N_API_KEY or "").strip()
    if not key:
        raise RuntimeError("N8N_API_KEY not configured")
    return key


def _safe_http_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:500]
    except Exception:
        return ""


def _request(
    method: str,
    path: str,
    *,
    body: Dict[str, Any] | None = None,
    query: Dict[str, Any] | None = None,
    timeout: int = 30,
    auth: bool = True,
) -> Any:
    base = _base_url()
    url = f"{base}{path}"
    if query:
        clean_query = {k: v for k, v in query.items() if v is not None}
        if clean_query:
            url = f"{url}?{urllib.parse.urlencode(clean_query)}"

    headers = {
        "Accept": "application/json",
    }
    if auth:
        headers["X-N8N-API-KEY"] = _api_key()
    if body is not None:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method.upper(),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"n8n API error {exc.code}: {body_str}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"n8n connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"n8n request timed out after {timeout}s") from exc

    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return raw


def list_workflows(*, active: bool | None = None, limit: int = 100, timeout: int = 30) -> Any:
    return _request(
        "GET",
        "/api/v1/workflows",
        query={"active": active, "limit": limit},
        timeout=timeout,
        auth=True,
    )


def get_workflow(workflow_id: str, *, timeout: int = 30) -> Any:
    return _request("GET", f"/api/v1/workflows/{workflow_id}", timeout=timeout, auth=True)


def create_workflow(workflow: Dict[str, Any], *, timeout: int = 30) -> Any:
    return _request("POST", "/api/v1/workflows", body=workflow, timeout=timeout, auth=True)


def update_workflow(workflow_id: str, workflow: Dict[str, Any], *, timeout: int = 30) -> Any:
    return _request("PUT", f"/api/v1/workflows/{workflow_id}", body=workflow, timeout=timeout, auth=True)


def post_webhook(
    *,
    webhook_path: str | None = None,
    webhook_url: str | None = None,
    payload: Dict[str, Any],
    timeout: int = 30,
) -> Any:
    base = _base_url()
    if webhook_path:
        path = webhook_path if webhook_path.startswith("/") else f"/{webhook_path}"
        target_url = f"{base}{path}"
    elif webhook_url:
        target_url = webhook_url
    else:
        raise RuntimeError("Either webhook_path or webhook_url is required")

    if not target_url.startswith(base):
        raise RuntimeError("n8n webhook URL must match the configured N8N_URL origin")

    req = urllib.request.Request(
        target_url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        return {
            "ok": False,
            "status_code": exc.code,
            "response": body_str,
            "url": target_url,
        }
    except urllib.error.URLError as exc:
        raise RuntimeError(f"n8n webhook connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"n8n webhook timed out after {timeout}s") from exc

    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
        parsed = raw

    return {
        "ok": True,
        "status_code": status,
        "response": parsed,
        "url": target_url,
    }
