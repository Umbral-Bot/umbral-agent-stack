"""
Recurring Drive->Notion Granola feeder (Q11-T1).

P1.1b (2026-07-16, PRs #532/#533) was a **one-shot** catch-up: 95 files,
13 hand-driven batches, per-batch throwaway driver scripts that were never
committed. Nothing about it recurs. Since it closed, David has kept pasting
transcripts into the Drive folder and none of them reached Notion -- the VPS
``gap-check`` cron looks at Notion, not at Drive, so it reports STALE without
ever noticing the backlog.

This module is that missing recurring spine. It chains the four existing
P1.1b scripts -- it does not reimplement any of them::

    granola_drive_md_ingest.py       parse the Drive folder    -> inventory
    granola_notion_raw_snapshot.py   page the Notion raw DB    -> snapshot
    list_granola_drive_ingest_gap.py classify each Drive file  -> gap report
    build_granola_drive_ingest_batch.py  emit worker payloads  -> batch
    send_granola_drive_batch.py::post_task   talk to the worker

...and adds the three things a one-shot never needed:

1. **Dry-run by default.** ``--execute`` is the only way to write, and the
   per-run caps still apply when it is passed.
2. **Per-item confirmation before every write.** Each item is sent to the
   worker as ``dry_run`` first; the write only follows if the worker's own
   verdict agrees with our classification (a ``create`` that the worker says
   matches an existing page is skipped, never written). This is the guard
   P1.1b introduced by hand at batch 10, made structural.
3. **Bounded work.** ``--max-creates`` / ``--max-updates`` keep one scheduled
   run from swallowing an entire backlog unattended. The rest is listed in
   the run report, not silently dropped.

It runs on THIS Windows machine, because ``G:\\`` only exists here -- the VPS
cannot see the Drive folder at all. Register it with
``scripts/vm/register_granola_drive_feeder_task.ps1``.

Out of scope by design: capitalization. Every payload carries
``notify_enlace=False`` and ``allow_legacy_raw_task_writes=False``, and the
worker writes ``Procesar con agente=False``. Promoting a raw page to a
task/project/publication is a separate, human-gated decision (see
``docs/54-granola-capitalize-raw-slice.md`` and the ``notion-governance-runtime``
skill).

Examples::

    # what would happen today (no network writes, exit 0)
    python scripts/vm/granola_drive_feeder.py

    # actually ingest, at most 10 new pages
    python scripts/vm/granola_drive_feeder.py --execute --max-creates 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.build_granola_drive_ingest_batch import build_batch  # noqa: E402
from scripts.list_granola_drive_ingest_gap import classify_gap, summarize  # noqa: E402
from scripts.vm.granola_drive_md_ingest import (  # noqa: E402
    DEFAULT_DRIVE_ROOT,
    build_inventory,
)
from scripts.vm.granola_notion_raw_snapshot import (  # noqa: E402
    build_snapshot,
    fetch_pages,
    resolve_notion_config,
)
from scripts.vm.send_granola_drive_batch import post_task, resolve_worker_config  # noqa: E402

DEFAULT_MAX_CREATES = 10
DEFAULT_MAX_UPDATES = 10
DEFAULT_YEAR = 2026


def default_state_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("TMPDIR") or "."
    return Path(base) / "umbral-agent-stack" / "granola-drive-feeder"


def select_items(
    batch: list[dict[str, Any]],
    *,
    max_creates: int,
    max_updates: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split ``batch`` into (selected, deferred) honouring the per-run caps.

    Order is preserved, so a backlog drains oldest-first across runs instead
    of re-picking whichever items happen to sort first.
    """
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    creates = 0
    updates = 0

    for item in batch:
        action = item.get("action")
        if action == "create":
            if max_creates >= 0 and creates >= max_creates:
                deferred.append(item)
                continue
            creates += 1
        elif action == "update_transcript":
            if max_updates >= 0 and updates >= max_updates:
                deferred.append(item)
                continue
            updates += 1
        else:
            deferred.append(item)
            continue
        selected.append(item)

    return selected, deferred


def worker_verdict_agrees(action: str, result: dict[str, Any]) -> bool:
    """True when the worker's dry-run verdict matches our classification.

    A ``create`` whose dry-run reports ``matched_existing`` means our snapshot
    was stale and a real write would either duplicate a meeting or overwrite
    someone else's page. A ``update_transcript`` that matches nothing means the
    opposite drift. Either way the item is dropped, not written.
    """
    matched = bool(result.get("matched_existing"))
    if action == "create":
        return not matched
    if action == "update_transcript":
        return matched
    return False


def _result_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        nested = response.get("result")
        if isinstance(nested, dict):
            return nested
        return response
    return {}


def run_item(
    item: dict[str, Any],
    *,
    worker_url: str,
    worker_token: str,
    execute: bool,
) -> dict[str, Any]:
    """Dry-run one item, then write it only if ``execute`` and the worker agrees."""
    action = str(item.get("action") or "")
    row: dict[str, Any] = {
        "relative_path": item["relative_path"],
        "action": action,
        "match_strategy": item.get("match_strategy", ""),
        "executed": False,
        "ok": False,
        "error": "",
    }

    payload = dict(item["payload"])
    payload["dry_run"] = True
    try:
        dry = _result_dict(post_task(worker_url, worker_token, payload))
    except Exception as exc:  # noqa: BLE001 - one bad item must not abort the run
        row["error"] = f"dry-run failed: {exc}"
        return row

    row["dry_run_reconciliation_action"] = dry.get("reconciliation_action", "")
    row["dry_run_matched_existing"] = dry.get("matched_existing")
    row["worker_match_strategy"] = dry.get("match_strategy", "")

    if not worker_verdict_agrees(action, dry):
        row["error"] = (
            f"worker dry-run disagrees with classification {action!r} "
            f"(matched_existing={dry.get('matched_existing')!r}) -- not written"
        )
        return row

    if not execute:
        row["ok"] = True
        return row

    payload["dry_run"] = False
    try:
        result = _result_dict(post_task(worker_url, worker_token, payload))
    except Exception as exc:  # noqa: BLE001
        row["error"] = f"execute failed: {exc}"
        return row

    row.update(
        {
            "executed": True,
            "ok": True,
            "page_id": result.get("page_id", ""),
            "url": result.get("url", ""),
            "reconciliation_action": result.get("reconciliation_action", ""),
            "resolved_title": result.get("resolved_title", ""),
        }
    )
    return row


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recurring Drive->Notion Granola feeder. Dry-run by default; "
            "--execute is required to write anything."
        )
    )
    parser.add_argument("--root", default=None, help=f"Drive folder (default: {DEFAULT_DRIVE_ROOT})")
    parser.add_argument("--default-year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--state-dir", default=None, help="Where run artifacts are written")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write to Notion. Without this nothing is written, whatever else is passed.",
    )
    parser.add_argument("--max-creates", type=int, default=DEFAULT_MAX_CREATES)
    parser.add_argument("--max-updates", type=int, default=DEFAULT_MAX_UPDATES)
    parser.add_argument("--worker-url", dest="worker_url", default=None)
    parser.add_argument("--worker-token", dest="worker_token", default=None)
    parser.add_argument("--notion-api-key", dest="notion_api_key", default=None)
    parser.add_argument("--notion-database-id", dest="notion_database_id", default=None)
    parser.add_argument(
        "--notion-pages",
        dest="notion_pages",
        default=None,
        help=(
            "Use this pre-built snapshot instead of querying Notion (same shape "
            "granola_notion_raw_snapshot.py writes). For offline inspection and for "
            "re-running a classification against a snapshot you already trust."
        ),
    )
    parser.add_argument(
        "--skip-worker",
        action="store_true",
        help="Stop after the gap report (no worker calls at all). Useful to inspect a backlog offline.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    state_dir = Path(args.state_dir) if args.state_dir else default_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    root = Path(args.root or DEFAULT_DRIVE_ROOT)
    drive_records = build_inventory(root, default_year=args.default_year)

    if args.notion_pages:
        notion_records = json.loads(
            Path(args.notion_pages).read_text(encoding="utf-8")
        ).get("records", [])
        notion_source = args.notion_pages
    else:
        api_key, database_id = resolve_notion_config(args.notion_api_key, args.notion_database_id)
        notion_records = build_snapshot(fetch_pages(api_key, database_id))["records"]
        notion_source = "live"

    gap_items = classify_gap(drive_records, notion_records)
    summary = summarize(gap_items)
    batch = build_batch(drive_records, gap_items)
    selected, deferred = select_items(
        batch, max_creates=args.max_creates, max_updates=args.max_updates
    )

    report: dict[str, Any] = {
        "timestamp": stamp,
        "root": str(root),
        "execute": bool(args.execute),
        "drive_files": len(drive_records),
        "notion_pages": len(notion_records),
        "notion_source": notion_source,
        "summary": summary,
        "batch_total": len(batch),
        "selected": [
            {"relative_path": i["relative_path"], "action": i["action"]} for i in selected
        ],
        "deferred": [
            {"relative_path": i["relative_path"], "action": i["action"]} for i in deferred
        ],
        "results": [],
    }

    if not args.skip_worker and selected:
        worker_url, worker_token = resolve_worker_config(args.worker_url, args.worker_token)
        report["results"] = [
            run_item(item, worker_url=worker_url, worker_token=worker_token, execute=args.execute)
            for item in selected
        ]

    report_path = state_dir / f"run-{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    written = sum(1 for r in report["results"] if r.get("executed"))
    failed = [r for r in report["results"] if not r.get("ok")]
    print(
        json.dumps(
            {
                "drive_files": report["drive_files"],
                "notion_pages": report["notion_pages"],
                "gap": summary,
                "selected": len(selected),
                "deferred": len(deferred),
                "written": written,
                "failed": len(failed),
                "execute": bool(args.execute),
                "report": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    for row in failed:
        print(f"FAIL {row['relative_path']}: {row['error']}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
