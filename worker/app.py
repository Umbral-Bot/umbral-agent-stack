"""
Umbral Agent Stack — Worker HTTP (FastAPI) v0.3.0

Servicio worker que recibe tareas desde el VPS (OpenClaw) vía Tailscale.
Escucha en 0.0.0.0:8088, autenticado por Bearer token.

Soporta:
    - TaskEnvelope v0.1 (formato completo con trazabilidad)
    - Legacy {task, input} (backward compat, se convierte a envelope)
    - GET /tasks/{task_id} para consultar estado de tareas

Uso:
    # Dev
    WORKER_TOKEN=mi_token python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088

    # Producción (NSSM)
    Ver scripts/setup-openclaw-service.ps1
"""

import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Union

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import WORKER_TOKEN
from .models import (
    LegacyRunRequest,
    TaskEnvelope,
    TaskResult,
    TaskStatus,
)
from .tasks import TASK_HANDLERS

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")

if WORKER_TOKEN:
    logger.info("WORKER_TOKEN loaded from environment (%d chars)", len(WORKER_TOKEN))
else:
    logger.warning(
        "WORKER_TOKEN not set — /run endpoint will return 500. "
        "Set the WORKER_TOKEN environment variable before starting."
    )

logger.info("Registered tasks: %s", list(TASK_HANDLERS.keys()))

# ---------------------------------------------------------------------------
# In-memory task store (bounded, most recent 1000)
# ---------------------------------------------------------------------------
MAX_TASK_HISTORY = 1000
_task_store: OrderedDict[str, TaskResult] = OrderedDict()


def _store_task(result: TaskResult) -> None:
    """Store a task result, evicting oldest if over limit."""
    _task_store[result.task_id] = result
    while len(_task_store) > MAX_TASK_HISTORY:
        _task_store.popitem(last=False)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Umbral Worker",
    description="Worker HTTP para ejecución de tareas desde OpenClaw (VPS). "
    "Soporta TaskEnvelope v0.1 y formato legacy.",
    version="0.3.0",
)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def _authenticate(authorization: str | None) -> None:
    """Validate Bearer token. Raises HTTPException on failure."""
    if not WORKER_TOKEN:
        logger.error("WORKER_TOKEN not configured on server")
        raise HTTPException(status_code=500, detail="WORKER_TOKEN not configured on server")

    if not authorization:
        logger.warning("Request to /run without Authorization header")
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != WORKER_TOKEN:
        logger.warning("Request to /run with invalid token")
        raise HTTPException(status_code=401, detail="Invalid or missing token")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Health check — no requiere autenticación."""
    return {
        "ok": True,
        "ts": int(time.time()),
        "version": "0.3.0",
        "tasks_registered": list(TASK_HANDLERS.keys()),
        "tasks_in_memory": len(_task_store),
    }


@app.post("/run")
async def run_task(
    body: Dict[str, Any],
    authorization: str = Header(None),
):
    """
    Ejecuta una tarea. Requiere Authorization: Bearer <token>.

    Acepta dos formatos:
      - TaskEnvelope v0.1: {schema_version, task_id, team, task_type, task, input, ...}
      - Legacy: {task, input}

    Ambos se normalizan a TaskEnvelope internamente.
    """
    _authenticate(authorization)

    # --- Parse: detect envelope vs legacy ---
    try:
        if "schema_version" in body:
            envelope = TaskEnvelope(**body)
        else:
            legacy = LegacyRunRequest(**body)
            envelope = legacy.to_envelope()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {exc}")

    # --- Dispatch task ---
    handler = TASK_HANDLERS.get(envelope.task)
    if handler is None:
        logger.warning("Unknown task: %s (task_id=%s)", envelope.task, envelope.task_id)
        # Store as failed
        _store_task(
            TaskResult(
                task_id=envelope.task_id,
                task=envelope.task,
                status=TaskStatus.FAILED,
                error=f"Unknown task: {envelope.task}. Available: {list(TASK_HANDLERS.keys())}",
            )
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task: {envelope.task}. Available: {list(TASK_HANDLERS.keys())}",
        )

    # --- Execute ---
    logger.info(
        "Executing task: %s (task_id=%s, team=%s, type=%s, trace=%s)",
        envelope.task,
        envelope.task_id,
        envelope.team,
        envelope.task_type,
        envelope.trace_id,
    )
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        result_data = handler(envelope.input)
    except ValueError as exc:
        logger.warning("Task %s input error: %s", envelope.task, exc)
        _store_task(
            TaskResult(
                task_id=envelope.task_id,
                task=envelope.task,
                status=TaskStatus.FAILED,
                error=str(exc),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Task %s failed: %s", envelope.task, exc)
        _store_task(
            TaskResult(
                task_id=envelope.task_id,
                task=envelope.task,
                status=TaskStatus.FAILED,
                error=str(exc),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        raise HTTPException(status_code=500, detail=f"Task failed: {str(exc)}")

    # --- Success ---
    completed_at = datetime.now(timezone.utc).isoformat()
    task_result = TaskResult(
        task_id=envelope.task_id,
        task=envelope.task,
        status=TaskStatus.DONE,
        result=result_data,
        started_at=started_at,
        completed_at=completed_at,
    )
    _store_task(task_result)

    return {
        "ok": True,
        "task_id": envelope.task_id,
        "task": envelope.task,
        "team": envelope.team,
        "trace_id": envelope.trace_id,
        "result": result_data,
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str, authorization: str = Header(None)):
    """Consultar estado de una tarea por task_id. Requiere auth."""
    _authenticate(authorization)

    task_result = _task_store.get(task_id)
    if task_result is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return task_result.model_dump()


@app.get("/tasks")
async def list_tasks(
    authorization: str = Header(None),
    limit: int = 20,
    team: str | None = None,
    status: str | None = None,
):
    """Listar tareas recientes. Filtrable por team y status."""
    _authenticate(authorization)

    tasks = list(reversed(_task_store.values()))

    if team:
        tasks = [t for t in tasks if t.task.startswith(team) or team in str(t.task_id)]
    if status:
        tasks = [t for t in tasks if t.status == status]

    return {"tasks": [t.model_dump() for t in tasks[:limit]], "total": len(tasks)}


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
