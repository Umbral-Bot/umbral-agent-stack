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

import httpx
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

# B2 anti-loop defense (Fase 2): author.id del bot/integration como guard primario.
# - Override por env NOTION_BOT_USER_ID si existe (mas predecible, zero HTTP).
# - Si no, resolver una vez via Notion /v1/users/me y cachear en memoria del proceso.
# - Si no se puede resolver, mantener ECHO_PREFIX como fallback (no breaking change).
# Ver docs/audits/openclaw-e2e-cycle-001/B2_ANTI_LOOP_DECISION.md
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
_NOTION_BOT_HTTP_TIMEOUT_SEC = 5.0
_BOT_USER_ID_CACHE: dict[str, str | None] = {}
_BOT_USER_ID_SENTINEL = "__resolved__"


def _resolve_bot_user_id() -> str | None:
    """Return the Notion bot/integration user id, or None if unresolvable.

    Resolution order:
      1. Env var NOTION_BOT_USER_ID (override, no HTTP).
      2. GET https://api.notion.com/v1/users/me using NOTION_API_KEY (cached per process).

    Never prints tokens or full headers. On failure logs a single warning per process
    and caches None so we do not retry on every poll cycle (avoid rate-limit risk).
    Callers must treat None as "author guard unavailable, fallback to ECHO_PREFIX".
    """
    override = os.environ.get("NOTION_BOT_USER_ID", "").strip()
    if override:
        return override

    if _BOT_USER_ID_SENTINEL in _BOT_USER_ID_CACHE:
        return _BOT_USER_ID_CACHE.get("value")

    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        logger.warning(
            "B2 author guard: NOTION_BOT_USER_ID not set and NOTION_API_KEY missing; "
            "falling back to ECHO_PREFIX only."
        )
        _BOT_USER_ID_CACHE[_BOT_USER_ID_SENTINEL] = "1"
        _BOT_USER_ID_CACHE["value"] = None
        return None

    try:
        with httpx.Client(timeout=_NOTION_BOT_HTTP_TIMEOUT_SEC) as client:
            resp = client.get(
                f"{NOTION_API_BASE_URL}/users/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": NOTION_API_VERSION,
                },
            )
        if resp.status_code >= 400:
            logger.warning(
                "B2 author guard: /users/me returned HTTP %d; falling back to ECHO_PREFIX only.",
                resp.status_code,
            )
            _BOT_USER_ID_CACHE[_BOT_USER_ID_SENTINEL] = "1"
            _BOT_USER_ID_CACHE["value"] = None
            return None
        data = resp.json() if resp.content else {}
        bot_id = (data or {}).get("id")
        if not isinstance(bot_id, str) or not bot_id:
            logger.warning(
                "B2 author guard: /users/me response missing 'id'; falling back to ECHO_PREFIX only."
            )
            _BOT_USER_ID_CACHE[_BOT_USER_ID_SENTINEL] = "1"
            _BOT_USER_ID_CACHE["value"] = None
            return None
        logger.info("B2 author guard: bot user id resolved (cached for process lifetime).")
        _BOT_USER_ID_CACHE[_BOT_USER_ID_SENTINEL] = "1"
        _BOT_USER_ID_CACHE["value"] = bot_id
        return bot_id
    except Exception as exc:  # noqa: BLE001 honest gap — never break poll cycle
        logger.warning(
            "B2 author guard: /users/me call failed (%s: %s); falling back to ECHO_PREFIX only.",
            type(exc).__name__,
            str(exc)[:160],
        )
        _BOT_USER_ID_CACHE[_BOT_USER_ID_SENTINEL] = "1"
        _BOT_USER_ID_CACHE["value"] = None
        return None


def _reset_bot_user_id_cache() -> None:
    """Test-only helper: clear the module-level cache so tests can re-resolve."""
    _BOT_USER_ID_CACHE.clear()
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

# Promote scan constants (P2.1 — Shortlist Aprobar -> Publicaciones).
# See docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.1 and
# docs/ops/editorial-norte-hitl-contract-2026-07-22.md §4/§6.
REDIS_KEY_PROMOTED_PREFIX = "umbral:notion_poller:promoted:"
REDIS_KEY_PROMOTE_FAIL_PREFIX = "umbral:notion_poller:promote_fail:"
PROMOTED_TTL_SEC = 24 * 60 * 60
PROMOTE_FAIL_TTL_SEC = 30 * 60  # 30 min backoff on failure
PROMOTE_BATCH_LIMIT = 3
PROMOTE_SCAN_LIMIT = 10

# P2.4: dedupe-of-candidate scan (Shortlist rows missing dedupe_status ->
# ask Worker/core to consult the Publicaciones backlog). Independent of the
# promote scan above: a row is evaluated once, regardless of its
# `Resultado revisión` — dedupe is a pre-registration signal for HITL-1, not a
# gate on promotion. See docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md
# row P2.4 and docs/ops/editorial-norte-hitl-contract-2026-07-22.md §5.J.
REDIS_KEY_DEDUPED_PREFIX = "umbral:notion_poller:deduped:"
REDIS_KEY_DEDUPE_FAIL_PREFIX = "umbral:notion_poller:dedupe_fail:"
DEDUPED_TTL_SEC = 24 * 60 * 60
DEDUPE_FAIL_TTL_SEC = 30 * 60  # 30 min backoff on failure
DEDUPE_BATCH_LIMIT = 3
DEDUPE_SCAN_LIMIT = 10

# P2.5: negative-example capture scan (Shortlist rows marked Descartar with
# ejemplo_negativo still false -> ask Worker/core to validate + persist the
# negative example). Fila D of the gap matrix (previously AUSENTE). See
# docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.5 and
# docs/ops/editorial-norte-hitl-contract-2026-07-22.md §4.
REDIS_KEY_NEGATIVE_CAPTURED_PREFIX = "umbral:notion_poller:negative_captured:"
REDIS_KEY_NEGATIVE_FAIL_PREFIX = "umbral:notion_poller:negative_fail:"
NEGATIVE_CAPTURED_TTL_SEC = 24 * 60 * 60
NEGATIVE_FAIL_TTL_SEC = 30 * 60  # 30 min backoff on failure
NEGATIVE_BATCH_LIMIT = 3
NEGATIVE_SCAN_LIMIT = 10

# P2a: the V2 classify scan is DEFAULT OFF and fail-closed. It caused the
# 2026-07-16 incident (rows silently marked classified as `?/?/?` while the
# Worker had no live LLM provider, scanning rows without the human gate) that
# forced CAP_POLLER_PAUSED. Only these explicit truthy values enable it; any
# other value — including absence — keeps it disabled while Control Room /
# review targets / smart replies keep running normally.
V2_CLASSIFY_ENV_FLAG = "NOTION_POLLER_ENABLE_V2_CLASSIFY"
_TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}
_V2_ESTADO_TERMINAL = {"Procesada", "Archivada", "Error"}
_V2_CLASSIFICATION_FIELDS = ("dominio", "tipo", "destino", "resumen")
_V2_CLASSIFIED_FIELD_NAMES = {"Dominio propuesto", "Tipo propuesto", "Destino canonico", "Resumen agente"}
_V2_DISABLED_LOG_STATE = {"logged": False}


def _v2_classify_enabled() -> bool:
    """Return True only for an explicit truthy NOTION_POLLER_ENABLE_V2_CLASSIFY."""
    return os.environ.get(V2_CLASSIFY_ENV_FLAG, "").strip().lower() in _TRUTHY_ENV_VALUES


def _log_v2_disabled_once() -> None:
    """One INFO line per process, DEBUG afterwards — clear but not noisy."""
    if not _V2_DISABLED_LOG_STATE["logged"]:
        logger.info(
            "V2 classify scan disabled (default; set %s=true to enable). "
            "Control Room / review / smart replies unaffected.",
            V2_CLASSIFY_ENV_FLAG,
        )
        _V2_DISABLED_LOG_STATE["logged"] = True
    else:
        logger.debug("V2 classify scan disabled (%s not truthy)", V2_CLASSIFY_ENV_FLAG)


def _reset_v2_disabled_log() -> None:
    """Test-only helper."""
    _V2_DISABLED_LOG_STATE["logged"] = False


# P2.1: the promote scan (Shortlist Aprobar -> Publicaciones) is DEFAULT OFF
# and fail-closed, mirroring the V2 classify scan above. Only these explicit
# truthy values enable it; any other value — including absence — keeps it
# disabled while Control Room / review targets / smart replies / V2 classify
# keep running normally. Even when enabled, the actual gate re-check and the
# Notion write happen inside the Worker task
# (editorial.promote_shortlist_approval, ADR-011 #1) — this scan only decides
# which Shortlist pages to ask Worker/core to (re-)evaluate.
PROMOTE_ENV_FLAG = "NOTION_POLLER_ENABLE_PROMOTE"
_PROMOTE_DISABLED_LOG_STATE = {"logged": False}


def _promote_enabled() -> bool:
    """Return True only for an explicit truthy NOTION_POLLER_ENABLE_PROMOTE."""
    return os.environ.get(PROMOTE_ENV_FLAG, "").strip().lower() in _TRUTHY_ENV_VALUES


def _log_promote_disabled_once() -> None:
    """One INFO line per process, DEBUG afterwards — clear but not noisy."""
    if not _PROMOTE_DISABLED_LOG_STATE["logged"]:
        logger.info(
            "Promote scan disabled (default; set %s=true to enable). "
            "Control Room / review / smart replies / V2 classify unaffected.",
            PROMOTE_ENV_FLAG,
        )
        _PROMOTE_DISABLED_LOG_STATE["logged"] = True
    else:
        logger.debug("Promote scan disabled (%s not truthy)", PROMOTE_ENV_FLAG)


def _reset_promote_disabled_log() -> None:
    """Test-only helper."""
    _PROMOTE_DISABLED_LOG_STATE["logged"] = False


# P2.4: the dedupe scan (Shortlist candidate vs Publicaciones backlog) is
# DEFAULT OFF and fail-closed, mirroring the promote scan above. Even when
# enabled, the actual backlog query and the Notion write happen inside the
# Worker task (editorial.dedupe_candidate_vs_backlog, ADR-011 #1) — this scan
# only decides which Shortlist pages still need a dedupe verdict.
DEDUPE_ENV_FLAG = "NOTION_POLLER_ENABLE_DEDUPE"
_DEDUPE_DISABLED_LOG_STATE = {"logged": False}


def _dedupe_enabled() -> bool:
    """Return True only for an explicit truthy NOTION_POLLER_ENABLE_DEDUPE."""
    return os.environ.get(DEDUPE_ENV_FLAG, "").strip().lower() in _TRUTHY_ENV_VALUES


def _log_dedupe_disabled_once() -> None:
    """One INFO line per process, DEBUG afterwards — clear but not noisy."""
    if not _DEDUPE_DISABLED_LOG_STATE["logged"]:
        logger.info(
            "Dedupe scan disabled (default; set %s=true to enable). "
            "Control Room / review / smart replies / V2 classify / promote unaffected.",
            DEDUPE_ENV_FLAG,
        )
        _DEDUPE_DISABLED_LOG_STATE["logged"] = True
    else:
        logger.debug("Dedupe scan disabled (%s not truthy)", DEDUPE_ENV_FLAG)


def _reset_dedupe_disabled_log() -> None:
    """Test-only helper."""
    _DEDUPE_DISABLED_LOG_STATE["logged"] = False


# P2.5: the negative-example capture scan is DEFAULT OFF and fail-closed,
# mirroring the promote/dedupe scans above. Even when enabled, the actual
# validation and Notion write happen inside the Worker task
# (editorial.capture_negative_example, ADR-011 #1) — this scan only decides
# which Shortlist pages still need capture.
NEGATIVE_CAPTURE_ENV_FLAG = "NOTION_POLLER_ENABLE_NEGATIVE_CAPTURE"
_NEGATIVE_CAPTURE_DISABLED_LOG_STATE = {"logged": False}


def _negative_capture_enabled() -> bool:
    """Return True only for an explicit truthy NOTION_POLLER_ENABLE_NEGATIVE_CAPTURE."""
    return os.environ.get(NEGATIVE_CAPTURE_ENV_FLAG, "").strip().lower() in _TRUTHY_ENV_VALUES


def _log_negative_capture_disabled_once() -> None:
    """One INFO line per process, DEBUG afterwards — clear but not noisy."""
    if not _NEGATIVE_CAPTURE_DISABLED_LOG_STATE["logged"]:
        logger.info(
            "Negative-capture scan disabled (default; set %s=true to enable). "
            "Control Room / review / smart replies / V2 classify / promote / dedupe unaffected.",
            NEGATIVE_CAPTURE_ENV_FLAG,
        )
        _NEGATIVE_CAPTURE_DISABLED_LOG_STATE["logged"] = True
    else:
        logger.debug("Negative-capture scan disabled (%s not truthy)", NEGATIVE_CAPTURE_ENV_FLAG)


def _reset_negative_capture_disabled_log() -> None:
    """Test-only helper."""
    _NEGATIVE_CAPTURE_DISABLED_LOG_STATE["logged"] = False


# Magnific scan constants (P2.2 — Publicaciones rows promoted by P2.1 get 5
# image variants generated). See docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md
# row P2.2 and docs/ops/editorial-magnific-p22-poller-2026-07-23.md.
REDIS_KEY_MAGNIFIC_PREFIX = "umbral:notion_poller:magnific:"
REDIS_KEY_MAGNIFIC_FAIL_PREFIX = "umbral:notion_poller:magnific_fail:"
MAGNIFIC_TTL_SEC = 24 * 60 * 60
MAGNIFIC_FAIL_TTL_SEC = 30 * 60  # 30 min backoff on failure
# Each promoted row costs up to 5 sequential external-API calls (minutes, not
# seconds) — keep the per-cycle batch small regardless of scan volume.
MAGNIFIC_BATCH_LIMIT = 1
MAGNIFIC_SCAN_LIMIT = 10
# The shared `wc` used elsewhere in _do_poll has a short default timeout
# (WorkerClient default 30s) tuned for fast calls; magnific.generate_variants
# can take several minutes (5 sequential Mystic submit+poll cycles). Override
# per-call via WorkerClient.run(..., timeout=...) rather than raising the
# shared client's timeout for every other (fast) task.
#
# Sizing: worker/tasks/magnific.py's own worst-case *sleep* budget alone is
# DEFAULT_VARIANT_COUNT(5) x _MAX_POLL_ATTEMPTS(40) x _POLL_INTERVAL_SEC(3s)
# = 600s, before counting any of the ~205 real HTTP round trips (5 submits +
# up to 200 polls) each attempt implies. Using exactly 600s here would leave
# zero margin and could time out work that is still legitimately in progress
# server-side. Keep a generous multiple instead of the bare theoretical floor
# — if worker/tasks/magnific.py's constants change, revisit this alongside it.
MAGNIFIC_CALL_TIMEOUT_SEC = 1200.0

# P2.2: the magnific scan is DEFAULT OFF and fail-closed, mirroring the
# promote scan above. Only these explicit truthy values enable it; any other
# value — including absence — keeps it disabled while everything else in the
# poller keeps running normally. Even when enabled, the actual eligibility
# re-check and every Notion write happen inside the Worker task
# (magnific.generate_variants, ADR-011 #1) — this scan only decides which
# Publicaciones rows to ask Worker/core to (re-)evaluate.
MAGNIFIC_ENV_FLAG = "NOTION_POLLER_ENABLE_MAGNIFIC"
_MAGNIFIC_DISABLED_LOG_STATE = {"logged": False}


def _magnific_enabled() -> bool:
    """Return True only for an explicit truthy NOTION_POLLER_ENABLE_MAGNIFIC."""
    return os.environ.get(MAGNIFIC_ENV_FLAG, "").strip().lower() in _TRUTHY_ENV_VALUES


def _log_magnific_disabled_once() -> None:
    """One INFO line per process, DEBUG afterwards — clear but not noisy."""
    if not _MAGNIFIC_DISABLED_LOG_STATE["logged"]:
        logger.info(
            "Magnific scan disabled (default; set %s=true to enable). "
            "Control Room / review / smart replies / V2 classify / promote scan unaffected.",
            MAGNIFIC_ENV_FLAG,
        )
        _MAGNIFIC_DISABLED_LOG_STATE["logged"] = True
    else:
        logger.debug("Magnific scan disabled (%s not truthy)", MAGNIFIC_ENV_FLAG)


def _reset_magnific_disabled_log() -> None:
    """Test-only helper."""
    _MAGNIFIC_DISABLED_LOG_STATE["logged"] = False


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


def _extract_item_text(item: dict, *names: str) -> str:
    """Extract a select/status/rich_text value from a read_database item.

    Defensive against both the Worker's flattened shape (plain scalars) and
    raw Notion property dicts.
    """
    props = item.get("properties") or {}
    for key in names:
        prop = props.get(key)
        if prop is None:
            continue
        if isinstance(prop, str):
            return prop.strip()
        if not isinstance(prop, dict):
            continue
        ptype = prop.get("type", "")
        if ptype == "select":
            return (((prop.get("select") or {}).get("name")) or "").strip()
        if ptype == "status":
            return (((prop.get("status") or {}).get("name")) or "").strip()
        if ptype == "rich_text":
            parts = prop.get("rich_text") or []
            return "".join(rt.get("plain_text", "") for rt in parts).strip()
    return ""


def _extract_item_checkbox(item: dict, *names: str) -> bool:
    """Extract a checkbox value from a read_database item (flattened or raw)."""
    props = item.get("properties") or {}
    for key in names:
        prop = props.get(key)
        if prop is None:
            continue
        if isinstance(prop, bool):
            return prop
        if isinstance(prop, str):
            return prop.strip().lower() in _TRUTHY_ENV_VALUES
        if isinstance(prop, dict) and prop.get("type") == "checkbox":
            return bool(prop.get("checkbox"))
    return False


def _extract_estado_agente(item: dict) -> str:
    """Kept for backwards compatibility; delegates to the generic extractor."""
    return _extract_item_text(item, "Estado agente")


def _has_v2_classification_fields(item: dict) -> bool:
    """True when the row already has ALL four V2 classification fields set."""
    return all(
        bool(_extract_item_text(item, field_name))
        for field_name in _V2_CLASSIFIED_FIELD_NAMES
    )


def _v2_row_eligible(item: dict) -> tuple[bool, str]:
    """P2a human-gate eligibility for the V2 classify scan.

    A row is NEVER classified just for being among the first N rows. It must
    carry the explicit human gate and a pending/reprocess-compatible state.
    """
    if item.get("archived") is True:
        return False, "archived"
    if not _extract_item_checkbox(item, "Procesar con agente"):
        return False, "gate_unticked"
    estado = _extract_item_text(item, "Estado")
    if estado in _V2_ESTADO_TERMINAL:
        return False, "estado_terminal"
    if _has_v2_classification_fields(item):
        return False, "already_classified"
    estado_agente = _extract_item_text(item, "Estado agente")
    if estado_agente in ("", "Pendiente"):
        return True, ""
    if estado_agente == "Revision requerida" and _extract_item_checkbox(
        item, "Reprocesar tras revisión", "Reprocesar tras revision"
    ):
        return True, ""
    return False, "estado_agente_not_pending"


def _classification_result_complete(result: dict | None) -> tuple[bool, str]:
    """Strict success validation for a granola.classify_raw response.

    Success requires non-empty, non-placeholder values for all four V2 fields.
    Anything else (error key, empty/partial classification, `?` placeholders)
    is an honest failure: no success checkpoint, normal retry via backoff.
    """
    if not isinstance(result, dict):
        return False, "non_dict_response"
    payload = result.get("result") if isinstance(result.get("result"), dict) else result
    error = result.get("error") or payload.get("error")
    if error:
        return False, f"worker_error: {str(error)[:160]}"
    classification = payload.get("classification")
    if not isinstance(classification, dict) or not classification:
        return False, "empty_classification"
    missing = [
        field
        for field in _V2_CLASSIFICATION_FIELDS
        if not str(classification.get(field) or "").strip()
        or str(classification.get(field)).strip() == "?"
    ]
    if missing:
        return False, "incomplete_fields: " + ",".join(missing)
    return True, ""


def _classify_pending_granola_pages(wc: WorkerClient, r: redis.Redis) -> None:
    """Scan Granola DB for human-gated pending rows and classify them.

    P2a contract: only rows with `Procesar con agente=true` and a
    pending/reprocess-compatible state are ever considered; a classification
    only checkpoints as success when the result carries the four complete V2
    fields. Failures log honestly and back off — never a fake `?/?/?` success.
    """
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
    scanned = len(items)
    eligible = 0
    classified = 0
    skipped_gate = 0
    errors = 0

    for item in items:
        if classified >= V2_CLASSIFY_BATCH_LIMIT:
            break

        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id:
            skipped_gate += 1
            continue

        is_eligible, gate_reason = _v2_row_eligible(item)
        if not is_eligible:
            skipped_gate += 1
            logger.debug("V2 classify: page %s skipped (%s)", page_id[:8], gate_reason)
            continue
        eligible += 1

        redis_key = f"{REDIS_KEY_CLASSIFIED_PREFIX}{page_id}"
        fail_key = f"{REDIS_KEY_CLASSIFY_FAIL_PREFIX}{page_id}"
        if r.exists(redis_key) or r.exists(fail_key):
            skipped_gate += 1
            continue

        try:
            result = wc.run("granola.classify_raw", {"page_id": page_id})
        except Exception:
            errors += 1
            r.set(fail_key, "1", ex=CLASSIFY_FAIL_TTL_SEC)
            logger.warning(
                "V2 classify: page %s call failed (backoff %ds)",
                page_id[:8], CLASSIFY_FAIL_TTL_SEC, exc_info=True,
            )
            continue

        complete, failure_reason = _classification_result_complete(result)
        if complete:
            payload = result.get("result") if isinstance(result.get("result"), dict) else result
            classification = payload.get("classification") or {}
            r.set(redis_key, "1", ex=CLASSIFIED_TTL_SEC)
            classified += 1
            logger.info(
                "V2 classify: page %s -> %s/%s/%s",
                page_id[:8],
                classification.get("dominio"),
                classification.get("tipo"),
                classification.get("destino"),
            )
        else:
            errors += 1
            r.set(fail_key, "1", ex=CLASSIFY_FAIL_TTL_SEC)
            logger.warning(
                "V2 classify: page %s did NOT classify (%s) — no success checkpoint, backoff %ds",
                page_id[:8], failure_reason, CLASSIFY_FAIL_TTL_SEC,
            )

    metrics_line = (
        f"V2 classify scan: v2_classify_enabled=True scanned={scanned} "
        f"eligible={eligible} classified={classified} skipped_gate={skipped_gate} errors={errors}"
    )
    if scanned > 0:
        logger.info(metrics_line)
    else:
        logger.debug(metrics_line)


def _promote_approved_shortlist_rows(wc: WorkerClient, r: redis.Redis) -> None:
    """Scan Shortlist for Aprobar rows and ask Worker/core to promote each.

    P2.1 contract: a row is a *candidate* here only if its flattened snapshot
    shows `Resultado revisión == "Aprobar"` and an empty `promovido_a`
    relation. This function never writes to Notion — it only calls the
    `editorial.promote_shortlist_approval` Worker task, which re-fetches the
    page and re-validates the gate before writing (fail-closed; avoids acting
    on a stale scan snapshot). Redis here only dedupes *scan attempts* across
    poll cycles, not the actual promotion (that idempotency lives in the
    Worker task via `promovido_a` / `origen_alternativa`).
    """
    shortlist_ds_id = os.environ.get("NOTION_SHORTLIST_DS_ID", "").strip()
    if not shortlist_ds_id:
        return

    try:
        resp = wc.run(
            "notion.read_database",
            {"database_id_or_url": shortlist_ds_id, "max_items": PROMOTE_SCAN_LIMIT},
        )
    except Exception:
        logger.warning("Promote scan: failed to read Shortlist DB", exc_info=True)
        return

    items = _extract_read_database_items(resp)
    scanned = len(items)
    eligible = 0
    promoted = 0
    skipped = 0
    errors = 0

    for item in items:
        if promoted >= PROMOTE_BATCH_LIMIT:
            break

        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id:
            skipped += 1
            continue

        resultado = _extract_item_text(item, "Resultado revisión")
        if resultado != "Aprobar":
            skipped += 1
            continue

        promovido_a = (item.get("properties") or {}).get("promovido_a")
        if promovido_a:
            skipped += 1
            continue

        eligible += 1

        redis_key = f"{REDIS_KEY_PROMOTED_PREFIX}{page_id}"
        fail_key = f"{REDIS_KEY_PROMOTE_FAIL_PREFIX}{page_id}"
        if r.exists(redis_key) or r.exists(fail_key):
            skipped += 1
            continue

        try:
            result = wc.run(
                "editorial.promote_shortlist_approval",
                {"shortlist_page_id": page_id},
            )
        except Exception:
            errors += 1
            r.set(fail_key, "1", ex=PROMOTE_FAIL_TTL_SEC)
            logger.warning(
                "Promote scan: page %s call failed (backoff %ds)",
                page_id[:8], PROMOTE_FAIL_TTL_SEC, exc_info=True,
            )
            continue

        ok = bool(result.get("ok")) if isinstance(result, dict) else False
        if ok:
            r.set(redis_key, "1", ex=PROMOTED_TTL_SEC)
            promoted += 1
            logger.info(
                "Promote scan: shortlist page %s -> publicacion %s (created=%s)",
                page_id[:8],
                str(result.get("publicacion_page_id") or "")[:8],
                result.get("created"),
            )
        else:
            errors += 1
            r.set(fail_key, "1", ex=PROMOTE_FAIL_TTL_SEC)
            logger.warning(
                "Promote scan: page %s did NOT promote (%s) — no success checkpoint, backoff %ds",
                page_id[:8], (result or {}).get("error"), PROMOTE_FAIL_TTL_SEC,
            )

    metrics_line = (
        f"Promote scan: promote_enabled=True scanned={scanned} eligible={eligible} "
        f"promoted={promoted} skipped={skipped} errors={errors}"
    )
    if scanned > 0:
        logger.info(metrics_line)
    else:
        logger.debug(metrics_line)


def _dedupe_pending_shortlist_rows(wc: WorkerClient, r: redis.Redis) -> None:
    """Scan Shortlist for rows missing `dedupe_status` and evaluate each (P2.4).

    A row is a *candidate* here only if its flattened snapshot shows an empty
    `dedupe_status` — independent of `Resultado revisión`, since dedupe is
    meant to run before/alongside HITL-1 review, not only after Aprobar. This
    function never writes to Notion — it only calls the
    `editorial.dedupe_candidate_vs_backlog` Worker task, which re-fetches the
    page and re-queries the Publicaciones backlog before writing (fail-closed;
    avoids acting on a stale scan snapshot). Redis here only dedupes *scan
    attempts* across poll cycles, not the dedupe verdict itself (that
    idempotency lives in the Worker task via `dedupe_status`).
    """
    shortlist_ds_id = os.environ.get("NOTION_SHORTLIST_DS_ID", "").strip()
    if not shortlist_ds_id:
        return

    try:
        resp = wc.run(
            "notion.read_database",
            {"database_id_or_url": shortlist_ds_id, "max_items": DEDUPE_SCAN_LIMIT},
        )
    except Exception:
        logger.warning("Dedupe scan: failed to read Shortlist DB", exc_info=True)
        return

    items = _extract_read_database_items(resp)
    scanned = len(items)
    eligible = 0
    evaluated = 0
    skipped = 0
    errors = 0

    for item in items:
        if evaluated >= DEDUPE_BATCH_LIMIT:
            break

        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id:
            skipped += 1
            continue

        if item.get("archived") is True:
            skipped += 1
            continue

        if _extract_item_text(item, "dedupe_status"):
            skipped += 1
            continue

        redis_key = f"{REDIS_KEY_DEDUPED_PREFIX}{page_id}"
        fail_key = f"{REDIS_KEY_DEDUPE_FAIL_PREFIX}{page_id}"
        if r.exists(redis_key) or r.exists(fail_key):
            skipped += 1
            continue

        eligible += 1

        try:
            result = wc.run(
                "editorial.dedupe_candidate_vs_backlog",
                {"shortlist_page_id": page_id},
            )
        except Exception:
            errors += 1
            r.set(fail_key, "1", ex=DEDUPE_FAIL_TTL_SEC)
            logger.warning(
                "Dedupe scan: page %s call failed (backoff %ds)",
                page_id[:8], DEDUPE_FAIL_TTL_SEC, exc_info=True,
            )
            continue

        ok = bool(result.get("ok")) if isinstance(result, dict) else False
        if ok:
            r.set(redis_key, "1", ex=DEDUPED_TTL_SEC)
            evaluated += 1
            logger.info(
                "Dedupe scan: shortlist page %s -> dedupe_status=%s",
                page_id[:8],
                result.get("dedupe_status"),
            )
        else:
            errors += 1
            r.set(fail_key, "1", ex=DEDUPE_FAIL_TTL_SEC)
            logger.warning(
                "Dedupe scan: page %s did NOT evaluate (%s) — no success checkpoint, backoff %ds",
                page_id[:8], (result or {}).get("error"), DEDUPE_FAIL_TTL_SEC,
            )

    metrics_line = (
        f"Dedupe scan: dedupe_enabled=True scanned={scanned} eligible={eligible} "
        f"evaluated={evaluated} skipped={skipped} errors={errors}"
    )
    if scanned > 0:
        logger.info(metrics_line)
    else:
        logger.debug(metrics_line)


def _capture_negative_shortlist_rows(wc: WorkerClient, r: redis.Redis) -> None:
    """Scan Shortlist for Descartar rows missing `ejemplo_negativo` (P2.5).

    A row is a *candidate* here only if its flattened snapshot shows
    `Resultado revisión == "Descartar"` and a falsy `ejemplo_negativo`. This
    function never writes to Notion — it only calls the
    `editorial.capture_negative_example` Worker task, which re-fetches the
    page and re-validates the gate (and `motivo_descarte` presence) before
    writing (fail-closed; avoids acting on a stale scan snapshot). Redis here
    only dedupes *scan attempts* across poll cycles, not the capture itself
    (that idempotency lives in the Worker task via `ejemplo_negativo`).
    """
    shortlist_ds_id = os.environ.get("NOTION_SHORTLIST_DS_ID", "").strip()
    if not shortlist_ds_id:
        return

    try:
        resp = wc.run(
            "notion.read_database",
            {"database_id_or_url": shortlist_ds_id, "max_items": NEGATIVE_SCAN_LIMIT},
        )
    except Exception:
        logger.warning("Negative-capture scan: failed to read Shortlist DB", exc_info=True)
        return

    items = _extract_read_database_items(resp)
    scanned = len(items)
    eligible = 0
    captured = 0
    skipped = 0
    errors = 0

    for item in items:
        if captured >= NEGATIVE_BATCH_LIMIT:
            break

        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id:
            skipped += 1
            continue

        if item.get("archived") is True:
            skipped += 1
            continue

        if _extract_item_text(item, "Resultado revisión") != "Descartar":
            skipped += 1
            continue

        if _extract_item_checkbox(item, "ejemplo_negativo"):
            skipped += 1
            continue

        redis_key = f"{REDIS_KEY_NEGATIVE_CAPTURED_PREFIX}{page_id}"
        fail_key = f"{REDIS_KEY_NEGATIVE_FAIL_PREFIX}{page_id}"
        if r.exists(redis_key) or r.exists(fail_key):
            skipped += 1
            continue

        eligible += 1

        try:
            result = wc.run(
                "editorial.capture_negative_example",
                {"shortlist_page_id": page_id},
            )
        except Exception:
            errors += 1
            r.set(fail_key, "1", ex=NEGATIVE_FAIL_TTL_SEC)
            logger.warning(
                "Negative-capture scan: page %s call failed (backoff %ds)",
                page_id[:8], NEGATIVE_FAIL_TTL_SEC, exc_info=True,
            )
            continue

        ok = bool(result.get("ok")) if isinstance(result, dict) else False
        if ok:
            r.set(redis_key, "1", ex=NEGATIVE_CAPTURED_TTL_SEC)
            captured += 1
            logger.info(
                "Negative-capture scan: shortlist page %s captured=%s",
                page_id[:8],
                result.get("captured"),
            )
        else:
            errors += 1
            r.set(fail_key, "1", ex=NEGATIVE_FAIL_TTL_SEC)
            logger.warning(
                "Negative-capture scan: page %s did NOT capture (%s) — no success checkpoint, backoff %ds",
                page_id[:8], (result or {}).get("error"), NEGATIVE_FAIL_TTL_SEC,
            )

    metrics_line = (
        f"Negative-capture scan: negative_capture_enabled=True scanned={scanned} "
        f"eligible={eligible} captured={captured} skipped={skipped} errors={errors}"
    )
    if scanned > 0:
        logger.info(metrics_line)
    else:
        logger.debug(metrics_line)


# States the *automatic* scan must never re-trigger: already produced
# results, already in flight, or `Error` — which the handler still accepts
# as an eligible manual retry (CLI script / dry-run), but which the scan
# excludes deliberately. Without this, a persistently-failing row (e.g. a
# prompt that always trips Magnific's content filter) would be retried
# forever on the flat 30-min backoff with no cap, burning credits on every
# retry. Moving a row out of `Error` for an automatic re-attempt requires an
# explicit human/system action (e.g. `Selección imagen = Regenerar`, a
# separate reaction not implemented by this package) that lands it in
# `Regeneración pedida` instead — which *is* scan-eligible.
_MAGNIFIC_SCAN_SKIP_STATES = {"Listo para selección", "Seleccionada", "Generando", "Error"}


def _generate_magnific_variants_for_pending_rows(wc: WorkerClient, r: redis.Redis) -> None:
    """Scan Publicaciones for rows promoted by P2.1 that still need images.

    P2.2 contract: a row is a *candidate* here only if it carries a non-empty
    `origen_alternativa` back-link (i.e. it was promoted by P2.1's Aprobar
    flow — roadmap dependency "P2.1 dispara tras Aprobar") and its flattened
    `Estado imagen` snapshot is not in `_MAGNIFIC_SCAN_SKIP_STATES` (already
    `Listo para selección` / `Seleccionada` / `Generando`, or `Error` — the
    scan deliberately never auto-retries a failed row; see that constant's
    comment). This function never writes to Notion — it only calls the
    `magnific.generate_variants` Worker task, which re-fetches the page and
    re-validates the state machine before writing (fail-closed; avoids
    acting on a stale scan snapshot). Redis here only dedupes *scan
    attempts* across poll cycles, not the actual generation (that idempotency
    lives in the Worker task via `Estado imagen`).

    Each call can take minutes (up to 5 sequential external-API round trips),
    so the batch limit is intentionally 1 and the call uses an extended
    per-call timeout (see MAGNIFIC_CALL_TIMEOUT_SEC) rather than the shared
    client's default.
    """
    publicaciones_db_id = os.environ.get("NOTION_PUBLICACIONES_DB_ID", "").strip()
    if not publicaciones_db_id:
        return

    try:
        resp = wc.run(
            "notion.read_database",
            {"database_id_or_url": publicaciones_db_id, "max_items": MAGNIFIC_SCAN_LIMIT},
        )
    except Exception:
        logger.warning("Magnific scan: failed to read Publicaciones DB", exc_info=True)
        return

    items = _extract_read_database_items(resp)
    scanned = len(items)
    eligible = 0
    generated = 0
    skipped = 0
    errors = 0

    for item in items:
        if generated >= MAGNIFIC_BATCH_LIMIT:
            break

        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id:
            skipped += 1
            continue

        origen_alternativa = (item.get("properties") or {}).get("origen_alternativa")
        if not origen_alternativa:
            skipped += 1
            continue

        estado_imagen = _extract_item_text(item, "Estado imagen")
        if estado_imagen in _MAGNIFIC_SCAN_SKIP_STATES:
            skipped += 1
            continue

        eligible += 1

        redis_key = f"{REDIS_KEY_MAGNIFIC_PREFIX}{page_id}"
        fail_key = f"{REDIS_KEY_MAGNIFIC_FAIL_PREFIX}{page_id}"
        if r.exists(redis_key) or r.exists(fail_key):
            skipped += 1
            continue

        try:
            result = wc.run(
                "magnific.generate_variants",
                {"publicacion_page_id": page_id},
                timeout=MAGNIFIC_CALL_TIMEOUT_SEC,
            )
        except Exception:
            errors += 1
            r.set(fail_key, "1", ex=MAGNIFIC_FAIL_TTL_SEC)
            logger.warning(
                "Magnific scan: page %s call failed (backoff %ds)",
                page_id[:8], MAGNIFIC_FAIL_TTL_SEC, exc_info=True,
            )
            continue

        ok = bool(result.get("ok")) if isinstance(result, dict) else False
        skipped_noop = bool(result.get("skipped")) if isinstance(result, dict) else False
        if ok and skipped_noop:
            # Handler-level idempotency (already Generando / already done) —
            # not a scan error, but also not a fresh generation to checkpoint
            # against the batch limit.
            skipped += 1
            continue
        if ok:
            r.set(redis_key, "1", ex=MAGNIFIC_TTL_SEC)
            generated += 1
            logger.info(
                "Magnific scan: publicacion %s -> %s/%s variants written",
                page_id[:8],
                result.get("generated"),
                result.get("requested"),
            )
        else:
            errors += 1
            r.set(fail_key, "1", ex=MAGNIFIC_FAIL_TTL_SEC)
            logger.warning(
                "Magnific scan: page %s did NOT generate (%s) — no success checkpoint, backoff %ds",
                page_id[:8], (result or {}).get("error"), MAGNIFIC_FAIL_TTL_SEC,
            )

    metrics_line = (
        f"Magnific scan: magnific_enabled=True scanned={scanned} eligible={eligible} "
        f"generated={generated} skipped={skipped} errors={errors}"
    )
    if scanned > 0:
        logger.info(metrics_line)
    else:
        logger.debug(metrics_line)


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

    bot_user_id = _resolve_bot_user_id()

    for c in comments:
        created = c.get("created_time", "")
        created_dt = _parse_notion_datetime(created)
        text = (c.get("text") or "").strip()
        comment_id = c.get("id", "")
        author = c.get("created_by")

        if created_dt and created_dt > latest_dt:
            latest_dt = created_dt
        # B2 Capa 1 (primaria): author.id del bot/integration.
        # Si conocemos el bot_user_id y el author coincide, skip silencioso.
        # Cubre replies del worker que NO empiezan con "Rick:" (handler v0
        # rick.orchestrator.triage emite "Worker /health response:", etc).
        if bot_user_id and author == bot_user_id:
            logger.debug(
                "Skipping bot-authored comment %s (author guard)", (comment_id or "?")[:8]
            )
            continue
        # B2 Capa 2 (defense-in-depth): ECHO_PREFIX. Cubre el caso de bot_user_id
        # no resoluble y replies de smart_reply (que siempre prefijan "Rick:").
        if text.startswith(ECHO_PREFIX):
            continue
        if not _claim_comment_processing(r, comment_id):
            logger.info("Skipping already processed comment %s", comment_id[:8])
            continue

        # Ola 1b: @rick mention adapter (bypass legacy intent path)
        from dispatcher.rick_mention import is_rick_mention, handle_rick_mention, _david_allowlist
        if is_rick_mention(text, author, _david_allowlist()):
            handle_rick_mention(
                text=text, comment_id=comment_id,
                page_id=c.get("page_id"), page_kind=c.get("page_kind"),
                author=author,
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

    # V2: classify pending Granola raw pages — DEFAULT OFF (P2a fail-closed).
    # Control Room / review targets / smart replies above never depend on this.
    if _v2_classify_enabled():
        try:
            _classify_pending_granola_pages(wc, r)
        except Exception:
            logger.warning("V2 classify scan failed (general cycle unaffected)", exc_info=True)
    else:
        _log_v2_disabled_once()

    # P2.1: promote approved Shortlist rows to Publicaciones — DEFAULT OFF
    # (fail-closed). Everything above never depends on this.
    if _promote_enabled():
        try:
            _promote_approved_shortlist_rows(wc, r)
        except Exception:
            logger.warning("Promote scan failed (general cycle unaffected)", exc_info=True)
    else:
        _log_promote_disabled_once()

    # P2.4: dedupe Shortlist candidates against the Publicaciones backlog —
    # DEFAULT OFF (fail-closed). Independent of promote; everything above
    # never depends on this.
    if _dedupe_enabled():
        try:
            _dedupe_pending_shortlist_rows(wc, r)
        except Exception:
            logger.warning("Dedupe scan failed (general cycle unaffected)", exc_info=True)
    else:
        _log_dedupe_disabled_once()

    # P2.5: capture negative-example metadata for Descartar'd Shortlist rows —
    # DEFAULT OFF (fail-closed). Independent of promote/dedupe; everything
    # above never depends on this.
    if _negative_capture_enabled():
        try:
            _capture_negative_shortlist_rows(wc, r)
        except Exception:
            logger.warning("Negative-capture scan failed (general cycle unaffected)", exc_info=True)
    else:
        _log_negative_capture_disabled_once()

    # P2.2: generate Magnific image variants for promoted rows — DEFAULT OFF
    # (fail-closed). Everything above never depends on this. Runs last: each
    # call can take minutes, and this must never delay Control Room / review
    # targets / smart replies / V2 classify / promote scan.
    if _magnific_enabled():
        try:
            _generate_magnific_variants_for_pending_rows(wc, r)
        except Exception:
            logger.warning("Magnific scan failed (general cycle unaffected)", exc_info=True)
    else:
        _log_magnific_disabled_once()


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

    if _v2_classify_enabled():
        logger.info("V2 classify scan ENABLED (%s is truthy).", V2_CLASSIFY_ENV_FLAG)
    else:
        logger.info("V2 classify scan disabled (default off; %s not truthy).", V2_CLASSIFY_ENV_FLAG)

    if _promote_enabled():
        logger.info("Promote scan ENABLED (%s is truthy).", PROMOTE_ENV_FLAG)
    else:
        logger.info("Promote scan disabled (default off; %s not truthy).", PROMOTE_ENV_FLAG)

    if _dedupe_enabled():
        logger.info("Dedupe scan ENABLED (%s is truthy).", DEDUPE_ENV_FLAG)
    else:
        logger.info("Dedupe scan disabled (default off; %s not truthy).", DEDUPE_ENV_FLAG)

    if _negative_capture_enabled():
        logger.info("Negative-capture scan ENABLED (%s is truthy).", NEGATIVE_CAPTURE_ENV_FLAG)
    else:
        logger.info("Negative-capture scan disabled (default off; %s not truthy).", NEGATIVE_CAPTURE_ENV_FLAG)

    if _magnific_enabled():
        logger.info("Magnific scan ENABLED (%s is truthy).", MAGNIFIC_ENV_FLAG)
    else:
        logger.info("Magnific scan disabled (default off; %s not truthy).", MAGNIFIC_ENV_FLAG)

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
