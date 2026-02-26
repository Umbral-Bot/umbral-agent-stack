"""
Umbral Agent Stack — Worker HTTP (FastAPI)

Servicio worker que recibe tareas desde el VPS (OpenClaw) vía Tailscale.
Escucha en 0.0.0.0:8088, autenticado por Bearer token.

Uso:
    # Dev
    WORKER_TOKEN=mi_token python -m uvicorn app:app --host 0.0.0.0 --port 8088

    # Producción (NSSM)
    Ver scripts/setup-openclaw-service.ps1
"""

import logging
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WORKER_TOKEN: str | None = os.environ.get("WORKER_TOKEN")

if WORKER_TOKEN:
    logger.info("WORKER_TOKEN loaded from environment (%d chars)", len(WORKER_TOKEN))
else:
    logger.warning(
        "WORKER_TOKEN not set — /run endpoint will return 500. "
        "Set the WORKER_TOKEN environment variable before starting."
    )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Umbral Worker",
    description="Worker HTTP para ejecución de tareas desde OpenClaw (VPS).",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    """Payload para POST /run."""

    task: str
    input: Dict[str, Any] = {}


class RunResponse(BaseModel):
    """Respuesta de POST /run."""

    ok: bool
    task: str
    result: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Respuesta de GET /health."""

    ok: bool
    ts: int


# ---------------------------------------------------------------------------
# Task Handlers
# ---------------------------------------------------------------------------
# Diccionario extensible de handlers por tarea.
# Cada handler recibe el input dict y devuelve un result dict.


def _handle_ping(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Echo de prueba — devuelve el input recibido."""
    return {"echo": input_data}


TASK_HANDLERS: Dict[str, callable] = {
    "ping": _handle_ping,
    # Agregar más handlers aquí:
    # "exec": _handle_exec,
    # "file_read": _handle_file_read,
}

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check — no requiere autenticación."""
    return HealthResponse(ok=True, ts=int(time.time()))


@app.post("/run", response_model=RunResponse)
async def run_task(
    body: RunRequest,
    authorization: str = Header(None),
):
    """
    Ejecuta una tarea. Requiere Authorization: Bearer <token>.
    """

    # --- Check WORKER_TOKEN is configured ---
    if not WORKER_TOKEN:
        logger.error("WORKER_TOKEN not configured on server")
        raise HTTPException(
            status_code=500,
            detail="WORKER_TOKEN not configured on server",
        )

    # --- Validate auth header ---
    if not authorization:
        logger.warning("Request to /run without Authorization header")
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    # Parse "Bearer <token>"
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != WORKER_TOKEN:
        logger.warning("Request to /run with invalid token")
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    # --- Dispatch task ---
    handler = TASK_HANDLERS.get(body.task)
    if handler is None:
        logger.warning("Unknown task: %s", body.task)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task: {body.task}. Available: {list(TASK_HANDLERS.keys())}",
        )

    logger.info("Executing task: %s", body.task)
    try:
        result = handler(body.input)
    except Exception as exc:
        logger.exception("Task %s failed: %s", body.task, exc)
        raise HTTPException(status_code=500, detail=f"Task failed: {str(exc)}")

    return RunResponse(ok=True, task=body.task, result=result)


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )
