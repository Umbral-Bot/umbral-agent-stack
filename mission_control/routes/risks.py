"""GET /risks — read-only operational risk register."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/risks")
async def risks_state() -> dict:
    return {
        "read_only": True,
        "risks": [
            {
                "id": "pip-audit",
                "severity": "high",
                "status": "mitigate_in_pr",
                "summary": "Transitive packages need secure minimums pinned in pyproject.",
            },
            {
                "id": "env-acl",
                "severity": "medium",
                "status": "local_hardening_required",
                "summary": "Local .env must stay untracked and restricted to user/admin/system.",
            },
            {
                "id": "board-drift",
                "severity": "medium",
                "status": "watch",
                "summary": "Board/tasks/PR state can drift across Cursor, Codex, Copilot, and VPS.",
            },
            {
                "id": "stale-prs",
                "severity": "medium",
                "status": "needs_david_authorization",
                "summary": "Stale tournament PRs #442/#443 should not be closed without explicit approval.",
            },
            {
                "id": "linkedin-autopublish",
                "severity": "high",
                "status": "blocked_by_policy",
                "summary": "LinkedIn v1 remains strict HITL; no blind autopublish.",
            },
        ],
    }
