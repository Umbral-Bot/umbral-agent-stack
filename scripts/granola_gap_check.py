#!/usr/bin/env python3
"""Notion raw DB gap check for Granola ingestion.

The VPS wrapper uses ``worker.notion_client.read_database``.  That helper
returns a flattened row shape: date properties look like
``{"start": "YYYY-MM-DD"}``, not the raw Notion
``{"type": "date", "date": {"start": ...}}`` payload.  Keep the check
compatible with both shapes so schema changes do not produce a vacuous OK.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DATE_FIELD_CANDIDATES = ("Fecha", "Date")
TRACEABILITY_FIELD_CANDIDATES = ("Trazabilidad", "Traceability")
STATUS_FIELD_CANDIDATES = ("Estado", "Status")
_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

# Freshness guard: independent of the 7-day "issues" window, alert when the
# most recent ``Fecha`` in the raw DB is older than this many days. This is the
# signal that was structurally missing when the intake stalled unnoticed for
# 69 days (spec b0004): the old check only looked at issues *inside* a 7-day
# window, so a dead intake produced a vacuous OK.
DEFAULT_STALE_AFTER_DAYS = 10
STALE_ENV_VAR = "GRANOLA_GAP_STALE_DAYS"


def _date_prefix(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    match = _DATE_PREFIX_RE.match(value)
    return match.group(0) if match else ""


def extract_date_start(value: Any) -> str:
    """Extract an ISO date prefix from flattened or raw Notion date values."""
    if isinstance(value, str):
        return _date_prefix(value)
    if not isinstance(value, dict):
        return ""

    if isinstance(value.get("start"), str):
        return _date_prefix(value.get("start"))

    date_value = value.get("date")
    if isinstance(date_value, dict) and isinstance(date_value.get("start"), str):
        return _date_prefix(date_value.get("start"))

    # Formula date flattening may return {"type": "date", "date": {"start": ...}}.
    if value.get("type") == "date":
        return extract_date_start(date_value)

    return ""


def _plain_text_from_rich_text(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    return "".join(
        str(item.get("plain_text") or "")
        for item in items
        if isinstance(item, dict)
    )


def extract_text(value: Any) -> str:
    """Extract flattened string or raw Notion rich_text/title plain text."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    if isinstance(value.get("plain_text"), str):
        return value.get("plain_text") or ""
    if value.get("type") == "rich_text":
        return _plain_text_from_rich_text(value.get("rich_text"))
    if value.get("type") == "title":
        return _plain_text_from_rich_text(value.get("title"))
    if isinstance(value.get("rich_text"), list):
        return _plain_text_from_rich_text(value.get("rich_text"))
    if isinstance(value.get("title"), list):
        return _plain_text_from_rich_text(value.get("title"))
    return ""


def extract_status(value: Any) -> str:
    """Extract flattened status/select string or raw Notion status/select."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    if value.get("type") == "select":
        return str((value.get("select") or {}).get("name") or "")
    if value.get("type") == "status":
        return str((value.get("status") or {}).get("name") or "")
    if isinstance(value.get("select"), dict):
        return str((value.get("select") or {}).get("name") or "")
    if isinstance(value.get("status"), dict):
        return str((value.get("status") or {}).get("name") or "")
    return ""


def _field_names_by_schema(
    schema: dict[str, Any],
    expected_type: str,
    fallback_names: tuple[str, ...],
) -> tuple[str, ...]:
    # read_database exposes the schema separately from flattened row values.
    # We still keep the field set narrow: scanning every date/rich_text/status
    # column can produce false OKs from unrelated properties.
    _ = (schema, expected_type)
    return fallback_names


def _first_date(properties: dict[str, Any], schema: dict[str, Any]) -> str:
    for name in _field_names_by_schema(schema, "date", DATE_FIELD_CANDIDATES):
        date_str = extract_date_start(properties.get(name))
        if date_str:
            return date_str
    return ""


def _first_text(
    properties: dict[str, Any],
    schema: dict[str, Any],
    fallback_names: tuple[str, ...],
) -> str:
    for name in _field_names_by_schema(schema, "rich_text", fallback_names):
        value = extract_text(properties.get(name))
        if value:
            return value
    return ""


def _first_status(properties: dict[str, Any], schema: dict[str, Any]) -> str:
    candidates = [
        *_field_names_by_schema(schema, "status", STATUS_FIELD_CANDIDATES),
        *_field_names_by_schema(schema, "select", STATUS_FIELD_CANDIDATES),
    ]
    seen: set[str] = set()
    for name in candidates:
        if name in seen:
            continue
        seen.add(name)
        value = extract_status(properties.get(name))
        if value:
            return value
    return ""


def build_gap_report(
    raw: dict[str, Any],
    *,
    now: datetime | None = None,
    recent_days: int = 7,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    schema = raw.get("schema") if isinstance(raw.get("schema"), dict) else {}
    items = raw.get("items") if isinstance(raw.get("items"), list) else []
    recent_cutoff = (now - timedelta(days=recent_days)).date().isoformat()

    issues: list[dict[str, Any]] = []
    skipped_no_date = 0
    max_date = ""  # newest Fecha seen (ISO YYYY-MM-DD; lexicographic max is valid)
    for item in items:
        if not isinstance(item, dict):
            continue
        properties = item.get("properties")
        props = properties if isinstance(properties, dict) else {}

        date_str = _first_date(props, schema)
        if not date_str:
            skipped_no_date += 1
            continue
        if date_str > max_date:
            max_date = date_str

        traceability = _first_text(props, schema, TRACEABILITY_FIELD_CANDIDATES)
        status = _first_status(props, schema)
        has_document_id = "granola_document_id=" in traceability

        issue_reasons: list[str] = []
        if not traceability.strip():
            issue_reasons.append("no_traceability")
        elif not has_document_id:
            issue_reasons.append("missing_granola_document_id")

        if status.strip().lower() in ("pendiente", "pending"):
            issue_reasons.append("still_pending")

        if issue_reasons and date_str >= recent_cutoff:
            issues.append(
                {
                    "page_id": item.get("page_id", ""),
                    "title": item.get("title", ""),
                    "date": date_str,
                    "estado": status,
                    "has_traceability": bool(traceability.strip()),
                    "has_document_id": has_document_id,
                    "reasons": issue_reasons,
                }
            )

    freshness_days: int | None = None
    stale = False
    stale_reason = ""
    if not max_date:
        # No dated rows at all: cannot prove freshness, so do not report a
        # vacuous OK. An empty/undated raw DB is itself a red flag for intake.
        stale = True
        stale_reason = "no_dated_items"
    else:
        freshness_days = (now.date() - date.fromisoformat(max_date)).days
        if freshness_days > stale_after_days:
            stale = True
            stale_reason = "max_date_older_than_threshold"

    return {
        "timestamp": now.isoformat(),
        "recent_cutoff": recent_cutoff,
        "total_pages": len(items),
        "recent_issues": len(issues),
        "skipped_no_date": skipped_no_date,
        "max_date": max_date,
        "freshness_days": freshness_days,
        "stale_after_days": stale_after_days,
        "stale": stale,
        "stale_reason": stale_reason,
        "issues": issues,
    }


def exit_code_for_report(report: dict[str, Any]) -> int:
    """Map a gap report to a process exit code for the VPS cron wrapper.

    0 = healthy, 2 = recent content gaps (existing behavior),
    3 = intake stale / freshness alert (new). Recent gaps take precedence when
    both would apply, though in practice they are mutually exclusive: a recent
    gap requires an item dated within the 7-day window, which keeps MAX(Fecha)
    fresher than the (>=10-day) staleness threshold.
    """
    if report.get("recent_issues"):
        return 2
    if report.get("stale"):
        return 3
    return 0


def _stale_after_days_from_env() -> int:
    raw = os.environ.get(STALE_ENV_VAR)
    if raw is None:
        return DEFAULT_STALE_AFTER_DAYS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_STALE_AFTER_DAYS
    return value if value > 0 else DEFAULT_STALE_AFTER_DAYS


def main() -> int:
    from worker import config, notion_client

    db_id = config.NOTION_GRANOLA_DB_ID
    if not db_id:
        print(json.dumps({"error": "NOTION_GRANOLA_DB_ID not set"}))
        return 1

    try:
        raw = notion_client.read_database(db_id, max_items=200)
        report = build_gap_report(raw, stale_after_days=_stale_after_days_from_env())
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return exit_code_for_report(report)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
