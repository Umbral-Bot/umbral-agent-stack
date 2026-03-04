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
from dispatcher.model_router import ModelRouter, load_quota_policy
from dispatcher.queue import TaskQueue
from dispatcher.quota_tracker import QuotaTracker
from dispatcher.router import TeamRouter
from dispatcher.team_config import get_team_capabilities
from client.worker_client import WorkerClient
from infra.ops_logger import ops_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


CALLBACK_TIMEOUT_SECONDS = 10.0
CALLBACK_RETRY_DELAY_SECONDS = 5


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
                "comment": "\n".join(body_lines),
            },
        )
    except Exception as e:
        logger.debug("Linear update_issue_status skipped or failed: %s", e)


logger = logging.getLogger("dispatcher.service")

DEFAULT_WORKERS = 2


def _run_worker(
    pool: redis.ConnectionPool,
    worker_url: str,
    worker_token: str,
    worker_url_vm: Optional[str],
    hm: HealthMonitor,
    model_router: ModelRouter,
    worker_id: int,
) -> None:
    """Worker thread: local WorkerClient siempre; VM WorkerClient solo si WORKER_URL_VM está definido."""
    r = redis.Redis(connection_pool=pool, decode_responses=True)
    queue = TaskQueue(r)
    wc_local = WorkerClient(base_url=worker_url, token=worker_token)
    wc_vm = WorkerClient(base_url=worker_url_vm, token=worker_token) if worker_url_vm else None
    capabilities = get_team_capabilities()

    while True:
        envelope = queue.dequeue(timeout=2)
        if not envelope:
            continue

        task_id = envelope["task_id"]
        team = envelope.get("team", "system")
        task = envelope.get("task", "unknown")
        task_type = envelope.get("task_type", "general")
        input_data = dict(envelope.get("input", {}))

        # S4: selección de modelo por task_type y cuotas
        decision = model_router.select_model(task_type)
        if decision.requires_approval:
            reason = "quota_exceeded_approval_required"
            logger.warning("[worker %d] Task %s blocked: %s (model=%s)", worker_id, task_id, reason, decision.model)
            ops_log.task_blocked(task_id, task, team, reason)
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "blocked", team, task), kwargs={"error": reason}, daemon=True).start()
            queue.block_task(task_id, reason)
            continue
        selected_model = decision.model
        ops_log.model_selected(task_id, task_type, selected_model, decision.reason if hasattr(decision, "reason") else "")
        input_data["selected_model"] = selected_model

        team_info = capabilities.get(team)
        requires_vm = team_info and team_info.get("requires_vm", False)
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

        wc = wc_vm if use_vm else wc_local
        threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "running", team, task), kwargs={"input_summary": str(input_data)[:300]}, daemon=True).start()
        t_start = time.time()
        try:
            result = wc.run(task, input_data)
            duration_ms = (time.time() - t_start) * 1000
            queue.complete_task(task_id, result)
            model_router.quota.record_usage(selected_model)
            ops_log.task_completed(task_id, task, team, selected_model, duration_ms, worker=target.lower())
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
                ops_log.task_retried(task_id, task, team, envelope["retry_count"])
                logger.warning(
                    "[worker %d] Task %s timed out, retry %d/2",
                    worker_id, task_id, envelope["retry_count"],
                )
                continue

            if is_connect_error:
                # Worker is down — log once and back off to avoid log spam
                logger.error(
                    "[worker %d] %s Worker connection refused for task %s. Backing off 5s.",
                    worker_id, target, task_id,
                )

            ops_log.task_failed(task_id, task, team, str(e), model=selected_model)
            threading.Thread(target=_notion_upsert, args=(wc_local, task_id, "failed", team, task), kwargs={"error": str(e)[:500]}, daemon=True).start()
            threading.Thread(target=_notify_linear_completion, args=(wc_local, envelope, False), kwargs={"error": str(e)}, daemon=True).start()
            logger.error("[worker %d] Task %s failed: %s", worker_id, task_id, str(e))
            queue.fail_task(task_id, str(e))
            _trigger_webhook_callback(envelope, status="failed", task=task, error=str(e))

            if is_connect_error:
                time.sleep(5)


def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_url = os.environ.get("WORKER_URL", "http://127.0.0.1:8088")
    worker_url_vm = os.environ.get("WORKER_URL_VM", "").strip() or None
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

    logger.info(
        "Dispatcher started. %d worker(s), queue '%s'. Local=%s VM=%s",
        num_workers,
        queue.QUEUE_PENDING,
        worker_url,
        worker_url_vm or "—",
    )

    threads = []
    for i in range(num_workers):
        t = threading.Thread(
            target=_run_worker,
            args=(pool, worker_url, worker_token, worker_url_vm, hm, model_router, i + 1),
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
