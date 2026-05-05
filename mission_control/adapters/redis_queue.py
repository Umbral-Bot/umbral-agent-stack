"""Adapter: longitudes de colas Redis conocidas.

Best-effort: si Redis no está disponible, devuelve `available=False` con error.
"""

from __future__ import annotations

from typing import Any

from .. import config


def read_state(redis_url: str | None = None) -> dict[str, Any]:
    url = redis_url or config.REDIS_URL
    try:
        import redis  # type: ignore[import-not-found]
    except ImportError as exc:
        return {
            "available": False,
            "error": f"redis library not installed: {exc}",
            "queues": {},
        }

    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=2)
        client.ping()
    except Exception as exc:  # noqa: BLE001 — best-effort adapter
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "queues": {},
        }

    queues: dict[str, int] = {}
    for name in config.KNOWN_QUEUES:
        try:
            queues[name] = int(client.llen(name))
        except Exception as exc:  # noqa: BLE001
            queues[name] = -1
            queues[f"{name}__error"] = f"{type(exc).__name__}: {exc}"  # type: ignore[assignment]

    return {
        "available": True,
        "url": url,
        "queues": queues,
    }
