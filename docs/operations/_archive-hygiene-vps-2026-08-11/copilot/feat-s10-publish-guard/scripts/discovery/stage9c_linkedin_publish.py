"""Stage 9c: publish LinkedIn drafts (real POST /v2/ugcPosts).

Reads ``proposals.linkedin_draft_payload`` rows produced by
``stage9_linkedin_draft.py`` and POSTs each to LinkedIn.

Pipeline per row:
  1. Skip if ``linkedin_status='published'`` (idempotent).
  2. Strip every meta key (``_endpoint``, ``_offline_draft``, ``_built_at``,
     ``_proposal_id``, ``_notion_page_id`` and any other ``_*``).
  3. Replace the placeholder author URN with the real one
     (``--author-urn`` > env ``LINKEDIN_AUTHOR_URN`` > stored ``member_urn``).
  4. Refresh the access token in-place if it expires in <5min
     (delegated to ``stage9b_linkedin_oauth.get_valid_access_token``).
  5. POST to ``https://api.linkedin.com/v2/ugcPosts`` with headers
     ``Authorization: Bearer …`` + ``X-Restli-Protocol-Version: 2.0.0``.
  6. On HTTP 201: capture ``x-restli-id`` (post URN) and UPDATE
     ``linkedin_status='published'``, ``linkedin_post_urn=<urn>``,
     ``linkedin_published_at=<UTC ISO>``. Otherwise UPDATE
     ``linkedin_status='failed'``, ``linkedin_last_error=<text>``.
  7. Sleep ≥2s between successful POSTs (rate-limit guard).

Cero secrets en logs: tokens never printed (not even prefixes).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import hashlib
import logging

import httpx

from scripts.discovery import stage9b_linkedin_oauth as oauth
from scripts.discovery.lib.publish_guard import (
    PublishBlockedError,
    assert_can_publish,
)

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_UGC_PATH = "/v2/ugcPosts"
RATE_LIMIT_SLEEP_S = 2.0

DEFAULT_STATE_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"

AUTHOR_URN_PLACEHOLDER = "urn:li:person:__TODO_RESOLVE_AT_PUBLISH__"

PUBLISH_COLUMNS: dict[str, str] = {
    "linkedin_post_urn": "TEXT",
    "linkedin_published_at": "TEXT",
}


# ---------- Logging ----------

def log_event(event: str, **fields: Any) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    try:
        DEFAULT_OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_OPS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ---------- Schema ----------

def ensure_publish_columns(db_path: Path) -> None:
    """Idempotent ALTER TABLE for Stage 9c columns."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA table_info(proposals)").fetchall()
        if not rows:
            raise RuntimeError(
                f"Table 'proposals' missing in {db_path}. Run Stage 6 first."
            )
        existing = {r[1] for r in rows}
        for col, typ in PUBLISH_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE proposals ADD COLUMN {col} {typ}")
        conn.commit()
    finally:
        conn.close()


# ---------- State access ----------

def read_publishable(
    db_path: Path, *, limit: int,
) -> list[dict[str, Any]]:
    """Return draft_ready rows (skipping already-published)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = list(conn.execute(
            "SELECT id, titular, notion_page_id, linkedin_status, "
            "       linkedin_draft_payload "
            "FROM proposals "
            "WHERE linkedin_draft_payload IS NOT NULL "
            "  AND COALESCE(linkedin_status, '') IN ('draft_ready', '') "
            "ORDER BY id ASC LIMIT ?",
            (int(limit),),
        ))
        return [dict(r) for r in rows]
    finally:
        conn.close()


def is_already_published(db_path: Path, proposal_id: int) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT linkedin_status FROM proposals WHERE id=?",
            (int(proposal_id),),
        ).fetchone()
        return bool(row and row[0] == "published")
    finally:
        conn.close()


def mark_published(
    db_path: Path, proposal_id: int, *, post_urn: str,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET linkedin_status='published', "
            "linkedin_post_urn=?, linkedin_published_at=?, "
            "linkedin_last_error=NULL WHERE id=?",
            (post_urn, now_iso, int(proposal_id)),
        )
        conn.commit()
    finally:
        conn.close()


def mark_failed(
    db_path: Path, proposal_id: int, *, error: str,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET linkedin_status='failed', "
            "linkedin_last_error=?, linkedin_last_attempt_at=? WHERE id=?",
            ((error or "")[:500], int(time.time()), int(proposal_id)),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- Payload sanitisation ----------

def strip_meta_keys(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy with all ``_*`` top-level keys removed."""
    return {k: v for k, v in payload.items() if not k.startswith("_")}


def resolve_author(
    payload: dict[str, Any], *, author_urn: str,
) -> dict[str, Any]:
    """Return a copy with ``author`` set to the real URN."""
    out = dict(payload)
    if not author_urn:
        raise ValueError("author_urn is required")
    out["author"] = author_urn
    return out


# ---------- HTTP ----------

def post_ugc(
    *, payload: dict[str, Any], access_token: str,
    client: httpx.Client | None = None,
) -> tuple[int, str, dict[str, Any]]:
    """POST to /v2/ugcPosts. Return (status_code, post_urn, response_body)."""
    owns = client is None
    if owns:
        client = httpx.Client(timeout=30.0)
    try:
        r = client.post(
            f"{LINKEDIN_API_BASE}{LINKEDIN_UGC_PATH}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        body: dict[str, Any] = {}
        try:
            body = r.json() if r.content else {}
        except ValueError:
            body = {"_raw_text": (r.text or "")[:500]}
        post_urn = (
            r.headers.get("x-restli-id")
            or r.headers.get("X-RestLi-Id")
            or body.get("id")
            or ""
        )
        return r.status_code, post_urn, body
    finally:
        if owns:
            client.close()


# ---------- Stage 10 publish-guard helpers ----------

_WS_RE_NORM = None  # populated lazily


def _normalize_text(s: str) -> str:
    """Mirror of ``dedup.normalize_text`` — kept inline so this file does
    not require Hilo 3 at import time."""
    import re as _re
    global _WS_RE_NORM
    if _WS_RE_NORM is None:
        _WS_RE_NORM = _re.compile(r"\s+")
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    return _WS_RE_NORM.sub(" ", s.strip().lower())


def compute_payload_content_hash(
    payload: dict[str, Any], *, canonical_url: str = "",
    title: str = "",
) -> str:
    """sha256 over canonical_url + normalized title + LinkedIn copy text.

    Matches ``dedup.compute_content_hash`` semantics so the hash computed
    pre-POST collides with the hash stored by ``register_published`` after
    a successful publish.
    """
    try:
        text = (
            payload.get("specificContent", {})
            .get("com.linkedin.ugc.ShareContent", {})
            .get("shareCommentary", {})
            .get("text", "")
        ) or ""
    except AttributeError:
        text = ""
    url = (canonical_url or "").strip()
    payload_str = f"{url}\n{_normalize_text(title)}\n{_normalize_text(text)}"
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


def fetch_notion_page(page_id: str) -> dict[str, Any]:
    """GET https://api.notion.com/v1/pages/{id}.

    Pure helper isolated for test injection. Reads ``NOTION_API_KEY`` from
    env. Returns ``{"id": page_id}`` if the env var is missing — the guard
    will then block on every Notion-checkbox gate (correct fail-safe).
    """
    if not page_id:
        return {}
    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        return {"id": page_id}
    try:
        r = httpx.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2025-09-03",
            },
            timeout=15.0,
        )
        if r.status_code == 200:
            return r.json()
    except (httpx.HTTPError, ValueError):
        pass
    return {"id": page_id}


def _emit_dry_run_json(
    *, proposal_id: int, page_id: str, content_hash: str,
    would_publish: bool, reasons_blocked: list[str],
) -> None:
    """Stable JSON contract for ``--dry-run`` (Hilo 6 spec §5.4)."""
    print(json.dumps({
        "proposal_id": proposal_id,
        "page_id": page_id,
        "content_hash": content_hash,
        "would_publish": would_publish,
        "reasons_blocked": reasons_blocked,
    }, ensure_ascii=False))


def _notify_blocked(page_id: str, reasons: list[str]) -> None:
    """Best-effort Notion review-comment when a publish is blocked.

    Imports lazily to keep stage9c usable when Notion creds are missing.
    Never raises.
    """
    if not page_id:
        return
    try:
        from scripts.discovery import stage7_5_post_review_comment as srvc
    except ImportError:
        return
    fn = getattr(srvc, "post_blocked_comment", None) or getattr(
        srvc, "post_review_comment", None
    )
    if fn is None:
        return
    try:  # pragma: no cover — exercised only with Notion creds
        fn(page_id=page_id, blocked_reasons=reasons)
    except Exception as e:  # noqa: BLE001
        logger.warning("stage9c.notify_blocked_failed page_id=%s err=%s",
                       page_id, e)


# ---------- Per-row pipeline ----------

def publish_one(
    *, row: dict[str, Any], state_db: Path, author_urn: str,
    access_token: str, dry_run: bool,
    client: httpx.Client | None = None,
    notion_fetcher=fetch_notion_page,
) -> tuple[str, str]:
    """Return (status, message). Status: published | skipped | failed | blocked."""
    pid = int(row["id"])
    if is_already_published(state_db, pid):
        return "skipped", "already published"

    raw = row.get("linkedin_draft_payload") or ""
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as e:
        msg = f"bad JSON in payload: {e!s:.120s}"
        if not dry_run:
            mark_failed(state_db, pid, error=msg)
        return "failed", msg

    clean = strip_meta_keys(payload)
    clean = resolve_author(clean, author_urn=author_urn)

    # ---- Stage 10 publish guard: 6 gates BEFORE any POST ----
    notion_page_id = (row.get("notion_page_id") or "").strip()
    notion_page = notion_fetcher(notion_page_id) if notion_page_id else {}
    content_hash = compute_payload_content_hash(clean)

    db_conn = sqlite3.connect(state_db)
    try:
        try:
            assert_can_publish(notion_page, content_hash, db_conn)
        except PublishBlockedError as e:
            reasons = e.reasons
            logger.warning(
                "stage9c.blocked proposal_id=%s page_id=%s reasons=%s",
                pid, notion_page_id, reasons,
            )
            log_event(
                "stage9c.blocked",
                proposal_id=pid, page_id=notion_page_id,
                content_hash=content_hash, reasons=reasons,
            )
            if dry_run:
                _emit_dry_run_json(
                    proposal_id=pid, page_id=notion_page_id,
                    content_hash=content_hash, would_publish=False,
                    reasons_blocked=reasons,
                )
            else:
                _notify_blocked(notion_page_id, reasons)
            return "blocked", f"gates_failed={reasons}"

        if dry_run:
            _emit_dry_run_json(
                proposal_id=pid, page_id=notion_page_id,
                content_hash=content_hash, would_publish=True,
                reasons_blocked=[],
            )
            return "skipped", "dry-run"

        try:
            status_code, post_urn, body = post_ugc(
                payload=clean, access_token=access_token, client=client,
            )
        except Exception as e:  # noqa: BLE001
            msg = f"http error: {e!s:.200s}"
            mark_failed(state_db, pid, error=msg)
            return "failed", msg

        if status_code == 201 and post_urn:
            mark_published(state_db, pid, post_urn=post_urn)
            published_url = (
                f"https://www.linkedin.com/feed/update/{post_urn}/"
            )
            try:
                # Lazy import: Hilo 3 dedup may not be merged yet.
                from scripts.discovery.lib import dedup as _dedup
                _dedup.register_published(
                    db_conn, content_hash, published_url, "linkedin",
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "stage9c.register_published_failed pid=%s err=%s",
                    pid, e,
                )
            log_event(
                "stage9c.published",
                proposal_id=pid, post_urn=post_urn,
                content_hash=content_hash,
            )
            return "published", post_urn

        # Failure path. Body may contain LinkedIn error message; safe to log.
        err_text = json.dumps(body)[:300] if body else f"HTTP {status_code}"
        msg = f"HTTP {status_code} {err_text}"
        mark_failed(state_db, pid, error=msg)
        log_event("stage9c.failed",
                  proposal_id=pid, http_status=status_code)
        return "failed", msg
    finally:
        db_conn.close()


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Stage 9c: publish LinkedIn drafts to /v2/ugcPosts."
    )
    p.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    p.add_argument("--max-posts", type=int, default=1)
    p.add_argument("--dry-run", action="store_true",
                   help="Print sanitised payloads; do not POST.")
    p.add_argument("--author-urn", default=None,
                   help="Override LINKEDIN_AUTHOR_URN env / stored member_urn.")
    p.add_argument("--tokens-path", type=Path, default=oauth.DEFAULT_TOKENS_PATH)
    args = p.parse_args(argv)

    state_db = Path(args.state_db)
    ensure_publish_columns(state_db)

    rows = read_publishable(state_db, limit=args.max_posts)
    log_event("stage9c.input.loaded",
              n=len(rows), max_posts=args.max_posts, dry_run=args.dry_run)
    if not rows:
        print("no draft_ready rows")
        return 0

    # Resolve author URN: --author-urn > env > stored member_urn.
    author_urn = (args.author_urn or "").strip()
    if not author_urn:
        author_urn = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip()
    if not author_urn:
        try:
            author_urn = oauth.get_member_urn(args.tokens_path)
        except FileNotFoundError:
            author_urn = ""
    if not author_urn or author_urn == AUTHOR_URN_PLACEHOLDER:
        print("ERROR: cannot resolve author URN. Run stage9b whoami first or "
              "pass --author-urn / LINKEDIN_AUTHOR_URN.", file=sys.stderr)
        return 2

    # Get / refresh access token (skip in dry-run).
    access_token = ""
    if not args.dry_run:
        try:
            access_token = oauth.get_valid_access_token(args.tokens_path)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"ERROR: cannot get access_token: {e}", file=sys.stderr)
            return 2

    published = skipped = failed = blocked = 0
    for i, row in enumerate(rows):
        if i > 0 and not args.dry_run:
            time.sleep(RATE_LIMIT_SLEEP_S)
        status, msg = publish_one(
            row=row, state_db=state_db, author_urn=author_urn,
            access_token=access_token, dry_run=args.dry_run,
        )
        if status == "published":
            published += 1
            print(f"published proposal_id={row['id']} post_urn={msg}")
        elif status == "skipped":
            skipped += 1
            print(f"skip proposal_id={row['id']} {msg}")
        elif status == "blocked":
            blocked += 1
            # Blocking is the expected outcome of the guard, NOT an error.
            # exit 0 (per Hilo 6 spec §5.3).
            print(f"blocked proposal_id={row['id']} {msg}")
        else:
            failed += 1
            print(f"FAIL proposal_id={row['id']} {msg}", file=sys.stderr)

    print(
        f"summary published={published} skipped={skipped} "
        f"blocked={blocked} failed={failed} dry_run={args.dry_run}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
