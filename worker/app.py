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

import asyncio
import hmac
import ipaddress
import json
import logging
import os
import re
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from infra.ops_logger import ops_log

from .config import RATE_LIMIT_INTERNAL_RPM, RATE_LIMIT_RPM, WORKER_TOKEN
from .rate_limiter import RateLimiter
from .client_auth import (
    is_client_api_key,
    get_client_store,
    is_task_allowed,
    get_tier_config,
)
from .sanitize import sanitize_input, sanitize_task_name
from .task_errors import TaskExecutionError
from .tracing import flush as flush_tracing
from .models import (
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
    source: Optional[str] = None
    source_kind: Optional[str] = None
    notion_track: bool = False
    project_name: Optional[str] = None
    project_page_id: Optional[str] = None
    deliverable_name: Optional[str] = None
    deliverable_page_id: Optional[str] = None

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


def _ops_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _ops_context_from_envelope(envelope: Union[TaskEnvelope, Dict[str, Any]]) -> Dict[str, str]:
    def _read(name: str) -> Any:
        if isinstance(envelope, dict):
            return envelope.get(name)
        return getattr(envelope, name, None)

    ctx: Dict[str, str] = {}
    trace_id = _read("trace_id")
    task_type = _ops_value(_read("task_type"))
    source = _read("source")
    source_kind = _read("source_kind")

    if trace_id:
        ctx["trace_id"] = str(trace_id)
    if task_type:
        ctx["task_type"] = str(task_type)
    if source:
        ctx["source"] = str(source).strip()
    if source_kind:
        ctx["source_kind"] = str(source_kind).strip()
    return ctx


def _build_handler_input(envelope: TaskEnvelope) -> Dict[str, Any]:
    payload = dict(envelope.input)
    if envelope.task in {"llm.generate", "composite.research_report", "research.web"}:
        payload["_task_id"] = envelope.task_id
        payload["_task_type"] = str(_ops_value(envelope.task_type))
        if envelope.source:
            payload["_source"] = str(envelope.source).strip()
        if envelope.source_kind:
            payload["_source_kind"] = str(envelope.source_kind).strip()
        if envelope.task == "llm.generate":
            payload["_usage_component"] = "llm.generate"
    return payload


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
_UUIDISH_SEGMENT = re.compile(r"^(?:\d+|[0-9a-f-]{8,})$", re.IGNORECASE)
_RATE_LIMIT_FRAGMENT = re.compile(r"[^a-z0-9._-]+")
_TAILSCALE_V4 = ipaddress.ip_network("100.64.0.0/10")
_TAILSCALE_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")
_RATE_LIMIT_BODY_PATHS = {"/run", "/enqueue"}


@dataclass(frozen=True)
class _RateLimitDecision:
    scope: str
    bucket: str
    limit: int


external_limiter = RateLimiter(max_requests=RATE_LIMIT_RPM, window_seconds=60)
internal_limiter = RateLimiter(max_requests=RATE_LIMIT_INTERNAL_RPM, window_seconds=60)
# Per-client API key limiter — bounded LRU cache (max 10k clients).
_MAX_CLIENT_LIMITERS = 10_000
_client_limiters: OrderedDict[str, RateLimiter] = OrderedDict()
# Backward-compat for tests and older imports.
limiter = external_limiter


def _has_valid_bearer_token(authorization: str | None) -> bool:
    if not WORKER_TOKEN or not authorization:
        return False
    parts = authorization.split(" ", 1)
    return (
        len(parts) == 2
        and parts[0].lower() == "bearer"
        and hmac.compare_digest(parts[1], WORKER_TOKEN)
    )


def _is_internal_host(host: str | None) -> bool:
    if not host:
        return False

    candidate = host.strip().lower()
    if candidate in {"localhost", "testclient"}:
        return True

    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return False

    if address.is_loopback or address.is_private or address.is_link_local:
        return True
    if address.version == 4 and address in _TAILSCALE_V4:
        return True
    if address.version == 6 and address in _TAILSCALE_V6:
        return True
    return False


def _rate_limit_fragment(value: Any) -> str:
    text = str(value or "").strip().lower().replace("/", ".")
    text = _RATE_LIMIT_FRAGMENT.sub("_", text).strip("._-")
    return text[:80] or "unknown"


def _normalized_rate_limit_path(path: str) -> str:
    parts = [part for part in path.strip("/").split("/") if part]
    if not parts:
        return "root"

    normalized: list[str] = []
    for part in parts:
        normalized.append("{id}" if _UUIDISH_SEGMENT.fullmatch(part) else part)
    return _rate_limit_fragment(".".join(normalized))


async def _load_rate_limit_payload(request: Request) -> Dict[str, Any] | None:
    if request.url.path not in _RATE_LIMIT_BODY_PATHS:
        return None
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return None

    try:
        raw_body = await request.body()
        if not raw_body:
            return None
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _internal_bucket_from_request(request: Request, payload: Dict[str, Any] | None) -> str:
    host = request.client.host if request.client else "unknown"
    bucket_parts = [
        "internal",
        _rate_limit_fragment(host),
        _rate_limit_fragment(request.method),
        _normalized_rate_limit_path(request.url.path),
    ]

    caller = request.headers.get("X-Umbral-Caller", "")
    if caller:
        bucket_parts.append(f"caller={_rate_limit_fragment(caller)}")

    if payload:
        task = payload.get("task")
        task_type = payload.get("task_type")
        source = payload.get("source")
        source_kind = payload.get("source_kind")

        if task:
            bucket_parts.append(f"task={_rate_limit_fragment(task)}")
        if task_type:
            bucket_parts.append(f"type={_rate_limit_fragment(task_type)}")
        if source_kind:
            bucket_parts.append(f"source_kind={_rate_limit_fragment(source_kind)}")
        elif source:
            bucket_parts.append(f"source={_rate_limit_fragment(source)}")

    return ":".join(bucket_parts)


async def _rate_limit_decision(request: Request) -> _RateLimitDecision:
    host = request.client.host if request.client else "unknown"
    authorization = request.headers.get("authorization")
    if _has_valid_bearer_token(authorization) and _is_internal_host(host):
        payload = await _load_rate_limit_payload(request)
        return _RateLimitDecision(
            scope="internal",
            bucket=_internal_bucket_from_request(request, payload),
            limit=internal_limiter.max_requests,
        )

    return _RateLimitDecision(
        scope="external",
        bucket=f"external:{_rate_limit_fragment(host)}",
        limit=external_limiter.max_requests,
    )


def _rate_limit_headers(decision: _RateLimitDecision, remaining: int, *, retry_after: bool = False) -> Dict[str, str]:
    headers = {
        "X-RateLimit-Scope": decision.scope,
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(max(remaining, 0)),
    }
    if retry_after:
        headers["Retry-After"] = "60"
    return headers

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    decision = await _rate_limit_decision(request)
    active_limiter = internal_limiter if decision.scope == "internal" else external_limiter
    allowed, remaining = active_limiter.is_allowed(decision.bucket)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Retry later."},
            headers=_rate_limit_headers(decision, remaining, retry_after=True),
        )

    response = await call_next(request)
    for name, value in _rate_limit_headers(decision, remaining).items():
        response.headers.setdefault(name, value)
    return response


def _load_quota_provider_config() -> dict[str, dict[str, Any]]:
    import yaml

    try:
        with open("config/quota_policy.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to load quota policy: %s", e)
        return {}
    return config.get("providers", {}) or {}


def _build_quota_snapshot(
    provider_config: dict[str, dict[str, Any]],
    details: dict[str, dict[str, Any]] | None = None,
    *,
    redis_available: bool,
) -> dict[str, dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    details = details or {}

    for provider in sorted(provider_config.keys()):
        d = details.get(provider, {})
        used = d.get("used", 0)
        limit = d.get("limit", provider_config.get(provider, {}).get("limit_requests", 0))
        fraction = d.get("fraction", 0.0)

        cfg = provider_config.get(provider, {})
        warn = float(cfg.get("warn", 0.8))
        restrict = float(cfg.get("restrict", 0.95))

        if not redis_available:
            status = "unknown"
        elif fraction >= 1.0:
            status = "exceeded"
        elif fraction >= restrict:
            status = "restrict"
        elif fraction >= warn:
            status = "warn"
        else:
            status = "ok"

        providers[provider] = {
            "used": used,
            "limit": limit,
            "fraction": round(fraction, 4),
            "status": status,
        }

    return providers



# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


@dataclass
class AuthContext:
    """Result of authentication — identifies caller type and client."""
    kind: str  # "admin" (WORKER_TOKEN) or "client" (API key)
    client_id: str | None = None
    tier: str | None = None


def _authenticate(authorization: str | None) -> AuthContext:
    """
    Validate Bearer token. Returns AuthContext.

    Supports two auth modes:
    - WORKER_TOKEN: admin/internal access (original behavior)
    - Client API key (ubim_*): per-client access with tier limits
    """
    if not authorization:
        logger.warning("Request to /run without Authorization header")
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token = parts[1]

    # Client API key path
    if is_client_api_key(token):
        store = get_client_store()
        record = store.get_by_api_key(token)
        if not record:
            logger.warning("Request with invalid client API key")
            raise HTTPException(status_code=401, detail="Invalid or missing token")
        return AuthContext(kind="client", client_id=record.client_id, tier=record.tier)

    # WORKER_TOKEN path (admin)
    if not WORKER_TOKEN:
        logger.error("WORKER_TOKEN not configured on server")
        raise HTTPException(status_code=500, detail="WORKER_TOKEN not configured on server")

    if not hmac.compare_digest(token, WORKER_TOKEN):
        logger.warning("Request to /run with invalid token")
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    return AuthContext(kind="admin")


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
    Client API keys: per-client rate limits, daily limits, and task access control.
    """
    auth = _authenticate(authorization)

    # --- Parse: detect envelope vs legacy ---
    try:
        envelope = TaskEnvelope.from_run_payload(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {exc}")

    # S7: sanitize task name and input size (apply sanitized result)
    try:
        sanitize_task_name(envelope.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        envelope.input = sanitize_input(envelope.input, task=envelope.task)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # --- Client tier enforcement ---
    if auth.kind == "client":
        # Task access check
        if not is_task_allowed(auth.tier, envelope.task):
            raise HTTPException(
                status_code=403,
                detail=f"Task '{envelope.task}' not allowed for tier '{auth.tier}'",
            )
        # Daily limit check
        store = get_client_store()
        if not store.check_daily_limit(auth.client_id):
            tier_cfg = get_tier_config(auth.tier)
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit ({tier_cfg.get('daily_limit', 0)}) exceeded for tier '{auth.tier}'",
            )
        # Per-client rate limit (RPM)
        tier_cfg = get_tier_config(auth.tier)
        client_rpm = tier_cfg.get("rate_limit_rpm", 10)
        if auth.client_id not in _client_limiters:
            _client_limiters[auth.client_id] = RateLimiter(
                max_requests=client_rpm, window_seconds=60
            )
            # LRU eviction
            while len(_client_limiters) > _MAX_CLIENT_LIMITERS:
                _client_limiters.popitem(last=False)
        _client_limiters.move_to_end(auth.client_id)
        allowed, remaining = _client_limiters[auth.client_id].is_allowed(auth.client_id)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit ({client_rpm} rpm) exceeded for your API key",
                headers={"Retry-After": "60"},
            )

    ops_context = _ops_context_from_envelope(envelope)
    team_value = _ops_value(envelope.team)
    selected_model = envelope.selected_model or envelope.input.get("selected_model") or ""
    input_summary = str(envelope.input)[:200]

    # --- Dispatch task ---
    handler = TASK_HANDLERS.get(envelope.task)
    if handler is None:
        logger.warning("Unknown task: %s (task_id=%s)", envelope.task, envelope.task_id)
        ops_log.task_failed(
            envelope.task_id,
            envelope.task,
            team_value,
            f"Unknown task: {envelope.task}. Available: {list(TASK_HANDLERS.keys())}",
            model=selected_model,
            input_summary=input_summary,
            **ops_context,
        )
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
    started_at_monotonic = time.time()

    try:
        loop = asyncio.get_event_loop()
        handler_input = _build_handler_input(envelope)
        result_data = await loop.run_in_executor(None, handler, handler_input)
    except TaskExecutionError as exc:
        logger.warning("Task %s failed with structured error: %s", envelope.task, exc.log_message())
        ops_log.task_failed(
            envelope.task_id,
            envelope.task,
            team_value,
            exc.log_message(),
            model=selected_model,
            input_summary=input_summary,
            **ops_context,
        )
        _store_task(
            TaskResult(
                task_id=envelope.task_id,
                task=envelope.task,
                status=TaskStatus.FAILED,
                error=exc.log_message(),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        return JSONResponse(status_code=exc.status_code, content=exc.response_payload())
    except ValueError as exc:
        logger.warning("Task %s input error: %s", envelope.task, exc)
        ops_log.task_failed(
            envelope.task_id,
            envelope.task,
            team_value,
            str(exc),
            model=selected_model,
            input_summary=input_summary,
            **ops_context,
        )
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
        ops_log.task_failed(
            envelope.task_id,
            envelope.task,
            team_value,
            str(exc),
            model=selected_model,
            input_summary=input_summary,
            **ops_context,
        )
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
    duration_ms = (time.time() - started_at_monotonic) * 1000
    ops_log.task_completed(
        envelope.task_id,
        envelope.task,
        team_value,
        selected_model,
        duration_ms,
        worker="direct",
        input_summary=input_summary,
        **ops_context,
    )

    # Record usage for client API key callers
    if auth.kind == "client":
        store = get_client_store()
        store.record_usage(auth.client_id, envelope.task)

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
    auth = _authenticate(authorization)

    # Sanitize (apply sanitized result)
    try:
        sanitize_task_name(body.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # --- Client tier enforcement on enqueue ---
    if auth.kind == "client":
        if not is_task_allowed(auth.tier, body.task):
            raise HTTPException(
                status_code=403,
                detail=f"Task '{body.task}' not allowed for tier '{auth.tier}'",
            )
        store = get_client_store()
        if not store.check_daily_limit(auth.client_id):
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit exceeded for tier '{auth.tier}'",
            )

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
    if body.source:
        envelope["source"] = body.source.strip()
    if body.source_kind:
        envelope["source_kind"] = body.source_kind.strip()
    if body.notion_track:
        envelope["notion_track"] = True
        sanitized_input.setdefault("notion_track", True)
    for field in ("project_name", "project_page_id", "deliverable_name", "deliverable_page_id"):
        value = getattr(body, field)
        if value:
            envelope[field] = value
            sanitized_input.setdefault(field, value)
    callback_url = body.callback_url.strip() if body.callback_url else ""
    if callback_url:
        envelope["callback_url"] = callback_url

    # Enqueue in Redis (same structure as TaskQueue.enqueue)
    from dispatcher.queue import TaskQueue
    queue = TaskQueue(r)
    queue.enqueue(envelope)

    # Emit task_queued event for observability (02-bugs #5)
    try:
        queue_ops_context = _ops_context_from_envelope(envelope)
        queue_ops_context.pop("task_type", None)
        ops_log.task_queued(
            task_id=task_id,
            task=body.task,
            team=body.team,
            task_type=body.task_type or "general",
            **queue_ops_context,
        )
    except Exception:
        pass  # ops_log is best-effort

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
    provider_config = _load_quota_provider_config()
    details: dict[str, dict[str, Any]] = {}
    if r is not None:
        from dispatcher.quota_tracker import QuotaTracker

        tracker = QuotaTracker(r, provider_config)
        details = tracker.get_all_quota_details()

    return {
        "providers": _build_quota_snapshot(provider_config, details, redis_available=r is not None),
        "redis_available": r is not None,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# Provider model names (human-readable mapping)
# ---------------------------------------------------------------------------
_PROVIDER_MODELS = {
    "azure_foundry":    "gpt-5.4",
    "claude_pro":       "claude-sonnet-4-6",
    "claude_opus":      "claude-opus-4-6",
    "claude_haiku":     "claude-haiku-4-5",
    "gemini_pro":       "gemini-2.5-pro",
    "gemini_flash":     "gemini-2.5-flash",
    "gemini_flash_lite": "gemini-2.5-flash-lite",
    "gemini_vertex":    "gemini-2.5-flash",
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

    # --- Load config ---
    from dispatcher.model_router import (
        ModelRouter,
        get_configured_providers,
        load_quota_policy,
        _PROVIDER_ENV_REQUIREMENTS,
    )

    routing, provider_config = load_quota_policy()
    configured = get_configured_providers()
    all_known = set(provider_config.keys()) | set(_PROVIDER_ENV_REQUIREMENTS.keys())
    unconfigured = sorted(all_known - configured)

    # --- Quota data ---
    details: dict[str, dict[str, Any]] = {}
    if r is not None:
        from dispatcher.quota_tracker import QuotaTracker

        tracker = QuotaTracker(r, provider_config)
        details = tracker.get_all_quota_details()
    else:
        class _NullQuotaTracker:
            def get_all_quota_states(self) -> dict[str, float]:
                return {}

        tracker = _NullQuotaTracker()

    router = ModelRouter(tracker)
    routing_snapshot = router.get_routing_snapshot()

    # --- Build routing maps per provider ---
    declared_routing_map: dict[str, list[str]] = {}
    for task_type, route in routing.items():
        declared_pref = route.get("preferred", "")
        if declared_pref:
            declared_routing_map.setdefault(declared_pref, []).append(task_type)

    effective_routing_map: dict[str, list[str]] = {}
    routing_out: dict[str, dict[str, Any]] = {}
    for task_type, route_info in routing_snapshot.items():
        effective_pref = route_info.get("preferred")
        if effective_pref:
            effective_routing_map.setdefault(effective_pref, []).append(task_type)

        routing_out[task_type] = {
            "declared_preferred": route_info["declared_preferred"],
            "declared_model": _PROVIDER_MODELS.get(route_info["declared_preferred"], "unknown"),
            "declared_fallback_chain": route_info["declared_fallback_chain"],
            "effective_preferred": effective_pref,
            "effective_model": _PROVIDER_MODELS.get(effective_pref, "unknown") if effective_pref else None,
            "effective_fallback_chain": route_info["fallback_chain"],
            "effective_fallback_models": [
                _PROVIDER_MODELS.get(provider, "unknown")
                for provider in route_info["fallback_chain"]
            ],
            "unconfigured": route_info["unconfigured"],
            "has_configured_route": route_info["has_configured_route"],
        }

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
            if r is None:
                q_status = "unknown"
            elif fraction >= 1.0:
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
            q_status = "unknown" if r is None or not is_configured else "ok"

        providers_out[provider] = {
            "configured": is_configured,
            "model": _PROVIDER_MODELS.get(provider, "unknown"),
            "quota_used": used,
            "quota_limit": limit,
            "quota_fraction": round(fraction, 4),
            "quota_status": q_status,
            "routing_preferred_for": sorted(declared_routing_map.get(provider, [])),
            "routing_effective_for": sorted(effective_routing_map.get(provider, [])),
        }

    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "redis_available": r is not None,
        "configured": sorted(configured),
        "unconfigured": unconfigured,
        "routing": routing_out,
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
    "google": "google",
    "figma": "figma",
    "azure": "azure",
    "make": "integrations",
    "client": "admin",
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
