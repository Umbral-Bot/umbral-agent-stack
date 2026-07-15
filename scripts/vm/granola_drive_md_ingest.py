"""
Granola Drive Markdown -> Worker -> Notion feeder (P1.1b, manual-paste raw ingest).

David pastes each Granola meeting transcript verbatim into a Google-Drive-synced
folder as one plain-text ``.md`` file, in Granola's own "copy transcript" shape::

    Meeting Title: <title>
    Date: <Mon Day>
    Meeting participants: <comma-separated names>   (optional)

    Transcript:

    Them: ...
    Me: ...

This feeder parses that folder and maps each file onto the EXISTING worker task
``granola.process_transcript`` (same canonical "Transcripciones Granola" DB,
same dedup/reconciliation as every other Granola feeder) — no new
Notion-writing code, no second DB. Unlike ``granola_mcp_ingest.py`` (AI summary
only), the ``content`` here is the FULL verbatim transcript.

These files carry no Granola id/URL/updated_at, so the only usable dedup
signal against *existing* Notion pages is normalized-title + date (see
``worker/tasks/granola.py::_find_existing_raw_candidate`` tiers 7/8).
``_normalize_lookup_text`` below is a deliberate mirror of that function so
this feeder's own gap classification agrees with what the worker will
actually decide at execute time. The payload still carries ``shared_folder_path``
+ ``sha1`` (tiers 5/6) so a *second* run of this same feeder re-matches its own
prior writes precisely, instead of relying on title/date again.

SAFETY: dry-run is the default. Nothing is written to Notion unless
``--execute`` is passed explicitly (and even then, only via the worker's own
``dry_run`` input flag semantics — see ``docs/78-granola-transcript-finality-reconciliation.md``).

Examples::

    # parse one file and print its payload (no writes, no network)
    python scripts/vm/granola_drive_md_ingest.py --input "G:\\...\\Granola\\BIM Forum 3.md"

    # parse every file under the default Drive root and print payloads
    python scripts/vm/granola_drive_md_ingest.py --root "G:\\Mi unidad\\07_Sesiones y Transcripciones\\Notas y Transcripciones\\Granola"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

CAPTURE_SOURCE = "granola_drive_md"
CAPTURE_MODE = "drive_manual_paste"
MIN_FILE_BYTES = 100
EXCLUDED_PREFIXES = ("Indice_Transcripciones_Locales",)

DEFAULT_DRIVE_ROOT = (
    r"G:\Mi unidad\07_Sesiones y Transcripciones\Notas y Transcripciones\Granola"
)

_TITLE_RE = re.compile(r"^Meeting Title:\s*(.+)$", re.IGNORECASE)
_DATE_RE = re.compile(r"^Date:\s*(.+)$", re.IGNORECASE)
_PARTICIPANTS_RE = re.compile(r"^Meeting participants:\s*(.+)$", re.IGNORECASE)
_TRANSCRIPT_HEADER_RE = re.compile(r"^Transcript:\s*$", re.IGNORECASE)

_MON_DAY_RE = re.compile(r"^([A-Za-z]{3,})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?$")
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_CONTENT_HEADER = "> Transcripcion verbatim capturada por Granola, pegada manualmente en Drive."


def _normalize_lookup_text(value: str) -> str:
    """Mirror of worker/tasks/granola.py::_normalize_lookup_text.

    Kept in sync deliberately: this feeder's own gap/dedup classification
    must agree with what the worker will decide at execute time.
    """
    text = unicodedata.normalize("NFKD", value or "")
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def parse_meeting_date_header(value: str, *, default_year: int) -> str:
    """Best-effort parse a ``Date: Mon Day`` header into ``YYYY-MM-DD``.

    These headers never carry a year (Granola's plain-text export omits it),
    so the caller must supply ``default_year`` (the file's paste year is the
    only signal we have — see the module docstring / gap-check report for
    the documented assumption).
    """
    text = (value or "").strip()
    if not text:
        return ""
    match = _MON_DAY_RE.match(text)
    if not match:
        return ""
    month = _MONTHS.get(match.group(1).lower()[:3])
    if not month:
        return ""
    day = int(match.group(2))
    try:
        return f"{default_year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        return ""


def parse_participants(value: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in (value or "").split(","):
        label = item.strip()
        if label and label not in seen:
            seen.add(label)
            result.append(label)
    return result


def parse_drive_transcript_md(text: str, filename: str, *, default_year: int) -> dict[str, Any]:
    """Parse one Drive-pasted Granola transcript ``.md`` file.

    Returns a dict with ``title``, ``date`` (``YYYY-MM-DD`` or ``""`` if the
    header couldn't be parsed), ``date_raw`` (verbatim ``Date:`` value),
    ``participants`` (list[str]), ``transcript`` (verbatim body after
    ``Transcript:``, stripped of a single leading blank/space line), and
    ``normalized_title``.
    """
    fallback_title = Path(filename).stem.strip()
    # Strip a leading UTF-8 BOM (some pastes carry one) — str.strip() does not
    # remove U+FEFF, so left uncleaned it silently breaks the "Meeting Title:"
    # match on the first line and falls back to the filename.
    text = (text or "").lstrip("﻿")

    title_parts: list[str] = []
    date_raw = ""
    participants: list[str] = []
    transcript_lines: list[str] = []
    in_transcript = False

    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if in_transcript:
            transcript_lines.append(line)
            i += 1
            continue

        if not title_parts:
            m = _TITLE_RE.match(stripped)
            if m:
                title_parts.append(m.group(1).strip())
                i += 1
                # Long titles sometimes wrap onto the next physical line(s)
                # with no label of their own — keep absorbing until a blank
                # line or the next recognized header.
                while i < n:
                    cont = lines[i].strip()
                    if not cont or _DATE_RE.match(cont) or _PARTICIPANTS_RE.match(cont) or _TRANSCRIPT_HEADER_RE.match(cont):
                        break
                    title_parts.append(cont)
                    i += 1
                continue

        if not date_raw:
            m = _DATE_RE.match(stripped)
            if m:
                date_raw = m.group(1).strip()
                i += 1
                continue

        if not participants:
            m = _PARTICIPANTS_RE.match(stripped)
            if m:
                participants = parse_participants(m.group(1))
                i += 1
                continue

        if _TRANSCRIPT_HEADER_RE.match(stripped):
            in_transcript = True
            i += 1
            continue

        i += 1

    title = " ".join(title_parts).strip()

    # Drop a single leading blank/whitespace-only line Granola inserts right
    # after "Transcript:" before the first "Them:"/"Me:" turn.
    while transcript_lines and not transcript_lines[0].strip():
        transcript_lines.pop(0)
    while transcript_lines and not transcript_lines[-1].strip():
        transcript_lines.pop()

    transcript = "\n".join(transcript_lines)
    resolved_title = title or fallback_title or "Reunion sin titulo"

    return {
        "title": resolved_title,
        "normalized_title": _normalize_lookup_text(resolved_title),
        "date_raw": date_raw,
        "date": parse_meeting_date_header(date_raw, default_year=default_year),
        "participants": participants,
        "transcript": transcript,
        "char_count": len(transcript),
    }


def list_drive_transcript_files(root: Path) -> list[Path]:
    """Return every eligible ``.md`` file directly under ``root``.

    Excludes ``Indice_Transcripciones_Locales_*`` (not a Granola transcript)
    and files under ``MIN_FILE_BYTES`` (empty/near-empty exports).
    """
    if not root.is_dir():
        raise FileNotFoundError(f"Drive root not found: {root}")

    files: list[Path] = []
    for path in sorted(root.glob("*.md")):
        if not path.is_file():
            continue
        if path.name.startswith(EXCLUDED_PREFIXES):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size < MIN_FILE_BYTES:
            continue
        files.append(path)
    return files


def sha1_of_text(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def build_content(parsed: dict[str, Any]) -> str:
    transcript = parsed.get("transcript") or ""
    if transcript:
        return f"{_CONTENT_HEADER}\n\n{transcript}"
    return _CONTENT_HEADER


def build_payload(
    parsed: dict[str, Any],
    *,
    relative_path: str,
    file_sha1: str,
    notify_enlace: bool = False,
) -> dict[str, Any]:
    """Map a parsed Drive transcript onto a ``granola.process_transcript`` payload."""
    title = str(parsed.get("title") or "").strip()
    if not title:
        raise ValueError("parsed transcript is missing a title")

    payload: dict[str, Any] = {
        "title": title,
        "content": build_content(parsed),
        "source": CAPTURE_SOURCE,
        "shared_folder_path": relative_path,
        "sha1": file_sha1,
        "notify_enlace": bool(notify_enlace),
        "allow_legacy_raw_task_writes": False,
        "metadata": {
            "capture_mode": CAPTURE_MODE,
            "shared_folder_path": relative_path,
            "sha1": file_sha1,
        },
    }

    date = str(parsed.get("date") or "").strip()
    if date:
        payload["date"] = date

    participants = parsed.get("participants") or []
    if participants:
        payload["attendees"] = list(participants)

    return payload


def build_inventory(root: Path, *, default_year: int) -> list[dict[str, Any]]:
    """Walk ``root`` and return one parsed+payload-ready record per eligible file."""
    records: list[dict[str, Any]] = []
    for path in list_drive_transcript_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_drive_transcript_md(text, path.name, default_year=default_year)
        relative_path = f"Granola/{path.name}"
        file_sha1 = sha1_of_text(text)
        records.append(
            {
                "filename": path.name,
                "relative_path": relative_path,
                "size_bytes": path.stat().st_size,
                "sha1": file_sha1,
                "parsed": parsed,
                "payload": build_payload(
                    parsed, relative_path=relative_path, file_sha1=file_sha1
                ),
            }
        )
    return records


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse Drive-pasted Granola transcripts into granola.process_transcript payloads (preview only)."
    )
    parser.add_argument("--input", help="Path to a single .md file to parse")
    parser.add_argument("--root", help="Drive folder to walk (default: the P1.1b Granola folder)")
    parser.add_argument("--default-year", type=int, default=2026, help="Year to assume for 'Date: Mon Day' headers")
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N files (0 = all)")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    if args.input:
        path = Path(args.input)
        text = path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_drive_transcript_md(text, path.name, default_year=args.default_year)
        payload = build_payload(
            parsed, relative_path=f"Granola/{path.name}", file_sha1=sha1_of_text(text)
        )
        print(json.dumps({"parsed": parsed, "payload": payload}, ensure_ascii=False, indent=2))
        return 0

    root = Path(args.root or DEFAULT_DRIVE_ROOT)
    records = build_inventory(root, default_year=args.default_year)
    if args.limit and args.limit > 0:
        records = records[: args.limit]
    print(json.dumps({"count": len(records), "records": records}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
