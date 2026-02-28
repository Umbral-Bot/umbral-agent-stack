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

import redis

from dispatcher.health import HealthMonitor
from dispatcher.model_router import ModelRouter, load_quota_policy
from dispatcher.queue import TaskQueue
from dispatcher.quota_tracker import QuotaTracker
from dispatcher.router import TeamRouter
from dispatcher.team_config import get_team_capabilities
from client.worker_client import WorkerClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


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
            _notion_upsert(wc_local, task_id, "blocked", team, task, error=reason)
            queue.block_task(task_id, reason)
            continue
        selected_model = decision.model
        input_data["selected_model"] = selected_model

        team_info = capabilities.get(team)
        requires_vm = team_info and team_info.get("requires_vm", False)
        use_vm = requires_vm and hm.vm_online and wc_vm is not None

        if requires_vm and not hm.vm_online and wc_vm is not None:
            reason = f"VM offline; task {task_id} (team={team}) requires VM."
            logger.warning("[worker %d] %s", worker_id, reason)
            _notion_upsert(wc_local, task_id, "blocked", team, task, error=reason[:500])
            queue.block_task(task_id, reason)
            continue

        target = "VM" if use_vm else "VPS"
        logger.info(
            "[worker %d] Executing task %s (task=%s, team=%s, model=%s) -> %s",
            worker_id, task_id, task, team, selected_model, target,
        )

        wc = wc_vm if use_vm else wc_local
        _notion_upsert(wc_local, task_id, "running", team, task, input_summary=str(input_data)[:300])
        try:
            result = wc.run(task, input_data)
            queue.complete_task(task_id, result)
            model_router.quota.record_usage(selected_model)
            _notion_upsert(
                wc_local, task_id, "done", team, task,
                result_summary=str(result.get("result", result))[:300] if isinstance(result, dict) else str(result)[:300],
            )
            logger.info("[worker %d] Task %s completed via %s Worker (model=%s)", worker_id, task_id, target, selected_model)
        except Exception as e:
            _notion_upsert(wc_local, task_id, "failed", team, task, error=str(e)[:500])
            logger.error("[worker %d] Task %s failed: %s", worker_id, task_id, str(e))
            queue.fail_task(task_id, str(e))


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
