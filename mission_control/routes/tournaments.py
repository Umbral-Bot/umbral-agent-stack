"""GET /tournaments — placeholder.

Stretch (O13.4) construye el dispatcher real. En MVP read-only sólo expone
una lista vacía + nota explícita, para que el frontend sepa que es esperado.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/tournaments")
async def list_tournaments() -> dict:
    return {
        "active": [],
        "note": (
            "MVP read-only (ADR-009 D1). Dispatcher de tournaments queda en "
            "stretch O13.4, condicionado al quality gate D6."
        ),
    }
