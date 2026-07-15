"""
Phase 4 sender for the P1.1b Drive->Notion Granola catch-up.

Takes a batch produced by ``scripts/build_granola_drive_ingest_batch.py``
(list of ``{relative_path, action, match_strategy, matched_page, payload}``)
and POSTs each ``payload`` to the worker's ``/run`` endpoint for task
``granola.process_transcript`` — the SAME existing worker task every other
Granola feeder uses. No new Notion-writing code.

SAFETY: without ``--execute``, every payload is sent with ``dry_run`` forced
``true`` regardless of what the batch file says — this script can never
write to Notion by omission. ``--execute`` is required, explicitly, to
perform a real write.

Select a slice of the batch with ``--relative-paths`` (comma-separated,
order preserved) or ``--limit``. Reads ``WORKER_URL``/``WORKER_TOKEN`` from
the environment (matches ``client/worker_client.py``'s own resolution).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


def resolve_worker_config(worker_url: str | None = None, worker_token: str | None = None) -> tuple[str, str]:
    url = (worker_url or os.environ.get("WORKER_URL") or "").strip()
    if not url:
        raise RuntimeError("WORKER_URL not set. Pass --worker-url or set the WORKER_URL env var.")
    token = (worker_token or os.environ.get("WORKER_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("WORKER_TOKEN not set. Pass --worker-token or set the WORKER_TOKEN env var.")
    return url.rstrip("/"), token


def select_items(
    items: list[dict[str, Any]],
    *,
    relative_paths: list[str] | None = None,
    limit: int = 0,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Select a slice of the batch. Returns (selected, missing_relative_paths)."""
    if relative_paths:
        by_path = {item["relative_path"]: item for item in items}
        selected = [by_path[p] for p in relative_paths if p in by_path]
        missing = [p for p in relative_paths if p not in by_path]
        return selected, missing
    if limit and limit > 0:
        return items[:limit], []
    return items, []


def post_task(worker_url: str, worker_token: str, payload: dict[str, Any]) -> Any:
    resp = requests.post(
        f"{worker_url}/run",
        json={"task": "granola.process_transcript", "input": payload},
        headers={"Authorization": f"Bearer {worker_token}", "Content-Type": "application/json"},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()


def _result_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        nested = response.get("result")
        if isinstance(nested, dict):
            return nested
        return response
    return {}


def run_batch(
    items: list[dict[str, Any]],
    *,
    worker_url: str,
    worker_token: str,
    execute: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in items:
        payload = dict(item["payload"])
        payload["dry_run"] = not execute
        row: dict[str, Any] = {
            "relative_path": item["relative_path"],
            "action": item["action"],
            "match_strategy": item.get("match_strategy", ""),
            "execute": execute,
        }
        try:
            response = post_task(worker_url, worker_token, payload)
            result = _result_dict(response)
            row.update(
                {
                    "ok": True,
                    "page_id": result.get("page_id", ""),
                    "url": result.get("url", ""),
                    "reconciliation_action": result.get("reconciliation_action", ""),
                    "matched_existing": result.get("matched_existing"),
                    "worker_match_strategy": result.get("match_strategy", ""),
                    "resolved_title": result.get("resolved_title", ""),
                    "dry_run": result.get("dry_run"),
                    "error": "",
                }
            )
        except Exception as exc:  # noqa: BLE001 - report per-item, never abort the batch
            row.update({"ok": False, "error": str(exc)})
        results.append(row)
    return results


def print_table(results: list[dict[str, Any]]) -> None:
    print(f"{'archivo':<45} {'accion':<18} {'OK/FAIL':<8} {'page_id / url'}")
    for r in results:
        status = "OK" if r.get("ok") else "FAIL"
        detail = r.get("url") or r.get("error") or ""
        print(f"{r['relative_path']:<45} {r['action']:<18} {status:<8} {detail}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a P1.1b Drive Granola batch slice to the worker (dry-run by default).")
    parser.add_argument("--batch", required=True, help="Path to the batch JSON from build_granola_drive_ingest_batch.py")
    parser.add_argument("--relative-paths", help="Comma-separated relative_path values to select (order preserved)")
    parser.add_argument("--limit", type=int, default=0, help="Only send the first N items (0 = all)")
    parser.add_argument("--execute", action="store_true", help="Actually write to Notion. Without this, every item is sent with dry_run=true.")
    parser.add_argument("--worker-url", dest="worker_url", default=None)
    parser.add_argument("--worker-token", dest="worker_token", default=None)
    parser.add_argument("--output", help="Optional path to write the results JSON")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    batch_data = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    items = batch_data.get("items", [])

    relative_paths = [p.strip() for p in args.relative_paths.split(",")] if args.relative_paths else None
    selected, missing = select_items(items, relative_paths=relative_paths, limit=args.limit)
    if missing:
        print(f"WARNING: relative_path(s) not found in batch, skipped: {missing}", file=sys.stderr)

    worker_url, worker_token = resolve_worker_config(args.worker_url, args.worker_token)
    results = run_batch(selected, worker_url=worker_url, worker_token=worker_token, execute=args.execute)

    print_table(results)
    if args.output:
        Path(args.output).write_text(json.dumps({"execute": args.execute, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
