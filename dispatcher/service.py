"""
Dispatcher Service Loop.

Continuously polls the Redis TaskQueue.
Interacts with the execution VM through WorkerClient.
Blocks un-executable tasks when VM is down (managed by HealthMonitor).
"""

import logging
import os
import sys
import time
from typing import Any, Dict

import redis

from dispatcher.health import HealthMonitor
from dispatcher.queue import TaskQueue
from dispatcher.router import TeamRouter
from client.worker_client import WorkerClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("dispatcher.service")

def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_url = os.environ.get("WORKER_URL", "http://localhost:8088")
    worker_token = os.environ.get("WORKER_TOKEN", "")

    if not worker_token:
        logger.error("WORKER_TOKEN not set! Set environment variable WORKER_TOKEN.")
        sys.exit(1)

    r = redis.from_url(redis_url, decode_responses=True)
    queue = TaskQueue(r)
    
    # Initialize health monitor 
    hm = HealthMonitor(
        worker_url=worker_url, 
        worker_token=worker_token, 
        check_interval=10, 
        failure_threshold=2
    )
    
    router = TeamRouter(queue=queue, health=hm)
    
    # Callback to automatically unblock tasks when VM returns
    hm.on_vm_back = router.on_vm_back
    
    # Start background health monitoring
    hm.start()
    
    # Initialize connection to the Worker API
    wc = WorkerClient(base_url=worker_url, token=worker_token)

    logger.info("Dispatcher Service started. Polling Redis queue '%s'...", queue.QUEUE_PENDING)

    try:
        while True:
            # Poll tasks with 2s timeout to remain responsive
            envelope = queue.dequeue(timeout=2)
            if not envelope:
                continue
                
            task_id = envelope["task_id"]
            team = envelope.get("team", "system")
            task = envelope.get("task", "unknown")
            input_data = envelope.get("input", {})
            
            logger.info("Executing task %s (task=%s, team=%s)", task_id, task, team)
            
            # Re-evaluate routing since VM state might have changed since enqueued
            team_info = router.get_team_info(team)
            if team_info and team_info["requires_vm"] and not hm.vm_online:
                reason = f"VM went offline while task {task_id} was waiting in queue."
                logger.warning(reason)
                # Re-block the task
                queue.block_task(task_id, reason)
                continue
                
            # If team requires VM or is unknown (fail safe locally to VM), send to WorkerClient
            if not team_info or team_info.get("requires_vm", True):
                try:
                    logger.info("Sending task %s to VM Worker...", task_id)
                    result = wc.run(task, input_data)
                    queue.complete_task(task_id, result)
                    logger.info("Task %s completed successfully via VM Worker", task_id)
                except Exception as e:
                    logger.error("Task %s failed during VM execution: %s", task_id, str(e))
                    queue.fail_task(task_id, str(e))
            else:
                # TODO: LLM-only execution on VPS
                logger.info("Task %s executing locally (LLM-only VPS mock)...", task_id)
                time.sleep(1)
                queue.complete_task(task_id, {"status": "ok", "mock": "llm_only_vps"})
                logger.info("Task %s completed successfully via VPS Mock", task_id)
                
    except KeyboardInterrupt:
        logger.info("Shutting down Dispatcher Service gracefully...")
    finally:
        hm.stop()

if __name__ == "__main__":
    main()
