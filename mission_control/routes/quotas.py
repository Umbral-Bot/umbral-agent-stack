"""GET /quotas — display de quota Claude Pro (ADR-009 D1: solo lectura, sin bloqueo)."""

from __future__ import annotations

from fastapi import APIRouter

from ..adapters import quota

router = APIRouter()


@router.get("/quotas")
async def get_quotas() -> dict:
    return quota.read_state()
