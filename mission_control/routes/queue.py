"""GET /queue — longitudes de las colas Redis conocidas."""

from __future__ import annotations

from fastapi import APIRouter

from ..adapters import redis_queue

router = APIRouter()


@router.get("/queue")
async def queue_state() -> dict:
    return redis_queue.read_state()
