#!/usr/bin/env python3
"""
Notion Poller Daemon — runs the poller every 60s on the VPS.

Writes PID to /tmp/notion_poller.pid, logs to /tmp/notion_poller.log.
Handles SIGTERM gracefully (cleans up PID file and exits).

Logging (Tanda A / sys-diag 2026-07-17):
    The log is written by a SINGLE RotatingFileHandler (bounded size +
    retention). Previously the daemon used a FileHandler *and* a StreamHandler
    (→ stderr); combined with the cron wrapper's ``>> notion_poller.log 2>&1``
    that redirected stderr into the *same* file, every log line was written
    twice and the file grew unbounded (~102 MB observed). Dropping the
    StreamHandler removes the duplication; RotatingFileHandler bounds the size.
    The cron wrapper now sends the process's stdout/stderr to a separate boot
    log so the RotatingFileHandler is the sole writer of LOG_FILE and rotation
    is not defeated by an external append fd.

Env (all optional):
    NOTION_POLLER_LOG_FILE        Log path (default: /tmp/notion_poller.log)
    NOTION_POLLER_LOG_MAX_BYTES   Rotate at this size (default: 10485760 = 10 MB)
    NOTION_POLLER_LOG_BACKUPS     Rotated files to keep (default: 5)

Usage:
    PYTHONPATH=. python3 scripts/vps/notion-poller-daemon.py
"""

import atexit
import logging
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler

PID_FILE = "/tmp/notion_poller.pid"
LOG_FILE = os.environ.get("NOTION_POLLER_LOG_FILE", "/tmp/notion_poller.log")
POLL_INTERVAL = 60  # seconds

_LOG_MAX_BYTES = int(os.environ.get("NOTION_POLLER_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
_LOG_BACKUPS = int(os.environ.get("NOTION_POLLER_LOG_BACKUPS", "5"))
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _configure_logging(log_file: str = LOG_FILE) -> None:
    """Install a single bounded RotatingFileHandler on the root logger.

    Idempotent: safe to call more than once (e.g. if an imported module also
    configures logging) — it removes any pre-existing root handlers first, so
    the daemon never accumulates duplicate handlers on re-init.
    """
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:  # noqa: BLE001 — closing a handler must never crash startup
            pass
    handler = RotatingFileHandler(
        log_file,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUPS,
        encoding="utf-8",
        delay=True,  # open on first emit — keeps module import filesystem-free
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


_configure_logging()
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
