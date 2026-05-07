"""Stage 7: write proposals as draft pages in the Notion 'Publicaciones' DB.

Reads rows from ``state.sqlite`` table ``proposals`` (created by Stage 6)
where ``status='draft'`` and ``notion_page_id IS NULL``, then creates a
Notion page in DB ``e6817ec4698a4f0fbbc8fedcf4e52472`` (data source resolved
dynamically). On success, updates the proposal row with the new page id and
flips status to ``published``.

Idempotent by ``idempotency_key`` rich-text property (sha256 of titular + ts).
``--dry-run`` prints the would-be payload without calling Notion.

Schema detection: at startup, GETs the data source schema and logs the property
keys it found. Only fills the minimum required to create a valid page:
``Título`` (title), ``idempotency_key`` (rich_text), ``Tipo de contenido`` (select)
and a body of paragraph blocks.

Notes:
- Required ``Título`` is the only Notion-mandatory property in this DB.
- Other props (Estado, Canal, Prioridad, etc.) are left to defaults; user
  refines manually after first review.
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
DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"
DEFAULT_PUBLICACIONES_DB_ID = "e6817ec4698a4f0fbbc8fedcf4e52472"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
RATE_LIMIT_SLEEP_S = 0.34  # ~3 req/s


# ---------- Logging ----------

def log_event(event: str, **fields: Any) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    try:
        DEFAULT_OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_OPS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


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

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        time.sleep(RATE_LIMIT_SLEEP_S)
        r = self._client.post(path, json=body)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()


# ---------- Schema ----------

def fetch_data_source_id(client: NotionClient, db_id: str) -> str:
    db = client.get(f"/databases/{db_id}")
    sources = db.get("data_sources") or []
    if not sources:
        raise RuntimeError(f"DB {db_id} has no data_sources field")
    return sources[0]["id"]


def fetch_schema(client: NotionClient, ds_id: str) -> dict[str, str]:
    """Return {prop_name: prop_type} for the data source."""
    ds = client.get(f"/data_sources/{ds_id}")
    return {name: p.get("type", "?") for name, p in (ds.get("properties") or {}).items()}


# ---------- State access ----------

def read_pending_proposals(
    db_path: Path, *, status: str, limit: int | None
) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT id, titular, hook, angulo, fuentes_urls, disciplinas, score, ts "
            "FROM proposals WHERE status = ? AND notion_page_id IS NULL "
            "ORDER BY id ASC"
        )
        params: tuple[Any, ...] = (status,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (status, limit)
        rows = list(conn.execute(sql, params))
        out = []
        for r in rows:
            d = dict(r)
            d["fuentes_urls"] = json.loads(d.get("fuentes_urls") or "[]")
            d["disciplinas"] = json.loads(d.get("disciplinas") or "[]")
            out.append(d)
        return out
    finally:
        conn.close()


def mark_proposal_published(
    db_path: Path, proposal_id: int, notion_page_id: str
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET status='published', notion_page_id=?, last_error=NULL "
            "WHERE id=?",
            (notion_page_id, proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_proposal_failed(db_path: Path, proposal_id: int, error: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET last_error=? WHERE id=?",
            (error[:500], proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- Payload ----------

def _idempotency_key(proposal: dict[str, Any]) -> str:
    raw = f"{proposal.get('titular','')}\n{proposal.get('ts','')}\n{proposal.get('id','')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rt(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text[:1900]}}]


def build_page_payload(
    *, proposal: dict[str, Any], data_source_id: str, schema: dict[str, str]
) -> dict[str, Any]:
    titular = proposal["titular"]
    hook = proposal.get("hook") or ""
    angulo = proposal.get("angulo") or ""
    fuentes = proposal.get("fuentes_urls") or []
    disciplinas = proposal.get("disciplinas") or []

    props: dict[str, Any] = {}
    if schema.get("Título") == "title":
        props["Título"] = {"title": _rt(titular)}
    if schema.get("idempotency_key") == "rich_text":
        props["idempotency_key"] = {"rich_text": _rt(_idempotency_key(proposal))}
    if schema.get("Tipo de contenido") == "select":
        props["Tipo de contenido"] = {"select": {"name": "linkedin_post"}}
    if schema.get("Ángulo editorial") == "rich_text" and angulo:
        props["Ángulo editorial"] = {"rich_text": _rt(angulo)}
    if schema.get("Resumen fuente") == "rich_text" and hook:
        props["Resumen fuente"] = {"rich_text": _rt(hook)}
    if schema.get("Fuente primaria") == "url" and fuentes:
        props["Fuente primaria"] = {"url": fuentes[0]}
    if schema.get("Creado por sistema") == "checkbox":
        props["Creado por sistema"] = {"checkbox": True}

    children: list[dict[str, Any]] = []
    if hook:
        children.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt(hook)},
        })
    if angulo:
        children.append({
            "object": "block", "type": "heading_3",
            "heading_3": {"rich_text": _rt("Ángulo editorial")},
        })
        children.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt(angulo)},
        })
    if disciplinas:
        children.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt("Disciplinas: " + ", ".join(disciplinas))},
        })
    if fuentes:
        children.append({
            "object": "block", "type": "heading_3",
            "heading_3": {"rich_text": _rt("Fuentes")},
        })
        for url in fuentes:
            children.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [
                    {"type": "text", "text": {"content": url, "link": {"url": url}}}
                ]},
            })

    return {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": props,
        "children": children,
    }


def create_page(client: NotionClient, payload: dict[str, Any]) -> str:
    resp = client.post("/pages", payload)
    return resp["id"]


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 7 publish proposals as Notion drafts.")
    p.add_argument("--status", default="draft")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    p.add_argument("--publicaciones-db-id", default=DEFAULT_PUBLICACIONES_DB_ID)
    p.add_argument("--publicaciones-data-source-id", default=None,
                   help="Skip dynamic resolution and use this data source id directly.")
    args = p.parse_args(argv)

    state_db = Path(args.state_db)
    proposals = read_pending_proposals(state_db, status=args.status, limit=args.limit)
    log_event("stage7.input.loaded", n=len(proposals), status=args.status)
    if not proposals:
        print("no pending proposals")
        return 0

    token = os.environ.get("NOTION_API_KEY", "")
    if not token:
        print("ERROR: NOTION_API_KEY not set", file=sys.stderr)
        return 2

    client = NotionClient(token)
    try:
        ds_id = args.publicaciones_data_source_id or fetch_data_source_id(
            client, args.publicaciones_db_id
        )
        schema = fetch_schema(client, ds_id)
        log_event("stage7.schema.detected",
                  ds_id=ds_id, n_props=len(schema), props=sorted(schema.keys()))
        print(f"data_source_id={ds_id} props={len(schema)}")

        ok, fail = 0, 0
        for prop in proposals:
            payload = build_page_payload(
                proposal=prop, data_source_id=ds_id, schema=schema
            )
            if args.dry_run:
                print(f"[dry-run] proposal_id={prop['id']} titular={prop['titular'][:80]!r} "
                      f"props={list(payload['properties'].keys())} blocks={len(payload['children'])}")
                ok += 1
                continue
            try:
                page_id = create_page(client, payload)
                mark_proposal_published(state_db, prop["id"], page_id)
                log_event("stage7.page.created",
                          proposal_id=prop["id"], page_id=page_id)
                print(f"created proposal_id={prop['id']} page_id={page_id}")
                ok += 1
            except httpx.HTTPStatusError as e:
                err = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                mark_proposal_failed(state_db, prop["id"], err)
                log_event("stage7.page.failed", proposal_id=prop["id"], error=err)
                print(f"FAIL proposal_id={prop['id']}: {err}", file=sys.stderr)
                fail += 1
            except Exception as e:
                err = str(e)[:200]
                mark_proposal_failed(state_db, prop["id"], err)
                log_event("stage7.page.failed", proposal_id=prop["id"], error=err)
                print(f"FAIL proposal_id={prop['id']}: {err}", file=sys.stderr)
                fail += 1
        print(f"summary ok={ok} fail={fail} dry_run={args.dry_run}")
        return 0 if fail == 0 else 1
    finally:
        client.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
