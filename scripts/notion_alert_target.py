#!/usr/bin/env python3
"""
Resolve the effective Notion target for supervisor alerts.

Priority:
1. Dedicated alert page via Supervisor integration, if active.
2. Dedicated alert page via Worker/Rick integration, if active.
3. Control Room page via Worker/Rick integration, if active.
4. Unavailable.

This allows operational tooling to detect archived pages and choose a clean
fallback before trying to post a comment.
"""
from __future__ import annotations

import argparse
import os
import shlex
from typing import Any, Callable

import httpx

NOTION_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"


def get_page_status(page_id: str | None, token: str | None) -> dict[str, Any]:
    if not page_id:
        return {"ok": False, "reason": "missing_page_id"}
    if not token:
        return {"ok": False, "reason": "missing_token"}

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{NOTION_BASE_URL}/pages/{page_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": NOTION_VERSION,
                },
            )
        data = resp.json()
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "reason": "request_error", "error": f"{type(exc).__name__}: {exc}"}

    if resp.status_code != 200:
        return {
            "ok": False,
            "reason": "http_error",
            "status_code": resp.status_code,
            "error_code": data.get("code"),
            "error_message": data.get("message"),
        }

    archived = bool(data.get("archived"))
    in_trash = bool(data.get("in_trash"))
    return {
        "ok": not archived and not in_trash,
        "reason": "ok" if not archived and not in_trash else "archived",
        "status_code": 200,
        "archived": archived,
        "in_trash": in_trash,
        "page_id": data.get("id"),
        "url": data.get("url"),
    }


def resolve_alert_target(
    env: dict[str, str] | None = None,
    *,
    page_probe: Callable[[str | None, str | None], dict[str, Any]] = get_page_status,
) -> dict[str, Any]:
    env = env or os.environ
    alert_page_id = (env.get("NOTION_SUPERVISOR_ALERT_PAGE_ID") or "").strip() or None
    control_page_id = (env.get("NOTION_CONTROL_ROOM_PAGE_ID") or "").strip() or None
    supervisor_token = (env.get("NOTION_SUPERVISOR_API_KEY") or "").strip() or None
    worker_token = (env.get("NOTION_API_KEY") or "").strip() or None

    checks = {
        "alert_supervisor": page_probe(alert_page_id, supervisor_token),
        "alert_worker": page_probe(alert_page_id, worker_token),
        "control_worker": page_probe(control_page_id, worker_token),
    }

    if checks["alert_supervisor"].get("ok"):
        return {
            "ok": True,
            "mode": "direct_supervisor",
            "target_page_id": alert_page_id,
            "reason": "alert_page_active_with_supervisor_integration",
            "checks": checks,
        }

    if checks["alert_worker"].get("ok"):
        return {
            "ok": True,
            "mode": "worker_alert_page",
            "target_page_id": alert_page_id,
            "reason": "alert_page_active_via_worker_integration",
            "checks": checks,
        }

    if checks["control_worker"].get("ok"):
        reason = checks["alert_supervisor"].get("reason") or checks["alert_worker"].get("reason") or "alert_page_unavailable"
        return {
            "ok": True,
            "mode": "worker_control_room_fallback",
            "target_page_id": control_page_id,
            "reason": reason,
            "checks": checks,
        }

    return {
        "ok": False,
        "mode": "unavailable",
        "target_page_id": None,
        "reason": "no_active_notion_target",
        "checks": checks,
    }


def _to_shell(result: dict[str, Any]) -> str:
    mapping = {
        "ALERT_ROUTE_OK": "true" if result.get("ok") else "false",
        "ALERT_MODE": result.get("mode") or "",
        "TARGET_PAGE_ID": result.get("target_page_id") or "",
        "ALERT_REASON": result.get("reason") or "",
    }
    return "\n".join(f"{key}={shlex.quote(str(value))}" for key, value in mapping.items())


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve effective Notion alert target.")
    parser.add_argument("--format", choices=("json", "shell"), default="json")
    args = parser.parse_args()

    result = resolve_alert_target()
    if args.format == "shell":
        print(_to_shell(result))
    else:
        import json

        print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
