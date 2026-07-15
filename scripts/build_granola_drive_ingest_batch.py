"""
Phase 3 batch builder for the P1.1b Drive->Notion Granola catch-up.

Joins the Drive inventory (``scripts/vm/granola_drive_md_ingest.py``) with the
gap classification (``scripts/list_granola_drive_ingest_gap.py``) and emits
one ``granola.process_transcript`` payload per ``create``/``update_transcript``
item, each carrying ``dry_run: true``. ``review_ambiguous`` and ``skip`` items
are excluded from the batch entirely (never auto-acted on).

This produces the batch file only — it does not call the worker. Nothing here
writes to Notion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.vm.granola_drive_md_ingest import build_payload

INCLUDED_ACTIONS = {"create", "update_transcript"}


def build_batch(
    drive_records: list[dict[str, Any]],
    gap_items: list[dict[str, Any]],
    *,
    dry_run: bool = True,
) -> list[dict[str, Any]]:
    drive_by_path = {r["relative_path"]: r for r in drive_records}
    batch: list[dict[str, Any]] = []

    for item in gap_items:
        if item["action"] not in INCLUDED_ACTIONS:
            continue
        drive = drive_by_path.get(item["relative_path"])
        if drive is None:
            continue
        payload = build_payload(
            drive["parsed"],
            relative_path=drive["relative_path"],
            file_sha1=drive["sha1"],
        )
        payload["dry_run"] = dry_run

        title_override = item.get("title_override")
        if title_override and title_override != payload["title"]:
            # Human-confirmed pairing with an existing page under a
            # different title (e.g. a typo) — send the CONFIRMED title so
            # the worker's own title+date matching finds that exact page
            # instead of creating a duplicate. The final stored title is
            # unaffected by this (the worker keeps the existing page's
            # title on update); this is purely a matching signal.
            payload["metadata"]["drive_original_title"] = payload["title"]
            payload["title"] = title_override
        batch.append(
            {
                "relative_path": item["relative_path"],
                "action": item["action"],
                "match_strategy": item.get("match_strategy", ""),
                "matched_page": item.get("matched_page"),
                "payload": payload,
            }
        )
    return batch


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the P1.1b dry-run batch (no Notion writes).")
    parser.add_argument("--drive-inventory", required=True)
    parser.add_argument("--gap-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    drive_data = json.loads(Path(args.drive_inventory).read_text(encoding="utf-8"))
    gap_data = json.loads(Path(args.gap_report).read_text(encoding="utf-8"))

    batch = build_batch(drive_data.get("records", []), gap_data.get("items", []))

    Path(args.output).write_text(
        json.dumps({"dry_run": True, "count": len(batch), "items": batch}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"count": len(batch)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
