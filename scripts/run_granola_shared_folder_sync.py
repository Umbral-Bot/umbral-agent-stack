"""
Audit and synchronize Granola raw transcripts from a shared folder into Notion.

This script treats the exported markdown files as the canonical source for raw
transcripts. It audits coverage and exact body integrity against the Notion raw
database and can optionally repair the drift by:

- creating missing raw pages,
- replacing mismatched bodies with the exact file content,
- archiving raw pages that no longer exist in the shared folder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_SOURCE_DIR = r"G:\Mi unidad\Trabajo\Granola"
DEFAULT_DATABASE_TITLE = "Transcripciones Granola"
PAGE_READ_MAX_ATTEMPTS = 3


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_dotenv(REPO_ROOT / ".env")

from scripts.vm.granola_watcher import parse_granola_markdown
from worker import config, notion_client


def _normalize_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def _normalize_title(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def _match_key(title: str, date: str) -> tuple[str, str]:
    return (_normalize_title(title), (date or "").strip())


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _resolve_database_id(explicit_database_id: str | None) -> str:
    if explicit_database_id:
        return notion_client._extract_notion_page_id(explicit_database_id)

    env_db_id = (config.NOTION_GRANOLA_DB_ID or "").strip()
    if env_db_id:
        return notion_client._extract_notion_page_id(env_db_id)

    results = notion_client.search_databases(DEFAULT_DATABASE_TITLE, max_results=10)
    for item in results.get("results", []):
        title = str(item.get("title") or "").strip()
        if title == f"📝 {DEFAULT_DATABASE_TITLE}" or title == DEFAULT_DATABASE_TITLE:
            return notion_client._extract_notion_page_id(str(item.get("database_id") or ""))

    raise RuntimeError(
        "Could not resolve the Granola raw database. "
        "Provide --database-id or configure NOTION_GRANOLA_DB_ID."
    )


def _row_title(row: dict[str, Any]) -> str:
    props = row.get("properties") or {}
    for candidate in ("Nombre", "Name", "Título", "Title"):
        meta = props.get(candidate)
        if isinstance(meta, dict) and meta.get("type") == "title":
            return notion_client._plain_text_from_rich_text(meta.get("title"))
    return ""


def _row_date(row: dict[str, Any]) -> str:
    props = row.get("properties") or {}
    for candidate in ("Fecha", "Date", "Fecha de transcripción", "Meeting Date"):
        meta = props.get(candidate)
        if isinstance(meta, dict) and meta.get("type") == "date":
            return str((meta.get("date") or {}).get("start") or "")[:10]
    return ""


def _row_status_property(row: dict[str, Any]) -> dict[str, Any] | None:
    props = row.get("properties") or {}
    for candidate in ("Estado", "Status"):
        meta = props.get(candidate)
        if isinstance(meta, dict):
            return meta
    return None


def _row_traceability(row: dict[str, Any]) -> str:
    props = row.get("properties") or {}
    meta = props.get("Trazabilidad")
    if isinstance(meta, dict):
        flattened = notion_client._flatten_property_value(meta)
        return str(flattened or "")
    return ""


def _collect_source_records(source_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []

    for path in sorted(source_dir.glob("*.md")):
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        normalized_text = _normalize_newlines(raw_text).strip()
        if not normalized_text:
            invalid.append(
                {
                    "file_name": path.name,
                    "path": str(path),
                    "reason": "empty_file",
                    "size_bytes": path.stat().st_size,
                }
            )
            continue

        parsed = parse_granola_markdown(raw_text, path.name)
        title = str(parsed.get("title") or "").strip() or path.stem
        date = str(parsed.get("date") or "").strip()
        content = _normalize_newlines(str(parsed.get("content") or "")).strip()
        valid.append(
            {
                "file_name": path.name,
                "path": str(path),
                "title": title,
                "date": date,
                "content": content,
                "sha1": _sha1(content),
                "size_bytes": path.stat().st_size,
                "match_key": _match_key(title, date),
            }
        )

    return valid, invalid


def _collect_raw_records(database_id: str) -> list[dict[str, Any]]:
    rows = notion_client.query_database(database_id)
    records: list[dict[str, Any]] = []
    for row in rows:
        title = _row_title(row)
        date = _row_date(row)
        records.append(
            {
                "page_id": row.get("id"),
                "url": row.get("url"),
                "title": title,
                "date": date,
                "status_meta": _row_status_property(row),
                "traceability": _row_traceability(row),
                "match_key": _match_key(title, date),
            }
        )
    return records


def _read_page_with_retries(page_id: str, *, max_blocks: int = 10000) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(1, PAGE_READ_MAX_ATTEMPTS + 1):
        try:
            return notion_client.read_page(page_id, max_blocks=max_blocks)
        except Exception as exc:  # pragma: no cover - exercised in live sync runs
            last_exc = exc
            if attempt >= PAGE_READ_MAX_ATTEMPTS:
                break
            time.sleep(attempt)
    assert last_exc is not None
    raise last_exc


def _build_traceability(existing_text: str, source_record: dict[str, Any]) -> str:
    preserved = []
    for line in _normalize_newlines(existing_text).splitlines():
        if not line.strip():
            continue
        if line.startswith("source_sync="):
            continue
        if line.startswith("shared_folder_path="):
            continue
        if line.startswith("shared_folder_sha1="):
            continue
        preserved.append(line)
    preserved.extend(
        [
            "source_sync=granola_shared_folder_sync",
            f"shared_folder_path={source_record['path']}",
            f"shared_folder_sha1={source_record['sha1']}",
        ]
    )
    return "\n".join(preserved)


def _traceability_checks(raw_record: dict[str, Any], source_record: dict[str, Any]) -> dict[str, bool]:
    traceability = _normalize_newlines(str(raw_record.get("traceability") or ""))
    return {
        "trace_has_path": f"shared_folder_path={source_record['path']}" in traceability,
        "trace_has_sha1": f"shared_folder_sha1={source_record['sha1']}" in traceability,
    }


def _build_match_record(raw_record: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
    page_snapshot = _read_page_with_retries(str(raw_record["page_id"]), max_blocks=10000)
    page_text = _normalize_newlines(page_snapshot["plain_text"]).strip()
    expected_text = source_record["content"]
    trace_checks = _traceability_checks(raw_record, source_record)
    title_exact = str(raw_record.get("title") or "").strip() == str(source_record["title"]).strip()
    date_exact = str(raw_record.get("date") or "").strip() == str(source_record["date"]).strip()
    content_exact = page_text == expected_text
    metadata_exact = title_exact and date_exact and trace_checks["trace_has_path"] and trace_checks["trace_has_sha1"]
    return {
        "source": source_record,
        "raw": raw_record,
        "page_len": len(page_text),
        "source_len": len(expected_text),
        "content_exact": content_exact,
        "title_exact": title_exact,
        "date_exact": date_exact,
        "trace_has_path": trace_checks["trace_has_path"],
        "trace_has_sha1": trace_checks["trace_has_sha1"],
        "metadata_exact": metadata_exact,
        "fully_aligned": content_exact and metadata_exact,
    }


def _transcript_update_properties(raw_record: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "Nombre": {"title": [{"text": {"content": str(source_record['title'])[:2000]}}]},
        "Fecha": {"date": {"start": source_record["date"]}},
        "Fuente": {"select": {"name": "granola"}},
        "Trazabilidad": {
            "rich_text": [
                {
                    "text": {
                        "content": _build_traceability(raw_record.get("traceability", ""), source_record)[:2000]
                    }
                }
            ]
        },
    }
    return properties


def _archive_extra_record(raw_record: dict[str, Any]) -> None:
    properties: dict[str, Any] = {}
    status_meta = raw_record.get("status_meta")
    if isinstance(status_meta, dict):
        status_type = status_meta.get("type")
        if status_type == "status":
            properties["Estado"] = {"status": {"name": "Archivada"}}
        elif status_type == "select":
            properties["Estado"] = {"select": {"name": "Archivada"}}

    notion_client.update_page_properties(
        page_id_or_url=str(raw_record["page_id"]),
        properties=properties,
        archived=True,
    )


def _repair_records(
    database_id: str,
    matched: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    extras: list[dict[str, Any]],
    *,
    archive_extras: bool,
) -> dict[str, int]:
    updated = 0
    created = 0
    archived = 0

    for item in matched:
        if item["fully_aligned"]:
            continue
        raw_record = item["raw"]
        source_record = item["source"]
        notion_client.update_page_properties(
            page_id_or_url=str(raw_record["page_id"]),
            properties=_transcript_update_properties(raw_record, source_record),
        )
        if not item["content_exact"]:
            notion_client.replace_blocks_in_page(
                page_id=str(raw_record["page_id"]),
                blocks=notion_client.transcript_text_to_blocks(source_record["content"]),
            )
        updated += 1

    config.NOTION_GRANOLA_DB_ID = database_id
    for source_record in missing:
        traceability_text = _build_traceability("", source_record)
        notion_client.create_transcript_page(
            title=source_record["title"],
            content=source_record["content"],
            source="granola",
            date=source_record["date"],
            traceability_text=traceability_text,
        )
        created += 1

    if archive_extras:
        for raw_record in extras:
            _archive_extra_record(raw_record)
            archived += 1

    return {
        "updated": updated,
        "created": created,
        "archived": archived,
    }


def audit_folder_vs_raw(source_dir: Path, database_id: str) -> dict[str, Any]:
    source_records, invalid_files = _collect_source_records(source_dir)
    raw_records = _collect_raw_records(database_id)

    raw_by_key = {record["match_key"]: record for record in raw_records}
    source_by_key = {record["match_key"]: record for record in source_records}

    missing: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    matched_raw_ids: set[str] = set()

    for source_record in source_records:
        raw_record = raw_by_key.get(source_record["match_key"])
        if raw_record is None:
            missing.append(source_record)
            continue
        matched_record = _build_match_record(raw_record, source_record)
        matched.append(matched_record)
        matched_raw_ids.add(str(raw_record["page_id"]))

    unresolved_raws = [
        raw_record
        for raw_record in raw_records
        if str(raw_record["page_id"]) not in matched_raw_ids
    ]
    still_missing: list[dict[str, Any]] = []
    fallback_matched_raw_ids: set[str] = set()
    for source_record in missing:
        same_date_candidates = [
            raw_record
            for raw_record in unresolved_raws
            if raw_record["date"] == source_record["date"]
            and str(raw_record["page_id"]) not in fallback_matched_raw_ids
        ]
        fallback_match: dict[str, Any] | None = None
        for raw_record in same_date_candidates:
            fallback_record = _build_match_record(raw_record, source_record)
            if fallback_record["content_exact"]:
                fallback_match = fallback_record
                break
        if fallback_match is None:
            still_missing.append(source_record)
            continue
        matched.append(fallback_match)
        fallback_matched_raw_ids.add(str(fallback_match["raw"]["page_id"]))

    missing = still_missing
    extras = [
        raw_record
        for raw_record in raw_records
        if raw_record["match_key"] not in source_by_key
        and str(raw_record["page_id"]) not in fallback_matched_raw_ids
    ]

    mismatched = [item for item in matched if not item["fully_aligned"]]

    return {
        "source_dir": str(source_dir),
        "database_id": database_id,
        "source_file_count": len(list(source_dir.glob('*.md'))),
        "valid_source_count": len(source_records),
        "invalid_source_files": invalid_files,
        "raw_count": len(raw_records),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "extra_count": len(extras),
        "mismatched_count": len(mismatched),
        "matched": matched,
        "missing": missing,
        "extras": extras,
        "mismatched": mismatched,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit and synchronize Granola raw transcripts from a shared folder into Notion."
    )
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, help="Shared folder containing Granola markdown exports")
    parser.add_argument("--database-id", help="Notion database ID for the raw Granola database")
    parser.add_argument("--apply", action="store_true", help="Apply missing/mismatch repairs to Notion")
    parser.add_argument("--archive-extras", action="store_true", help="Archive raw pages that are not present in the shared folder")
    parser.add_argument("--report-json", help="Optional path to write the audit report as JSON")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    source_dir = Path(args.source_dir)
    if not source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {source_dir}")

    database_id = _resolve_database_id(args.database_id)
    audit_before = audit_folder_vs_raw(source_dir, database_id)

    result: dict[str, Any] = {
        "audit_before": audit_before,
        "applied": False,
        "repair": {"updated": 0, "created": 0, "archived": 0},
    }

    if args.apply:
        repair = _repair_records(
            database_id=database_id,
            matched=audit_before["matched"],
            missing=audit_before["missing"],
            extras=audit_before["extras"],
            archive_extras=args.archive_extras,
        )
        audit_after = audit_folder_vs_raw(source_dir, database_id)
        result["applied"] = True
        result["repair"] = repair
        result["audit_after"] = audit_after

    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    output = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        print(output)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
