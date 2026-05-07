"""Stage 9: build LinkedIn draft payloads for approved Publicaciones pages.

For each proposal that already has:
  * ``notion_page_id`` (created by Stage 7), and
  * ``image_status='ok'`` (created by Stage 8), and
  * ``linkedin_status IS NULL`` (or ``--force``),

this script:

1. Fetches the Notion page properties + body blocks.
2. Verifies that the page's ``Estado`` (status) property is one of the
   APPROVED states (default: ``Aprobado`` or ``Autorizado``). If not, the
   row is marked ``linkedin_status='awaiting_approval'`` and skipped.
3. Builds the post text from ``Copy LinkedIn`` (rich_text) when non-empty,
   otherwise from the body paragraph blocks (headings stripped).
4. Normalises text: first line = hook, body trimmed, source URL appended,
   capped at ``MAX_POST_CHARS`` (3000).
5. Builds a LinkedIn ``/v2/ugcPosts`` payload (offline only — no HTTP call
   is made in this scaffold) and persists the JSON to
   ``proposals.linkedin_draft_payload`` plus ``linkedin_status='draft_ready'``.

This is **offline scaffolding**:
  * No LinkedIn HTTP call is performed.
  * No OAuth flow is implemented (gap documented in
    ``docs/spikes/O18-linkedin-auth-gap-report.md``).
  * Stage 9b (real publish) will plug into the same SQLite columns and
    re-use the persisted payload.

Schema introspection (live, not hardcoded):
  * The Notion ``Estado`` property and the optional ``Copy LinkedIn`` /
    ``Fuente primaria`` / ``Fuente referente`` properties are read at
    runtime from the page response — missing properties fall back to body
    blocks or are skipped silently.

Cero secrets en logs: tokens never printed (only lengths + counts).
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

import httpx

DEFAULT_STATE_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
RATE_LIMIT_SLEEP_S = 0.34  # ~3 req/s

MAX_POST_CHARS = 3000
DEFAULT_APPROVED_STATES = ("Aprobado", "Autorizado")

# LinkedIn UGC Posts payload constants (used to build the offline draft).
LINKEDIN_UGC_ENDPOINT = "/v2/ugcPosts"
LINKEDIN_VISIBILITY_PUBLIC = "PUBLIC"
LINKEDIN_LIFECYCLE_DRAFT = "DRAFT"

# Author URN placeholder (resolved at real-publish time, not here).
AUTHOR_URN_ENV = "LINKEDIN_AUTHOR_URN"
AUTHOR_URN_PLACEHOLDER = "urn:li:person:__TODO_RESOLVE_AT_PUBLISH__"


# ---------- Logging ----------

def log_event(event: str, **fields: Any) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    try:
        DEFAULT_OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_OPS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ---------- State DB migration ----------

LINKEDIN_COLUMNS: dict[str, str] = {
    # Re-declare image_status defensively in case Stage 8 never ran in this
    # environment. ALTER TABLE ADD COLUMN is a no-op when the column exists.
    "image_status": "TEXT",
    "linkedin_status": "TEXT",
    "linkedin_draft_payload": "TEXT",
    "linkedin_last_attempt_at": "INTEGER",
    "linkedin_last_error": "TEXT",
}


def ensure_linkedin_columns(db_path: Path) -> None:
    """Idempotent ALTER TABLE for the LinkedIn-stage columns."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA table_info(proposals)").fetchall()
        if not rows:
            raise RuntimeError(
                f"Table 'proposals' missing in {db_path}. Run Stage 6 first."
            )
        existing = {r[1] for r in rows}
        for col, typ in LINKEDIN_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE proposals ADD COLUMN {col} {typ}")
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

    def get(self, path: str) -> dict[str, Any]:
        time.sleep(RATE_LIMIT_SLEEP_S)
        r = self._client.get(path)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()


def fetch_page(client: NotionClient, page_id: str) -> dict[str, Any]:
    return client.get(f"/pages/{page_id}")


def fetch_page_blocks(client: NotionClient, page_id: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        resp = client.get(path)
        blocks.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        if not cursor:
            break
    return blocks


# ---------- State access ----------

def read_pending_proposals(
    db_path: Path, *, force: bool, limit: int
) -> list[dict[str, Any]]:
    """Return proposals ready for LinkedIn drafting.

    Selection rules:
      * ``notion_page_id IS NOT NULL`` (Stage 7 done)
      * ``image_status = 'ok'`` (Stage 8 done)
      * ``linkedin_status`` is NULL/empty, OR ``--force`` (regenerate
        existing draft).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT id, titular, hook, angulo, fuentes_urls, disciplinas, "
            "       notion_page_id, linkedin_status, linkedin_draft_payload "
            "FROM proposals "
            "WHERE notion_page_id IS NOT NULL "
            "  AND COALESCE(image_status, '') = 'ok' "
        )
        if not force:
            sql += "  AND COALESCE(linkedin_status, '') = '' "
        sql += "ORDER BY id ASC LIMIT ?"
        rows = list(conn.execute(sql, (int(limit),)))
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["fuentes_urls"] = json.loads(d.get("fuentes_urls") or "[]")
            d["disciplinas"] = json.loads(d.get("disciplinas") or "[]")
            out.append(d)
        return out
    finally:
        conn.close()


def mark_proposal_draft_ready(
    db_path: Path, proposal_id: int, payload: dict[str, Any]
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET linkedin_status='draft_ready', "
            "linkedin_draft_payload=?, linkedin_last_attempt_at=?, "
            "linkedin_last_error=NULL WHERE id=?",
            (json.dumps(payload, ensure_ascii=False), int(time.time()),
             proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_proposal_status(
    db_path: Path, proposal_id: int, status: str, error: str | None = None
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET linkedin_status=?, linkedin_last_attempt_at=?, "
            "linkedin_last_error=? WHERE id=?",
            (status, int(time.time()), (error or "")[:500], proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


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


def _read_status_name(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    s = prop.get("status") or {}
    return (s.get("name") or "").strip()


def _read_title(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    rt = prop.get("title") or []
    return "".join(seg.get("plain_text", "") for seg in rt).strip()


def extract_paragraphs_from_blocks(blocks: list[dict[str, Any]]) -> list[str]:
    """Return paragraph text lines from page body, stripping headings.

    Headings are kept as a single capitalised line (no markdown ``#``).
    Bulleted/numbered list items become ``- text`` lines.
    """
    lines: list[str] = []
    for b in blocks:
        t = b.get("type")
        node = b.get(t) or {}
        rt = node.get("rich_text") or []
        text = "".join(seg.get("plain_text", "") for seg in rt).strip()
        if not text:
            continue
        if t in ("heading_1", "heading_2", "heading_3"):
            lines.append(text)
        elif t in ("bulleted_list_item", "numbered_list_item"):
            lines.append(f"- {text}")
        elif t == "paragraph":
            lines.append(text)
        # other block types (image, divider, ...) ignored on purpose
    return lines


# ---------- Post text builder ----------

def build_post_text(
    *, copy_linkedin: str, body_lines: list[str], source_url: str,
    titular: str, hook: str,
) -> str:
    """Assemble the LinkedIn post text.

    Precedence:
      1. ``Copy LinkedIn`` rich_text from Notion (if non-empty).
      2. Body paragraph lines from the page.
      3. Fallback: ``hook`` + ``titular`` from the proposal row.

    First line is the *hook*; if a content source already starts with a
    short line we keep it; otherwise we prepend the proposal hook.
    Source URL is appended on its own trailing line. Total length is
    capped at ``MAX_POST_CHARS`` (LinkedIn ugcPosts hard limit is 3000).
    """
    if copy_linkedin.strip():
        text = copy_linkedin.strip()
    elif body_lines:
        text = "\n\n".join(body_lines).strip()
    else:
        text = (hook or titular or "").strip()

    # Ensure first line is a short hook (≤ 220 chars). If the leading
    # paragraph is longer, prepend the proposal hook (or the titular).
    first_line = text.split("\n", 1)[0].strip()
    if len(first_line) > 220 and (hook or titular):
        prepend = (hook or titular).strip()
        if prepend and prepend not in text:
            text = f"{prepend}\n\n{text}"

    # Append source URL (skip if already in text).
    if source_url and source_url not in text:
        text = f"{text.rstrip()}\n\n{source_url}".strip()

    if len(text) > MAX_POST_CHARS:
        # Reserve room for an ellipsis + URL on a clean break.
        if source_url and source_url in text:
            head_budget = MAX_POST_CHARS - len(source_url) - 4
            head = text[: max(0, head_budget)].rstrip()
            text = f"{head}…\n\n{source_url}"
        else:
            text = text[: MAX_POST_CHARS - 1].rstrip() + "…"
    return text


# ---------- LinkedIn payload builder ----------

def build_linkedin_payload(
    *, proposal: dict[str, Any], page: dict[str, Any], post_text: str,
    source_url: str,
) -> dict[str, Any]:
    """Build a LinkedIn ``/v2/ugcPosts`` payload (offline draft).

    Author URN is read from ``LINKEDIN_AUTHOR_URN`` env var if set,
    otherwise a placeholder is written (resolved at real publish time).
    """
    author = os.environ.get(AUTHOR_URN_ENV, "").strip() or AUTHOR_URN_PLACEHOLDER

    media: list[dict[str, Any]] = []
    cover = (page.get("cover") or {})
    cover_url = ""
    if cover.get("type") == "external":
        cover_url = cover.get("external", {}).get("url", "")
    elif cover.get("type") == "file":
        cover_url = cover.get("file", {}).get("url", "")
    if cover_url:
        media.append({
            "status": "READY",
            "originalUrl": cover_url,
            "title": {"text": (proposal.get("titular") or "")[:200]},
        })

    share_content: dict[str, Any] = {
        "shareCommentary": {"text": post_text},
        "shareMediaCategory": "ARTICLE" if (media or source_url) else "NONE",
    }
    if media:
        share_content["media"] = media
    elif source_url:
        share_content["media"] = [{
            "status": "READY",
            "originalUrl": source_url,
        }]

    return {
        "_endpoint": LINKEDIN_UGC_ENDPOINT,  # for future Stage 9b real call
        "_offline_draft": True,
        "_built_at": datetime.now(timezone.utc).isoformat(),
        "_proposal_id": proposal["id"],
        "_notion_page_id": proposal["notion_page_id"],
        "author": author,
        "lifecycleState": LINKEDIN_LIFECYCLE_DRAFT,
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_content,
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": LINKEDIN_VISIBILITY_PUBLIC,
        },
    }


# ---------- Per-proposal pipeline ----------

def process_proposal(
    *, proposal: dict[str, Any], client: NotionClient,
    approved_states: tuple[str, ...], dry_run: bool, state_db: Path,
) -> tuple[str, dict[str, Any] | None, str]:
    """Return ``(status, payload_or_none, message)`` for a single proposal.

    ``status`` is one of: ``draft_ready``, ``awaiting_approval``, ``failed``.
    """
    page_id = proposal["notion_page_id"]
    try:
        page = fetch_page(client, page_id)
    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code} on /pages/{page_id}"
        return "failed", None, msg
    except Exception as e:  # noqa: BLE001
        return "failed", None, f"page fetch error: {e!s:.200s}"

    props = page.get("properties") or {}
    estado = _read_status_name(props.get("Estado"))
    if estado not in approved_states:
        return "awaiting_approval", None, f"Estado={estado!r} not in {approved_states}"

    copy_linkedin = _read_rich_text(props.get("Copy LinkedIn"))
    source_url = (
        _read_url(props.get("Fuente primaria"))
        or _read_url(props.get("Fuente referente"))
        or (proposal.get("fuentes_urls") or [""])[0]
    )

    body_lines: list[str] = []
    if not copy_linkedin:
        try:
            blocks = fetch_page_blocks(client, page_id)
            body_lines = extract_paragraphs_from_blocks(blocks)
        except Exception as e:  # noqa: BLE001
            return "failed", None, f"blocks fetch error: {e!s:.200s}"

    titular = _read_title(props.get("Título")) or proposal.get("titular") or ""
    post_text = build_post_text(
        copy_linkedin=copy_linkedin, body_lines=body_lines,
        source_url=source_url, titular=titular,
        hook=proposal.get("hook") or "",
    )
    payload = build_linkedin_payload(
        proposal=proposal, page=page, post_text=post_text,
        source_url=source_url,
    )
    if not dry_run:
        mark_proposal_draft_ready(state_db, proposal["id"], payload)
    return "draft_ready", payload, f"chars={len(post_text)}"


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 9 LinkedIn draft scaffold (offline).")
    p.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    p.add_argument("--max-drafts", type=int, default=3)
    p.add_argument("--dry-run", action="store_true",
                   help="Build payloads in-memory only; do not write SQLite.")
    p.add_argument("--force", action="store_true",
                   help="Regenerate drafts even if linkedin_status is set.")
    p.add_argument("--approved-state", action="append", default=None,
                   help=f"Notion 'Estado' values that count as approved. "
                        f"Repeatable. Default: {list(DEFAULT_APPROVED_STATES)}")
    args = p.parse_args(argv)

    state_db = Path(args.state_db)
    ensure_linkedin_columns(state_db)

    approved_states = tuple(args.approved_state or DEFAULT_APPROVED_STATES)
    proposals = read_pending_proposals(
        state_db, force=args.force, limit=args.max_drafts,
    )
    log_event("stage9.input.loaded",
              n=len(proposals), force=args.force, max_drafts=args.max_drafts)
    if not proposals:
        print("no candidates (need notion_page_id + image_status=ok)")
        return 0

    token = os.environ.get("NOTION_API_KEY", "")
    if not token:
        print("ERROR: NOTION_API_KEY not set", file=sys.stderr)
        return 2

    client = NotionClient(token)
    ok = skipped = failed = 0
    try:
        for prop in proposals:
            status, payload, msg = process_proposal(
                proposal=prop, client=client,
                approved_states=approved_states, dry_run=args.dry_run,
                state_db=state_db,
            )
            if status == "draft_ready":
                ok += 1
                log_event("stage9.draft.ready",
                          proposal_id=prop["id"],
                          page_id=prop["notion_page_id"],
                          payload_chars=len(json.dumps(payload or {})))
                print(f"draft_ready proposal_id={prop['id']} {msg}")
            elif status == "awaiting_approval":
                skipped += 1
                if not args.dry_run:
                    mark_proposal_status(
                        state_db, prop["id"], "awaiting_approval", msg,
                    )
                log_event("stage9.draft.awaiting_approval",
                          proposal_id=prop["id"],
                          page_id=prop["notion_page_id"])
                print(f"skip proposal_id={prop['id']} {msg}")
            else:
                failed += 1
                if not args.dry_run:
                    mark_proposal_status(state_db, prop["id"], "failed", msg)
                log_event("stage9.draft.failed",
                          proposal_id=prop["id"],
                          page_id=prop["notion_page_id"])
                print(f"FAIL proposal_id={prop['id']} {msg}", file=sys.stderr)
    finally:
        client.close()

    print(f"summary draft_ready={ok} awaiting_approval={skipped} "
          f"failed={failed} dry_run={args.dry_run} force={args.force}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
