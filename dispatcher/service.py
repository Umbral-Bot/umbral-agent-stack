"""
Dispatcher Service Loop.

VPS autosuficiente: Worker local (WORKER_URL) siempre; VM opcional (WORKER_URL_VM).
- Sin VM o VM caída: todas las tareas van al Worker local (VPS).
- Con VM online: tareas con requires_vm=True van a la VM; el resto al Worker local.
"""

import logging
import os
import sys
import threading
import time
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
from infra.ops_logger import ops_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# S4: Mapeo de provider name (quota alias) → model string que entiende el Worker.
PROVIDER_MODEL_MAP: Dict[str, str] = {
    # OpenAI / Codex — Worker solo accede GPT vía Azure Foundry
    "azure_foundry": "gpt-5.2-chat",
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
) -> None:
    """Actualiza el Kanban de Notion. Fire-and-forget; no bloquea el flujo."""
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

ESCALATE_TO_LINEAR = os.environ.get("ESCALATE_FAILURES_TO_LINEAR", "true").lower() in ("true", "1", "yes")


def _escalate_failure_to_linear(
    wc: "WorkerClient",
    envelope: dict,
    task_id: str,
    task: str,
    team: str,
    error: str,
) -> None:
    """
    Create a Linear issue when a task fails, unless the envelope already
    has a linear_issue_id (avoid duplicate issues for the same task).
    Stores the created issue_id back in envelope for follow-up notifications.
    Controlled by ESCALATE_FAILURES_TO_LINEAR env var (default: true).
    """
    if not ESCALATE_TO_LINEAR:
        return
    if envelope.get("linear_issue_id"):
        return
    if task.startswith("linear."):
        return

    capabilities = get_team_capabilities()
    team_info = capabilities.get(team, {})
    linear_team_key = team_info.get("linear_team_key", "UMBRAL")

    priority_map = {"critical": 1, "coding": 2, "ms_stack": 2, "general": 3, "writing": 3, "research": 3, "light": 4}
    task_type = envelope.get("task_type", "general")
    priority = priority_map.get(task_type, 3)

    title = f"[Auto] Tarea fallida: {task} ({task_id[:8]})"
    description = (
        f"**Task:** `{task}`\n"
        f"**Task ID:** `{task_id}`\n"
        f"**Team:** {team}\n"
        f"**Task Type:** {task_type}\n\n"
        f"**Error:**\n```\n{error[:500]}\n```\n\n"
        f"_Issue creado automáticamente por el Dispatcher al detectar fallo._"
    )

    try:
        resp = wc.run("linear.create_issue", {
            "title": title,
            "description": description,
            "team_key": linear_team_key,
            "priority": priority,
        })
        # Store issue_id for follow-up status updates on retry success
        issue_id = (resp or {}).get("result", {})
        if isinstance(issue_id, dict):
            issue_id = issue_id.get("id") or issue_id.get("issue_id")
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
    wc_local = WorkerClient(base_url=worker_url, token=worker_token)
    wc_vm = WorkerClient(base_url=worker_url_vm, token=worker_token) if worker_url_vm else None
    # GUI tasks (interactive automation) use a separate port on the VM (default 8089)
    wc_vm_gui = WorkerClient(base_url=worker_url_vm_gui, token=worker_token) if worker_url_vm_gui else wc_vm
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
        input_data = dict(envelope.get("input", {}))

        # S4: selección de modelo por task_type y cuotas
        is_llm_task = any(task.startswith(p) for p in LLM_TASK_PREFIXES)
        decision = model_router.select_model(task_type)
        if decision.requires_approval and is_llm_task:
            reason = "quota_exceeded_approval_required"
            logger.warning("[worker %d] Task %s blocked: %s (model=%s)", worker_id, task_id, reason, decision.model)
            ops_log.task_blocked(task_id, task, team, reason, trace_id=trace_id)
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "blocked", team, task), kwargs={"error": reason}, daemon=True).start()
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
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "blocked", team, task), kwargs={"error": reason[:500]}, daemon=True).start()
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
        threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "running", team, task), kwargs={"input_summary": str(input_data)[:300]}, daemon=True).start()
        t_start = time.time()
        try:
            result = wc.run(task, input_data, envelope=envelope)
            duration_ms = (time.time() - t_start) * 1000
            queue.complete_task(task_id, result)
            model_router.quota.record_usage(selected_model)
            _input_summary = str(envelope.get("input", {}))[:200]
            ops_log.task_completed(task_id, task, team, selected_model, duration_ms, worker=target.lower(), trace_id=trace_id, input_summary=_input_summary)
            _result_summary = str(result.get("result", result))[:300] if isinstance(result, dict) else str(result)[:300]
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "done", team, task), kwargs={"result_summary": _result_summary}, daemon=True).start()
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
                ops_log.task_queued(task_id, task, team, task_type, trace_id=trace_id)
                ops_log.task_retried(task_id, task, team, envelope["retry_count"], trace_id=trace_id)
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
                    ops_log.task_queued(task_id, task, team, task_type, trace_id=trace_id)
                    ops_log.task_retried(task_id, task, team, envelope["retry_count"], trace_id=trace_id)
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
            ops_log.task_failed(task_id, task, team, str(e), model=selected_model, trace_id=trace_id, input_summary=_input_summary)
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "failed", team, task), kwargs={"error": str(e)[:500]}, daemon=True).start()
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
        hm.stop()


if __name__ == "__main__":
    main()
