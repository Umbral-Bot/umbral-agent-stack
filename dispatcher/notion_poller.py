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
DEFAULT_POLL_OVERLAP_SEC = 5 * 60
DEFAULT_REVIEW_TARGET_LIMIT = 30
REVIEW_DELIVERABLE_STATUSES = (
    "Pendiente revision",
    "Aprobado con ajustes",
    "Rechazado",
)

# V2 classify scan constants
REDIS_KEY_CLASSIFIED_PREFIX = "umbral:notion_poller:classified:"
REDIS_KEY_CLASSIFY_FAIL_PREFIX = "umbral:notion_poller:classify_fail:"
CLASSIFIED_TTL_SEC = 24 * 60 * 60
CLASSIFY_FAIL_TTL_SEC = 30 * 60  # 30 min backoff on failure
V2_CLASSIFY_BATCH_LIMIT = 3
V2_SCAN_LIMIT = 10
_V2_ESTADO_AGENTE_DONE = {"Procesada", "Revision requerida"}
# V2 property names that indicate classification already happened
_V2_CLASSIFIED_FIELD_NAMES = {"Dominio propuesto", "Tipo propuesto", "Destino canonico", "Resumen agente"}


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


def _compute_effective_since(last_ts: str | None) -> str | None:
    last_dt = _parse_notion_datetime(last_ts)
    if not last_dt:
        return None
    overlap_sec = int(os.environ.get("NOTION_POLL_OVERLAP_SEC", str(DEFAULT_POLL_OVERLAP_SEC)))
    return (last_dt - timedelta(seconds=max(0, overlap_sec))).isoformat()


def _extract_read_database_items(response: dict | None) -> list[dict]:
    if not isinstance(response, dict):
        return []
    nested = response.get("result")
    if isinstance(nested, dict) and isinstance(nested.get("items"), list):
        return nested["items"]
    if isinstance(response.get("items"), list):
        return response["items"]
    return []


def _unique_page_ids(items: list[dict]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id or page_id in seen:
            continue
        seen.add(page_id)
        ordered.append(page_id)
    return ordered


def _filter_items_by_property_equals(
    items: list[dict],
    property_name: str,
    allowed_values: tuple[str, ...],
) -> list[dict]:
    allowed = {value.strip() for value in allowed_values if value.strip()}
    if not allowed:
        return items

    filtered: list[dict] = []
    for item in items:
        properties = item.get("properties") or {}
        value = str(properties.get(property_name) or "").strip()
        if value in allowed:
            filtered.append(item)
    return filtered


def _session_capitalizable_db_id() -> str:
    """
    Resolve the V1 session_capitalizable binding from the legacy curated env var.
    """
    return os.environ.get("NOTION_CURATED_SESSIONS_DB_ID", "").strip()


def _resolve_review_targets(wc: WorkerClient) -> list[dict[str, str]]:
    """Return relevant Notion pages that may carry human review comments."""
    targets: list[dict[str, str]] = []
    max_items = int(os.environ.get("NOTION_REVIEW_TARGET_LIMIT", str(DEFAULT_REVIEW_TARGET_LIMIT)))

    deliverables_db_id = os.environ.get("NOTION_DELIVERABLES_DB_ID", "").strip()
    if deliverables_db_id:
        try:
            deliverable_resp = wc.run(
                "notion.read_database",
                {
                    "database_id_or_url": deliverables_db_id,
                    "max_items": max_items,
                },
            )
            deliverable_items = _filter_items_by_property_equals(
                _extract_read_database_items(deliverable_resp),
                "Estado revision",
                REVIEW_DELIVERABLE_STATUSES,
            )
            for page_id in _unique_page_ids(deliverable_items):
                targets.append({"page_id": page_id, "page_kind": "deliverable"})
        except Exception:
            logger.warning("Failed to resolve deliverable review targets", exc_info=True)

    projects_db_id = os.environ.get("NOTION_PROJECTS_DB_ID", "").strip()
    if projects_db_id:
        try:
            project_resp = wc.run(
                "notion.read_database",
                {
                    "database_id_or_url": projects_db_id,
                    "max_items": min(15, max_items),
                },
            )
            for page_id in _unique_page_ids(_extract_read_database_items(project_resp)):
                targets.append({"page_id": page_id, "page_kind": "project"})
        except Exception:
            logger.warning("Failed to resolve project review targets", exc_info=True)

    session_capitalizable_db_id = _session_capitalizable_db_id()
    if session_capitalizable_db_id:
        try:
            session_resp = wc.run(
                "notion.read_database",
                {
                    "database_id_or_url": session_capitalizable_db_id,
                    "max_items": min(20, max_items),
                },
            )
            for page_id in _unique_page_ids(_extract_read_database_items(session_resp)):
                targets.append({"page_id": page_id, "page_kind": "session_capitalizable"})
        except Exception:
            logger.warning("Failed to resolve session_capitalizable review targets", exc_info=True)

    control_room_page = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID", "").strip()
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for target in targets:
        page_id = target.get("page_id", "").strip()
        if not page_id or page_id == control_room_page or page_id in seen:
            continue
        seen.add(page_id)
        deduped.append(target)
    return deduped


def _control_room_poll_target() -> dict[str, str | None]:
    page_id = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID", "").strip() or None
    if not page_id:
        logger.warning(
            "Control Room poll target missing NOTION_CONTROL_ROOM_PAGE_ID; "
            "page_id remains unset for control_room comments"
        )
    return {"page_id": page_id, "page_kind": "control_room"}


def _collect_candidate_comments(wc: WorkerClient, last_ts: str | None, limit: int) -> list[dict]:
    """Poll comments from Control Room plus active review targets."""
    effective_since = _compute_effective_since(last_ts)
    comments_by_id: dict[str, dict] = {}

    poll_targets: list[dict[str, str | None]] = [_control_room_poll_target()]
    poll_targets.extend(_resolve_review_targets(wc))

    for target in poll_targets:
        page_id = target.get("page_id")
        page_kind = target.get("page_kind")
        response = wc.notion_poll_comments(
            since=effective_since,
            limit=limit,
            page_id=page_id,
        )
        for comment in _extract_poll_comments_result(response):
            comment_id = str(comment.get("id") or "").strip()
            if not comment_id:
                continue
            merged = dict(comment)
            if page_id:
                merged.setdefault("page_id", page_id)
            if page_kind:
                merged.setdefault("page_kind", page_kind)
            comments_by_id.setdefault(comment_id, merged)

    return sorted(
        comments_by_id.values(),
        key=lambda c: _parse_notion_datetime(c.get("created_time")) or datetime.min.replace(tzinfo=timezone.utc),
    )


def _claim_comment_processing(r: redis.Redis, comment_id: str) -> bool:
    if not comment_id:
        return False
    key = f"{REDIS_KEY_PROCESSED_COMMENT_PREFIX}{comment_id}"
    return bool(r.set(key, "1", nx=True, ex=PROCESSED_COMMENT_TTL_SEC))


def _extract_estado_agente(item: dict) -> str:
    """Extract Estado agente value from a read_database item, defensively."""
    props = item.get("properties") or {}
    for key in ("Estado agente",):
        prop = props.get(key)
        if not prop:
            continue
        if isinstance(prop, str):
            return prop.strip()
        if not isinstance(prop, dict):
            continue
        ptype = prop.get("type", "")
        if ptype == "select":
            sel = prop.get("select") or {}
            return (sel.get("name") or "").strip()
        if ptype == "status":
            st = prop.get("status") or {}
            return (st.get("name") or "").strip()
        if ptype == "rich_text":
            parts = prop.get("rich_text") or []
            return "".join(rt.get("plain_text", "") for rt in parts).strip()
    return ""


def _has_v2_classification_fields(item: dict) -> bool:
    """Check if a page already has V2 classification fields populated."""
    props = item.get("properties") or {}
    for field_name in _V2_CLASSIFIED_FIELD_NAMES:
        prop = props.get(field_name)
        if not prop:
            continue
        if isinstance(prop, str):
            return True
        if not isinstance(prop, dict):
            continue
        ptype = prop.get("type", "")
        value = ""
        if ptype == "select":
            value = ((prop.get("select") or {}).get("name") or "").strip()
        elif ptype == "status":
            value = ((prop.get("status") or {}).get("name") or "").strip()
        elif ptype == "rich_text":
            parts = prop.get("rich_text") or []
            value = "".join(rt.get("plain_text", "") for rt in parts).strip()
        if value:
            return True
    return False


def _classify_pending_granola_pages(wc: WorkerClient, r: redis.Redis) -> None:
    """Scan Granola DB for unclassified pages and invoke classify_raw on them."""
    granola_db_id = os.environ.get("NOTION_GRANOLA_DB_ID", "").strip()
    if not granola_db_id:
        return

    try:
        resp = wc.run(
            "notion.read_database",
            {"database_id_or_url": granola_db_id, "max_items": V2_SCAN_LIMIT},
        )
    except Exception:
        logger.warning("V2 classify: failed to read Granola DB", exc_info=True)
        return

    items = _extract_read_database_items(resp)
    if not items:
        return

    classified_count = 0
    skipped_count = 0
    error_count = 0

    for item in items:
        if classified_count >= V2_CLASSIFY_BATCH_LIMIT:
            break

        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id:
            continue

        # Redis dedup: already classified this cycle?
        redis_key = f"{REDIS_KEY_CLASSIFIED_PREFIX}{page_id}"
        if r.exists(redis_key):
            skipped_count += 1
            continue

        # Redis backoff: recently failed classification?
        fail_key = f"{REDIS_KEY_CLASSIFY_FAIL_PREFIX}{page_id}"
        if r.exists(fail_key):
            skipped_count += 1
            continue

        # Property check: already classified by a prior run?
        estado = _extract_estado_agente(item)
        if estado in _V2_ESTADO_AGENTE_DONE:
            r.set(redis_key, "1", ex=CLASSIFIED_TTL_SEC)
            skipped_count += 1
            continue

        # V2 field check: already has classification data?
        if _has_v2_classification_fields(item):
            r.set(redis_key, "1", ex=CLASSIFIED_TTL_SEC)
            skipped_count += 1
            continue

        # Classify this page
        try:
            result = wc.run("granola.classify_raw", {"page_id": page_id})
            ok = isinstance(result, dict) and not result.get("error")
            if ok:
                r.set(redis_key, "1", ex=CLASSIFIED_TTL_SEC)
                classified_count += 1
                classification = (result.get("result") or result).get("classification") or {}
                logger.info(
                    "V2 classify: page %s → %s/%s/%s",
                    page_id[:8],
                    classification.get("dominio", "?"),
                    classification.get("tipo", "?"),
                    classification.get("destino", "?"),
                )
            else:
                error_count += 1
                r.set(fail_key, "1", ex=CLASSIFY_FAIL_TTL_SEC)
                logger.warning(
                    "V2 classify: page %s returned error (backoff %ds): %s",
                    page_id[:8],
                    CLASSIFY_FAIL_TTL_SEC,
                    (result or {}).get("error", "unknown"),
                )
        except Exception:
            error_count += 1
            r.set(fail_key, "1", ex=CLASSIFY_FAIL_TTL_SEC)
            logger.warning("V2 classify: page %s call failed (backoff %ds)", page_id[:8], CLASSIFY_FAIL_TTL_SEC, exc_info=True)

    total_scanned = classified_count + skipped_count + error_count
    if total_scanned > 0:
        logger.info(
            "V2 classify scan: %d scanned, %d classified, %d skipped, %d errors",
            total_scanned, classified_count, skipped_count, error_count,
        )


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

    comments = _collect_candidate_comments(wc, last_ts, limit=20)
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

        # Ola 1b: @rick mention adapter (bypass legacy intent path)
        from dispatcher.rick_mention import is_rick_mention, handle_rick_mention, _david_allowlist
        if is_rick_mention(text, c.get("created_by"), _david_allowlist()):
            handle_rick_mention(
                text=text, comment_id=comment_id,
                page_id=c.get("page_id"), page_kind=c.get("page_kind"),
                author=c.get("created_by"),
                wc=wc, queue=queue, scheduler=scheduler,
            )
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
        handle_smart_reply(
            text,
            comment_id,
            intent,
            team,
            wc,
            queue,
            scheduler,
            page_id=c.get("page_id"),
            page_kind=c.get("page_kind"),
        )

    latest_ts = latest_dt.isoformat()
    if latest_ts != last_ts:
        r.set(REDIS_KEY_LAST_TS, latest_ts)
        logger.info("Notion poll advanced last_ts from %s to %s", last_ts, latest_ts)

    # V2: classify pending Granola raw pages
    try:
        _classify_pending_granola_pages(wc, r)
    except Exception:
        logger.warning("V2 classify scan failed", exc_info=True)


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
