"""Audit data-quality of the Notion 'Referentes' database (read-only).

Detects two classes of issues:

A. Empty YouTube identification on YouTube creators
   Rows where ``Plataformas`` multi_select contains ``YouTube`` but the
   ``YouTube channel`` URL property is empty.

B. Fuzzy duplicates by name
   Pairs of rows whose ``Nombre`` matches with
   ``rapidfuzz.fuzz.token_set_ratio`` >= ``--fuzzy-threshold`` (default 90).

Outputs:
- A JSON report to ``--output-json``.
- Optionally, comment(s) on a Notion page (``--notion-comment-parent-page-id``)
  with a short summary. Long bodies are split inline (no dependency on PR
  #354's paginator helper) using ``SAFE_LIMIT``.

The script is read-only against the Referentes DB; the only mutation it can do
is creating one comment chain on the explicitly provided control page.

NOTE: the IDs in the original task description (DB ``b9d3d867...`` /
data source ``9d4dbf65...``) actually point to the *Publicaciones* DB, not the
canonical *Referentes* DB. We use the verified Referentes data source resolved
live during the smoke run on 2026-05-07. They can still be overridden via the
``--data-source-id`` CLI flag.

Usage:
    export NOTION_API_KEY=...
    python scripts/discovery/audit_referentes_quality.py \\
        --output-json /tmp/audit_referentes.json \\
        --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - import-time guard
    print("ERROR: rapidfuzz not installed. pip install rapidfuzz", file=sys.stderr)
    raise

NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2025-09-03"
# Verified live on 2026-05-07 via /v1/search and /v1/data_sources/<id>.
REFERENTES_DATA_SOURCE_ID = "afc8d960-086c-4878-b562-7511dd02ff76"
REFERENTES_DB_ID = "05f04d48-c449-43e8-b4ac-c572a4ec6f19"
RATE_LIMIT_SLEEP_S = 0.34
SAFE_LIMIT = 1900  # Notion comment payload soft cap

# Property-name candidates (Referentes uses Title Case Spanish).
NAME_PROP_CANDIDATES = ("Nombre", "Name", "Título", "Title")
YT_URL_CANDIDATES = ("YouTube channel", "YouTube Channel", "youtube_channel")
PLATAFORMAS_CANDIDATES = ("Plataformas", "Platforms", "plataformas")
YOUTUBE_PLATFORM_NAMES = {"youtube", "youtube channel"}


# ---------- Notion HTTP client (minimal, read-only + comments) ----------

class NotionClient:
    def __init__(self, api_key: str, *, client: httpx.Client | None = None):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }
        self._client = client or httpx.Client(timeout=30.0)

    def __repr__(self) -> str:
        return "<NotionClient token=***REDACTED***>"

    def close(self) -> None:
        self._client.close()

    def post(self, path: str, json_body: Any) -> httpx.Response:
        return self._client.post(
            f"{NOTION_BASE_URL}{path}", headers=self._headers, json=json_body
        )


# ---------- Property extraction helpers ----------

def _first_present(props: dict[str, Any], candidates: Iterable[str]) -> Any:
    for name in candidates:
        if name in props:
            return props[name]
    return None


def _extract_text(prop: Any) -> str | None:
    if not isinstance(prop, dict):
        return None
    ptype = prop.get("type")
    if ptype == "title":
        parts = prop.get("title", [])
    elif ptype == "rich_text":
        parts = prop.get("rich_text", [])
    elif ptype == "url":
        return prop.get("url")
    elif ptype == "select":
        sel = prop.get("select")
        return (sel or {}).get("name") if sel else None
    else:
        return None
    return ("".join(p.get("plain_text", "") for p in parts) or None) if parts else None


def _extract_multi_select_names(prop: Any) -> list[str]:
    if not isinstance(prop, dict) or prop.get("type") != "multi_select":
        return []
    return [item.get("name", "") for item in (prop.get("multi_select") or [])]


def extract_row_fields(page: dict[str, Any]) -> dict[str, Any]:
    """Project a Notion page into the minimal flat dict the audit needs."""
    props = page.get("properties", {}) or {}
    plataformas = _extract_multi_select_names(
        _first_present(props, PLATAFORMAS_CANDIDATES)
    )
    return {
        "id": page.get("id"),
        "url": page.get("url"),
        "nombre": _extract_text(_first_present(props, NAME_PROP_CANDIDATES)),
        "youtube_url": _extract_text(_first_present(props, YT_URL_CANDIDATES)),
        "plataformas": plataformas,
        "is_youtube_creator": any(
            p.strip().lower() in YOUTUBE_PLATFORM_NAMES for p in plataformas
        ),
    }


# ---------- Fetch ----------

def fetch_all_referentes(client: NotionClient, data_source_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = client.post(f"/data_sources/{data_source_id}/query", body)
        if r.status_code != 200:
            raise RuntimeError(
                f"referentes query failed: HTTP {r.status_code} body={r.text[:300]}"
            )
        data = r.json()
        for page in data.get("results", []):
            rows.append(extract_row_fields(page))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        time.sleep(RATE_LIMIT_SLEEP_S)
    return rows


# ---------- Detectors ----------

def _is_empty(val: Any) -> bool:
    return val is None or (isinstance(val, str) and not val.strip())


def detect_empty_youtube(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag rows that claim YouTube as a platform but have empty YouTube channel URL."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("is_youtube_creator"):
            continue
        if _is_empty(row.get("youtube_url")):
            out.append({
                "id": row.get("id"),
                "nombre": row.get("nombre"),
                "plataformas": row.get("plataformas"),
                "missing_fields": ["YouTube channel"],
                "url": row.get("url"),
            })
    return out


def detect_fuzzy_duplicates(
    rows: list[dict[str, Any]], threshold: int = 90
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    items = [(r.get("id"), (r.get("nombre") or "").strip()) for r in rows]
    items = [(i, n) for i, n in items if i and n]
    for a in range(len(items)):
        id_a, name_a = items[a]
        for b in range(a + 1, len(items)):
            id_b, name_b = items[b]
            score = fuzz.token_set_ratio(name_a, name_b)
            if score >= threshold:
                out.append({
                    "id_a": id_a,
                    "name_a": name_a,
                    "id_b": id_b,
                    "name_b": name_b,
                    "score": int(score),
                })
    return out


# ---------- Report ----------

def render_report(
    empty: list[dict[str, Any]],
    dups: list[dict[str, Any]],
    *,
    total_referentes: int,
) -> dict[str, Any]:
    return {
        "empty_youtube": empty,
        "fuzzy_duplicates": dups,
        "summary": {
            "n_empty": len(empty),
            "n_dups": len(dups),
            "total_referentes": total_referentes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def render_comment_text(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "Audit Referentes (data quality)",
        f"timestamp: {s['timestamp']}",
        f"total_referentes: {s['total_referentes']}",
        f"YouTube creators sin URL: {s['n_empty']}",
        f"pares fuzzy-duplicados: {s['n_dups']}",
        "",
    ]
    if report["empty_youtube"]:
        lines.append("YouTube creators sin URL:")
        for row in report["empty_youtube"][:25]:
            lines.append(f"- {row['nombre']} ({row['id']})")
        lines.append("")
    if report["fuzzy_duplicates"]:
        lines.append("Pares fuzzy-duplicados (score >= threshold):")
        for d in report["fuzzy_duplicates"][:25]:
            lines.append(
                f"- {d['name_a']} <-> {d['name_b']} score={d['score']} "
                f"({d['id_a']} | {d['id_b']})"
            )
    return "\n".join(lines)


def _split_for_notion(text: str, limit: int = SAFE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    total = len(chunks)
    return [f"[{i+1}/{total}] {c}" for i, c in enumerate(chunks)]


def post_to_notion(
    client: NotionClient, parent_page_id: str, report: dict[str, Any]
) -> list[str]:
    """Post the audit summary as one or more comments. Returns list of comment ids."""
    text = render_comment_text(report)
    parts = _split_for_notion(text)
    ids: list[str] = []
    for part in parts:
        body = {
            "parent": {"page_id": parent_page_id},
            "rich_text": [{"type": "text", "text": {"content": part}}],
        }
        r = client.post("/comments", body)
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"notion comment failed: HTTP {r.status_code} body={r.text[:300]}"
            )
        ids.append(r.json().get("id", ""))
        time.sleep(RATE_LIMIT_SLEEP_S)
    return ids


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Audit Referentes Notion DB for data quality.")
    p.add_argument("--output-json", required=True, help="Path to write JSON report.")
    p.add_argument(
        "--data-source-id",
        default=REFERENTES_DATA_SOURCE_ID,
        help="Notion data_source_id of the Referentes DB (default: live verified).",
    )
    p.add_argument(
        "--notion-comment-parent-page-id",
        default=None,
        help="If set, post the audit summary as comment(s) on this page.",
    )
    p.add_argument("--fuzzy-threshold", type=int, default=90)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not post any Notion comments even if parent-page-id is set.",
    )
    args = p.parse_args(argv)

    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        print("ERROR: NOTION_API_KEY not set in env", file=sys.stderr)
        return 2

    client = NotionClient(api_key)
    try:
        rows = fetch_all_referentes(client, args.data_source_id)
        empty = detect_empty_youtube(rows)
        dups = detect_fuzzy_duplicates(rows, threshold=args.fuzzy_threshold)
        report = render_report(empty, dups, total_referentes=len(rows))

        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        s = report["summary"]
        print(f"total={s['total_referentes']} n_empty={s['n_empty']} n_dups={s['n_dups']}")
        print(f"report: {args.output_json}")

        if args.notion_comment_parent_page_id and not args.dry_run:
            ids = post_to_notion(client, args.notion_comment_parent_page_id, report)
            print(f"posted {len(ids)} comment(s) to {args.notion_comment_parent_page_id}")
        elif args.notion_comment_parent_page_id and args.dry_run:
            print("dry-run: skipping Notion comment post")
    finally:
        client.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
