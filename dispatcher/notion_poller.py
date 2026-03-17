"""
Notion Poller - S3: loop Notion <-> Rick.

Lee comentarios de la pagina Control Room via Worker y encola tareas para Rick.
Pensado para coordinacion con el agente de Notion "Enlace Notion <-> Rick":
- Enlace corre cada hora en punto (00:00, 01:00, ...)
- Rick (este poller) corre a las XX:10 para revisar mensajes que Enlace o David dejaron

Variables de entorno:
- NOTION_POLL_AT_MINUTE: minuto de cada hora en que hacer poll (default 10 -> XX:10)
- NOTION_POLL_INTERVAL_SEC: si se define, ignora AT_MINUTE y hace poll cada N segundos
- WORKER_URL, WORKER_TOKEN, REDIS_URL: obligatorios
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import redis

# Repo root en PATH para client + dispatcher
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.worker_client import WorkerClient
from dispatcher.queue import TaskQueue
from dispatcher.scheduler import TaskScheduler
from dispatcher.smart_reply import handle_smart_reply

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dispatcher.notion_poller")

REDIS_KEY_LAST_TS = "umbral:notion_poller:last_ts"
REDIS_KEY_PROCESSED_COMMENT_PREFIX = "umbral:notion_poller:processed_comment:"
PROCESSED_COMMENT_TTL_SEC = 24 * 60 * 60
DEFAULT_POLL_AT_MINUTE = 10  # XX:10 de cada hora (despues de Enlace a las XX:00)
ECHO_PREFIX = "Rick:"  # Comentarios que empiezan por esto los ignoramos (son nuestros)


def _parse_notion_datetime(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        logger.warning("Could not parse Notion datetime in poller: %s", value)
        return None


def _seconds_until_next_run(at_minute: int) -> float:
    """Segundos hasta el proximo XX:at_minute (UTC)."""
    now = datetime.now(timezone.utc)
    next_run = now.replace(minute=at_minute, second=0, microsecond=0)
    if now >= next_run:
        next_run += timedelta(hours=1)
    return (next_run - now).total_seconds()


def _extract_poll_comments_result(response: dict | None) -> list[dict]:
    if not isinstance(response, dict):
        return []

    nested = response.get("result")
    if isinstance(nested, dict) and isinstance(nested.get("comments"), list):
        return nested["comments"]

    top_level = response.get("comments")
    if isinstance(top_level, list):
        return top_level

    return []


def _claim_comment_processing(r: redis.Redis, comment_id: str) -> bool:
    if not comment_id:
        return False
    key = f"{REDIS_KEY_PROCESSED_COMMENT_PREFIX}{comment_id}"
    return bool(r.set(key, "1", nx=True, ex=PROCESSED_COMMENT_TTL_SEC))


def _do_poll(
    wc: WorkerClient,
    queue: TaskQueue,
    r: redis.Redis,
    scheduler: TaskScheduler,
) -> None:
    last_ts = r.get(REDIS_KEY_LAST_TS)
    if not last_ts:
        last_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        r.set(REDIS_KEY_LAST_TS, last_ts)

    response = wc.notion_poll_comments(since=last_ts, limit=20)
    comments = _extract_poll_comments_result(response)
    latest_dt = _parse_notion_datetime(last_ts) or datetime.min.replace(tzinfo=timezone.utc)

    logger.info("Notion poll retrieved %d comments since %s", len(comments), last_ts)

    for c in comments:
        created = c.get("created_time", "")
        created_dt = _parse_notion_datetime(created)
        text = (c.get("text") or "").strip()
        comment_id = c.get("id", "")

        if created_dt and created_dt > latest_dt:
            latest_dt = created_dt
        if text.startswith(ECHO_PREFIX):
            continue
        if not _claim_comment_processing(r, comment_id):
            logger.info("Skipping already processed comment %s", comment_id[:8])
            continue

        # Classify intent and route to team (S5 Hackathon - intelligent poller)
        from dispatcher.intent_classifier import classify_intent, route_to_team

        intent = classify_intent(text)
        team = route_to_team(text)

        # Smart reply: research + LLM + post answer (replaces old ack-only envelope)
        logger.info(
            "Processing [%s->%s] for comment %s: %.40s...",
            intent.intent,
            team,
            comment_id[:8],
            text[:40],
        )
        handle_smart_reply(text, comment_id, intent, team, wc, queue, scheduler)

    latest_ts = latest_dt.isoformat()
    if latest_ts != last_ts:
        r.set(REDIS_KEY_LAST_TS, latest_ts)
        logger.info("Notion poll advanced last_ts from %s to %s", last_ts, latest_ts)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Notion Poller - poll Control Room comments")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll cycle and exit (for cron usage)",
    )
    args = parser.parse_args()

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
    except Exception as exc:
        logger.error("Redis no disponible: %s", exc)
        sys.exit(1)

    queue = TaskQueue(r)
    scheduler = TaskScheduler(r)
    wc = WorkerClient(base_url=worker_url, token=worker_token)

    if args.once:
        logger.info("Notion poller --once (cron mode, worker=%s).", worker_url)
        _do_poll(wc, queue, r, scheduler)
        logger.info("Poll complete, exiting.")
        return

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
                _do_poll(wc, queue, r, scheduler)
                time.sleep(interval_sec)
            else:
                wait = _seconds_until_next_run(at_minute)
                logger.debug("Next poll in %.0fs (at XX:%02d)", wait, at_minute)
                time.sleep(wait)
                _do_poll(wc, queue, r, scheduler)
        except Exception as exc:
            logger.exception("Notion poll error: %s", exc)
            if interval_sec is not None:
                time.sleep(interval_sec)
            else:
                time.sleep(60)


if __name__ == "__main__":
    main()
