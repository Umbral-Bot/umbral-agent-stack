"""
Granola Direct API -> Worker -> Notion ingestion helper.

Runs on the Windows VM where the Granola desktop app is installed.
Uses the local WorkOS access token stored by Granola to fetch meeting
documents and transcripts from Granola's internal API, then forwards the
selected meeting to the local Worker via granola.process_transcript.

Examples:
    python scripts/vm/granola_api_ingest.py --latest
    python scripts/vm/granola_api_ingest.py --title-query "BIM"
    python scripts/vm/granola_api_ingest.py --document-id 4d4c239d-...
    python scripts/vm/granola_api_ingest.py --latest --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.vm.granola_watcher_env_loader import load_env

DEFAULT_ENV_FILE = r"C:\Granola\.env"
DEFAULT_SUPABASE_PATH = r"C:\Users\Rick\AppData\Roaming\Granola\supabase.json"
DEFAULT_WORKER_TOKEN_FILE = r"C:\openclaw-worker\worker_token"
GRANOLA_API_BASE = "https://api.granola.ai/v1"


def load_granola_access_token(supabase_path: str) -> str:
    raw = json.loads(Path(supabase_path).read_text(encoding="utf-8"))
    workos_tokens = raw.get("workos_tokens")
    if isinstance(workos_tokens, str):
        workos_tokens = json.loads(workos_tokens)
    if not isinstance(workos_tokens, dict):
        raise RuntimeError("Granola supabase.json does not contain workos_tokens")
    token = str(workos_tokens.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Granola WorkOS access_token not found in supabase.json")
    return token


def _granola_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "Granola/Direct-Ingest",
    }


def granola_post(path: str, payload: dict[str, Any], access_token: str) -> Any:
    resp = requests.post(
        f"{GRANOLA_API_BASE}{path}",
        json=payload,
        headers=_granola_headers(access_token),
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()


def list_documents(access_token: str) -> list[dict[str, Any]]:
    data = granola_post("/get-documents", {}, access_token)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("documents", "results", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    raise RuntimeError("Granola get-documents response shape not recognized")


def choose_document(
    documents: list[dict[str, Any]],
    *,
    document_id: str | None = None,
    title_query: str | None = None,
    latest: bool = False,
) -> dict[str, Any]:
    if not documents:
        raise RuntimeError("Granola documents list is empty")

    if document_id:
        for doc in documents:
            if str(doc.get("id", "")).strip() == document_id.strip():
                return doc
        raise RuntimeError(f"Granola document not found: {document_id}")

    ordered = sorted(
        documents,
        key=lambda d: str(d.get("updated_at") or d.get("created_at") or ""),
        reverse=True,
    )

    if title_query:
        needle = title_query.strip().lower()
        for doc in ordered:
            title = str(doc.get("title") or "").lower()
            if needle in title:
                return doc
        raise RuntimeError(f"No Granola document matched title query: {title_query}")

    if latest:
        return ordered[0]

    raise RuntimeError("Provide one of: --document-id, --title-query, or --latest")


def render_transcript_markdown(items: list[dict[str, Any]]) -> str:
    lines = ["## Transcripción", ""]
    for item in items:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        source = str(item.get("source") or "system").strip().lower()
        speaker = "David/host" if source == "microphone" else "Interlocutor"
        start = str(item.get("start_timestamp") or "").strip()
        ts = start[11:19] if len(start) >= 19 else ""
        prefix = f"[{ts}] " if ts else ""
        lines.append(f"- **{speaker}:** {prefix}{text}")
    return "\n".join(lines).strip()


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


def send_to_worker(worker_url: str, worker_token: str, task: str, input_data: dict[str, Any]) -> Any:
    resp = requests.post(
        f"{worker_url.rstrip('/')}/run",
        json={"task": task, "input": input_data},
        headers={
            "Authorization": f"Bearer {worker_token}",
            "Content-Type": "application/json",
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()


def ingest_document(
    doc: dict[str, Any],
    *,
    access_token: str,
    worker_url: str,
    worker_token: str,
    notify_enlace: bool,
    dry_run: bool,
) -> dict[str, Any]:
    doc_id = str(doc.get("id") or "").strip()
    if not doc_id:
        raise RuntimeError("Granola document has no id")

    metadata = granola_post("/get-document-metadata", {"document_id": doc_id}, access_token)
    transcript_items = granola_post("/get-document-transcript", {"document_id": doc_id}, access_token)
    if not isinstance(transcript_items, list):
        raise RuntimeError("Granola transcript response is not a list")

    title = str(doc.get("title") or metadata.get("title") or doc_id).strip()
    created_at = str(doc.get("created_at") or doc.get("updated_at") or "").strip()
    meeting_date = created_at[:10] if len(created_at) >= 10 else None

    attendees: list[str] = []
    creator = metadata.get("creator") if isinstance(metadata, dict) else None
    if isinstance(creator, dict):
        creator_name = str(creator.get("name") or "").strip()
        if creator_name:
            attendees.append(creator_name)
        for attendee in creator.get("attendees") or []:
            if isinstance(attendee, dict):
                name = str(attendee.get("name") or attendee.get("email") or "").strip()
            else:
                name = str(attendee).strip()
            if name:
                attendees.append(name)

    content = render_transcript_markdown(transcript_items)
    payload = {
        "title": title,
        "content": content,
        "source": "granola_api",
        "notify_enlace": notify_enlace,
    }
    if meeting_date:
        payload["date"] = meeting_date
    if attendees:
        payload["attendees"] = attendees

    if dry_run:
        worker_result: Any = {"dry_run": True, "payload_preview": payload}
    else:
        worker_result = send_to_worker(worker_url, worker_token, "granola.process_transcript", payload)

    return {
        "document_id": doc_id,
        "title": title,
        "meeting_date": meeting_date,
        "transcript_items": len(transcript_items),
        "content_chars": len(content),
        "worker_result": worker_result,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest a real Granola meeting directly from the desktop app API."
    )
    parser.add_argument("--document-id", help="Exact Granola document id to ingest")
    parser.add_argument("--title-query", help="Case-insensitive substring to match in Granola titles")
    parser.add_argument("--latest", action="store_true", help="Select the most recently updated meeting")
    parser.add_argument("--list", action="store_true", help="List recent documents and exit")
    parser.add_argument("--limit", type=int, default=10, help="Max docs to print in --list mode")
    parser.add_argument("--dry-run", action="store_true", help="Build payload but do not call the Worker")
    parser.add_argument(
        "--notify-enlace",
        dest="notify_enlace",
        action="store_true",
        default=True,
        help="Notify @Enlace after transcript ingestion (default on)",
    )
    parser.add_argument(
        "--no-notify-enlace",
        dest="notify_enlace",
        action="store_false",
        help="Do not notify @Enlace",
    )
    return parser


def main() -> int:
    load_env(os.environ.get("GRANOLA_ENV_FILE", DEFAULT_ENV_FILE))
    args = build_arg_parser().parse_args()

    access_token = load_granola_access_token(
        os.environ.get("GRANOLA_SUPABASE_PATH", DEFAULT_SUPABASE_PATH)
    )
    documents = list_documents(access_token)

    if args.list:
        ordered = sorted(
            documents,
            key=lambda d: str(d.get("updated_at") or d.get("created_at") or ""),
            reverse=True,
        )
        preview = [
            {
                "id": doc.get("id"),
                "title": doc.get("title"),
                "updated_at": doc.get("updated_at"),
                "created_at": doc.get("created_at"),
            }
            for doc in ordered[: max(1, args.limit)]
        ]
        print(json.dumps({"documents": preview, "count": len(preview)}, ensure_ascii=False, indent=2))
        return 0

    selected = choose_document(
        documents,
        document_id=args.document_id,
        title_query=args.title_query,
        latest=args.latest,
    )
    worker_url = os.environ.get("GRANOLA_WORKER_URL") or os.environ.get("WORKER_URL") or "http://127.0.0.1:8088"
    worker_token = _worker_token_from_env_or_file()
    result = ingest_document(
        selected,
        access_token=access_token,
        worker_url=worker_url,
        worker_token=worker_token,
        notify_enlace=args.notify_enlace,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
