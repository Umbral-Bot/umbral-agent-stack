"""GET /tournaments — read-only tournament status.

No launcher in v1. The endpoint reports D3.x state and stale PR risk only.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/tournaments")
async def list_tournaments() -> dict:
    return {
        "read_only": True,
        "launcher_enabled": False,
        "active": [],
        "history": [
            {
                "id": "D3.0",
                "status": "done",
                "pr_count": 1,
                "winner": "protocol-baseline",
                "salvage_used": False,
            },
            {
                "id": "D3.1",
                "status": "done",
                "pr_count": 1,
                "winner": "runner-hardening",
                "salvage_used": False,
            },
            {
                "id": "D3.2",
                "status": "incomplete_lane_no_pr_url",
                "pr_count": 1,
                "winner": None,
                "salvage_used": True,
            },
            {
                "id": "D3.3",
                "status": "done",
                "pr_count": 2,
                "winner": "sync-skills-adapters",
                "salvage_used": True,
            },
        ],
        "stale_prs": ["#442", "#443"],
        "note": (
            "MVP read-only. No ejecutar torneos desde Mission Control v1; "
            "D3.5 limpio requiere autorización explícita de David."
        ),
    }
