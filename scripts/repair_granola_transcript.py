#!/usr/bin/env python3
"""Repair a single Granola raw transcript page by reconciling its content.

This is the manual counterpart to the automatic finality/stability gate built
into ``granola.process_transcript``. Use it when David / Enlace spot a raw
Notion page that looks truncated or out of sync and want to force the ingest
pipeline to pick up the latest version of the transcript, keeping the same
Notion page and URL.

The script deliberately does *not* hardcode any meeting content. It either
reads an export file provided on the command line, fetches the document with
``granola_api_ingest`` helpers, or reconstructs it from a provided
``--content-file`` / stdin.

Usage examples::

    # Dry-run preview only; no Notion writes.
    python scripts/repair_granola_transcript.py \
        --granola-document-id 4d4c239d-... \
        --dry-run --mode local --json

    # Real repair using a transcript markdown file already on disk.
    python scripts/repair_granola_transcript.py \
        --page-id 3305f443-fb5c-81db-9162-fd70c8574938 \
        --content-file ./exports/comgrap-dynamo.md \
        --execute --mode worker

    # Fetch directly from Granola's private API on the VM.
    python scripts/repair_granola_transcript.py \
        --granola-document-id 4d4c239d-... \
        --fetch-from-granola --execute --mode local --json

Output is a JSON summary describing the reconciliation decision taken by the
worker so that operators can audit 7 / 30-day windows of repairs without
grepping logs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import env_loader

env_loader.load()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_content_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Content file not found: {path}")
    return path.read_text(encoding="utf-8")


def _resolve_from_notion(page_id: str) -> dict[str, Any]:
    """Look up granola_document_id / title / date from the existing raw page."""
    from worker import notion_client
    from worker.tasks.granola import (
        _build_existing_raw_candidate,
        _extract_date_from_page,
        _extract_title_from_page,
    )

    page_data = notion_client.get_page(page_id)
    candidate = _build_existing_raw_candidate(page_data)
    return {
        "page_id": candidate.get("page_id") or page_id,
        "title": candidate.get("title") or _extract_title_from_page(page_data),
        "date": candidate.get("date") or _extract_date_from_page(page_data),
        "granola_document_id": candidate.get("granola_document_id") or "",
        "source_updated_at": candidate.get("source_updated_at") or "",
        "source_url": candidate.get("source_url") or "",
    }


def _resolve_document_from_granola(document_id: str) -> dict[str, Any]:
    """Best-effort fetch of title/content from the Granola private API.

    This only works when run on a host that has access to Granola's local
    supabase.json / WorkOS token (typically the Windows VM). It is optional —
    operators can always provide ``--content-file`` instead.
    """
    from scripts.vm.granola_api_ingest import (
        GRANOLA_API_BASE,  # noqa: F401
        _worker_token_from_env_or_file,  # noqa: F401
        granola_post,
        load_granola_access_token,
        render_transcript_markdown,
    )

    supabase_path = os.environ.get(
        "GRANOLA_SUPABASE_PATH",
        str(Path(os.environ.get("APPDATA", "")) / "Granola" / "supabase.json"),
    )
    access_token = load_granola_access_token(supabase_path)
    metadata = granola_post(
        "/get-document-metadata", {"document_id": document_id}, access_token
    )
    transcript_items = granola_post(
        "/get-document-transcript", {"document_id": document_id}, access_token
    )
    if not isinstance(transcript_items, list):
        raise RuntimeError("Granola transcript response is not a list")
    title = str((metadata or {}).get("title") or document_id).strip()
    updated_at = str((metadata or {}).get("updated_at") or "").strip()
    content = render_transcript_markdown(transcript_items)
    return {
        "title": title,
        "content": content,
        "source_updated_at": updated_at,
        "granola_document_id": document_id,
        "segment_count": len(transcript_items),
    }


def _send_payload(
    *,
    mode: str,
    payload: dict[str, Any],
    worker_url: str,
    worker_token: str,
) -> dict[str, Any]:
    if mode == "local":
        from worker.tasks.granola import handle_granola_process_transcript

        return handle_granola_process_transcript(payload)
    if mode == "worker":
        from client.worker_client import WorkerClient

        wc = WorkerClient(
            base_url=worker_url,
            token=worker_token,
            timeout=180.0,
            caller_id="script.repair_granola_transcript",
        )
        return wc.run("granola.process_transcript", payload)
    raise ValueError(f"Unsupported mode: {mode}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Manually reconcile a single Granola raw transcript page without "
            "duplicating it."
        ),
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--page-id",
        help="Existing Notion raw page id to repair (preferred when known).",
    )
    target.add_argument(
        "--granola-document-id",
        help="Granola document id — used as the canonical reconciliation key.",
    )
    parser.add_argument("--title", help="Override transcript title (optional)")
    parser.add_argument("--date", help="Override meeting date (YYYY-MM-DD, optional)")
    parser.add_argument(
        "--source",
        default="granola",
        help="Source label (default: granola)",
    )
    parser.add_argument(
        "--content-file",
        help="Path to a markdown/text file with the latest transcript content.",
    )
    parser.add_argument(
        "--fetch-from-granola",
        action="store_true",
        help=(
            "Fetch the latest content from Granola's private API "
            "(requires supabase.json access; typically VM-only)."
        ),
    )
    parser.add_argument(
        "--source-updated-at",
        help="ISO-8601 source timestamp; inferred from Notion/Granola when omitted.",
    )
    parser.add_argument(
        "--source-url",
        help="Source URL; inferred from Notion when omitted.",
    )
    parser.add_argument(
        "--stability-window-seconds",
        type=int,
        help=(
            "Override the stability window in seconds. Use 0 to skip the gate entirely."
        ),
    )
    parser.add_argument(
        "--no-notify-enlace",
        dest="notify_enlace",
        action="store_false",
        default=False,
        help="Do not notify @Enlace (default: off for repairs).",
    )
    parser.add_argument(
        "--notify-enlace",
        dest="notify_enlace",
        action="store_true",
        help="Notify @Enlace after a successful repair.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the reconciliation. Default is preview-only (--dry-run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly force dry-run (overrides --execute).",
    )
    parser.add_argument(
        "--force-reconcile",
        action="store_true",
        default=True,
        help="Always reconcile even when metrics look unchanged (default).",
    )
    parser.add_argument(
        "--no-force-reconcile",
        dest="force_reconcile",
        action="store_false",
        help="Let the automatic stability/metrics gate decide whether to update.",
    )
    parser.add_argument(
        "--mode",
        choices=("local", "worker"),
        default="local",
        help="Execution mode (default: local; use worker for VPS Worker /run).",
    )
    parser.add_argument(
        "--worker-url",
        default=os.environ.get("WORKER_URL") or "http://127.0.0.1:8088",
    )
    parser.add_argument(
        "--worker-token",
        default=os.environ.get("WORKER_TOKEN") or "",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    parser.add_argument(
        "--audit-log",
        default=os.environ.get(
            "GRANOLA_REPAIR_AUDIT_LOG",
            str(REPO_ROOT / ".tmp" / "granola_repair_audit.jsonl"),
        ),
        help=(
            "Append-only JSONL audit trail for 7/30-day review "
            "(default: .tmp/granola_repair_audit.jsonl)."
        ),
    )
    parser.add_argument(
        "--no-audit-log",
        dest="write_audit_log",
        action="store_false",
        default=True,
        help="Do not append to the audit log.",
    )
    return parser


def _resolve_content(
    args: argparse.Namespace, lookup: dict[str, Any]
) -> dict[str, Any]:
    if args.content_file:
        content = _read_content_file(Path(args.content_file))
        return {
            "content": content,
            "title": lookup.get("title") or "",
            "source_updated_at": lookup.get("source_updated_at") or "",
            "granola_document_id": lookup.get("granola_document_id")
            or args.granola_document_id
            or "",
        }
    if args.fetch_from_granola:
        document_id = args.granola_document_id or lookup.get("granola_document_id") or ""
        if not document_id:
            raise RuntimeError(
                "--fetch-from-granola requires a known granola_document_id "
                "(either via --granola-document-id or an existing Notion page)."
            )
        fetched = _resolve_document_from_granola(document_id)
        return {
            "content": fetched["content"],
            "title": fetched["title"] or lookup.get("title") or "",
            "source_updated_at": fetched.get("source_updated_at")
            or lookup.get("source_updated_at")
            or "",
            "granola_document_id": document_id,
        }
    # Fall back to stdin if available.
    if not sys.stdin.isatty():
        content = sys.stdin.read()
        if content.strip():
            return {
                "content": content,
                "title": lookup.get("title") or "",
                "source_updated_at": lookup.get("source_updated_at") or "",
                "granola_document_id": lookup.get("granola_document_id")
                or args.granola_document_id
                or "",
            }
    raise RuntimeError(
        "No content source provided. Pass --content-file, --fetch-from-granola, "
        "or pipe markdown content via stdin."
    )


def _append_audit_entry(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False))
        handle.write("\n")


def main() -> int:
    args = build_arg_parser().parse_args()

    lookup: dict[str, Any] = {}
    if args.page_id:
        lookup = _resolve_from_notion(args.page_id)
    elif args.granola_document_id:
        lookup = {"granola_document_id": args.granola_document_id}

    content_info = _resolve_content(args, lookup)
    title = (args.title or content_info.get("title") or "").strip()
    if not title:
        raise RuntimeError("Transcript title could not be resolved; pass --title")

    content = content_info.get("content") or ""
    if not content.strip():
        raise RuntimeError("Resolved transcript content is empty")

    granola_document_id = (
        args.granola_document_id
        or lookup.get("granola_document_id")
        or content_info.get("granola_document_id")
        or ""
    ).strip()
    if not granola_document_id:
        raise RuntimeError(
            "granola_document_id could not be resolved. Pass --granola-document-id "
            "or point --page-id at a page that already has it stored."
        )

    effective_dry_run = bool(args.dry_run or not args.execute)
    payload: dict[str, Any] = {
        "title": title,
        "content": content,
        "source": args.source,
        "granola_document_id": granola_document_id,
        "source_updated_at": args.source_updated_at
        or content_info.get("source_updated_at")
        or lookup.get("source_updated_at")
        or "",
        "source_url": args.source_url or lookup.get("source_url") or "",
        "notify_enlace": bool(args.notify_enlace),
        "dry_run": effective_dry_run,
        "force_reconcile": bool(args.force_reconcile),
    }
    if args.date:
        payload["date"] = args.date
    elif lookup.get("date"):
        payload["date"] = lookup["date"]
    if args.stability_window_seconds is not None:
        payload["stability_window_seconds"] = int(args.stability_window_seconds)

    response = _send_payload(
        mode=args.mode,
        payload=payload,
        worker_url=args.worker_url,
        worker_token=args.worker_token,
    )

    summary = {
        "generated_at": _iso_now(),
        "granola_document_id": granola_document_id,
        "page_id_input": args.page_id,
        "mode": args.mode,
        "dry_run": effective_dry_run,
        "force_reconcile": bool(args.force_reconcile),
        "payload_preview": {
            "title": payload["title"],
            "date": payload.get("date", ""),
            "content_chars": len(content),
            "source_updated_at": payload["source_updated_at"],
            "source_url": payload["source_url"],
        },
        "response": response,
    }

    if args.write_audit_log:
        try:
            _append_audit_entry(Path(args.audit_log), summary)
        except OSError as exc:
            sys.stderr.write(f"warning: could not write audit log: {exc}\n")

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        reconciliation = (
            response.get("reconciliation")
            if isinstance(response, dict)
            else {}
        ) or {}
        print(
            "granola_document_id=%s action=%s dry_run=%s page_id=%s"
            % (
                granola_document_id,
                reconciliation.get("action", "?") if isinstance(reconciliation, dict) else "?",
                effective_dry_run,
                (response or {}).get("page_id", ""),
            )
        )
        if isinstance(reconciliation, dict) and reconciliation.get("reason"):
            print(f"reason={reconciliation['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
