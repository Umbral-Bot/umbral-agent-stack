"""
Phase 0/1 gap-check for the P1.1b Drive->Notion Granola catch-up.

Read-only. Compares the Drive-pasted transcript inventory (built by
``scripts/vm/granola_drive_md_ingest.py``) against the existing pages in the
canonical "Transcripciones Granola" Notion DB, and classifies each Drive file
as ``create`` / ``update_transcript`` / ``skip`` / ``review_ambiguous``.

Match criterion (documented, per the P1.1b spec):

1. ``shared_folder_path`` + ``sha1`` both equal an existing page's traceability
   -> ``skip`` (this exact file was already ingested byte-for-byte by this
   same feeder on a prior run).
2. ``shared_folder_path`` equal but ``sha1`` differs -> ``update_transcript``
   (the file changed since a prior run of this feeder ingested it).
3. Otherwise, **normalized title + date** (mirroring
   ``worker/tasks/granola.py::_find_existing_raw_candidate`` tiers 7/8 —
   accent/case-folded title, exact ``YYYY-MM-DD`` date), matched only when
   exactly one existing page qualifies:
   - if that page's existing content looks summary-only (short "Longitud
     Notion" and/or ``Fuente`` in {"granola", "granola_mcp"} without a prior
     Drive ingest) -> ``update_transcript`` (attach the verbatim transcript)
   - otherwise -> ``update_transcript`` as well, since only a full transcript
     upsert can tell whether content actually changed; the worker's own
     finality/reconciliation gate (``decide_reconciliation``) is the
     authority on whether a real write happens once this reaches
     ``granola.process_transcript`` with ``dry_run``/execute.
4. If more than one existing page matches normalized title + date -> flagged
   ``review_ambiguous`` (never auto-create or auto-update).
5. If normalized title matches but zero or more-than-one page share the date
   (including drive files with no parseable date) -> also
   ``review_ambiguous`` if there is at least one same-title candidate,
   otherwise fall through to (6).
6. No existing page shares the normalized title at all -> ``create``.

This mirrors (but does not replace) the worker's own dedup logic — the
worker's ``dry_run`` request is the final authority at execute time.
"""

from __future__ import annotations

import argparse
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

NEAR_DUPLICATE_THRESHOLD = 0.84


def _title_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def classify_gap(
    drive_records: list[dict[str, Any]],
    notion_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify each Drive record against the existing Notion pages.

    ``drive_records`` items must have ``relative_path``, ``sha1``, and
    ``parsed`` (with ``title``, ``normalized_title``, ``date``).
    ``notion_records`` items must have ``title``, ``normalized_title``,
    ``date``, ``shared_folder_path``, ``sha1``, ``fuente``, ``page_id``,
    ``url``.
    """
    results: list[dict[str, Any]] = []

    for drive in drive_records:
        parsed = drive.get("parsed") or {}
        title = str(parsed.get("title") or "")
        normalized_title = str(parsed.get("normalized_title") or "")
        date = str(parsed.get("date") or "")
        relative_path = str(drive.get("relative_path") or "")
        file_sha1 = str(drive.get("sha1") or "")

        entry: dict[str, Any] = {
            "filename": drive.get("filename"),
            "relative_path": relative_path,
            "title": title,
            "date": date,
            "en_drive": True,
            "en_notion": False,
            "action": "create",
            "match_strategy": "",
            "matched_page": None,
            "candidates": [],
            "notes": [],
        }

        # Tier 1/2: this feeder's own prior traceability.
        path_matches = [
            n for n in notion_records if n.get("shared_folder_path") == relative_path
        ]
        if path_matches:
            match = path_matches[0]
            entry["en_notion"] = True
            entry["matched_page"] = {"page_id": match.get("page_id"), "url": match.get("url")}
            if match.get("sha1") == file_sha1 and file_sha1:
                entry["action"] = "skip"
                entry["match_strategy"] = "shared_folder_path_sha1"
            else:
                entry["action"] = "update_transcript"
                entry["match_strategy"] = "shared_folder_path_changed"
            results.append(entry)
            continue

        # Tier 3-6: normalized title (+ date).
        title_matches = [
            n for n in notion_records if n.get("normalized_title") == normalized_title
        ]
        if title_matches:
            entry["en_notion"] = True
            date_matches = [n for n in title_matches if date and n.get("date") == date]
            if len(date_matches) == 1:
                match = date_matches[0]
                entry["matched_page"] = {"page_id": match.get("page_id"), "url": match.get("url")}
                entry["action"] = "update_transcript"
                entry["match_strategy"] = "normalized_title_date"
                fuente = str(match.get("fuente") or "")
                if fuente and fuente != "granola_drive_md":
                    entry["notes"].append(
                        f"existing page fuente={fuente!r} (likely summary/other source) — verbatim transcript will be attached"
                    )
            elif len(title_matches) == 1 and not date:
                match = title_matches[0]
                entry["matched_page"] = {"page_id": match.get("page_id"), "url": match.get("url")}
                entry["action"] = "review_ambiguous"
                entry["match_strategy"] = "normalized_title_only_no_drive_date"
                entry["notes"].append("Drive file has no parseable date; single title match found — confirm before update")
            elif date and len(date_matches) == 0:
                # Same title exists in Notion, but under a DIFFERENT date than
                # every candidate — e.g. a recurring meeting series
                # ("Konstruedu", "BIM Forum") where each dated instance is a
                # genuinely distinct meeting. Per David's rule: exact date
                # match -> update; no date match at all among same-title
                # candidates -> treat as a new/distinct meeting -> create.
                entry["action"] = "create"
                entry["match_strategy"] = "same_title_no_exact_date_match"
                entry["candidates"] = [
                    {"page_id": n.get("page_id"), "url": n.get("url"), "title": n.get("title"), "date": n.get("date")}
                    for n in title_matches
                ]
                entry["notes"].append(
                    "same normalized title exists in Notion but none share the exact date — treated as a distinct meeting instance"
                )
            else:
                # Multiple candidates share the exact date (data-quality
                # collision) -> genuinely ambiguous, never auto-resolved.
                entry["action"] = "review_ambiguous"
                entry["match_strategy"] = "normalized_title_multiple_or_date_mismatch"
                entry["candidates"] = [
                    {"page_id": n.get("page_id"), "url": n.get("url"), "title": n.get("title"), "date": n.get("date")}
                    for n in title_matches
                ]
            results.append(entry)
            continue

        # No exact normalized-title match at all -> create, but flag near-dup titles.
        near_dupes = [
            {"page_id": n.get("page_id"), "url": n.get("url"), "title": n.get("title"), "date": n.get("date"), "ratio": round(ratio, 3)}
            for n in notion_records
            if (ratio := _title_ratio(normalized_title, str(n.get("normalized_title") or ""))) >= NEAR_DUPLICATE_THRESHOLD
        ]
        if near_dupes:
            entry["candidates"] = near_dupes
            exact_date_dupes = [d for d in near_dupes if date and d.get("date") == date]
            if exact_date_dupes:
                # A near-duplicate title (typo/rewording) sharing the exact
                # same date is much more likely the same meeting than a
                # coincidence — do NOT auto-create a probable duplicate page.
                # Escalate for human/worker-dry-run confirmation instead.
                entry["en_notion"] = True
                entry["action"] = "review_ambiguous"
                entry["match_strategy"] = "near_duplicate_title_exact_date"
                entry["notes"].append(
                    "near-duplicate title with an EXACT date match — likely the same meeting under a different title; confirm before create/update"
                )
            else:
                entry["notes"].append("near-duplicate title(s) in Notion — not an exact date match, review before create")
        results.append(entry)

    return results


def apply_manual_overrides(
    classified: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply human-confirmed resolutions for ``review_ambiguous`` items.

    Each override must have ``relative_path`` (to find the item) and
    ``action``. When resolving to ``update_transcript`` it should also carry
    ``page_id``, ``url``, and ``title`` (the CONFIRMED existing page's own
    title) — ``title`` is required because the worker's own dedup logic
    (``worker/tasks/granola.py::_find_existing_raw_candidate``) only offers a
    title+date matching tier for payloads with no id/URL; sending the
    Drive file's original (possibly typo'd) title would make the worker fail
    to find the confirmed page and create a duplicate instead. The final
    stored title is unaffected — the worker keeps the existing page's title
    on any real update, this is purely a matching signal. ``reason`` is
    optional and is recorded for audit but not otherwise used.

    Raises ``ValueError`` if an override's ``relative_path`` doesn't match
    any classified item (fail loud — a stale/typo'd override must not be
    silently ignored).
    """
    by_path = {item["relative_path"]: item for item in classified}
    for override in overrides:
        relative_path = override.get("relative_path")
        item = by_path.get(relative_path)
        if item is None:
            raise ValueError(f"manual override references unknown relative_path: {relative_path!r}")

        item["action"] = override["action"]
        item["match_strategy"] = "manual_override"
        if override.get("page_id"):
            item["matched_page"] = {"page_id": override["page_id"], "url": override.get("url", "")}
            item["en_notion"] = True
        if override.get("title"):
            item["title_override"] = override["title"]
        note = "manual override (David)"
        if override.get("reason"):
            note += f": {override['reason']}"
        item["notes"] = list(item.get("notes") or []) + [note]
    return classified


def summarize(classified: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"create": 0, "update_transcript": 0, "skip": 0, "review_ambiguous": 0}
    for entry in classified:
        summary[entry["action"]] = summary.get(entry["action"], 0) + 1
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gap-check Drive Granola transcripts against the Notion DB (read-only).")
    parser.add_argument("--drive-inventory", required=True, help="Path to JSON from granola_drive_md_ingest.py")
    parser.add_argument("--notion-pages", required=True, help="Path to JSON snapshot of existing Notion pages")
    parser.add_argument("--overrides", help="Optional path to a JSON list of human-confirmed resolutions (see apply_manual_overrides)")
    parser.add_argument("--output", help="Optional path to write the classified JSON report")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    drive_data = json.loads(Path(args.drive_inventory).read_text(encoding="utf-8"))
    notion_data = json.loads(Path(args.notion_pages).read_text(encoding="utf-8"))

    drive_records = drive_data.get("records", [])
    notion_records = notion_data.get("records", [])

    classified = classify_gap(drive_records, notion_records)
    if args.overrides:
        overrides = json.loads(Path(args.overrides).read_text(encoding="utf-8"))
        classified = apply_manual_overrides(classified, overrides)
    summary = summarize(classified)

    report = {"summary": summary, "items": classified}
    output_text = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
