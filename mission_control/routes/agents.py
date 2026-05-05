"""GET /agents — lectura de openclaw.json + sesiones vivas (best-effort)."""

from __future__ import annotations

from fastapi import APIRouter

from ..adapters import openclaw

router = APIRouter()


@router.get("/agents")
async def list_agents() -> dict:
    snapshot = openclaw.read_snapshot()
    return {
        "source": str(snapshot.source_path),
        "available": snapshot.available,
        "error": snapshot.error,
        "agents": snapshot.agents,
        "channels": snapshot.channels,
    }
