"""Stage 7.5: LLM copywriter for LinkedIn — transformer core.

For each proposal that already has a Notion page (Stage 7) and a hero image
(Stage 8), this script:

1. Reads the page properties via the Notion API.
2. Skips silently if ``Copy LinkedIn`` is already populated by a human
   (unless ``--force-overwrite``).
3. Builds an editorial prompt and asks an LLM (via the local OpenClaw
   gateway) to produce a publishable LinkedIn post.
4. Validates the output (length, source URL substring, prohibited tokens).
5. PATCHes the page to set ``Copy LinkedIn`` (chunked ≤ 2000 chars per
   rich_text segment) and ``Estado='En revisión'``.
6. Persists state locally in ``proposals``: ``copy_status='copy_ready'``,
   ``copy_text``, ``copy_model_used``, ``copy_cost_usd_estimate``,
   ``copy_last_attempt_at``.

The first real run (writing to Notion) is performed by the operator after
review; this script gates by ``Estado`` indirectly because Stage 9 only
publishes when ``Estado='Autorizado'`` — Stage 7.5 sets ``En revisión``
on purpose so David can still authorise from Notion.

Schema introspection is live: the script fetches the Publicaciones data
source schema once per run and aborts a row if the ``Copy LinkedIn``
property is missing or if the ``Estado`` option ``En revisión`` is not
defined. NO automatic schema changes — that responsibility belongs to
Hilo C.

Cero secrets en logs: tokens never printed (only lengths + counts).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_STATE_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_CACHE_DB = Path.home() / ".cache" / "rick-discovery" / "llm_cache.sqlite"
DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"
DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789/v1/chat/completions"
DEFAULT_MODEL = "openclaw/main"
DEFAULT_PUBLICACIONES_DS_ID = "dc833f1f-07d9-49d0-82ec-fdfad1c808c4"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
RATE_LIMIT_SLEEP_S = 0.34  # ~3 req/s

CACHE_TTL_S = 7 * 24 * 3600
COST_GUARD_MAX_INPUT_TOKENS = 10_000
APPROX_CHARS_PER_TOKEN = 4
# Rough $/token estimate for Azure OpenAI Responses gpt-5.4 class; used only
# for telemetry (copy_cost_usd_estimate). Override via --cost-per-1k.
DEFAULT_COST_PER_1K_INPUT_USD = 0.005
DEFAULT_COST_PER_1K_OUTPUT_USD = 0.015

RETRY_FAILED_AFTER_S = 24 * 3600

POST_MIN_CHARS = 400
POST_MAX_CHARS = 3000
NOTION_RICH_TEXT_SEGMENT_MAX = 2000
PROHIBITED_TOKENS = ("[TODO]", "__", "<")

COPY_LINKEDIN_PROP = "Copy LinkedIn"
ESTADO_PROP = "Estado"
ESTADO_TARGET = "En revisión"

LLM_TIMEOUT_S = 60.0
LLM_MAX_RETRIES = 2

NOTION_MAX_RETRIES = 5
NOTION_BACKOFF_BASE_S = 0.5

# Columns added to ``proposals`` (idempotent ALTER TABLE).
COPY_COLUMNS: dict[str, str] = {
    "copy_status": "TEXT",
    "copy_last_attempt_at": "INTEGER",
    "copy_last_error": "TEXT",
    "copy_text": "TEXT",
    "copy_model_used": "TEXT",
    "copy_cost_usd_estimate": "REAL",
}


# ---------- Logging ----------

def log_event(event: str, *, ops_log: Path = DEFAULT_OPS_LOG, **fields: Any) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    try:
        ops_log.parent.mkdir(parents=True, exist_ok=True)
        with open(ops_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ---------- State DB migration ----------

def ensure_copy_columns(db_path: Path) -> None:
    """Idempotent ALTER TABLE for the Stage 7.5 columns."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA table_info(proposals)").fetchall()
        if not rows:
            raise RuntimeError(
                f"Table 'proposals' missing in {db_path}. Run Stage 6 first."
            )
        existing = {r[1] for r in rows}
        for col, typ in COPY_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE proposals ADD COLUMN {col} {typ}")
        conn.commit()
    finally:
        conn.close()


# ---------- Candidate selection ----------

def read_pending_proposals(
    db_path: Path,
    *,
    force: bool,
    limit: int,
    only_proposal_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return proposals eligible for copy generation.

    Selection rules (matching the spec):
      * ``notion_page_id IS NOT NULL``
      * ``image_status='ok'``
      * ``copy_status IS NULL``, OR ``copy_status='failed'`` with last
        attempt older than ``RETRY_FAILED_AFTER_S``.
      * ``--force`` ignores ``copy_status`` entirely.
      * ``--proposal-id N`` restricts to that single id (still requires
        notion_page_id + image_status='ok' unless ``--force``).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        params: list[Any] = []
        if force:
            sql = (
                "SELECT id, titular, hook, angulo, fuentes_urls, disciplinas, "
                "       notion_page_id, image_status, copy_status, "
                "       copy_last_attempt_at "
                "FROM proposals WHERE notion_page_id IS NOT NULL "
            )
        else:
            now = int(time.time())
            sql = (
                "SELECT id, titular, hook, angulo, fuentes_urls, disciplinas, "
                "       notion_page_id, image_status, copy_status, "
                "       copy_last_attempt_at "
                "FROM proposals "
                "WHERE notion_page_id IS NOT NULL "
                "  AND COALESCE(image_status,'') = 'ok' "
                "  AND ( copy_status IS NULL "
                "        OR (copy_status = 'failed' "
                "            AND (copy_last_attempt_at IS NULL "
                "                 OR copy_last_attempt_at < ?)) ) "
            )
            params.append(now - RETRY_FAILED_AFTER_S)
        if only_proposal_id is not None:
            sql += " AND id = ? "
            params.append(int(only_proposal_id))
        sql += "ORDER BY id ASC LIMIT ?"
        params.append(int(limit))
        rows = list(conn.execute(sql, tuple(params)))
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["fuentes_urls"] = json.loads(d.get("fuentes_urls") or "[]")
            d["disciplinas"] = json.loads(d.get("disciplinas") or "[]")
            out.append(d)
        return out
    finally:
        conn.close()


def mark_copy_ready(
    db_path: Path,
    proposal_id: int,
    *,
    copy_text: str,
    model: str,
    cost_usd: float,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET copy_status='copy_ready', copy_text=?, "
            "copy_model_used=?, copy_cost_usd_estimate=?, "
            "copy_last_attempt_at=?, copy_last_error=NULL WHERE id=?",
            (copy_text, model, float(cost_usd), int(time.time()), proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_copy_status(
    db_path: Path,
    proposal_id: int,
    status: str,
    error: str | None = None,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET copy_status=?, copy_last_attempt_at=?, "
            "copy_last_error=? WHERE id=?",
            (status, int(time.time()), (error or "")[:500], proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- Notion client ----------

class NotionClient:
    def __init__(self, token: str, *, timeout_s: float = 30.0) -> None:
        if not token:
            raise ValueError("NOTION_API_KEY not set")
        self._token = token
        self._client = httpx.Client(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=timeout_s,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return "NotionClient(token=***)"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        delay = NOTION_BACKOFF_BASE_S
        last_exc: Exception | None = None
        for attempt in range(NOTION_MAX_RETRIES):
            time.sleep(RATE_LIMIT_SLEEP_S)
            try:
                if method == "GET":
                    r = self._client.get(path)
                elif method == "PATCH":
                    r = self._client.patch(path, json=payload or {})
                else:  # pragma: no cover
                    raise ValueError(f"unsupported method {method}")
            except httpx.HTTPError as e:  # network-level
                last_exc = e
                time.sleep(delay)
                delay *= 2
                continue
            if r.status_code == 429 or 500 <= r.status_code < 600:
                last_exc = httpx.HTTPStatusError(
                    f"Notion {r.status_code}", request=r.request, response=r,
                )
                time.sleep(delay)
                delay *= 2
                continue
            r.raise_for_status()
            return r.json()
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"Notion {method} {path} exhausted retries")

    def get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path)

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", path, payload)

    def close(self) -> None:
        self._client.close()


def fetch_page(client: NotionClient, page_id: str) -> dict[str, Any]:
    return client.get(f"/pages/{page_id}")


def fetch_publicaciones_schema(
    client: NotionClient, ds_id: str
) -> dict[str, dict[str, Any]]:
    """Return ``{prop_name: {type, options?}}``.

    For ``select`` / ``status`` properties, ``options`` lists the option
    names so callers can validate ``ESTADO_TARGET`` is present.
    """
    ds = client.get(f"/data_sources/{ds_id}")
    out: dict[str, dict[str, Any]] = {}
    for name, p in (ds.get("properties") or {}).items():
        ptype = p.get("type") or "?"
        entry: dict[str, Any] = {"type": ptype}
        if ptype in ("select", "status"):
            opts = ((p.get(ptype) or {}).get("options")) or []
            entry["options"] = [(o.get("name") or "") for o in opts]
        out[name] = entry
    return out


# ---------- Notion property helpers ----------

def _read_rich_text(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    rt = prop.get("rich_text") or []
    return "".join(seg.get("plain_text", "") for seg in rt).strip()


def _read_url(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    return (prop.get("url") or "").strip()


def _read_title(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    rt = prop.get("title") or []
    return "".join(seg.get("plain_text", "") for seg in rt).strip()


def _read_status_or_select_type(prop: dict[str, Any] | None) -> str:
    """Return ``'status'`` or ``'select'`` for the Estado prop on the page."""
    if not prop:
        return "status"
    return prop.get("type") or "status"


# ---------- Prompt ----------

SYSTEM_PROMPT = (
    "Sos Rick, copywriter editorial de Umbral BIM. "
    "Voz: directa, AECO, sin jerga corporativa. "
    "Idioma: español rioplatense neutro. "
    "Hashtags: 3-5 relevantes (#BIM #AECO #Construccion etc según disciplinas)."
)

USER_PROMPT_TEMPLATE = (
    "Convertí esta idea editorial en un post LinkedIn publicable. "
    "Hook ≤120 chars, cuerpo 600-1800 chars, atribución a fuente al final, "
    "hashtags al final.\n"
    "  Titular: {titular}\n"
    "  Ángulo: {angulo}\n"
    "  Disciplinas: {disciplinas}\n"
    "  Body raw: {body_raw}\n"
    "  Fuente: {fuente_url}\n"
    "Devuelvé SOLO el texto del post (sin meta-comentarios)."
)


def _truncate(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


def build_copy_prompt(
    proposal_row: dict[str, Any],
    page_props: dict[str, Any],
) -> tuple[str, str]:
    """Return ``(system_prompt, user_prompt)``.

    Extension point for Hilo B: replace the body of this function to
    refine the prompt without touching the rest of the pipeline.
    """
    titular = proposal_row.get("titular") or _read_title(page_props.get("Título")) or ""
    angulo = proposal_row.get("angulo") or ""
    disciplinas = ", ".join(proposal_row.get("disciplinas") or []) or "BIM"
    fuente_url = (
        _read_url(page_props.get("Fuente primaria"))
        or _read_url(page_props.get("Fuente referente"))
        or (proposal_row.get("fuentes_urls") or [""])[0]
        or ""
    )
    body_raw = _read_rich_text(page_props.get("Body raw")) or _read_rich_text(page_props.get("Cuerpo"))
    body_truncado = _truncate(body_raw or "", 3000)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        titular=titular,
        angulo=angulo,
        disciplinas=disciplinas,
        body_raw=body_truncado,
        fuente_url=fuente_url,
    )
    return SYSTEM_PROMPT, user_prompt


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // APPROX_CHARS_PER_TOKEN)


# ---------- Cache ----------

CACHE_DDL = (
    "CREATE TABLE IF NOT EXISTS llm_cache "
    "(key TEXT PRIMARY KEY, response TEXT NOT NULL, ts INTEGER NOT NULL)"
)


def _cache_key(model: str, prompt: str) -> str:
    """SHA256 keyed with a stage-specific prefix to avoid collisions with Stage 6."""
    return hashlib.sha256(f"stage7_5:{model}\n{prompt}".encode("utf-8")).hexdigest()


def cache_get(cache_db: Path, model: str, prompt: str, *, ttl_s: int = CACHE_TTL_S) -> str | None:
    cache_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_db)
    try:
        conn.execute(CACHE_DDL)
        key = _cache_key(model, prompt)
        row = conn.execute(
            "SELECT response, ts FROM llm_cache WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return None
        if int(time.time()) - int(row[1]) > ttl_s:
            return None
        return row[0]
    finally:
        conn.close()


def cache_put(cache_db: Path, model: str, prompt: str, response: str) -> None:
    cache_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_db)
    try:
        conn.execute(CACHE_DDL)
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (key, response, ts) VALUES (?, ?, ?)",
            (_cache_key(model, prompt), response, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- LLM call ----------

def _gateway_token() -> str | None:
    try:
        cfg = json.loads((Path.home() / ".openclaw" / "openclaw.json").read_text())
        return cfg.get("gateway", {}).get("auth", {}).get("token")
    except (OSError, json.JSONDecodeError):
        return None


def llm_call(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    gateway_url: str,
    auth_token: str,
    timeout_s: float = LLM_TIMEOUT_S,
    max_retries: int = LLM_MAX_RETRIES,
) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    delay = 1.0
    last_err: str = ""
    for attempt in range(max_retries + 1):
        try:
            r = httpx.post(gateway_url, headers=headers, json=body, timeout=timeout_s)
        except httpx.HTTPError as e:
            last_err = f"transport: {e!s:.200s}"
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"LLM call failed: {last_err}") from e
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"]
        if r.status_code == 429 or 500 <= r.status_code < 600:
            last_err = f"HTTP {r.status_code}"
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
        raise RuntimeError(
            f"LLM call failed: HTTP {r.status_code} body={r.text[:200]}"
        )
    raise RuntimeError(f"LLM call exhausted retries: {last_err}")


# ---------- Validation ----------

class CopyValidationError(Exception):
    pass


def validate_copy(
    copy_text: str,
    *,
    source_url: str,
    allow_no_source: bool = False,
) -> None:
    """Raise ``CopyValidationError`` if the LLM output is unfit to publish."""
    if not copy_text or not copy_text.strip():
        raise CopyValidationError("empty_copy")
    n = len(copy_text)
    if n < POST_MIN_CHARS:
        raise CopyValidationError(f"too_short:{n}<{POST_MIN_CHARS}")
    if n > POST_MAX_CHARS:
        raise CopyValidationError(f"too_long:{n}>{POST_MAX_CHARS}")
    for tok in PROHIBITED_TOKENS:
        if tok in copy_text:
            raise CopyValidationError(f"prohibited_token:{tok!r}")
    if not allow_no_source:
        if not source_url or source_url not in copy_text:
            raise CopyValidationError("missing_source_url")


# ---------- Notion write ----------

def _chunk_rich_text(text: str, max_seg: int = NOTION_RICH_TEXT_SEGMENT_MAX) -> list[dict[str, Any]]:
    """Split ``text`` into Notion rich_text segments of ≤ ``max_seg`` chars each."""
    if not text:
        return []
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(text):
        chunk = text[i : i + max_seg]
        out.append({"type": "text", "text": {"content": chunk}})
        i += max_seg
    return out


def write_copy_to_notion(
    client: NotionClient,
    *,
    page_id: str,
    copy_text: str,
    estado_property_type: str,
) -> None:
    """PATCH ``Copy LinkedIn`` (rich_text) and ``Estado`` (select|status)."""
    estado_value: dict[str, Any]
    if estado_property_type == "select":
        estado_value = {"select": {"name": ESTADO_TARGET}}
    else:
        estado_value = {"status": {"name": ESTADO_TARGET}}
    payload = {
        "properties": {
            COPY_LINKEDIN_PROP: {"rich_text": _chunk_rich_text(copy_text)},
            ESTADO_PROP: estado_value,
        }
    }
    client.patch(f"/pages/{page_id}", payload)


# ---------- Per-proposal pipeline ----------

def _estimate_cost_usd(input_chars: int, output_chars: int,
                       *, in_per_1k: float, out_per_1k: float) -> float:
    in_tokens = max(1, input_chars // APPROX_CHARS_PER_TOKEN)
    out_tokens = max(1, output_chars // APPROX_CHARS_PER_TOKEN)
    return (in_tokens / 1000.0) * in_per_1k + (out_tokens / 1000.0) * out_per_1k


def process_proposal(
    *,
    proposal: dict[str, Any],
    notion: NotionClient,
    schema_props: dict[str, dict[str, Any]],
    model: str,
    gateway_url: str,
    gateway_token: str,
    cache_db: Path,
    state_db: Path,
    ops_log: Path,
    dry_run: bool,
    force_overwrite: bool,
    allow_no_source: bool,
    cost_per_1k_input: float,
    cost_per_1k_output: float,
    use_llm: bool = True,
) -> tuple[str, str]:
    """Return ``(status, message)`` for one proposal.

    ``status`` ∈ {``copy_ready``, ``skipped_existing_copy``, ``failed``}.
    """
    pid = int(proposal["id"])
    page_id = proposal["notion_page_id"]

    # Pre-flight schema validation (fail fast, per spec).
    cl_entry = schema_props.get(COPY_LINKEDIN_PROP)
    if cl_entry is None:
        msg = f"notion_property_missing:{COPY_LINKEDIN_PROP}"
        if not dry_run:
            mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg
    if cl_entry.get("type") != "rich_text":
        msg = f"notion_property_wrong_type:{COPY_LINKEDIN_PROP}={cl_entry.get('type')}"
        if not dry_run:
            mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg
    estado_entry = schema_props.get(ESTADO_PROP)
    if estado_entry is None:
        msg = f"notion_property_missing:{ESTADO_PROP}"
        if not dry_run:
            mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg
    if ESTADO_TARGET not in (estado_entry.get("options") or []):
        msg = f"notion_estado_option_missing:{ESTADO_TARGET}"
        if not dry_run:
            mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg

    # Fetch page (skip pre-check on dry-run too, we still want to show the
    # full pipeline shape).
    try:
        page = fetch_page(notion, page_id)
    except httpx.HTTPStatusError as e:
        msg = f"page_fetch_http_{e.response.status_code}"
        if not dry_run:
            mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg
    except Exception as e:  # noqa: BLE001
        msg = f"page_fetch_error:{e!s:.200s}"
        if not dry_run:
            mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg

    props = page.get("properties") or {}
    existing_copy = _read_rich_text(props.get(COPY_LINKEDIN_PROP))
    if existing_copy and not force_overwrite:
        log_event(
            "stage7_5.skip_existing_copy",
            ops_log=ops_log,
            proposal_id=pid,
            notion_page_id=page_id,
            existing_chars=len(existing_copy),
        )
        if not dry_run:
            mark_copy_status(state_db, pid, "copy_ready", error=None)
            # Cache the human copy locally for diff/debug.
            conn = sqlite3.connect(state_db)
            try:
                conn.execute(
                    "UPDATE proposals SET copy_text=? WHERE id=?",
                    (existing_copy, pid),
                )
                conn.commit()
            finally:
                conn.close()
        return "skipped_existing_copy", f"chars={len(existing_copy)}"

    # Build prompt + cost guard.
    system_prompt, user_prompt = build_copy_prompt(proposal, props)
    est_in_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
    if est_in_tokens > COST_GUARD_MAX_INPUT_TOKENS:
        msg = f"cost_guard_aborted:{est_in_tokens}>{COST_GUARD_MAX_INPUT_TOKENS}"
        log_event("stage7_5.cost.aborted", ops_log=ops_log,
                  proposal_id=pid, est_tokens=est_in_tokens)
        if not dry_run:
            mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg

    if not use_llm or dry_run:
        return "dry_run", f"would_call_llm est_in_tokens={est_in_tokens}"

    # Cache lookup.
    cache_prompt_key = system_prompt + "\n---\n" + user_prompt
    cached = cache_get(cache_db, model, cache_prompt_key)
    if cached is not None:
        log_event("stage7_5.cache.hit", ops_log=ops_log, proposal_id=pid, model=model)
        copy_text = cached
    else:
        try:
            copy_text = llm_call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                gateway_url=gateway_url,
                auth_token=gateway_token,
            )
        except Exception as e:  # noqa: BLE001
            msg = f"llm_error:{e!s:.200s}"
            mark_copy_status(state_db, pid, "failed", msg)
            return "failed", msg
        cache_put(cache_db, model, cache_prompt_key, copy_text)

    copy_text = copy_text.strip()

    # Resolve canonical source URL for validation.
    source_url = (
        _read_url(props.get("Fuente primaria"))
        or _read_url(props.get("Fuente referente"))
        or (proposal.get("fuentes_urls") or [""])[0]
        or ""
    )

    try:
        validate_copy(copy_text, source_url=source_url, allow_no_source=allow_no_source)
    except CopyValidationError as e:
        msg = f"validation_failed:{e!s}"
        log_event("stage7_5.validation.failed", ops_log=ops_log,
                  proposal_id=pid, reason=str(e), copy_chars=len(copy_text))
        mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg

    estado_type = (
        _read_status_or_select_type(props.get(ESTADO_PROP))
        or estado_entry.get("type")
        or "status"
    )
    try:
        write_copy_to_notion(
            notion,
            page_id=page_id,
            copy_text=copy_text,
            estado_property_type=estado_type,
        )
    except httpx.HTTPStatusError as e:
        msg = f"notion_write_http_{e.response.status_code}"
        mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg
    except Exception as e:  # noqa: BLE001
        msg = f"notion_write_error:{e!s:.200s}"
        mark_copy_status(state_db, pid, "failed", msg)
        return "failed", msg

    cost = _estimate_cost_usd(
        len(system_prompt) + len(user_prompt),
        len(copy_text),
        in_per_1k=cost_per_1k_input,
        out_per_1k=cost_per_1k_output,
    )
    mark_copy_ready(state_db, pid, copy_text=copy_text, model=model, cost_usd=cost)
    log_event(
        "stage7_5.copy_written",
        ops_log=ops_log,
        proposal_id=pid,
        notion_page_id=page_id,
        copy_len=len(copy_text),
        model=model,
        cost_usd=round(cost, 6),
    )
    return "copy_ready", f"chars={len(copy_text)} cost_usd={cost:.5f}"


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Stage 7.5 LLM copywriter for LinkedIn (transformer core).",
    )
    p.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    p.add_argument("--cache-db", default=str(DEFAULT_CACHE_DB))
    p.add_argument("--ops-log", default=str(DEFAULT_OPS_LOG))
    p.add_argument("--max-copies", type=int, default=3)
    p.add_argument("--proposal-id", type=int, default=None,
                   help="Process only this proposal id.")
    p.add_argument("--dry-run", action="store_true",
                   help="List candidates, do NOT call LLM and do NOT write Notion.")
    p.add_argument("--force", action="store_true",
                   help="Ignore copy_status guard.")
    p.add_argument("--force-overwrite", action="store_true",
                   help="Overwrite existing non-empty Copy LinkedIn in Notion.")
    p.add_argument("--allow-no-source", action="store_true",
                   help="Skip source-URL substring validation.")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    p.add_argument("--publicaciones-ds-id", default=DEFAULT_PUBLICACIONES_DS_ID)
    p.add_argument("--cost-per-1k-input-usd", type=float,
                   default=DEFAULT_COST_PER_1K_INPUT_USD)
    p.add_argument("--cost-per-1k-output-usd", type=float,
                   default=DEFAULT_COST_PER_1K_OUTPUT_USD)
    args = p.parse_args(argv)

    state_db = Path(args.state_db)
    cache_db = Path(args.cache_db)
    ops_log = Path(args.ops_log)

    ensure_copy_columns(state_db)

    proposals = read_pending_proposals(
        state_db,
        force=args.force,
        limit=args.max_copies,
        only_proposal_id=args.proposal_id,
    )
    log_event(
        "stage7_5.input.loaded", ops_log=ops_log,
        n=len(proposals), force=args.force, max_copies=args.max_copies,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"stage7_5 dry-run: {len(proposals)} candidate(s)")
        for prop in proposals:
            print(
                f"  id={prop['id']} status={prop.get('copy_status') or '(null)'} "
                f"page={prop['notion_page_id']} titular={(prop.get('titular') or '')[:80]!r}"
            )
        print(
            f"stage7_5: copy_ready=0 skipped_existing=0 failed=0 "
            f"dry_run=True force={args.force}"
        )
        return 0

    if not proposals:
        print("no candidates (need notion_page_id + image_status=ok + copy_status null/failed)")
        print(
            f"stage7_5: copy_ready=0 skipped_existing=0 failed=0 "
            f"dry_run=False force={args.force}"
        )
        return 0

    notion_token = os.environ.get("NOTION_API_KEY", "")
    if not notion_token:
        print("ERROR: NOTION_API_KEY not set", file=sys.stderr)
        return 2
    gateway_token = _gateway_token() or os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
    if not gateway_token:
        print("ERROR: no gateway token (set OPENCLAW_GATEWAY_TOKEN or ~/.openclaw/openclaw.json)",
              file=sys.stderr)
        return 2

    notion = NotionClient(notion_token)
    try:
        try:
            schema_props = fetch_publicaciones_schema(notion, args.publicaciones_ds_id)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: cannot fetch Publicaciones schema: {e!s:.200s}",
                  file=sys.stderr)
            return 2

        ok = skipped = failed = 0
        for prop in proposals:
            status, msg = process_proposal(
                proposal=prop,
                notion=notion,
                schema_props=schema_props,
                model=args.model,
                gateway_url=args.gateway_url,
                gateway_token=gateway_token,
                cache_db=cache_db,
                state_db=state_db,
                ops_log=ops_log,
                dry_run=False,
                force_overwrite=args.force_overwrite,
                allow_no_source=args.allow_no_source,
                cost_per_1k_input=args.cost_per_1k_input_usd,
                cost_per_1k_output=args.cost_per_1k_output_usd,
            )
            if status == "copy_ready":
                ok += 1
                print(f"copy_ready proposal_id={prop['id']} {msg}")
            elif status == "skipped_existing_copy":
                skipped += 1
                print(f"skip_existing proposal_id={prop['id']} {msg}")
            else:
                failed += 1
                print(f"FAIL proposal_id={prop['id']} {msg}", file=sys.stderr)
    finally:
        notion.close()

    print(
        f"stage7_5: copy_ready={ok} skipped_existing={skipped} "
        f"failed={failed} dry_run=False force={args.force}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
