"""
Dispatcher Service Loop.

VPS autosuficiente: Worker local (WORKER_URL) siempre; VM opcional (WORKER_URL_VM).
- Sin VM o VM caída: todas las tareas van al Worker local (VPS).
- Con VM online: tareas con requires_vm=True van a la VM; el resto al Worker local.
"""

import atexit
import hashlib
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import redis

from dispatcher.health import HealthMonitor
from dispatcher.alert_manager import AlertManager
from dispatcher.model_router import ModelRouter, load_quota_policy
from dispatcher.queue import TaskQueue
from dispatcher.quota_tracker import QuotaTracker
from dispatcher.router import TeamRouter
from dispatcher.team_config import get_team_capabilities
from dispatcher.task_routing import task_requires_vm
from client.worker_client import WorkerClient
from infra.error_classification import classify_error
from infra.ops_logger import ops_log

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows dev environments
    fcntl = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# S4: Mapeo de provider name (quota alias) → model string que entiende el Worker.
PROVIDER_MODEL_MAP: Dict[str, str] = {
    # OpenAI / Codex — Worker accede GPT vía Azure Foundry ($20K credits)
    "azure_foundry": "gpt-5.4",
    # Anthropic (directo)
    "claude_pro":    "claude-sonnet-4-6",
    "claude_opus":   "claude-opus-4-6",
    "claude_haiku":  "claude-haiku-4-5",
    # OpenClaw Proxy (Claude vía gateway local — alias único para el proxy)
    "openclaw_proxy": "anthropic/claude-sonnet-4-6",
    # Google AI Studio
    "gemini_pro":        "gemini-2.5-pro",
    "gemini_flash":      "gemini-2.5-flash",
    "gemini_flash_lite": "gemini-2.5-flash-lite",
    # Google Vertex
    "gemini_vertex":     "gemini_vertex",  # alias preservado → Worker detecta vertex provider
}

# Tareas LLM que reciben inyección de modelo
LLM_TASK_PREFIXES = ("llm.", "composite.")

CALLBACK_TIMEOUT_SECONDS = 10.0
CALLBACK_RETRY_DELAY_SECONDS = 5

MAX_CONNECT_RETRIES = 3
DEFAULT_DISPATCHER_LOCK_PATH = "/tmp/umbral-dispatcher.lock"


class DispatcherInstanceError(RuntimeError):
    """Raised when another dispatcher process already owns the instance lock."""


def _read_lock_owner_pid(handle: Any) -> Optional[int]:
    handle.seek(0)
    raw_value = handle.read().strip()
    if not raw_value:
        return None
    try:
        return int(raw_value.splitlines()[0])
    except ValueError:
        return None


class DispatcherInstanceLock:
    """Best-effort cross-process lock so the VPS keeps only one dispatcher alive."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.handle: Any = None

    def acquire(self) -> tuple[bool, Optional[int]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                owner_pid = _read_lock_owner_pid(handle)
                handle.close()
                return False, owner_pid

        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        self.handle = handle
        return True, None

    def release(self) -> None:
        if self.handle is None:
            return

        try:
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.flush()
            if fcntl is not None:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def _acquire_dispatcher_instance_lock() -> DispatcherInstanceLock:
    lock_path = os.environ.get("DISPATCHER_LOCK_PATH", DEFAULT_DISPATCHER_LOCK_PATH)
    instance_lock = DispatcherInstanceLock(lock_path)
    acquired, owner_pid = instance_lock.acquire()
    if not acquired:
        owner_text = f" (pid {owner_pid})" if owner_pid else ""
        raise DispatcherInstanceError(
            f"Another dispatcher instance is already running{owner_text}. "
            f"Lock file: {lock_path}"
        )

    atexit.register(instance_lock.release)
    return instance_lock


def _post_webhook_callback(callback_url: str, payload: Dict[str, Any]) -> None:
    """
    POST callback with one retry for timeout/5xx failures.

    Fire-and-forget caller is responsible for running this in a daemon thread.
    """
    task_id = payload.get("task_id", "unknown")
    status = payload.get("status", "unknown")

    for attempt in (1, 2):
        try:
            with httpx.Client(timeout=CALLBACK_TIMEOUT_SECONDS) as client:
                resp = client.post(callback_url, json=payload)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Callback server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
            logger.info(
                "Callback delivered for task %s (status=%s) -> %s",
                task_id,
                status,
                callback_url,
            )
            return
        except httpx.TimeoutException as exc:
            if attempt == 1:
                logger.warning(
                    "Callback timeout for task %s -> %s (retrying in %ss): %s",
                    task_id,
                    callback_url,
                    CALLBACK_RETRY_DELAY_SECONDS,
                    exc,
                )
                time.sleep(CALLBACK_RETRY_DELAY_SECONDS)
                continue
            logger.warning(
                "Callback timeout for task %s after retry -> %s: %s",
                task_id,
                callback_url,
                exc,
            )
            return
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            if status_code >= 500 and attempt == 1:
                logger.warning(
                    "Callback 5xx for task %s -> %s (retrying in %ss): %s",
                    task_id,
                    callback_url,
                    CALLBACK_RETRY_DELAY_SECONDS,
                    status_code,
                )
                time.sleep(CALLBACK_RETRY_DELAY_SECONDS)
                continue
            logger.warning(
                "Callback failed for task %s -> %s: HTTP %s",
                task_id,
                callback_url,
                status_code,
            )
            return
        except Exception as exc:
            logger.warning(
                "Callback error for task %s -> %s: %s",
                task_id,
                callback_url,
                exc,
            )
            return


def _trigger_webhook_callback(
    envelope: Dict[str, Any],
    status: str,
    task: str,
    result: Any = None,
    error: str = "",
) -> None:
    """Schedule webhook callback delivery if callback_url exists in the envelope."""
    callback_url = str(envelope.get("callback_url", "")).strip()
    if not callback_url:
        return

    payload: Dict[str, Any] = {
        "task_id": envelope.get("task_id", ""),
        "status": status,
        "task": task,
        "result": result,
        "completed_at": int(time.time()),
    }
    if error:
        payload["error"] = error

    threading.Thread(
        target=_post_webhook_callback,
        args=(callback_url, payload),
        daemon=True,
    ).start()


def _notion_upsert(
    wc: WorkerClient,
    task_id: str,
    status: str,
    team: str,
    task: str,
    input_summary: str | None = None,
    error: str | None = None,
    result_summary: str | None = None,
    envelope: dict | None = None,
    selected_model: str | None = None,
) -> None:
    """Actualiza el Kanban de Notion. Fire-and-forget; no bloquea el flujo."""
    envelope = envelope or {}
    input_payload = dict(envelope.get("input", {}) if isinstance(envelope.get("input"), dict) else {})
    for key in (
        "project_name",
        "project_page_id",
        "deliverable_name",
        "deliverable_page_id",
        "notion_track",
        "source",
        "source_kind",
    ):
        if envelope.get(key) and key not in input_payload:
            input_payload[key] = envelope.get(key)
    is_project_scoped = any(
        str(input_payload.get(key, "")).strip()
        for key in ("project_name", "project_page_id", "deliverable_name", "deliverable_page_id")
    )
    explicit_track = bool(input_payload.get("notion_track") or envelope.get("notion_track"))
    if not (is_project_scoped or explicit_track):
        return
    try:
        wc.run(
            "notion.upsert_task",
            {
                "task_id": task_id,
                "status": status,
                "team": team,
                "task": task,
                "input_summary": input_summary,
                "error": error,
                "result_summary": result_summary,
                "project_name": input_payload.get("project_name"),
                "project_page_id": input_payload.get("project_page_id"),
                "deliverable_name": input_payload.get("deliverable_name"),
                "deliverable_page_id": input_payload.get("deliverable_page_id"),
                "source": input_payload.get("source"),
                "source_kind": input_payload.get("source_kind"),
                "trace_id": envelope.get("trace_id"),
                "selected_model": selected_model,
            },
        )
    except Exception as e:
        logger.debug("Notion upsert_task skipped or failed: %s", e)


def _notify_linear_completion(
    wc: "WorkerClient",
    envelope: dict,
    success: bool,
    result: Any = None,
    error: str = "",
) -> None:
    """
    Si el envelope tiene linear_issue_id, actualiza el issue en Linear
    con el estado final (Done / Cancelled) y un comentario con el resultado.
    Fire-and-forget; no bloquea el flujo.
    """
    issue_id = envelope.get("linear_issue_id")
    if not issue_id:
        return

    task = envelope.get("task", "unknown")
    state_name = "Done" if success else "Cancelled"
    emoji = "✅" if success else "❌"
    body_lines = [f"{emoji} **Tarea `{task}` {'completada' if success else 'fallida'}**"]

    if success and result is not None:
        summary = str(result)[:400] if not isinstance(result, dict) else str(result.get("result", result))[:400]
        body_lines += ["", f"**Resultado:**\n```\n{summary}\n```"]
    elif error:
        body_lines += ["", f"**Error:**\n```\n{error[:400]}\n```"]

    try:
        wc.run(
            "linear.update_issue_status",
            {
                "issue_id": issue_id,
                "state_name": state_name,
                "team_id": envelope.get("team", ""),
                "comment": "\n".join(body_lines),
            },
        )
    except Exception as e:
        logger.debug("Linear update_issue_status skipped or failed: %s", e)


logger = logging.getLogger("dispatcher.service")

ESCALATE_TO_LINEAR = os.environ.get("ESCALATE_FAILURES_TO_LINEAR", "false").lower() in ("true", "1", "yes")
ESCALATE_ONLY_CANONICAL = os.environ.get("ESCALATE_ONLY_CANONICAL", "true").lower() in ("true", "1", "yes")
ESCALATION_DEDUPE_WINDOW_HOURS = max(0, int(os.environ.get("ESCALATION_DEDUPE_WINDOW_HOURS", "24")))

_CANONICAL_ESCALATION_SOURCES = {
    "linear_webhook",
    "notion_poll",
    "notion_poller",
    "openclaw_gateway",
    "smart_reply",
    "workflow_engine",
}
_CANONICAL_ESCALATION_SOURCE_KINDS = {
    "instruction_comment",
    "linear_webhook",
    "tool_enqueue",
    "workflow_engine",
}
_NOISY_ESCALATION_SOURCES = {
    "daily_digest",
    "dashboard_report",
    "notion_curate_ops_vps",
    "ooda_report",
    "quota_guard",
    "sim_daily",
    "sim_report",
}
_NOISY_ESCALATION_SOURCE_KINDS = {
    "cron",
    "historical_backfill",
    "scheduled_report",
}


def _normalize_for_fingerprint(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _failure_error_class(error: str) -> str:
    normalized = _normalize_for_fingerprint(error)
    if not normalized:
        return "unknown_error"
    if "400" in normalized or "bad request" in normalized:
        return "http_400"
    if "429" in normalized or "rate limit" in normalized or "quota" in normalized:
        return "quota_or_rate_limit"
    if "401" in normalized or "unauthorized" in normalized:
        return "http_401"
    if "403" in normalized or "forbidden" in normalized:
        return "http_403"
    if "404" in normalized or "not found" in normalized:
        return "http_404"
    if "500" in normalized or "internal server error" in normalized:
        return "http_500"
    if "timeout" in normalized or "timed out" in normalized:
        return "timeout"
    if (
        "connecterror" in normalized
        or "connection refused" in normalized
        or "connection error" in normalized
    ):
        return "connect_error"
    return normalized.split(":", 1)[0].replace(" ", "_")[:80] or "unknown_error"


def _failure_followup_fingerprint(
    task: str,
    team: str,
    task_type: str,
    source: str,
    source_kind: str,
    worker_endpoint: str,
    error_class: str,
) -> str:
    parts = [
        task,
        team,
        task_type,
        source,
        source_kind,
        worker_endpoint,
        error_class,
    ]
    digest = hashlib.sha1(
        "|".join(_normalize_for_fingerprint(part) for part in parts).encode("utf-8")
    ).hexdigest()
    return digest[:16]


def _should_escalate_failure(envelope: dict) -> bool:
    source = str(envelope.get("source") or "").strip().lower()
    source_kind = str(envelope.get("source_kind") or "").strip().lower()

    if not ESCALATE_ONLY_CANONICAL:
        return True
    if source in _NOISY_ESCALATION_SOURCES or source_kind in _NOISY_ESCALATION_SOURCE_KINDS:
        return False
    if source in _CANONICAL_ESCALATION_SOURCES:
        return True
    if source_kind in _CANONICAL_ESCALATION_SOURCE_KINDS:
        return True
    return False



def _escalate_failure_to_linear(
    wc: "WorkerClient",
    envelope: dict,
    task_id: str,
    task: str,
    team: str,
    error: str,
) -> None:
    """
    Publish a canonical Agent Stack follow-up when a task fails.

    Skips duplicate, recursive, and non-canonical failures so Linear only
    receives follow-ups from the main Dispatcher -> Redis -> Worker flow.
    """
    if not ESCALATE_TO_LINEAR:
        return
    if envelope.get("linear_issue_id"):
        return
    if task.startswith("linear."):
        return
    if not _should_escalate_failure(envelope):
        logger.info(
            "[escalation] Skipping non-canonical failure for task %s (source=%s, source_kind=%s)",
            task_id,
            envelope.get("source", ""),
            envelope.get("source_kind", ""),
        )
        return

    priority_map = {"critical": 1, "coding": 2, "ms_stack": 2, "general": 3, "writing": 3, "research": 3, "light": 4}
    task_type = envelope.get("task_type", "general")
    priority = priority_map.get(task_type, 3)
    trace_id = str(envelope.get("trace_id") or "").strip()
    source = str(envelope.get("source") or "").strip() or "unspecified"
    source_kind = str(envelope.get("source_kind") or "").strip() or "unspecified"
    input_payload = envelope.get("input", {}) if isinstance(envelope.get("input"), dict) else {}
    selected_model = str(
        envelope.get("selected_model")
        or input_payload.get("selected_model")
        or "unspecified"
    ).strip() or "unspecified"
    retry_count = int(envelope.get("retry_count") or 0)
    worker_endpoint = str(getattr(wc, "base_url", "") or "unknown").strip() or "unknown"
    error_class = _failure_error_class(error)
    representative_error = str(error or "")[:500]
    fingerprint = _failure_followup_fingerprint(
        task,
        team,
        str(task_type),
        source,
        source_kind,
        worker_endpoint,
        error_class,
    )
    dedupe_comment = (
        "Nueva ocurrencia automatica del mismo fallo.\n\n"
        f"Fingerprint: `{fingerprint}`\n"
        f"- task_id={task_id}\n"
        f"- trace_id={trace_id or 'n/a'}\n"
        f"- team={team}\n"
        f"- task_type={task_type}\n"
        f"- source={source}\n"
        f"- source_kind={source_kind}\n"
        f"- worker_endpoint={worker_endpoint}\n"
        f"- selected_model={selected_model}\n"
        f"- retry_count={retry_count}\n"
        f"- error_class={error_class}\n\n"
        f"Error representativo:\n```text\n{representative_error}\n```"
    )

    try:
        resp = wc.run(
            "linear.publish_agent_stack_followup",
            {
                "title": f"Task fallida: {task} [{team}/{task_type}]",
                "summary": (
                    f"La tarea {task} fallo durante ejecucion automatica del Agent Stack "
                    f"para el team {team} con clase de error {error_class}."
                ),
                "evidence": (
                    f"task_id={task_id}\n"
                    f"trace_id={trace_id or 'n/a'}\n"
                    f"team={team}\n"
                    f"task_type={task_type}\n"
                    f"source={source}\n"
                    f"source_kind={source_kind}\n"
                    f"worker_endpoint={worker_endpoint}\n"
                    f"selected_model={selected_model}\n"
                    f"retry_count={retry_count}\n"
                    f"error_class={error_class}\n"
                    f"error={representative_error}"
                ),
                "impact": "El flujo canonico Dispatcher -> Redis -> Worker no pudo completar la tarea y requiere follow-up tecnico.",
                "next_action": "Revisar logs, reproducir el fallo y corregir el handler o la dependencia que rompio la ejecucion.",
                "source_ref": f"{source} / {source_kind}",
                "requested_by": "Dispatcher",
                "kind": "operational_debt",
                "priority": priority,
                "auto_generated": True,
                "dedupe_key": fingerprint,
                "dedupe_window_hours": ESCALATION_DEDUPE_WINDOW_HOURS,
                "dedupe_comment": dedupe_comment,
                "task_id": task_id,
                "trace_id": trace_id,
                "team_name": team,
                "task_type_name": task_type,
                "source": source,
                "source_kind": source_kind,
                "worker_endpoint": worker_endpoint,
                "selected_model": selected_model,
                "retry_count": retry_count,
                "error_class": error_class,
                "representative_error": representative_error,
            },
        )
        issue_id = None
        result = (resp or {}).get("result", {})
        if isinstance(result, dict):
            issue = result.get("issue", {})
            if isinstance(issue, dict):
                issue_id = issue.get("id")
            if not issue_id:
                issue_id = result.get("id") or result.get("issue_id")
        if issue_id:
            envelope["linear_issue_id"] = issue_id
        logger.info("[escalation] Linear issue created for failed task %s (issue=%s)", task_id, issue_id)
    except Exception as exc:
        logger.debug("[escalation] Could not create Linear issue: %s", exc)


DEFAULT_WORKERS = 2


def _run_worker(
    pool: redis.ConnectionPool,
    worker_url: str,
    worker_token: str,
    worker_url_vm: Optional[str],
    hm: HealthMonitor,
    model_router: ModelRouter,
    alert_manager: Optional[AlertManager],
    worker_id: int,
    worker_url_vm_gui: Optional[str] = None,
) -> None:
    """Worker thread: local WorkerClient siempre; VM WorkerClient solo si WORKER_URL_VM está definido."""
    r = redis.Redis(connection_pool=pool, decode_responses=True)
    queue = TaskQueue(r)
    # Timeout 120s: composite tasks (composite.research_report) do multiple
    # sequential API calls (LLM + research) that reliably take 30-60s.
    # The default 30s caused 100% failure rate on those tasks.
    wc_local = WorkerClient(base_url=worker_url, token=worker_token, timeout=120.0)
    wc_vm = WorkerClient(base_url=worker_url_vm, token=worker_token, timeout=120.0) if worker_url_vm else None
    # GUI tasks (interactive automation) use a separate port on the VM (default 8089)
    wc_vm_gui = WorkerClient(base_url=worker_url_vm_gui, token=worker_token, timeout=120.0) if worker_url_vm_gui else wc_vm
    capabilities = get_team_capabilities()

    while True:
        if alert_manager:
            try:
                pending_count = queue.pending_count()
                if pending_count > 50:
                    threading.Thread(
                        target=alert_manager.alert_queue_overflow,
                        args=(pending_count, 50),
                        daemon=True,
                    ).start()
            except Exception as e:
                logger.debug("Queue overflow alert check skipped: %s", e)

        envelope = queue.dequeue(timeout=2)
        if not envelope:
            continue

        task_id = envelope["task_id"]
        team = envelope.get("team", "system")
        task = envelope.get("task", "unknown")
        task_type = envelope.get("task_type", "general")
        trace_id = envelope.get("trace_id", "")
        source = envelope.get("source", "")
        source_kind = envelope.get("source_kind", "")
        input_data = dict(envelope.get("input", {}))
        ops_context: Dict[str, str] = {"trace_id": trace_id, "task_type": task_type}
        if source:
            ops_context["source"] = source
        if source_kind:
            ops_context["source_kind"] = source_kind
        queued_ops_context = {k: v for k, v in ops_context.items() if k != "task_type"}

        # S4: selección de modelo por task_type y cuotas
        is_llm_task = any(task.startswith(p) for p in LLM_TASK_PREFIXES)
        decision = model_router.select_model(task_type)
        if is_llm_task and decision.reason == "no_configured_provider":
            reason = "no_configured_provider"
            logger.warning(
                "[worker %d] Task %s blocked: %s (task_type=%s)",
                worker_id, task_id, reason, task_type,
            )
            ops_log.task_blocked(task_id, task, team, reason, **ops_context)
            threading.Thread(
                target=_notion_upsert,
                args=(wc_local, task_id, "blocked", team, task),
                kwargs={"error": reason, "envelope": envelope},
                daemon=True,
            ).start()
            queue.block_task(task_id, reason)
            continue
        if decision.requires_approval and is_llm_task:
            reason = "quota_exceeded_approval_required"
            logger.warning("[worker %d] Task %s blocked: %s (model=%s)", worker_id, task_id, reason, decision.model)
            ops_log.task_blocked(task_id, task, team, reason, **ops_context)
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "blocked", team, task), kwargs={"error": reason, "envelope": envelope}, daemon=True).start()
            queue.block_task(task_id, reason)
            continue
        selected_model = decision.model
        ops_log.model_selected(task_id, task_type, selected_model, decision.reason if hasattr(decision, "reason") else "", trace_id=trace_id)

        # Solo inyectar modelo concreto para tareas LLM
        if is_llm_task:
            model_string = PROVIDER_MODEL_MAP.get(selected_model, selected_model)
            input_data["model"] = model_string
        input_data["selected_model"] = selected_model

        team_info = capabilities.get(team)
        requires_vm = task_requires_vm(bool(team_info and team_info.get("requires_vm", False)), task)
        use_vm = requires_vm and hm.vm_online and wc_vm is not None

        if requires_vm and not hm.vm_online and wc_vm is not None:
            reason = f"VM offline; task {task_id} (team={team}) requires VM."
            logger.warning("[worker %d] %s", worker_id, reason)
            ops_log.task_blocked(task_id, task, team, reason, **ops_context)
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "blocked", team, task), kwargs={"error": reason[:500], "envelope": envelope}, daemon=True).start()
            queue.block_task(task_id, reason)
            continue

        target = "VM" if use_vm else "VPS"
        logger.info(
            "[worker %d] Executing task %s (task=%s, team=%s, model=%s) -> %s",
            worker_id, task_id, task, team, selected_model, target,
        )

        if use_vm and task.startswith("gui."):
            wc = wc_vm_gui if wc_vm_gui else wc_vm
        elif use_vm:
            wc = wc_vm
        else:
            wc = wc_local
        threading.Thread(
            target=_notion_upsert,
            args=(wc_local, task_id, "running", team, task),
            kwargs={"input_summary": str(input_data)[:300], "envelope": envelope, "selected_model": selected_model},
            daemon=True,
        ).start()
        t_start = time.time()
        try:
            result = wc.run(task, input_data, envelope=envelope)
            duration_ms = (time.time() - t_start) * 1000
            queue.complete_task(task_id, result)
            model_router.quota.record_usage(selected_model)
            _input_summary = str(envelope.get("input", {}))[:200]
            ops_log.task_completed(
                task_id,
                task,
                team,
                selected_model,
                duration_ms,
                worker=target.lower(),
                input_summary=_input_summary,
                **ops_context,
            )
            _result_summary = str(result.get("result", result))[:300] if isinstance(result, dict) else str(result)[:300]
            threading.Thread(
                target=_notion_upsert,
                args=(wc_local, task_id, "done", team, task),
                kwargs={"result_summary": _result_summary, "envelope": envelope, "selected_model": selected_model},
                daemon=True,
            ).start()
            threading.Thread(target=_notify_linear_completion, args=(wc_local, envelope, True), kwargs={"result": result}, daemon=True).start()
            _trigger_webhook_callback(envelope, status="done", task=task, result=result)
            logger.info("[worker %d] Task %s completed via %s Worker (model=%s)", worker_id, task_id, target, selected_model)
        except Exception as e:
            duration_ms = (time.time() - t_start) * 1000
            is_timeout = isinstance(e, (httpx.ReadTimeout, httpx.WriteTimeout))
            is_connect_error = isinstance(e, httpx.ConnectError)
            retry_count = envelope.get("retry_count", 0)

            if is_timeout and retry_count < 2:
                # Re-enqueue with incremented retry_count
                envelope["retry_count"] = retry_count + 1
                envelope["status"] = "queued"
                queue.enqueue(envelope)
                ops_log.task_queued(task_id, task, team, task_type, **queued_ops_context)
                ops_log.task_retried(task_id, task, team, envelope["retry_count"], **ops_context)
                logger.warning(
                    "[worker %d] Task %s timed out, retry %d/2",
                    worker_id, task_id, envelope["retry_count"],
                )
                continue

            if is_connect_error:
                if retry_count < MAX_CONNECT_RETRIES:
                    envelope["retry_count"] = retry_count + 1
                    envelope["status"] = "queued"
                    queue.enqueue(envelope)
                    ops_log.task_queued(task_id, task, team, task_type, **queued_ops_context)
                    ops_log.task_retried(task_id, task, team, envelope["retry_count"], **ops_context)
                    logger.warning(
                        "[worker %d] %s Worker unreachable for task %s, retry %d/%d. Backing off 30s.",
                        worker_id, target, task_id, envelope["retry_count"], MAX_CONNECT_RETRIES,
                    )
                    if alert_manager:
                        worker_ref = worker_url_vm if (use_vm and worker_url_vm) else worker_url
                        threading.Thread(
                            target=alert_manager.alert_worker_down,
                            args=(worker_ref, str(e)),
                            daemon=True,
                        ).start()
                    time.sleep(30)
                    continue
                else:
                    logger.error(
                        "[worker %d] %s Worker unreachable after %d retries for task %s. Failing.",
                        worker_id, target, MAX_CONNECT_RETRIES, task_id,
                    )

            _input_summary = str(envelope.get("input", {}))[:200]
            classification = classify_error(e)
            ops_log.task_failed(
                task_id,
                task,
                team,
                str(e),
                model=selected_model,
                error_kind=classification.error_kind,
                error_code=classification.error_code,
                retryable=classification.retryable,
                input_summary=_input_summary,
                **ops_context,
            )
            threading.Thread(
                target=_notion_upsert,
                args=(wc_local, task_id, "failed", team, task),
                kwargs={"error": str(e)[:500], "envelope": envelope, "selected_model": selected_model},
                daemon=True,
            ).start()
            threading.Thread(target=_notify_linear_completion, args=(wc_local, envelope, False), kwargs={"error": str(e)}, daemon=True).start()
            threading.Thread(
                target=_escalate_failure_to_linear,
                args=(wc_local, envelope, task_id, task, team, str(e)),
                daemon=True,
            ).start()
            logger.error("[worker %d] Task %s failed: %s", worker_id, task_id, str(e))
            queue.fail_task(task_id, str(e))
            _trigger_webhook_callback(envelope, status="failed", task=task, error=str(e))
            if alert_manager:
                threading.Thread(
                    target=alert_manager.alert_task_failed,
                    args=(task_id, task, team, str(e), envelope),
                    daemon=True,
                ).start()


def main():
    try:
        instance_lock = _acquire_dispatcher_instance_lock()
    except DispatcherInstanceError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_url = os.environ.get("WORKER_URL", "http://127.0.0.1:8088")
    worker_url_vm = os.environ.get("WORKER_URL_VM", "").strip() or None
    # GUI tasks on the VM use an interactive worker on port 8089 by default
    _default_vm_gui = worker_url_vm.replace(":8088", ":8089") if worker_url_vm else None
    worker_url_vm_gui = os.environ.get("WORKER_URL_VM_GUI", "").strip() or _default_vm_gui
    worker_token = os.environ.get("WORKER_TOKEN", "")
    num_workers = int(os.environ.get("DISPATCHER_WORKERS", str(DEFAULT_WORKERS)))

    if not worker_token:
        logger.error("WORKER_TOKEN not set! Set environment variable WORKER_TOKEN.")
        sys.exit(1)

    pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)
    r = redis.Redis(connection_pool=pool)
    queue = TaskQueue(r)
    hm: Optional[HealthMonitor] = None

    # HealthMonitor vigila la VM (si hay WORKER_URL_VM); si no hay VM, vm_online queda False
    hm_url = worker_url_vm if worker_url_vm else "http://127.0.0.1:1"
    hm = HealthMonitor(
        worker_url=hm_url,
        worker_token=worker_token,
        check_interval=10,
        failure_threshold=2,
    )
    router = TeamRouter(queue=queue, health=hm)
    hm.on_vm_back = router.on_vm_back
    hm.start()

    # S4: ModelRouter + QuotaTracker (cuotas en Redis)
    _, provider_config = load_quota_policy()
    quota_tracker = QuotaTracker(r, provider_config)
    model_router = ModelRouter(quota_tracker)
    alert_wc = WorkerClient(base_url=worker_url, token=worker_token)
    alert_manager = AlertManager(
        worker_client=alert_wc,
        control_room_page_id=os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID"),
        cooldown_seconds=300,
    )

    logger.info(
        "Dispatcher started. %d worker(s), queue '%s'. Local=%s VM=%s VM_GUI=%s",
        num_workers,
        queue.QUEUE_PENDING,
        worker_url,
        worker_url_vm or "—",
        worker_url_vm_gui or "—",
    )

    threads = []
    for i in range(num_workers):
        t = threading.Thread(
            target=_run_worker,
            args=(pool, worker_url, worker_token, worker_url_vm, hm, model_router, alert_manager, i + 1),
            kwargs={"worker_url_vm_gui": worker_url_vm_gui},
            daemon=True,
        )
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("Shutting down Dispatcher Service gracefully...")
    finally:
        if hm is not None:
            hm.stop()
        instance_lock.release()


if __name__ == "__main__":
    main()
