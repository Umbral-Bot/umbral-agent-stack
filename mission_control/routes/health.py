"""GET /health — anónimo, para healthchecks externos."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "mission_control",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
