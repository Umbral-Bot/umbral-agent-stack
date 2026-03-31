#!/usr/bin/env python3
"""Run a controlled raw-only Granola ingest batch from the live gap report.

This runner is intentionally narrow:
- it only targets the raw Granola DB through `granola.process_transcript`
- it never enables raw -> canonical writes
- it defaults to `batch1_recent_unique`
- it refuses ambiguous buckets unless explicitly allowed

By default it performs a dry-run preview and still materializes temporary
markdown exports under `.tmp/granola_raw_ingest_batch/...` so the exact payload
can be inspected before writing to Notion.
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
sys.path.insert(0, str(REPO_ROOT))

from client.worker_client import WorkerClient
from scripts import env_loader

env_loader.load()

from scripts.list_granola_raw_ingest_gap import build_report
from scripts.vm import granola_cache_exporter
from scripts.vm.granola_watcher import parse_granola_markdown
from worker.tasks.granola import handle_granola_process_transcript


SAFE_BUCKETS = {"batch1_recent_unique", "historic_unique"}
AMBIGUOUS_BUCKETS = {"batch1_recent_ambiguous", "historic_ambiguous"}
ALL_BUCKETS = SAFE_BUCKETS | AMBIGUOUS_BUCKETS


def _default_cache_path() -> str:
    return os.environ.get(
        "GRANOLA_CACHE_PATH",
        str(Path(os.environ.get("APPDATA", "")) / "Granola" / "cache-v6.json"),
    )


def _default_batch_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / ".tmp" / "granola_raw_ingest_batch" / stamp


def _select_candidates(
    report: dict[str, Any],
    *,
    bucket: str,
    document_ids: list[str] | None = None,
    limit: int | None = None,
    allow_ambiguous: bool = False,
) -> list[dict[str, Any]]:
    if bucket not in ALL_BUCKETS:
        raise ValueError(f"Unsupported bucket: {bucket}")
    if bucket in AMBIGUOUS_BUCKETS and not allow_ambiguous:
        raise ValueError(
            f"Bucket '{bucket}' is ambiguous and requires --allow-ambiguous"
        )

    selected = list(report.get(bucket) or [])
    if document_ids:
        allowed = {item.strip() for item in document_ids if item.strip()}
        selected = [
            item
            for item in selected
            if str(item.get("document_id") or "").strip() in allowed
        ]
    if limit is not None:
        selected = selected[: max(0, limit)]
    return selected


def _resolve_execution_mode(
    mode: str,
    *,
    worker_url: str = "",
    worker_token: str = "",
) -> str:
    normalized = (mode or "auto").strip().lower()
    if normalized not in {"auto", "worker", "local"}:
        raise ValueError(f"Unsupported mode: {mode}")
    if normalized != "auto":
        return normalized
    if worker_url.strip() and worker_token.strip():
        return "worker"
    return "local"


def _build_task_input(
    parsed: dict[str, Any],
    export_item: dict[str, Any],
    *,
    notify_enlace: bool,
) -> dict[str, Any]:
    task_input = dict(parsed)
    task_input["source"] = str(task_input.get("source") or "granola")
    task_input["notify_enlace"] = bool(notify_enlace)
    task_input["allow_legacy_raw_task_writes"] = False
    task_input["granola_document_id"] = str(
        task_input.get("granola_document_id") or export_item.get("document_id") or ""
    ).strip()
    task_input["source_updated_at"] = str(
        task_input.get("source_updated_at") or ""
    ).strip()
    task_input["source_url"] = str(task_input.get("source_url") or "").strip()
    return task_input


def _prepare_batch_inputs(
    *,
    cache_path: Path,
    selected_candidates: list[dict[str, Any]],
    batch_dir: Path,
    notify_enlace: bool,
    enable_private_api_hydration: bool,
) -> dict[str, Any]:
    export_dir = batch_dir / "exports"
    processed_dir = batch_dir / "processed"
    manifest_path = batch_dir / "manifest.json"
    export_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    requested_ids = {
        str(item.get("document_id") or "").strip()
        for item in selected_candidates
        if str(item.get("document_id") or "").strip()
    }
    export_summary = granola_cache_exporter.export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        dry_run=False,
        force=True,
        limit=None,
        document_ids=requested_ids or None,
        enable_private_api_hydration=enable_private_api_hydration,
    )

    candidate_by_id = {
        str(item.get("document_id") or "").strip(): item for item in selected_candidates
    }
    order = {doc_id: index for index, doc_id in enumerate(candidate_by_id)}
    prepared: list[dict[str, Any]] = []
    for export_item in export_summary.get("exports", []):
        document_id = str(export_item.get("document_id") or "").strip()
        export_path = export_dir / str(export_item.get("filename") or "")
        text = export_path.read_text(encoding="utf-8")
        parsed = parse_granola_markdown(text, export_path.name)
        task_input = _build_task_input(
            parsed,
            export_item,
            notify_enlace=notify_enlace,
        )
        prepared.append(
            {
                "document_id": document_id,
                "title": str(export_item.get("title") or task_input.get("title") or ""),
                "meeting_date": str(
                    export_item.get("meeting_date") or task_input.get("date") or ""
                ),
                "filename": export_path.name,
                "export_path": str(export_path),
                "candidate": candidate_by_id.get(document_id, {}),
                "task_input": task_input,
            }
        )

    prepared.sort(key=lambda item: order.get(item["document_id"], 10**6))
    prepared_ids = {item["document_id"] for item in prepared}
    missing_ids = sorted(requested_ids - prepared_ids)

    return {
        "batch_dir": str(batch_dir),
        "export_dir": str(export_dir),
        "processed_dir": str(processed_dir),
        "manifest_path": str(manifest_path),
        "export_summary": export_summary,
        "prepared": prepared,
        "missing_document_ids": missing_ids,
    }


def _execute_prepared(
    prepared: list[dict[str, Any]],
    *,
    mode: str,
    worker_url: str,
    worker_token: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    wc: WorkerClient | None = None
    if mode == "worker":
        wc = WorkerClient(
            base_url=worker_url,
            token=worker_token,
            timeout=120.0,
            caller_id="script.run_granola_raw_ingest_batch",
        )

    for item in prepared:
        task_input = dict(item["task_input"])
        try:
            if mode == "worker":
                assert wc is not None
                response = wc.run("granola.process_transcript", task_input)
            else:
                response = handle_granola_process_transcript(task_input)
            results.append(
                {
                    "document_id": item["document_id"],
                    "title": item["title"],
                    "ok": True,
                    "response": response,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "document_id": item["document_id"],
                    "title": item["title"],
                    "ok": False,
                    "error": str(exc),
                }
            )
    return results


def _print_human(summary: dict[str, Any]) -> None:
    print(
        f"Bucket: {summary['bucket']} | selected={summary['selected_count']} | "
        f"execute={summary['execute']} | mode={summary['execution_mode']}"
    )
    print(f"Batch dir: {summary['batch_dir']}")
    if summary["missing_document_ids"]:
        print(f"Missing exports: {', '.join(summary['missing_document_ids'])}")
    for item in summary["selected_items"]:
        print(
            f"- {item['document_id']} :: {item['title']} :: {item['meeting_date']} :: "
            f"classification={item['classification']}"
        )
    if summary["execute"]:
        ok = sum(1 for item in summary["results"] if item.get("ok"))
        failed = len(summary["results"]) - ok
        print(f"Execution results: ok={ok} failed={failed}")
        for item in summary["results"]:
            status = "OK" if item["ok"] else "FAILED"
            print(f"  [{status}] {item['document_id']} :: {item['title']}")
            if not item["ok"]:
                print(f"    error: {item['error']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a controlled raw-only Granola ingest batch"
    )
    parser.add_argument(
        "--bucket",
        default="batch1_recent_unique",
        help="Gap report bucket to ingest (default: batch1_recent_unique)",
    )
    parser.add_argument(
        "--document-id",
        action="append",
        help="Restrict to a specific Granola document id (repeatable)",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of items to run")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the raw writes. Default is preview-only dry-run.",
    )
    parser.add_argument(
        "--mode",
        default="auto",
        help="Execution mode: auto | worker | local (default: auto)",
    )
    parser.add_argument(
        "--allow-ambiguous",
        action="store_true",
        help="Allow ambiguous buckets. Default is blocked for safety.",
    )
    parser.add_argument(
        "--notify-enlace",
        action="store_true",
        help="Notify Enlace during ingest. Default is off for batch safety.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    parser.add_argument(
        "--cache-path",
        default=_default_cache_path(),
        help="Path to Granola cache-v6.json",
    )
    parser.add_argument(
        "--max-raw-items",
        type=int,
        default=200,
        help="Maximum raw Notion items to inspect in the gap report",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=7,
        help="How many trailing days count as recent in the gap report",
    )
    parser.add_argument(
        "--batch-dir",
        help="Explicit directory for temporary exported markdown batch files",
    )
    parser.add_argument(
        "--worker-url",
        help="Override WORKER_URL when using worker mode",
    )
    parser.add_argument(
        "--worker-token",
        help="Override WORKER_TOKEN when using worker mode",
    )
    parser.add_argument(
        "--no-private-api-hydration",
        action="store_true",
        help="Disable Granola private API hydration and rely on cache-v6.json only",
    )
    args = parser.parse_args()

    cache_path = Path(args.cache_path)
    if not cache_path.is_file():
        raise RuntimeError(f"Granola cache not found: {cache_path}")

    report = build_report(
        cache_path=cache_path,
        max_items=args.max_raw_items,
        recent_days=args.recent_days,
        enable_private_api_hydration=not args.no_private_api_hydration,
    )
    selected_candidates = _select_candidates(
        report,
        bucket=args.bucket,
        document_ids=args.document_id,
        limit=args.limit,
        allow_ambiguous=args.allow_ambiguous,
    )

    batch_dir = Path(args.batch_dir) if args.batch_dir else _default_batch_dir()
    prepared_batch = _prepare_batch_inputs(
        cache_path=cache_path,
        selected_candidates=selected_candidates,
        batch_dir=batch_dir,
        notify_enlace=args.notify_enlace,
        enable_private_api_hydration=not args.no_private_api_hydration,
    )

    worker_url = (args.worker_url or os.environ.get("WORKER_URL") or "").rstrip("/")
    worker_token = (args.worker_token or os.environ.get("WORKER_TOKEN") or "").strip()
    execution_mode = _resolve_execution_mode(
        args.mode,
        worker_url=worker_url,
        worker_token=worker_token,
    )

    results: list[dict[str, Any]] = []
    if args.execute:
        results = _execute_prepared(
            prepared_batch["prepared"],
            mode=execution_mode,
            worker_url=worker_url,
            worker_token=worker_token,
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "bucket": args.bucket,
        "execute": bool(args.execute),
        "execution_mode": execution_mode,
        "notify_enlace": bool(args.notify_enlace),
        "selected_count": len(selected_candidates),
        "selected_items": [
            {
                "document_id": str(item.get("document_id") or ""),
                "title": str(item.get("title") or ""),
                "meeting_date": str(item.get("meeting_date") or ""),
                "classification": str(item.get("classification") or ""),
            }
            for item in selected_candidates
        ],
        "batch_dir": prepared_batch["batch_dir"],
        "export_dir": prepared_batch["export_dir"],
        "processed_dir": prepared_batch["processed_dir"],
        "manifest_path": prepared_batch["manifest_path"],
        "missing_document_ids": prepared_batch["missing_document_ids"],
        "prepared_count": len(prepared_batch["prepared"]),
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_human(summary)

    if args.execute:
        failed = sum(1 for item in results if not item.get("ok"))
        return 0 if failed == 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
