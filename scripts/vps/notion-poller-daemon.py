#!/usr/bin/env python3
"""
Notion Poller Daemon — runs the poller every 60s on the VPS.

Writes PID to /tmp/notion_poller.pid, logs to /tmp/notion_poller.log.
Handles SIGTERM gracefully (cleans up PID file and exits).

Usage:
    PYTHONPATH=. python3 scripts/vps/notion-poller-daemon.py
"""

import atexit
import logging
import os
import signal
import sys
import time

PID_FILE = "/tmp/notion_poller.pid"
LOG_FILE = "/tmp/notion_poller.log"
POLL_INTERVAL = 60  # seconds

# Logging to file + stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("notion_poller_daemon")

_running = True


def _write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    logger.info("PID %d written to %s", os.getpid(), PID_FILE)


def _remove_pid():
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass


def _handle_signal(signum, _frame):
    global _running
    logger.info("Received signal %d, shutting down...", signum)
    _running = False


def main():
    global _running

    _write_pid()
    atexit.register(_remove_pid)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Import the poller here so env vars are already loaded
    from dispatcher.notion_poller import _do_poll, WorkerClient, TaskQueue
    from dispatcher.scheduler import TaskScheduler
    import redis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_url = os.environ.get("WORKER_URL", "")
    worker_token = os.environ.get("WORKER_TOKEN", "")

    if not worker_url or not worker_token:
        logger.error("WORKER_URL and WORKER_TOKEN are required.")
        sys.exit(1)

    try:
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
    except Exception as e:
        logger.error("Redis unavailable: %s", e)
        sys.exit(1)

    # SEV-1 2026-05-05: notion.poll_comments paginates ALL comments on a page
    # (oldest-first, since-filter applied post-fetch). On busy pages like
    # OpenClaw (30c5f443, ~30k comments), one poll call can take 60s+. The
    # default 30s WorkerClient timeout caused ReadTimeout → poller silenced
    # since 2026-05-02 17:49 UTC. Bumping to 300s as a tactical mitigation
    # while a cursor-checkpoint refactor of poll_comments is scoped.
    wc = WorkerClient(base_url=worker_url, token=worker_token, timeout=300.0)
    queue = TaskQueue(r)
    scheduler = TaskScheduler(r)

    logger.info(
        "Notion Poller daemon started (interval=%ds, worker=%s)",
        POLL_INTERVAL,
        worker_url,
    )

    while _running:
        try:
            # 1. Process scheduled tasks that are due
            scheduler.check_and_enqueue(queue)
            
            # 2. Check for new comments in Notion
            _do_poll(wc, queue, r, scheduler)
        except Exception:
            logger.exception("Poll iteration failed")
        # Sleep in small increments to respond to signals quickly
        for _ in range(POLL_INTERVAL):
            if not _running:
                break
            time.sleep(1)

    logger.info("Notion Poller daemon stopped.")


if __name__ == "__main__":
    main()
