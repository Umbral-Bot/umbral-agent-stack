"""
Granola MCP -> Worker -> Notion feeder (free / Basic-plan capture path).

P1.1 R1, "gratis y automatico" flavour. Granola encrypted its local storage, so
the old local-token ingest (granola_api_ingest.py / cache exporter) is dead. On a
Basic plan the official transcript API/MCP is paid-gated, BUT the Granola MCP
server still returns each meeting's AI **summary + notes + participants** for free.
This feeder maps those MCP meeting objects onto the EXISTING worker task
``granola.process_transcript`` (which already upserts into the canonical
"Transcripciones Granola" DB with dedup/reconciliation) — so no new Notion-writing
code is needed here.

Substrate: the Granola MCP connection lives in a Claude/agent session (not the
headless VPS worker), so the intended runner is a scheduled Claude routine on the
VM that (1) calls the MCP for recent meetings, (2) hands the normalized JSON to
this feeder. This module is deliberately transport-agnostic and pure so it can be
unit-tested: it takes normalized meeting dicts, not raw MCP XML.

Input contract (normalized JSON, one object per meeting)::

    {"id": "<uuid>", "title": "...", "date": "Jul 13, 2026 9:02 AM GMT-4",
     "participants": ["David Moreira <dm@umbralbim.cl>"], "summary": "<markdown>",
     "source_url": "https://...", "updated_at": "2026-07-13T13:02:00Z"}

SAFETY: dry-run is the default. Nothing is written to Notion unless ``--execute``
is passed explicitly.

Examples::

    # preview only (no writes)
    python scripts/vm/granola_mcp_ingest.py --input meetings.json
    cat meetings.json | python scripts/vm/granola_mcp_ingest.py

    # actually post to the worker (requires explicit --execute + a GO)
    python scripts/vm/granola_mcp_ingest.py --input meetings.json --execute
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

CAPTURE_SOURCE = "granola_mcp"
CAPTURE_MODE = "mcp_summary_no_transcript"
DEFAULT_WORKER_TOKEN_FILE = r"C:\openclaw-worker\worker_token"

_ISO_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
# e.g. "Jul 13, 2026 9:02 AM GMT-4" -> capture "Jul 13 2026"
_HUMAN_DATE_RE = re.compile(r"^([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})")
_MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

_CONTENT_HEADER = (
    "> Captura via Granola MCP — resumen AI y notas de la reunion.\n"
    "> Sin transcripcion verbatim (plan Basic; la transcripcion via API/MCP es de pago)."
)


def parse_meeting_date(value: Any) -> str:
    """Best-effort normalize a meeting date to ``YYYY-MM-DD`` (empty if unknown)."""
    text = str(value or "").strip()
    if not text:
        return ""
    iso = _ISO_DATE_RE.match(text)
    if iso:
        return iso.group(1)
    human = _HUMAN_DATE_RE.match(text)
    if human:
        month = _MONTHS.get(human.group(1).lower())
        if month:
            return f"{human.group(3)}-{month}-{int(human.group(2)):02d}"
    return ""


def normalize_participants(meeting: dict[str, Any]) -> list[str]:
    """Return a clean list of participant labels (names/emails), de-duplicated."""
    raw = meeting.get("participants")
    if raw is None:
        raw = meeting.get("attendees")
    result: list[str] = []
    seen: set[str] = set()
    for item in raw or []:
        if isinstance(item, dict):
            label = str(item.get("name") or item.get("email") or "").strip()
        else:
            label = str(item or "").strip()
        if label and label not in seen:
            seen.add(label)
            result.append(label)
    return result


def build_content(meeting: dict[str, Any]) -> str:
    summary = str(meeting.get("summary") or meeting.get("notes") or "").strip()
    if summary:
        return f"{_CONTENT_HEADER}\n\n{summary}"
    return _CONTENT_HEADER


def build_payload(meeting: dict[str, Any], *, notify_enlace: bool = False) -> dict[str, Any]:
    """Map a normalized MCP meeting dict to a granola.process_transcript payload."""
    meeting_id = str(meeting.get("id") or "").strip()
    if not meeting_id:
        raise ValueError("meeting is missing required 'id'")

    title = str(meeting.get("title") or "").strip() or meeting_id
    payload: dict[str, Any] = {
        "title": title,
        "content": build_content(meeting),
        "source": CAPTURE_SOURCE,
        "granola_document_id": meeting_id,
        "notify_enlace": bool(notify_enlace),
        "metadata": {"capture_mode": CAPTURE_MODE},
    }

    date = parse_meeting_date(meeting.get("date"))
    if date:
        payload["date"] = date

    participants = normalize_participants(meeting)
    if participants:
        payload["attendees"] = participants

    source_url = str(meeting.get("source_url") or "").strip()
    if source_url:
        payload["source_url"] = source_url

    updated_at = str(
        meeting.get("updated_at") or meeting.get("source_updated_at") or ""
    ).strip()
    if updated_at:
        payload["source_updated_at"] = updated_at
        payload["metadata"]["source_updated_at"] = updated_at

    return payload


def build_payloads(meetings: list[dict[str, Any]], *, notify_enlace: bool = False) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for meeting in meetings:
        if isinstance(meeting, dict):
            payloads.append(build_payload(meeting, notify_enlace=notify_enlace))
    return payloads


def _load_meetings(raw_text: str) -> list[dict[str, Any]]:
    data = json.loads(raw_text)
    if isinstance(data, dict):
        # Allow {"meetings": [...]} or a single meeting object.
        if isinstance(data.get("meetings"), list):
            return data["meetings"]
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("input JSON must be a meeting object, a list, or {\"meetings\": [...]}")


def _worker_token_from_env_or_file() -> str:
    env_token = str(
        os.environ.get("GRANOLA_WORKER_TOKEN") or os.environ.get("WORKER_TOKEN") or ""
    ).strip()
    if env_token:
        return env_token
    token_file = Path(os.environ.get("GRANOLA_WORKER_TOKEN_FILE", DEFAULT_WORKER_TOKEN_FILE))
    if token_file.exists():
        return token_file.read_text(encoding="utf-8-sig").strip()
    raise RuntimeError("GRANOLA_WORKER_TOKEN/WORKER_TOKEN not configured")


def _post_to_worker(worker_url: str, worker_token: str, payload: dict[str, Any]) -> Any:
    resp = requests.post(
        f"{worker_url.rstrip('/')}/run",
        json={"task": "granola.process_transcript", "input": payload},
        headers={
            "Authorization": f"Bearer {worker_token}",
            "Content-Type": "application/json",
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Feed normalized Granola MCP meetings into granola.process_transcript."
    )
    parser.add_argument("--input", help="Path to JSON meetings file (default: stdin)")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually POST to the worker. Without this flag the run is a dry preview.",
    )
    parser.add_argument("--worker-url", dest="worker_url", default=None)
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N meetings (0 = all)")
    parser.add_argument(
        "--notify-enlace",
        dest="notify_enlace",
        action="store_true",
        default=False,
        help="Notify @Enlace after ingestion (default off for metadata-only capture)",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    raw_text = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    meetings = _load_meetings(raw_text)
    if args.limit and args.limit > 0:
        meetings = meetings[: args.limit]

    payloads = build_payloads(meetings, notify_enlace=args.notify_enlace)

    if not args.execute:
        print(json.dumps({
            "dry_run": True,
            "count": len(payloads),
            "capture_mode": CAPTURE_MODE,
            "payloads": payloads,
        }, ensure_ascii=False, indent=2))
        return 0

    worker_url = (
        args.worker_url
        or os.environ.get("GRANOLA_WORKER_URL")
        or os.environ.get("WORKER_URL")
        or "http://127.0.0.1:8088"
    )
    worker_token = _worker_token_from_env_or_file()
    results: list[dict[str, Any]] = []
    for payload in payloads:
        result = _post_to_worker(worker_url, worker_token, payload)
        results.append({
            "granola_document_id": payload.get("granola_document_id"),
            "title": payload.get("title"),
            "worker_result": result,
        })
    print(json.dumps({"dry_run": False, "count": len(results), "results": results},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
