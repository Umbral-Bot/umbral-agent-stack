"""Stage 7.5 helper — post a review-pending comment on a Publicaciones page.

When Stage 7.5 (Hilo A) writes the ``Copy LinkedIn`` rich_text and flips the
page's ``Estado`` to "En revisión" / "Revisión pendiente", this module posts
a Notion comment on the page mentioning David and asking him to authorise.

Idempotency
-----------
Before posting, the script lists existing comments on the page. If a comment
authored previously by Rick already exists with marker
``REVIEW_COMMENT_MARKER`` and the same preview substring, it returns
``{"action": "skipped"}`` instead of posting a duplicate. If the preview
string changed, a new comment is posted (treated as a re-write).

@David mention
--------------
If ``DAVID_NOTION_USER_ID`` is set in the environment (or passed as
``david_user_id`` argument), the rich_text contains a real ``mention``
of type ``user``. Otherwise the literal ``@David`` is used.

Cero secrets
------------
The Notion token is only ever set in the Authorization header — never logged.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

if __package__ in (None, ""):
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from scripts.discovery.check_publicaciones_schema import (
    NOTION_API_BASE,
    NOTION_VERSION,
    build_headers,
)

REVIEW_COMMENT_MARKER = "🤖 Rick escribió un borrador de Copy LinkedIn"
PREVIEW_LIMIT = 200

COMMENT_TEMPLATE = (
    "{marker} para esta publicación.\n\n"
    "Preview (primeros {limit} chars):\n"
    "> {preview}\n\n"
    "{mention} revisá el campo \"Copy LinkedIn\" arriba. Cuando esté listo:\n"
    "- Si te sirve tal cual → setear Estado=Autorizado\n"
    "- Si querés ajustar → editar el campo y luego Estado=Autorizado\n"
    "- Si no sirve → Estado=Rechazado (Rick no reintenta automáticamente)\n\n"
    "— Rick (Stage 7.5)"
)


# ---------------------------------------------------------------------------
# Rich text builder
# ---------------------------------------------------------------------------

def _truncate_preview(copy_text: str, limit: int = PREVIEW_LIMIT) -> str:
    s = (copy_text or "").strip().replace("\n", " ")
    if len(s) <= limit:
        return s
    return s[:limit].rstrip() + "…"


def build_rich_text(
    preview: str,
    *,
    david_user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Build the rich_text array, splitting around the @David token so we can
    inject a real user mention when ``david_user_id`` is provided."""
    mention_text = "@David"
    body = COMMENT_TEMPLATE.format(
        marker=REVIEW_COMMENT_MARKER,
        limit=PREVIEW_LIMIT,
        preview=preview,
        mention=mention_text,
    )

    if not david_user_id:
        return [{"type": "text", "text": {"content": body}}]

    # Split once around the mention placeholder so we can put a real mention
    # node where the literal "@David" was.
    before, _, after = body.partition(mention_text)
    rt: list[dict[str, Any]] = []
    if before:
        rt.append({"type": "text", "text": {"content": before}})
    rt.append({
        "type": "mention",
        "mention": {"type": "user", "user": {"id": david_user_id}},
    })
    if after:
        rt.append({"type": "text", "text": {"content": after}})
    return rt


def render_comment_text(preview: str) -> str:
    """Plain-text rendering of the comment (used by tests + idempotency)."""
    return COMMENT_TEMPLATE.format(
        marker=REVIEW_COMMENT_MARKER,
        limit=PREVIEW_LIMIT,
        preview=preview,
        mention="@David",
    )


# ---------------------------------------------------------------------------
# Notion API
# ---------------------------------------------------------------------------

def list_existing_comments(client: httpx.Client, page_id: str) -> list[dict[str, Any]]:
    """Return all comments attached to the given block / page."""
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"block_id": page_id, "page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        r = client.get("/comments", params=params)
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("results", []))
        if not data.get("has_more"):
            return out
        cursor = data.get("next_cursor")
        if not cursor:
            return out


def _comment_plain_text(comment: dict[str, Any]) -> str:
    parts = []
    for rt in comment.get("rich_text", []) or []:
        # Notion returns ``plain_text`` on every rich_text node.
        parts.append(rt.get("plain_text") or "")
    return "".join(parts)


def find_existing_review_comment(
    comments: list[dict[str, Any]], preview: str
) -> dict[str, Any] | None:
    """Return a comment that already carries the marker AND the same preview;
    otherwise None."""
    for c in comments:
        text = _comment_plain_text(c)
        if REVIEW_COMMENT_MARKER in text and preview in text:
            return c
    return None


def post_comment(
    client: httpx.Client,
    page_id: str,
    rich_text: list[dict[str, Any]],
) -> dict[str, Any]:
    body = {"parent": {"page_id": page_id}, "rich_text": rich_text}
    r = client.post("/comments", json=body)
    r.raise_for_status()
    return r.json()


def post_review_comment(
    client: httpx.Client,
    page_id: str,
    copy_text: str,
    *,
    david_user_id: str | None = None,
) -> dict[str, Any]:
    """Top-level reusable function.

    Returns a dict ``{"action": "posted"|"skipped", "comment_id": str|None,
    "preview": str}``.
    """
    preview = _truncate_preview(copy_text)
    comments = list_existing_comments(client, page_id)
    dup = find_existing_review_comment(comments, preview)
    if dup:
        return {
            "action": "skipped",
            "comment_id": dup.get("id"),
            "preview": preview,
            "reason": "duplicate_marker_and_preview",
        }
    rt = build_rich_text(preview, david_user_id=david_user_id)
    created = post_comment(client, page_id, rt)
    return {
        "action": "posted",
        "comment_id": created.get("id"),
        "preview": preview,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--page-id", required=True)
    p.add_argument("--copy", required=True,
                   help="Copy LinkedIn text (script truncates to 200 chars).")
    p.add_argument(
        "--david-user-id",
        default=os.environ.get("DAVID_NOTION_USER_ID", ""),
        help="Notion user id for David. If empty, falls back to literal '@David'.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    token = os.environ.get("NOTION_API_KEY", "")
    if not token:
        print("ERROR: NOTION_API_KEY not set", file=sys.stderr)
        return 2
    client = httpx.Client(
        base_url=NOTION_API_BASE, headers=build_headers(token), timeout=30.0
    )
    try:
        result = post_review_comment(
            client,
            args.page_id,
            args.copy,
            david_user_id=args.david_user_id or None,
        )
    except httpx.HTTPStatusError as exc:
        print(
            f"ERROR: Notion API HTTP {exc.response.status_code}: "
            f"{exc.response.text[:300]}",
            file=sys.stderr,
        )
        return 2
    finally:
        client.close()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
