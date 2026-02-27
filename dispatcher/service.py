"""
Dispatcher Service Loop.

Polls the Redis TaskQueue with N worker threads (delegación paralela, S3).
Interacts with the execution VM through WorkerClient.
Blocks un-executable tasks when VM is down (managed by HealthMonitor).
"""

import logging
import os
import sys
import threading
import time
from typing import Any, Dict

import redis

from dispatcher.health import HealthMonitor
from dispatcher.queue import TaskQueue
from dispatcher.router import TeamRouter
from dispatcher.team_config import get_team_capabilities
from client.worker_client import WorkerClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("dispatcher.service")

DEFAULT_WORKERS = 2


def _run_worker(
    pool: redis.ConnectionPool,
    worker_url: str,
    worker_token: str,
    hm: HealthMonitor,
    worker_id: int,
) -> None:
    """One worker thread: own Redis connection from pool, own WorkerClient, same health monitor."""
    r = redis.Redis(connection_pool=pool, decode_responses=True)
    queue = TaskQueue(r)
    wc = WorkerClient(base_url=worker_url, token=worker_token)
    capabilities = get_team_capabilities()

    while True:
        envelope = queue.dequeue(timeout=2)
        if not envelope:
            continue

        task_id = envelope["task_id"]
        team = envelope.get("team", "system")
        task = envelope.get("task", "unknown")
        input_data = envelope.get("input", {})

        logger.info("[worker %d] Executing task %s (task=%s, team=%s)", worker_id, task_id, task, team)

        team_info = capabilities.get(team)
        if team_info and team_info.get("requires_vm") and not hm.vm_online:
            reason = f"VM went offline while task {task_id} was waiting in queue."
            logger.warning("[worker %d] %s", worker_id, reason)
            queue.block_task(task_id, reason)
            continue

        if not team_info or team_info.get("requires_vm", True):
            try:
                result = wc.run(task, input_data)
                queue.complete_task(task_id, result)
                logger.info("[worker %d] Task %s completed via VM Worker", worker_id, task_id)
            except Exception as e:
                logger.error("[worker %d] Task %s failed: %s", worker_id, task_id, str(e))
                queue.fail_task(task_id, str(e))
        else:
            time.sleep(1)
            queue.complete_task(task_id, {"status": "ok", "mock": "llm_only_vps"})
            logger.info("[worker %d] Task %s completed via VPS Mock", worker_id, task_id)


def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_url = os.environ.get("WORKER_URL", "http://localhost:8088")
    worker_token = os.environ.get("WORKER_TOKEN", "")
    num_workers = int(os.environ.get("DISPATCHER_WORKERS", str(DEFAULT_WORKERS)))

    if not worker_token:
        logger.error("WORKER_TOKEN not set! Set environment variable WORKER_TOKEN.")
        sys.exit(1)

    pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)
    r = redis.Redis(connection_pool=pool)
    queue = TaskQueue(r)

    hm = HealthMonitor(
        worker_url=worker_url,
        worker_token=worker_token,
        check_interval=10,
        failure_threshold=2,
    )
    router = TeamRouter(queue=queue, health=hm)
    hm.on_vm_back = router.on_vm_back
    hm.start()

    logger.info(
        "Dispatcher Service started. %d worker(s), queue '%s'.",
        num_workers,
        queue.QUEUE_PENDING,
    )

    threads = []
    for i in range(num_workers):
        t = threading.Thread(
            target=_run_worker,
            args=(pool, worker_url, worker_token, hm, i + 1),
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
