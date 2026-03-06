"""
Umbral Agent Stack — Worker HTTP (FastAPI) v0.4.0

Servicio worker que recibe tareas desde el VPS (OpenClaw) vía Tailscale.
Escucha en 0.0.0.0:8088, autenticado por Bearer token.

Soporta:
    - TaskEnvelope v0.1 (formato completo con trazabilidad)
    - Legacy {task, input} (backward compat, se convierte a envelope)
    - POST /enqueue para encolar tareas vía Redis (servicios externos)
    - GET /task/{task_id}/status para consultar estado desde Redis
    - GET /tasks/{task_id} para consultar estado in-memory

Uso:
    # Dev
    WORKER_TOKEN=mi_token python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088

    # Producción (NSSM)
    Ver scripts/setup-openclaw-service.ps1
"""

import json
import hmac
import logging
import os
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from infra.ops_logger import ops_log

from .config import RATE_LIMIT_RPM, WORKER_TOKEN
from .rate_limiter import RateLimiter
from .sanitize import sanitize_input, sanitize_task_name
from .tracing import flush as flush_tracing
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
# Redis connection (lazy, for /enqueue and /task/{id}/status)
# ---------------------------------------------------------------------------
_redis_client = None


def _get_redis():
    """Lazy Redis client. Returns None if redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis connected for /enqueue API (%s)", redis_url)
        return _redis_client
    except Exception as e:
        logger.warning("Redis not available for /enqueue: %s", e)
        _redis_client = None
        return None


# ---------------------------------------------------------------------------
# Pydantic models for /enqueue
# ---------------------------------------------------------------------------


class EnqueueRequest(BaseModel):
    """Request body for POST /enqueue."""
    task: str
    team: str = "system"
    task_type: str = "general"
    input: Dict[str, Any] = {}
    callback_url: Optional[str] = Field(default=None, description="Webhook URL opcional para callback al completar/fallar")

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
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    flush_tracing()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Umbral Worker",
    description="Worker HTTP para ejecución de tareas desde OpenClaw (VPS). "
    "Soporta TaskEnvelope v0.1, formato legacy, y enqueue vía Redis.",
    version="0.4.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Rate Limiting Middleware
# ---------------------------------------------------------------------------
limiter = RateLimiter(max_requests=RATE_LIMIT_RPM, window_seconds=60)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    
    client_id = request.client.host if request.client else "unknown"
    allowed, remaining = limiter.is_allowed(client_id)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Retry later."},
            headers={"Retry-After": "60"}
        )
    
    response = await call_next(request)
    return response



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
    if len(parts) != 2 or parts[0].lower() != "bearer" or not hmac.compare_digest(parts[1], WORKER_TOKEN):
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
        "version": "0.4.0",
        "tasks_registered": list(TASK_HANDLERS.keys()),
        "tasks_in_memory": len(_task_store),
    }


@app.post("/run")
async def run_task(
    request: Request,
    body: Dict[str, Any],
    authorization: str = Header(None),
):
    """
    Ejecuta una tarea. Requiere Authorization: Bearer <token>.

    Acepta dos formatos:
      - TaskEnvelope v0.1: {schema_version, task_id, team, task_type, task, input, ...}
      - Legacy: {task, input}

    Ambos se normalizan a TaskEnvelope internamente.
    S7: rate limiting y sanitización de inputs.
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

    # S7: sanitize task name and input size
    try:
        sanitize_task_name(envelope.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        envelope.input = sanitize_input(envelope.input)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

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


# ---------------------------------------------------------------------------
# Enqueue API (Redis-backed, for external services)
# ---------------------------------------------------------------------------


@app.post("/enqueue")
async def enqueue_task(
    request: Request,
    body: EnqueueRequest,
    authorization: str = Header(None),
):
    """
    Encola una tarea en Redis para procesamiento asíncrono por el Dispatcher.

    Pensado para servicios externos (Make.com, n8n, webhooks, cron) que
    quieren enviar trabajo sin necesitar el SDK Python.

    Returns:
        {"ok": true, "task_id": "uuid", "queued": true}
    """
    _authenticate(authorization)

    # Sanitize
    try:
        sanitize_task_name(body.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        sanitized_input = sanitize_input(body.input)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Redis required
    r = _get_redis()
    if r is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not available. Cannot enqueue tasks.",
        )

    # Build envelope
    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    envelope = {
        "schema_version": "0.1",
        "task_id": task_id,
        "team": body.team,
        "task_type": body.task_type,
        "task": body.task,
        "input": sanitized_input,
        "status": "queued",
        "trace_id": trace_id,
        "created_at": now,
        "queued_at": time.time(),
    }
    callback_url = body.callback_url.strip() if body.callback_url else ""
    if callback_url:
        envelope["callback_url"] = callback_url

    # Enqueue in Redis (same structure as TaskQueue.enqueue)
    from dispatcher.queue import TaskQueue
    queue = TaskQueue(r)
    queue.enqueue(envelope)
    ops_log.task_queued(task_id, body.task, body.team, body.task_type or "general", trace_id=trace_id)

    logger.info(
        "Enqueued task via API: %s (task=%s, team=%s, type=%s)",
        task_id, body.task, body.team, body.task_type,
    )

    return {"ok": True, "task_id": task_id, "queued": True}


@app.get("/task/{task_id}/status")
async def get_task_status(
    task_id: str,
    authorization: str = Header(None),
):
    """
    Consulta el estado de una tarea desde Redis.

    Lee de umbral:task:{task_id}. Retorna el envelope completo incluyendo
    status, result (si done), error (si failed), timestamps, etc.
    """
    _authenticate(authorization)

    r = _get_redis()
    if r is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not available. Cannot query task status.",
        )

    task_key = f"umbral:task:{task_id}"
    raw = r.get(task_key)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found in Redis")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Corrupt task data in Redis")

    return {
        "task_id": data.get("task_id", task_id),
        "status": data.get("status", "unknown"),
        "task": data.get("task", ""),
        "team": data.get("team", ""),
        "task_type": data.get("task_type", ""),
        "result": data.get("result"),
        "error": data.get("error"),
        "created_at": data.get("created_at"),
        "queued_at": data.get("queued_at"),
        "started_at": data.get("started_at"),
        "completed_at": data.get("completed_at"),
    }


@app.get("/task/history")
async def get_task_history(
    authorization: str = Header(None),
    hours: int = Query(24, ge=1, le=24 * 30),
    team: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Consulta historial de tareas desde Redis (paginado).

    Usa SCAN sobre `umbral:task:*` con filtros por ventana temporal, team y status.
    """
    _authenticate(authorization)

    if status:
        valid_status = {"queued", "running", "done", "failed", "blocked", "degraded"}
        if status not in valid_status:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {sorted(valid_status)}",
            )

    r = _get_redis()
    if r is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not available. Cannot query task history.",
        )

    from dispatcher.task_history import TaskHistory

    history = TaskHistory(r)
    page = history.query(
        hours=hours,
        team=team,
        status=status,
        limit=limit,
        offset=offset,
    )
    stats = history.stats(hours=hours)

    return {
        "tasks": page["tasks"],
        "total": page["total"],
        "page": page["page"],
        "stats": stats,
    }


@app.get("/scheduled")
async def list_scheduled_tasks(
    authorization: str = Header(None),
):
    """
    Lista las tareas programadas a futuro (Redis sorted set).
    """
    _authenticate(authorization)

    r = _get_redis()
    if r is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not available. Cannot query scheduled tasks.",
        )

    from dispatcher.scheduler import TaskScheduler
    scheduler = TaskScheduler(r)
    tasks = scheduler.list_scheduled()

    return {"ok": True, "scheduled": tasks, "total": len(tasks)}


@app.get("/quota/status")
async def get_quota_status(
    authorization: str = Header(None)
):
    """
    Devuelve el estado de cuotas de todos los proveedores configurados.
    """
    _authenticate(authorization)
    r = _get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis not available. Cannot query quota status.")

    import yaml
    try:
        with open("config/quota_policy.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            provider_config = config.get("providers", {})
    except Exception as e:
        logger.error("Failed to load quota policy: %s", e)
        provider_config = {}

    from dispatcher.quota_tracker import QuotaTracker
    tracker = QuotaTracker(r, provider_config)
    details = tracker.get_all_quota_details()

    providers = {}
    for p, d in details.items():
        used = d["used"]
        limit = d["limit"]
        fraction = d["fraction"]
        
        cfg = provider_config.get(p, {})
        warn = float(cfg.get("warn", 0.8))
        restrict = float(cfg.get("restrict", 0.95))
        
        if fraction >= 1.0:
            status = "exceeded"
        elif fraction >= restrict:
            status = "restrict"
        elif fraction >= warn:
            status = "warn"
        else:
            status = "ok"
            
        providers[p] = {
            "used": used,
            "limit": limit,
            "fraction": round(fraction, 4),
            "status": status
        }
        
    return {
        "providers": providers,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }


# ---------------------------------------------------------------------------
# Provider model names (human-readable mapping)
# ---------------------------------------------------------------------------
_PROVIDER_MODELS = {
    "azure_foundry":    "gpt-5.3-codex",
    "claude_pro":       "claude-sonnet-4-6",
    "claude_opus":      "claude-opus-4-6",
    "claude_haiku":     "claude-haiku-4-5",
    "gemini_pro":       "gemini-3.1-pro-preview-customtools",
    "gemini_flash":     "gemini-flash-latest",
    "gemini_flash_lite": "gemini-flash-lite-latest",
    "gemini_vertex":    "gemini-3.1-pro-preview",
}


@app.get("/providers/status")
async def get_provider_status(
    authorization: str = Header(None),
):
    """
    Dashboard de estado de providers: qué modelos están configurados,
    su cuota actual y a qué task_types enrutan.
    """
    _authenticate(authorization)

    r = _get_redis()
    if r is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not available. Cannot query provider status.",
        )

    # --- Load config ---
    from dispatcher.model_router import (
        get_configured_providers,
        _load_quota_policy,
        _PROVIDER_ENV_REQUIREMENTS,
    )
    from dispatcher.quota_tracker import QuotaTracker

    routing, provider_config = _load_quota_policy()
    configured = get_configured_providers()
    all_known = set(provider_config.keys()) | set(_PROVIDER_ENV_REQUIREMENTS.keys())
    unconfigured = sorted(all_known - configured)

    # --- Quota data ---
    tracker = QuotaTracker(r, provider_config)
    details = tracker.get_all_quota_details()

    # --- Build routing_preferred_for per provider ---
    routing_map: dict[str, list[str]] = {}
    for task_type, route in routing.items():
        pref = route.get("preferred", "")
        if pref:
            routing_map.setdefault(pref, []).append(task_type)

    # --- Assemble response ---
    providers_out = {}
    for provider in sorted(all_known):
        is_configured = provider in configured
        d = details.get(provider)

        # Quota status
        if d:
            used = d["used"]
            limit = d["limit"]
            fraction = d["fraction"]
            cfg = provider_config.get(provider, {})
            warn = float(cfg.get("warn", 0.8))
            restrict = float(cfg.get("restrict", 0.95))
            if fraction >= 1.0:
                q_status = "exceeded"
            elif fraction >= restrict:
                q_status = "restrict"
            elif fraction >= warn:
                q_status = "warn"
            else:
                q_status = "ok"
        else:
            used = 0
            limit = int(provider_config.get(provider, {}).get("limit_requests", 0))
            fraction = 0.0
            q_status = "unknown" if not is_configured else "ok"

        providers_out[provider] = {
            "configured": is_configured,
            "model": _PROVIDER_MODELS.get(provider, "unknown"),
            "quota_used": used,
            "quota_limit": limit,
            "quota_fraction": round(fraction, 4),
            "quota_status": q_status,
            "routing_preferred_for": sorted(routing_map.get(provider, [])),
        }

    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "configured": sorted(configured),
        "unconfigured": unconfigured,
        "providers": providers_out,
    }


# ---------------------------------------------------------------------------
# Tools inventory
# ---------------------------------------------------------------------------

_CATEGORY_MAP = {
    "ping": "system",
    "notion": "notion",
    "windows": "windows",
    "system": "system",
    "linear": "linear",
    "research": "ai",
    "llm": "ai",
    "composite": "ai",
    "figma": "figma",
    "azure": "azure",
    "make": "integrations",
}


def _detect_skills() -> list[dict]:
    """Scan openclaw/workspace-templates/skills/*/SKILL.md for available skills."""
    import pathlib
    import re

    skills_dir = pathlib.Path(__file__).resolve().parent.parent / "openclaw" / "workspace-templates" / "skills"
    skills = []
    if not skills_dir.is_dir():
        return skills

    for skill_md in skills_dir.glob("*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        # Parse YAML frontmatter (between --- markers)
        fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not fm_match:
            skills.append({"name": skill_md.parent.name, "description": ""})
            continue
        fm = fm_match.group(1)
        name = skill_md.parent.name
        desc = ""
        for line in fm.splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                # Handle >- multiline or single-line
                val = line.split(":", 1)[1].strip()
                if val and val not in (">-", "|"):
                    desc = val
        if not desc:
            # Try to grab the first indented line after description: >-
            in_desc = False
            for line in fm.splitlines():
                if line.strip().startswith("description:"):
                    in_desc = True
                    continue
                if in_desc and line.startswith("  ") and not line.strip().startswith("metadata"):
                    desc = line.strip()
                    break
                elif in_desc and not line.startswith(" "):
                    break
        skills.append({"name": name, "description": desc})
    return skills


@app.get("/tools/inventory")
async def get_tools_inventory(
    authorization: str = Header(None),
):
    """
    Inventario completo de tasks registradas en el Worker,
    skills detectados, y categorización.
    """
    _authenticate(authorization)

    tasks_list = []
    categories: dict[str, int] = {}
    for task_name in sorted(TASK_HANDLERS.keys()):
        # Module = first segment (e.g. "notion" from "notion.add_comment")
        parts = task_name.split(".")
        module = parts[0]
        # Category from mapping; for "windows.fs.*", also map to windows
        category = _CATEGORY_MAP.get(module, module)
        tasks_list.append({
            "name": task_name,
            "module": module,
            "category": category,
        })
        categories[category] = categories.get(category, 0) + 1

    skills = _detect_skills()

    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_tasks": len(tasks_list),
        "tasks": tasks_list,
        "skills": [s["name"] for s in skills],
        "skills_detail": skills,
        "categories": dict(sorted(categories.items())),
    }

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
