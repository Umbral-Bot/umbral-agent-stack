"""
Completeness audit for the Drive-pasted Granola transcripts (Q11-T2).

The feeder proves *that* a file reaches Notion. This proves *what* reaches it:
that the body the parser hands to ``granola.process_transcript`` is the full
verbatim transcript, not Granola's AI summary.

The distinction matters because the two live in the same folder shape. Granola
can copy either one, and ``parse_drive_transcript_md`` takes whatever follows
the ``Transcript:`` header without asking what it is. A summary pasted there
parses cleanly, and on an ``update_transcript`` it would replace a full meeting
page with a few paragraphs.

Per file this reports the four signals that separate the two, and nothing else:

===========================  ===============================================
``has_transcript_header``    a ``Transcript:`` line exists at all
``turns_me`` / ``turns_them``  Granola's speaker labels at line start
``body_chars``               length of the body the worker would write
``longest_line_chars``       the flattening tell (see below)
===========================  ===============================================

**Flattened transcripts are real, not summaries.** Some pastes lose their
newlines and arrive as one or two enormous lines, so a turn count alone reads
them as "one paragraph" and would reject a complete 73k-character meeting. The
size dimension is what tells the two apart: an AI summary is short. So
``SOLO_RESUMEN`` requires *both* few turns and a small body, and anything large
with too few turns is ``VERBATIM_APLANADO`` -- complete content, degraded shape.

SAFETY: read-only and offline. It opens the Drive folder, never Notion, and
prints only metrics -- no meeting content, ever, not even an excerpt. Its output
is meant to be pasted into an acta.

Examples::

    python scripts/vm/granola_drive_transcript_audit.py
    python scripts/vm/granola_drive_transcript_audit.py --json --output audit.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.vm.granola_drive_md_ingest import (  # noqa: E402
    DEFAULT_DRIVE_ROOT,
    FLATTENED_LINE_CHARS,
    _TRANSCRIPT_HEADER_RE,
    build_inventory,
)

# Granola labels the two sides of a meeting ``Me:`` and ``Them:`` at the start
# of a line. A few leading spaces survive some pastes.
_ME_RE = re.compile(r"^[ \t]{0,4}Me:[ \t]", re.MULTILINE)
_THEM_RE = re.compile(r"^[ \t]{0,4}Them:[ \t]", re.MULTILINE)
# Any short speaker label, so a transcript that uses real names instead of
# Me/Them is not mistaken for prose.
_TURN_RE = re.compile(r"^[ \t]{0,4}([^\s:][^:\n]{0,40}?):[ \t]")

# A body under this length cannot be a full meeting; combined with a missing
# turn structure it is what an AI summary looks like.
SUMMARY_MAX_CHARS = 6000
# Below this many turns the body has no dialogue structure to speak of.
MIN_VERBATIM_TURNS = 6
# A body this short is not a meeting transcript whatever its shape.
MIN_VERBATIM_CHARS = 2000

VERBATIM = "VERBATIM"
VERBATIM_FLATTENED = "VERBATIM_APLANADO"
SUMMARY_ONLY = "SOLO_RESUMEN"
EMPTY = "VACIO"
UNCERTAIN = "DUDOSO"

# The classes the feeder may execute.
#
# ``VERBATIM_APLANADO`` is in the set. It was not, and holding it back turned
# out to be the wrong call: the four files it stranded are webinars Granola
# recorded as one long ``Them:`` turn, because one person was talking. Their
# bodies are complete -- 15k to 73k characters, ~100 characters per sentence,
# no interior speaker labels to recover (``unflatten_transcript`` returns them
# unchanged, and there is nothing in the file for it to work with). Refusing
# them meant a real meeting never reached Notion over a shape that is not a
# defect.
#
# ``SOLO_RESUMEN``, ``VACIO`` and ``DUDOSO`` stay out: those are bodies that
# are short or unrecognized, i.e. content that may genuinely be missing.
EXECUTABLE_CLASSES = frozenset({VERBATIM, VERBATIM_FLATTENED})


def classify(
    *,
    has_header: bool,
    turns: int,
    body_chars: int,
    longest_line_chars: int,
) -> str:
    """Bucket one parsed transcript body.

    ``VACIO`` first: an empty body is the only case the feeder already refuses
    on its own (``drop_unparsed_transcripts``), and it must not be reported as
    anything softer.
    """
    if body_chars <= 0:
        return EMPTY
    if not has_header:
        # No ``Transcript:`` line means the parser produced this body by some
        # other route -- worth a human look whatever its size.
        return UNCERTAIN
    if turns >= MIN_VERBATIM_TURNS and body_chars >= MIN_VERBATIM_CHARS:
        return VERBATIM
    if body_chars <= SUMMARY_MAX_CHARS:
        return SUMMARY_ONLY
    if longest_line_chars >= FLATTENED_LINE_CHARS:
        return VERBATIM_FLATTENED
    return UNCERTAIN


def audit_record(record: dict[str, Any], raw_text: str) -> dict[str, Any]:
    """Metrics for one inventory record. Returns no transcript text."""
    parsed = record.get("parsed") or {}
    body = str(parsed.get("transcript") or "")

    has_header = any(
        _TRANSCRIPT_HEADER_RE.match(line.strip()) for line in raw_text.splitlines()
    )

    non_blank = [line for line in body.splitlines() if line.strip()]
    longest_line_chars = max((len(line) for line in non_blank), default=0)

    labels: dict[str, int] = {}
    for line in non_blank:
        match = _TURN_RE.match(line)
        if match:
            label = match.group(1).strip()
            labels[label] = labels.get(label, 0) + 1

    body_chars = len(body)
    turns = sum(labels.values())
    return {
        "filename": record.get("filename", ""),
        "relative_path": record.get("relative_path", ""),
        "title": str(parsed.get("title") or ""),
        "date": str(parsed.get("date") or ""),
        "file_bytes": int(record.get("size_bytes") or 0),
        "has_transcript_header": has_header,
        "body_chars": body_chars,
        # How much of the file survives into Notion. A verbatim paste is ~0.99;
        # a low ratio means most of the file sits BEFORE ``Transcript:`` and is
        # being dropped -- the summary-above-transcript shape.
        "body_ratio": round(body_chars / len(raw_text), 3) if raw_text else 0.0,
        "turns_me": len(_ME_RE.findall(body)),
        "turns_them": len(_THEM_RE.findall(body)),
        "turns_total": turns,
        "distinct_labels": len(labels),
        "lines": len(non_blank),
        "longest_line_chars": longest_line_chars,
        "class": classify(
            has_header=has_header,
            turns=turns,
            body_chars=body_chars,
            longest_line_chars=longest_line_chars,
        ),
    }


def audit_root(root: Path, *, default_year: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in build_inventory(root, default_year=default_year):
        path = root / str(record["filename"])
        rows.append(audit_record(record, path.read_text(encoding="utf-8", errors="replace")))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    return counts


def not_executable(rows: list[dict[str, Any]]) -> list[str]:
    """Filenames a run should hold back until a human has looked at them.

    This is the audit's actionable output: each name goes straight into a
    ``granola_drive_feeder.py --exclude`` argument. Without it an operator has
    to retype accented meeting titles by hand off a table.
    """
    return [row["filename"] for row in rows if row["class"] not in EXECUTABLE_CLASSES]


def exclude_hint(rows: list[dict[str, Any]]) -> str:
    """The ``--exclude`` arguments that would run only the approved files."""
    return " ".join('--exclude "' + name + '"' for name in not_executable(rows))


def format_table(rows: list[dict[str, Any]]) -> str:
    header = (
        f"{'archivo':<52} {'hdr':<3} {'Me:':>5} {'Them:':>6} {'turnos':>7} "
        f"{'body':>8} {'bytes':>8} {'ratio':>6}  clase"
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{row['filename'][:52]:<52} {'Y' if row['has_transcript_header'] else 'N':<3} "
            f"{row['turns_me']:>5} {row['turns_them']:>6} {row['turns_total']:>7} "
            f"{row['body_chars']:>8} {row['file_bytes']:>8} {row['body_ratio']:>6.3f}  "
            f"{row['class']}"
        )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit whether the Drive-pasted Granola .md files carry full verbatim "
            "transcripts or only AI summaries. Read-only, offline, metrics only."
        )
    )
    parser.add_argument("--root", default=None, help=f"Drive folder (default: {DEFAULT_DRIVE_ROOT})")
    parser.add_argument(
        "--default-year",
        type=int,
        default=None,
        help="Force a year for Granola's year-less 'Date: Mon Day' headers (default: per-file mtime).",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="FILENAME",
        help=(
            "Audit just this file (repeatable). One filename per flag, never a "
            "comma-separated list -- real Granola filenames contain commas. A "
            "name that matches nothing aborts the run: an audit that quietly "
            "reports on fewer files than asked is worse than no audit. The rest "
            "of the folder still parses, so the classification is identical to "
            "a full run."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Write to this path as UTF-8 instead of stdout. Needed on Windows, "
            "whose console default (cp1252) cannot encode accented meeting titles."
        ),
    )
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    args = build_arg_parser().parse_args()
    root = Path(args.root or DEFAULT_DRIVE_ROOT)
    rows = audit_root(root, default_year=args.default_year)

    if args.only:
        wanted = {name.strip() for name in args.only if name.strip()}
        missing = sorted(wanted - {row["filename"] for row in rows})
        if missing:
            print(
                "--only matched nothing: "
                + ", ".join(repr(name) for name in missing)
                + " -- refusing to report on a smaller set than was asked for.",
                file=sys.stderr,
            )
            return 1
        rows = [row for row in rows if row["filename"] in wanted]

    if args.json:
        text = json.dumps(
            {
                "root": str(root),
                "count": len(rows),
                "by_class": summarize(rows),
                "not_executable": not_executable(rows),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    else:
        text = format_table(rows) + "\n\n" + json.dumps(summarize(rows), ensure_ascii=False)
        hint = exclude_hint(rows)
        if hint:
            text += "\n\nPara correr solo lo aprobado:\n  " + hint

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(json.dumps({"count": len(rows), "by_class": summarize(rows), "output": args.output}, ensure_ascii=False))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
