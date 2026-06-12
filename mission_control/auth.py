"""Bearer token auth para Mission Control.

ADR-009 D4: token separado de WORKER_TOKEN. /health es anónimo (healthchecks).

PIT-5 P5.3: helpers de firma HMAC para el preview de prototipos
(`make_preview_sig` / `verify_preview_sig`) — URL firmada de vida corta +
cookie HttpOnly path-scoped. Las rutas JSON siguen bearer-only.
"""

from __future__ import annotations

import hashlib
import hmac
import time

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


def _preview_hmac(scope: str, expires_at: int) -> str:
    """HMAC-SHA256 hex sobre ``<scope>:<expiry-epoch>`` con MISSION_CONTROL_TOKEN."""
    assert config.TOKEN is not None  # callers verifican antes (fail-closed 503)
    return hmac.new(
        config.TOKEN.encode("utf-8"),
        f"{scope}:{expires_at}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def make_preview_sig(scope: str, ttl_seconds: int) -> tuple[str, int]:
    """Token firmado ``<expiry-epoch>.<hex-hmac>`` para un scope de preview.

    ``scope`` = ``"<pit_id>/<lane_id>/<iteration>"``. Devuelve
    ``(token, expires_at_epoch)``. Requiere MISSION_CONTROL_TOKEN configurado.
    """
    if not config.TOKEN:
        raise RuntimeError("MISSION_CONTROL_TOKEN no configurado")
    expires_at = int(time.time()) + ttl_seconds
    return f"{expires_at}.{_preview_hmac(scope, expires_at)}", expires_at


def verify_preview_sig(scope: str, token_value: str | None) -> bool:
    """Valida un token de preview (formato, expiry y HMAC) para ``scope``.

    Constant-time sobre la firma (``hmac.compare_digest``). False si el token
    está malformado, vencido, firmado para otro scope, o no hay TOKEN.
    """
    if not config.TOKEN or not token_value:
        return False
    expiry_raw, sep, presented = token_value.partition(".")
    if not sep or not presented:
        return False
    try:
        expires_at = int(expiry_raw)
    except ValueError:
        return False
    if expires_at < time.time():
        return False
    return hmac.compare_digest(presented, _preview_hmac(scope, expires_at))
