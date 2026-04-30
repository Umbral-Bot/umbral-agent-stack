#!/usr/bin/env python3
"""Migrate legacy Granola sessions into raw and deprecate session shells."""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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


from worker import config, notion_client  # noqa: E402


RAW_TEXT_PROJECT_FIELD = "Proyecto"
RAW_PROPOSED_DOMAIN_FIELD = "Dominio propuesto"
RAW_PROPOSED_TYPE_FIELD = "Tipo propuesto"
RAW_CANONICAL_DESTINATION_FIELD = "Destino canonico"
RAW_PROJECT_RELATION_FIELD = "Proyecto relacionado"
RAW_PROGRAM_RELATION_FIELD = "Programa relacionado"
RAW_RESOURCE_RELATION_FIELD = "Recurso relacionado"
RAW_AGENT_STATE_FIELD = "Estado agente"
RAW_AGENT_ACTION_FIELD = "Accion agente"
RAW_AGENT_SUMMARY_FIELD = "Resumen agente"
RAW_AGENT_LOG_FIELD = "Log del agente"
RAW_TRACEABILITY_FIELD = "Trazabilidad"
RAW_ARTIFACT_URL_FIELD = "URL artefacto"
RAW_STATUS_FIELD = "Estado"

SESSION_SOURCE_NAME = "Granola"


def _normalize_spaces(text: str) -> str:
    return " ".join((text or "").split())


def _normalize_title(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def _exact_key(title: str, date: str) -> tuple[str, str]:
    return (_normalize_spaces(title), (date or "").strip())


def _normalized_key(title: str, date: str) -> tuple[str, str]:
    return (_normalize_title(title), (date or "").strip())


def _append_log(existing: str, entry: str) -> str:
    parts = [part for part in [str(existing or "").strip(), entry.strip()] if part]
    if not parts:
        return ""
    return "\n".join(parts)[-2000:]


def _session_notes_are_unique(session_notes: str, raw_summary: str, raw_log: str) -> bool:
    notes = _normalize_spaces(session_notes).lower()
    if not notes:
        return False
    haystack = " ".join(
        _normalize_spaces(part).lower()
        for part in (raw_summary or "", raw_log or "")
        if part
    )
    return notes not in haystack


def _body_is_shell(body_text: str, notes_text: str, title: str, date: str) -> bool:
    body = _normalize_spaces(body_text)
    notes = _normalize_spaces(notes_text)
    if not body:
        return True

    low_body = body.lower()
    low_notes = notes.lower()
    if low_notes and low_body == low_notes:
        return True
    if low_notes and low_body in {
        f"notas {low_notes}",
        f"resumen {low_notes}",
        f"observaciones {low_notes}",
    }:
        return True

    filler = {
        _normalize_spaces(title).lower(),
        _normalize_spaces(date).lower(),
        f"nombre { _normalize_spaces(title).lower() }".strip(),
        f"fecha { _normalize_spaces(date).lower() }".strip(),
        low_notes,
    }
    body_lines = [_normalize_spaces(line).lower() for line in body_text.splitlines() if line.strip()]
    unique_lines = [line for line in body_lines if line not in filler and line not in {"nombre", "fecha", "notas", "resumen"}]
    return not unique_lines


def _load_db_schema(database_id: str) -> dict[str, str]:
    snapshot = notion_client.read_database(database_id, max_items=1)
    schema = dict(snapshot.get("schema") or {})
    for row in notion_client.query_database(database_id):
        properties = row.get("properties") or {}
        if isinstance(properties, dict):
            for prop_name, prop_value in properties.items():
                if not isinstance(prop_name, str) or not prop_name:
                    continue
                if isinstance(prop_value, dict):
                    schema.setdefault(prop_name, str(prop_value.get("type") or ""))
                else:
                    schema.setdefault(prop_name, "")
        if schema:
            break
    return schema


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    props_raw = row.get("properties") or {}
    flat_props = notion_client.flatten_page_properties(props_raw)
    title = ""
    for meta in props_raw.values():
        if isinstance(meta, dict) and meta.get("type") == "title":
            title = notion_client._plain_text_from_rich_text(meta.get("title"))  # type: ignore[attr-defined]
            break

    return {
        "page_id": str(row.get("id") or ""),
        "url": str(row.get("url") or ""),
        "title": title,
        "date": str((flat_props.get("Fecha") or {}).get("start") or flat_props.get("Date") or "")[:10],
        "properties_raw": props_raw,
        "properties": flat_props,
    }


def _fetch_rows(database_id: str) -> list[dict[str, Any]]:
    return [_flatten_row(row) for row in notion_client.query_database(database_id)]


def _resolve_page_title(page_id: str, cache: dict[str, dict[str, str]]) -> str:
    cached = cache.get(page_id)
    if cached and cached.get("title"):
        return cached["title"]
    page = notion_client.get_page(page_id)
    title = ""
    for meta in (page.get("properties") or {}).values():
        if isinstance(meta, dict) and meta.get("type") == "title":
            title = notion_client._plain_text_from_rich_text(meta.get("title"))  # type: ignore[attr-defined]
            break
    cache[page_id] = {"title": title, "url": str(page.get("url") or "")}
    return title


def _resolve_page_url(page_id: str, cache: dict[str, dict[str, str]]) -> str:
    cached = cache.get(page_id)
    if cached and cached.get("url"):
        return cached["url"]
    page = notion_client.get_page(page_id)
    title = ""
    for meta in (page.get("properties") or {}).values():
        if isinstance(meta, dict) and meta.get("type") == "title":
            title = notion_client._plain_text_from_rich_text(meta.get("title"))  # type: ignore[attr-defined]
            break
    url = str(page.get("url") or "")
    cache[page_id] = {"title": title, "url": url}
    return url


def _match_raw_record(
    session_record: dict[str, Any],
    raw_records: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    source_url = str(session_record["properties"].get("URL fuente") or "").strip()
    session_url = str(session_record.get("url") or "").strip()

    if source_url:
        for raw_record in raw_records:
            if str(raw_record.get("url") or "").strip() == source_url:
                return raw_record, "url_fuente"

    if session_url:
        for raw_record in raw_records:
            artifact_url = str(raw_record["properties"].get(RAW_ARTIFACT_URL_FIELD) or "").strip()
            if artifact_url and artifact_url == session_url:
                return raw_record, "raw_url_artefacto"

    exact_session_key = _exact_key(session_record["title"], session_record["date"])
    for raw_record in raw_records:
        if _exact_key(raw_record["title"], raw_record["date"]) == exact_session_key:
            return raw_record, "titulo_fecha_exactos"

    normalized_session_key = _normalized_key(session_record["title"], session_record["date"])
    for raw_record in raw_records:
        if _normalized_key(raw_record["title"], raw_record["date"]) == normalized_session_key:
            return raw_record, "titulo_fecha_normalizados"

    return None, None


def _resolve_canonical_url_from_session(
    session_record: dict[str, Any],
    cache: dict[str, dict[str, str]],
) -> str | None:
    relation_candidates = []
    for field_name in ("Proyecto", "Programa", "Recurso relacionado"):
        relation_ids = session_record["properties"].get(field_name) or []
        if isinstance(relation_ids, list):
            relation_candidates.extend(str(item).strip() for item in relation_ids if str(item).strip())
    relation_candidates = list(dict.fromkeys(relation_candidates))
    if len(relation_candidates) != 1:
        return None
    return _resolve_page_url(relation_candidates[0], cache)


def _build_raw_update_from_session(
    *,
    raw_record: dict[str, Any],
    session_record: dict[str, Any],
    raw_schema: dict[str, str],
    page_cache: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], bool]:
    properties: dict[str, Any] = {}
    raw_props = raw_record["properties"]
    session_props = session_record["properties"]
    requires_review = False

    domain = str(session_props.get("Dominio") or "").strip()
    if domain and RAW_PROPOSED_DOMAIN_FIELD in raw_schema:
        properties[RAW_PROPOSED_DOMAIN_FIELD] = {"select": {"name": domain}}

    session_type = str(session_props.get("Tipo") or "").strip()
    if session_type and RAW_PROPOSED_TYPE_FIELD in raw_schema:
        properties[RAW_PROPOSED_TYPE_FIELD] = {"select": {"name": session_type}}

    project_ids = session_props.get("Proyecto") or []
    if isinstance(project_ids, list) and project_ids:
        if RAW_PROJECT_RELATION_FIELD in raw_schema:
            properties[RAW_PROJECT_RELATION_FIELD] = {"relation": [{"id": project_id} for project_id in project_ids]}
        if RAW_TEXT_PROJECT_FIELD in raw_schema:
            project_titles = [_resolve_page_title(project_id, page_cache) for project_id in project_ids]
            project_titles = [title for title in project_titles if title]
            if project_titles:
                properties[RAW_TEXT_PROJECT_FIELD] = {
                    "rich_text": [{"text": {"content": ", ".join(project_titles)[:2000]}}]
                }

    program_ids = session_props.get("Programa") or []
    if isinstance(program_ids, list) and program_ids and RAW_PROGRAM_RELATION_FIELD in raw_schema:
        properties[RAW_PROGRAM_RELATION_FIELD] = {"relation": [{"id": page_id} for page_id in program_ids]}

    resource_ids = session_props.get("Recurso relacionado") or []
    if isinstance(resource_ids, list) and resource_ids and RAW_RESOURCE_RELATION_FIELD in raw_schema:
        properties[RAW_RESOURCE_RELATION_FIELD] = {"relation": [{"id": page_id} for page_id in resource_ids]}

    session_notes = str(session_props.get("Notas") or "").strip()
    raw_summary = str(raw_props.get(RAW_AGENT_SUMMARY_FIELD) or "").strip()
    raw_log = str(raw_props.get(RAW_AGENT_LOG_FIELD) or "").strip()
    migration_note = f"{session_record['date']} session-migration: metadata from legacy session {session_record['page_id']}"
    if _session_notes_are_unique(session_notes, raw_summary, raw_log):
        migration_note += f" | notes={session_notes}"
    properties[RAW_AGENT_LOG_FIELD] = {
        "rich_text": [{"text": {"content": _append_log(raw_log, migration_note)[:2000]}}]
    }

    raw_artifact_url = str(raw_props.get(RAW_ARTIFACT_URL_FIELD) or "").strip()
    session_url = str(session_record.get("url") or "").strip()
    if raw_artifact_url and session_url and raw_artifact_url == session_url:
        canonical_url = _resolve_canonical_url_from_session(session_record, page_cache)
        if canonical_url:
            properties[RAW_ARTIFACT_URL_FIELD] = {"url": canonical_url}
        else:
            properties[RAW_ARTIFACT_URL_FIELD] = {"url": None}
            properties[RAW_AGENT_STATE_FIELD] = {"select": {"name": "Revision requerida"}}
            properties[RAW_AGENT_ACTION_FIELD] = {"select": {"name": "Bloqueado por ambiguedad"}}
            requires_review = True

    return properties, requires_review


def _load_session_body(session_page_id: str) -> str:
    snapshot = notion_client.get_page_snapshot(session_page_id, max_blocks=2000)
    return str(snapshot.get("plain_text") or "").strip()


def build_migration_report(raw_db_id: str, session_db_id: str) -> dict[str, Any]:
    raw_schema = _load_db_schema(raw_db_id)
    raw_records = _fetch_rows(raw_db_id)
    session_records = _fetch_rows(session_db_id)
    granola_sessions = [
        row
        for row in session_records
        if str(row["properties"].get("Fuente") or "").strip() == SESSION_SOURCE_NAME
    ]

    page_cache: dict[str, dict[str, str]] = {}
    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    raw_updates: list[dict[str, Any]] = []
    archive_candidates: list[dict[str, Any]] = []
    review_candidates: list[dict[str, Any]] = []

    for session_record in granola_sessions:
        raw_record, match_method = _match_raw_record(session_record, raw_records)
        if raw_record is None:
            unmatched.append(
                {
                    "session_page_id": session_record["page_id"],
                    "session_url": session_record["url"],
                    "title": session_record["title"],
                    "date": session_record["date"],
                }
            )
            continue

        matched.append(
            {
                "session_page_id": session_record["page_id"],
                "raw_page_id": raw_record["page_id"],
                "match_method": match_method,
                "title": session_record["title"],
                "date": session_record["date"],
            }
        )
        update_properties, requires_review = _build_raw_update_from_session(
            raw_record=raw_record,
            session_record=session_record,
            raw_schema=raw_schema,
            page_cache=page_cache,
        )
        raw_updates.append(
            {
                "raw_page_id": raw_record["page_id"],
                "session_page_id": session_record["page_id"],
                "match_method": match_method,
                "properties": update_properties,
            }
        )
        if requires_review:
            review_candidates.append(
                {
                    "raw_page_id": raw_record["page_id"],
                    "session_page_id": session_record["page_id"],
                    "reason": "raw_url_artefacto_pointed_to_session_without_single_canonical_relation",
                }
            )

        body_text = _load_session_body(session_record["page_id"])
        notes_text = str(session_record["properties"].get("Notas") or "")
        if _body_is_shell(body_text, notes_text, session_record["title"], session_record["date"]):
            archive_candidates.append(
                {
                    "session_page_id": session_record["page_id"],
                    "session_url": session_record["url"],
                    "title": session_record["title"],
                    "date": session_record["date"],
                    "reason": "blank_or_metadata_only_shell",
                }
            )

    return {
        "raw_db_id": raw_db_id,
        "session_db_id": session_db_id,
        "raw_schema_fields": sorted(raw_schema.keys()),
        "counts": {
            "raw_rows": len(raw_records),
            "session_rows": len(session_records),
            "granola_sessions": len(granola_sessions),
            "matched": len(matched),
            "unmatched": len(unmatched),
            "raw_updates": len(raw_updates),
            "archive_candidates": len(archive_candidates),
            "review_candidates": len(review_candidates),
        },
        "matched": matched,
        "unmatched": unmatched,
        "raw_updates": raw_updates,
        "archive_candidates": archive_candidates,
        "review_candidates": review_candidates,
    }


def apply_migration_report(report: dict[str, Any]) -> dict[str, int]:
    updated = 0
    archived = 0

    for item in report.get("raw_updates", []):
        properties = item.get("properties") or {}
        if properties:
            notion_client.update_page_properties(
                page_id_or_url=str(item["raw_page_id"]),
                properties=properties,
            )
            updated += 1

    archive_ids = {item["session_page_id"] for item in report.get("archive_candidates", [])}
    for session_page_id in archive_ids:
        notion_client.update_page_properties(
            page_id_or_url=str(session_page_id),
            properties={},
            archived=True,
        )
        archived += 1

    return {
        "updated_raw_rows": updated,
        "archived_session_rows": archived,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate Granola session metadata into raw and deprecate session shells.",
    )
    parser.add_argument("--raw-db-id", default=config.NOTION_GRANOLA_DB_ID or "", help="Raw DB id.")
    parser.add_argument(
        "--session-db-id",
        default=config.NOTION_GRANOLA_SESSION_DB_ID or "",
        help="Legacy session DB id.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply the planned migration.")
    parser.add_argument("--report-json", default="", help="Optional path to write the report JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _load_dotenv(REPO_ROOT / ".env")
    args = parse_args(argv)
    raw_db_id = (args.raw_db_id or "").strip()
    session_db_id = (args.session_db_id or "").strip()
    if not raw_db_id:
        raise SystemExit("Missing --raw-db-id or NOTION_GRANOLA_DB_ID")
    if not session_db_id:
        raise SystemExit("Missing --session-db-id or NOTION_GRANOLA_SESSION_DB_ID")

    report = build_migration_report(raw_db_id=raw_db_id, session_db_id=session_db_id)
    if args.apply:
        report["apply_summary"] = apply_migration_report(report)
    else:
        report["apply_summary"] = {"updated_raw_rows": 0, "archived_session_rows": 0}

    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
