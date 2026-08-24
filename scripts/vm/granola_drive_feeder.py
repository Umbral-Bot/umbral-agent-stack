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
import re
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
from scripts.vm.send_granola_drive_batch import (  # noqa: E402
    _result_dict,
    post_task,
    resolve_worker_config,
)

DEFAULT_MAX_CREATES = 10
DEFAULT_MAX_UPDATES = 10


_SECRET_RE = re.compile(r"(?i)(bearer\s+|token[\"'\s:=]+)([A-Za-z0-9._\-]{8,})")


def _redact(text: str) -> str:
    """Mask bearer tokens before an error string reaches disk or a terminal.

    Worker error bodies are echoed verbatim into the run report and onto
    stderr, and a 500 whose traceback quotes the request would otherwise write
    ``Authorization: Bearer <WORKER_TOKEN>`` into a file an operator is likely
    to paste into an acta.
    """
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}<redacted>", text or "")


def default_state_dir() -> Path:
    # TMPDIR is POSIX; on Windows the names are TEMP/TMP. Falling through to
    # "." would drop run reports (meeting titles, page ids, URLs) into the
    # process CWD -- which the Scheduled Task sets to the repo checkout.
    base = (
        os.environ.get("LOCALAPPDATA")
        or os.environ.get("TEMP")
        or os.environ.get("TMP")
        or os.environ.get("TMPDIR")
        or "."
    )
    return Path(base) / "umbral-agent-stack" / "granola-drive-feeder"


def select_items(
    batch: list[dict[str, Any]],
    *,
    max_creates: int,
    max_updates: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split ``batch`` into (selected, deferred) honouring the per-run caps.

    Batch order is preserved. That order comes from ``sorted(root.glob(...))``,
    i.e. filename order -- not chronological. It is stable, which is what
    matters for a backlog draining across runs, but do not read it as
    oldest-first.
    """
    # A negative cap used to read as "unlimited", so one stray -1 turned a
    # bounded daily job into an unattended full-backlog drain. Clamp instead.
    max_creates = max(0, max_creates)
    max_updates = max(0, max_updates)

    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    creates = 0
    updates = 0

    for item in batch:
        action = item.get("action")
        if action == "create":
            if creates >= max_creates:
                deferred.append(item)
                continue
            creates += 1
        elif action == "update_transcript":
            if updates >= max_updates:
                deferred.append(item)
                continue
            updates += 1
        else:
            deferred.append(item)
            continue
        selected.append(item)

    return selected, deferred


def worker_verdict_agrees(
    action: str,
    result: dict[str, Any],
    *,
    expected_page_id: str = "",
) -> str:
    """Return "" when the worker's dry-run agrees with us, else why it does not.

    Three independent ways this can disagree, all of which must block the write:

    * ``matched_existing`` absent. ``bool(None)`` is ``False``, so reading it
      with ``.get`` would turn "the worker never answered" into "the worker
      confirms nothing exists" and approve a ``create`` -- fail-open in exactly
      the duplicate-creating direction. A missing key is a disagreement.
    * ``matched_existing`` disagrees in value. A ``create`` the worker can
      already match is a duplicate; an ``update_transcript`` it cannot match
      would create a page instead of updating one.
    * The worker matched a DIFFERENT page than we did. Its match ladder is
      wider than the gap-check's (it also keys on ``granola_document_id``,
      ``source_url`` and ``export_signature``), so the two can legitimately land
      on different pages -- and executing then overwrites a page nobody chose.
    """
    if "matched_existing" not in result:
        return "worker dry-run omitted matched_existing"

    matched = bool(result.get("matched_existing"))
    if action == "create":
        return "" if not matched else "worker already matches an existing page"
    if action != "update_transcript":
        return f"unsupported action {action!r}"
    if not matched:
        return "worker matched no existing page"

    worker_page_id = str(result.get("page_id") or "").strip()
    expected = str(expected_page_id or "").strip()
    if expected and worker_page_id and worker_page_id != expected:
        return (
            f"worker resolved a different page ({worker_page_id} != {expected})"
        )
    return ""


def run_item(
    item: dict[str, Any],
    *,
    worker_url: str,
    worker_token: str,
    execute: bool,
) -> dict[str, Any]:
    """Dry-run one item, then write it only if ``execute`` and the worker agrees.

    ``declined`` marks the guard doing its job -- an expected, benign no-write.
    It is deliberately NOT ``error``: a Scheduled Task that goes red the first
    time a classification legitimately diverges trains its operator to ignore
    the only failure signal the run emits.
    """
    action = str(item.get("action") or "")
    expected_page_id = str((item.get("matched_page") or {}).get("page_id") or "")
    row: dict[str, Any] = {
        "relative_path": item["relative_path"],
        "action": action,
        "match_strategy": item.get("match_strategy", ""),
        "executed": False,
        "written": False,
        "declined": "",
        "error": "",
    }

    payload = dict(item["payload"])
    payload["dry_run"] = True
    try:
        dry = _result_dict(post_task(worker_url, worker_token, payload))
    except Exception as exc:  # noqa: BLE001 - one bad item must not abort the run
        row["error"] = f"dry-run failed: {_redact(str(exc))}"
        return row

    row["dry_run_reconciliation_action"] = dry.get("reconciliation_action", "")
    row["dry_run_matched_existing"] = dry.get("matched_existing")
    row["worker_match_strategy"] = dry.get("match_strategy", "")

    # The worker echoes dry_run back precisely so a caller can prove the
    # request was honoured. If it did not come back True, POST #1 may have been
    # a real write and POST #2 would be a second one.
    if dry.get("dry_run") is not True:
        row["error"] = "worker did not confirm dry_run=true -- refusing to continue"
        return row

    disagreement = worker_verdict_agrees(action, dry, expected_page_id=expected_page_id)
    if disagreement:
        row["declined"] = disagreement
        return row

    if str(dry.get("reconciliation_action") or "") == "noop":
        # The worker already decided this changes nothing. Executing would cost
        # a second full task run (a paged query over the whole DB) to be told
        # the same thing.
        row["declined"] = "worker reconciliation_action=noop -- nothing to write"
        return row

    if not execute:
        return row

    payload["dry_run"] = False
    try:
        result = _result_dict(post_task(worker_url, worker_token, payload))
    except Exception as exc:  # noqa: BLE001
        row["error"] = f"execute failed: {_redact(str(exc))}"
        return row

    reconciliation = str(result.get("reconciliation_action") or "")
    row.update(
        {
            "executed": True,
            # "written" is the honest count: the worker can still answer noop
            # or defer, in which case a POST happened but Notion did not change.
            "written": reconciliation not in {"", "noop", "defer"},
            "page_id": result.get("page_id", ""),
            "url": result.get("url", ""),
            "reconciliation_action": reconciliation,
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
    parser.add_argument(
        "--default-year",
        type=int,
        default=None,
        help=(
            "Force a year for Granola's year-less 'Date: Mon Day' headers. "
            "Default: derive per file from its modification time. A recurring "
            "job must never carry a fixed year -- see resolve_meeting_date."
        ),
    )
    parser.add_argument("--state-dir", default=None, help="Where run artifacts are written")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write to Notion. Without this nothing is written, whatever else is passed.",
    )
    parser.add_argument(
        "--max-creates",
        type=int,
        default=DEFAULT_MAX_CREATES,
        help="Maximum new pages per run (negative values are clamped to 0, never 'unlimited').",
    )
    parser.add_argument(
        "--max-updates",
        type=int,
        default=DEFAULT_MAX_UPDATES,
        help="Maximum page updates per run (negative values are clamped to 0).",
    )
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


def _force_utf8_console() -> None:
    """Make our own stdout/stderr UTF-8 before printing anything.

    Meeting filenames and worker error bodies carry emoji and accents, and the
    Windows console default (cp1252) cannot encode them: the reporting line
    itself raises ``UnicodeEncodeError`` and the run dies with no summary. The
    Scheduled Task passes ``-X utf8``, but the manual invocation this module's
    own docstring shows does not, so the entry point fixes it for both.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def load_notion_records(path: str) -> list[dict[str, Any]]:
    """Read a pre-built snapshot, refusing shapes that would mean "create everything".

    An empty or wrong-shaped snapshot is the most dangerous input this script
    can take: ``classify_gap`` reads zero existing pages as "nothing is in
    Notion" and proposes a create for every Drive file. Fail loud instead --
    the same reasoning ``fetch_pages`` applies to a truncated cursor walk.
    ``utf-8-sig`` because the file is routinely produced by Windows tools that
    prepend a BOM, which ``json.loads`` rejects with an opaque error.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or "records" not in data:
        raise RuntimeError(
            f"{path}: not a snapshot (expected a JSON object with a 'records' key)"
        )
    records = data["records"]
    if not isinstance(records, list) or not records:
        raise RuntimeError(
            f"{path}: snapshot has no records -- refusing to treat an empty "
            "Notion side as 'create everything'."
        )
    return records


def drop_unparsed_transcripts(
    selected: list[dict[str, Any]],
    drive_by_path: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split off items whose transcript body did not parse.

    ``parse_drive_transcript_md`` only recognizes a line that is exactly
    ``Transcript:``. If Granola relabels its export, a perfectly large .md
    parses to an EMPTY transcript and ``build_content`` yields nothing but the
    one-line header. Sent as an ``update_transcript`` that the worker happily
    matches, it would replace a full meeting page with 76 characters. Nothing
    downstream refuses a shrink, so it has to be refused here.
    """
    ok: list[dict[str, Any]] = []
    unparsed: list[dict[str, Any]] = []
    for item in selected:
        drive = drive_by_path.get(item["relative_path"]) or {}
        if int((drive.get("parsed") or {}).get("char_count") or 0) > 0:
            ok.append(item)
        else:
            unparsed.append(item)
    return ok, unparsed


def _brief(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"relative_path": i["relative_path"], "action": i["action"]} for i in items]


def main() -> int:
    _force_utf8_console()
    args = build_arg_parser().parse_args()

    state_dir = Path(args.state_dir) if args.state_dir else default_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = state_dir / f"run-{stamp}.json"

    report: dict[str, Any] = {
        "timestamp": stamp,
        "execute": bool(args.execute),
        "fatal_error": "",
        "results": [],
    }

    def flush_report() -> None:
        # Written after every item, not once at the end: a run killed by the
        # task's ExecutionTimeLimit must not take the record of the pages it
        # already wrote with it.
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    try:
        root = Path(args.root or DEFAULT_DRIVE_ROOT)
        report["root"] = str(root)
        drive_records = build_inventory(root, default_year=args.default_year)

        if args.notion_pages:
            notion_records = load_notion_records(args.notion_pages)
            notion_source = args.notion_pages
        else:
            api_key, database_id = resolve_notion_config(
                args.notion_api_key, args.notion_database_id
            )
            notion_records = build_snapshot(fetch_pages(api_key, database_id))["records"]
            notion_source = "live"
            if not notion_records:
                raise RuntimeError(
                    "live Notion snapshot came back empty -- refusing to treat that "
                    "as 'create everything'."
                )

        gap_items = classify_gap(drive_records, notion_records)
        summary = summarize(gap_items)
        batch = build_batch(drive_records, gap_items)
        selected, deferred = select_items(
            batch, max_creates=args.max_creates, max_updates=args.max_updates
        )
        drive_by_path = {r["relative_path"]: r for r in drive_records}
        selected, unparsed = drop_unparsed_transcripts(selected, drive_by_path)

        report.update(
            {
                "drive_files": len(drive_records),
                "notion_pages": len(notion_records),
                "notion_source": notion_source,
                "summary": summary,
                "batch_total": len(batch),
                "selected": _brief(selected),
                "deferred": _brief(deferred),
                "unparsed_transcript": _brief(unparsed),
                # review_ambiguous never enters the batch, so without this it
                # would exist only as an integer in `summary` -- the one class
                # of item that needs a human, invisible in the run record.
                "review_ambiguous": [
                    {"relative_path": i["relative_path"], "notes": i.get("notes", [])}
                    for i in gap_items
                    if i["action"] == "review_ambiguous"
                ],
            }
        )
        flush_report()

        if not args.skip_worker and selected:
            worker_url, worker_token = resolve_worker_config(args.worker_url, args.worker_token)
            for item in selected:
                report["results"].append(
                    run_item(
                        item,
                        worker_url=worker_url,
                        worker_token=worker_token,
                        execute=args.execute,
                    )
                )
                flush_report()
    except Exception as exc:  # noqa: BLE001 - an unattended run must leave a record
        report["fatal_error"] = _redact(f"{type(exc).__name__}: {exc}")
        flush_report()
        print(json.dumps({"fatal_error": report["fatal_error"], "report": str(report_path)}))
        return 1

    flush_report()

    written = sum(1 for r in report["results"] if r.get("written"))
    declined = [r for r in report["results"] if r.get("declined")]
    failed = [r for r in report["results"] if r.get("error")]
    print(
        json.dumps(
            {
                "drive_files": report["drive_files"],
                "notion_pages": report["notion_pages"],
                "gap": report["summary"],
                "selected": len(report["selected"]),
                "deferred": len(report["deferred"]),
                "review_ambiguous": len(report["review_ambiguous"]),
                "unparsed_transcript": len(report["unparsed_transcript"]),
                "written": written,
                "declined": len(declined),
                "failed": len(failed),
                "execute": bool(args.execute),
                "report": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    for row in declined:
        print(f"DECLINED {row['relative_path']}: {row['declined']}", file=sys.stderr)
    for row in failed:
        print(f"FAIL {row['relative_path']}: {row['error']}", file=sys.stderr)

    # Exit non-zero only for real errors. A declined item is the guard working
    # as designed; failing the task on it would make the Scheduled Task's Last
    # Run Result permanently red and train the operator to ignore it.
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
