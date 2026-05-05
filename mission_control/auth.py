"""Bearer token auth para Mission Control.

ADR-009 D4: token separado de WORKER_TOKEN. /health es anónimo (healthchecks).
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from . import config


def require_token(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency: rechaza si Bearer ausente o no coincide.

    Si MISSION_CONTROL_TOKEN no está configurado, rechaza TODO con 503 para
    evitar exposición accidental de un dashboard sin auth en producción.
    """
    if not config.TOKEN:
        raise HTTPException(
            status_code=503,
            detail="MISSION_CONTROL_TOKEN no configurado",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token requerido")

    presented = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(presented, config.TOKEN):
        raise HTTPException(status_code=403, detail="Token inválido")
