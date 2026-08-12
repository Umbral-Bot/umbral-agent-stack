"""013-H quality gate: GET /blocks/children for given Notion page IDs and grep
all rich_text content for forbidden literal markdown remnants.

Read-only. Token sourced from NOTION_API_KEY env var; sent only in headers.
Forbidden tokens (per task spec): ``**``, ``__``, ``\\*``, ``\\---``, ``\\!\\[``, ``[![``.
Exit code 0 if zero hits across all pages, 1 otherwise.

Usage:
    python -m scripts.discovery.quality_gate_grep_blocks \
        --page-ids id1,id2,id3 [--report reports/qa-grep-<TS>.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
RATE_LIMIT_SLEEP_S = 0.35
FORBIDDEN = ["**", "__", "\\*", "\\---", "\\!\\[", "[!["]


def _headers() -> dict[str, str]:
    tok = os.environ.get("NOTION_API_KEY")
    if not tok:
        sys.exit("ERROR: NOTION_API_KEY not set")
    return {
        "Authorization": f"Bearer {tok}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _get_with_retry(client: httpx.Client, url: str) -> dict:
    backoffs = [1.0, 2.0, 4.0, 8.0]
    for attempt in range(len(backoffs) + 1):
        r = client.get(url, headers=_headers(), timeout=20.0)
        if r.status_code == 429 and attempt < len(backoffs):
            time.sleep(backoffs[attempt])
            continue
        if r.status_code >= 400:
            r.raise_for_status()
        return r.json()
    raise RuntimeError("rate-limit retries exhausted")


def fetch_all_blocks(client: httpx.Client, page_id: str) -> list[dict]:
    out: list[dict] = []
    cursor: str | None = None
    while True:
        url = f"{NOTION_API}/blocks/{page_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        body = _get_with_retry(client, url)
        out.extend(body.get("results", []))
        time.sleep(RATE_LIMIT_SLEEP_S)
        if not body.get("has_more"):
            break
        cursor = body.get("next_cursor")
    return out


def _iter_rich_text(block: dict):
    for key in ("paragraph", "heading_1", "heading_2", "heading_3",
                "bulleted_list_item", "numbered_list_item",
                "quote", "callout", "to_do"):
        body = block.get(key)
        if isinstance(body, dict):
            for span in body.get("rich_text", []) or []:
                txt = (span.get("text") or {}).get("content", "")
                if txt:
                    yield (key, txt)
    img = block.get("image")
    if isinstance(img, dict):
        for span in img.get("caption", []) or []:
            txt = (span.get("text") or {}).get("content", "")
            if txt:
                yield ("image_caption", txt)


def scan_page(client: httpx.Client, page_id: str) -> dict:
    blocks = fetch_all_blocks(client, page_id)
    hits: list[dict] = []
    total_spans = 0
    for b in blocks:
        for kind, content in _iter_rich_text(b):
            total_spans += 1
            for tok in FORBIDDEN:
                if tok in content:
                    hits.append({
                        "block_type": b.get("type"),
                        "container": kind,
                        "forbidden_token": tok,
                        "content_excerpt": content[:120],
                    })
    return {
        "page_id": page_id,
        "blocks_total": len(blocks),
        "rich_text_spans_total": total_spans,
        "hits_total": len(hits),
        "hits": hits,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-ids", required=True,
                    help="Comma-separated Notion page UUIDs")
    ap.add_argument("--report", default=None,
                    help="Path to write JSON report (default: auto-named)")
    args = ap.parse_args()

    page_ids = [p.strip() for p in args.page_ids.split(",") if p.strip()]
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: list[dict] = []
    with httpx.Client(follow_redirects=True) as client:
        for pid in page_ids:
            results.append(scan_page(client, pid))

    total_hits = sum(r["hits_total"] for r in results)
    summary = {
        "started": started,
        "finished": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "page_ids": page_ids,
        "forbidden": FORBIDDEN,
        "total_hits": total_hits,
        "per_page": results,
    }
    out_path = Path(args.report or
                    f"reports/qa-grep-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({
        "total_hits": total_hits,
        "per_page_hits": [
            (r["page_id"], r["hits_total"], r["blocks_total"]) for r in results
        ],
        "report_path": str(out_path),
    }, indent=2))
    return 0 if total_hits == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
