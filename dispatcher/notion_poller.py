"""
Notion Poller — S3: loop Notion ↔ Rick.

Lee comentarios de la página Control Room (vía Worker/VM) y encola tareas para Rick.
Pensado para coordinación con el agente de Notion "Enlace Notion ↔ Rick":
- Enlace corre cada hora en punto (00:00, 01:00, …).
- Rick (este poller) corre a las XX:10 para revisar mensajes que Enlace o David dejaron.

Variables de entorno:
- NOTION_POLL_AT_MINUTE: minuto de cada hora en que hacer poll (default 10 → XX:10).
- NOTION_POLL_INTERVAL_SEC: si se define, ignora AT_MINUTE y hace poll cada N segundos (modo continuo).
- WORKER_URL, WORKER_TOKEN, REDIS_URL: obligatorios.
"""

import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import redis

# Repo root en PATH para client + dispatcher
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.worker_client import WorkerClient
from dispatcher.queue import TaskQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dispatcher.notion_poller")

REDIS_KEY_LAST_TS = "umbral:notion_poller:last_ts"
DEFAULT_POLL_AT_MINUTE = 10  # XX:10 de cada hora (después de Enlace a las XX:00)
ECHO_PREFIX = "Rick:"  # Comentarios que empiezan por esto los ignoramos (son nuestros)


def _seconds_until_next_run(at_minute: int) -> float:
    """Segundos hasta el próximo XX:at_minute (UTC)."""
    now = datetime.now(timezone.utc)
    next_run = now.replace(minute=at_minute, second=0, microsecond=0)
    if now >= next_run:
        next_run += timedelta(hours=1)
    return (next_run - now).total_seconds()


def _do_poll(wc: WorkerClient, queue: TaskQueue, r: redis.Redis) -> None:
    last_ts = r.get(REDIS_KEY_LAST_TS)
    if not last_ts:
        last_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        r.set(REDIS_KEY_LAST_TS, last_ts)

    result = wc.notion_poll_comments(since=last_ts, limit=20)
    comments = result.get("comments", [])
    latest_ts = last_ts

    for c in comments:
        created = c.get("created_time", "")
        text = (c.get("text") or "").strip()
        comment_id = c.get("id", "")

        if created > latest_ts:
            latest_ts = created
        if text.startswith(ECHO_PREFIX):
            continue

        task_id = str(uuid.uuid4())
        envelope = {
            "schema_version": "0.1",
            "task_id": task_id,
            "team": "system",
            "task_type": "general",
            "task": "notion.add_comment",
            "input": {
                "text": f"{ECHO_PREFIX} Recibido. (comment_id={comment_id[:8]}...)",
            },
        }
        queue.enqueue(envelope)
        logger.info("Enqueued reply for comment %s: %.40s...", comment_id[:8], text[:40])

    if latest_ts != last_ts:
        r.set(REDIS_KEY_LAST_TS, latest_ts)


def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_url = os.environ.get("WORKER_URL", "")
    worker_token = os.environ.get("WORKER_TOKEN", "")
    interval_sec = os.environ.get("NOTION_POLL_INTERVAL_SEC")
    at_minute = int(os.environ.get("NOTION_POLL_AT_MINUTE", str(DEFAULT_POLL_AT_MINUTE)))

    if not worker_url or not worker_token:
        logger.error("WORKER_URL y WORKER_TOKEN son obligatorios.")
        sys.exit(1)

    try:
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
    except Exception as e:
        logger.error("Redis no disponible: %s", e)
        sys.exit(1)

    queue = TaskQueue(r)
    wc = WorkerClient(base_url=worker_url, token=worker_token)

    if interval_sec is not None:
        interval_sec = int(interval_sec)
        logger.info(
            "Notion poller started (interval=%ds, worker=%s). Control Room -> queue.",
            interval_sec,
            worker_url,
        )
    else:
        logger.info(
            "Notion poller started (at XX:%02d every hour, worker=%s). Enlace at XX:00, Rick at XX:%02d.",
            at_minute,
            worker_url,
            at_minute,
        )

    while True:
        try:
            if interval_sec is not None:
                _do_poll(wc, queue, r)
                time.sleep(interval_sec)
            else:
                wait = _seconds_until_next_run(at_minute)
                logger.debug("Next poll in %.0fs (at XX:%02d)", wait, at_minute)
                time.sleep(wait)
                _do_poll(wc, queue, r)
        except Exception as e:
            logger.exception("Notion poll error: %s", e)
            if interval_sec is not None:
                time.sleep(interval_sec)
            else:
                time.sleep(60)


if __name__ == "__main__":
    main()
