"""
Tasks: Granola pipeline handlers.

- granola.process_transcript: pipeline completo de transcripción → Notion
- granola.classify_raw: clasificación V2 de una página raw de Granola
- granola.create_followup: follow-up proactivo (reminder, email_draft, proposal)
"""

import json
import logging
import re
import hashlib
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .. import config, notion_client
from .granola_finality import (
    decide_reconciliation,
    detect_truncation,
)
from .notion import (
    handle_notion_upsert_bridge_item,
    handle_notion_upsert_deliverable,
    handle_notion_upsert_project,
    handle_notion_upsert_task,
)
from .notion_markdown import markdown_to_blocks

logger = logging.getLogger("worker.tasks.granola")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTION_ITEM_RE = re.compile(
    r"[-*]\s*\[[ x]?\]\s*(.+)", re.IGNORECASE
)


def _build_action_item_task_id(title: str, date: str, item: Dict[str, str]) -> str:
    """Build a stable task id so repeated transcript ingests upsert instead of duplicating."""
    parts = [
        (title or "").strip().lower(),
        (date or "").strip(),
        (item.get("text") or "").strip().lower(),
        (item.get("assignee") or "").strip().lower(),
        (item.get("due") or "").strip(),
    ]
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"granola-action-item-{digest}"


def _extract_action_items_from_content(content: str) -> List[Dict[str, str]]:
    """Best-effort extraction of action items from freeform markdown content."""
    items: List[Dict[str, str]] = []
    in_section = False
    for line in content.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("## ") and any(
            kw in stripped for kw in ("action item", "compromisos", "tareas", "to-do", "todo")
        ):
            in_section = True
            continue
        if stripped.startswith("## ") and in_section:
            break
        if in_section:
            m = _ACTION_ITEM_RE.match(line.strip())
            if m:
                item_text = m.group(1).strip()
                assignee = ""
                due = ""
                paren = re.search(r"\(([^)]+)\)\s*$", item_text)
                if paren:
                    parts = [p.strip() for p in paren.group(1).split(",")]
                    for p in parts:
                        if re.match(r"\d{4}-\d{2}-\d{2}", p):
                            due = p
                        else:
                            assignee = p
                    item_text = item_text[: paren.start()].strip()
                items.append({"text": item_text, "assignee": assignee, "due": due})
    return items


def _extract_title_from_page(page_data: Dict[str, Any]) -> str:
    properties = page_data.get("properties") or {}
    for prop in properties.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            parts: list[str] = []
            for item in prop.get("title") or []:
                if isinstance(item, dict):
                    parts.append(item.get("plain_text", item.get("text", {}).get("content", "")))
            return "".join(parts).strip()
    return ""


def _extract_date_from_page(page_data: Dict[str, Any]) -> str:
    return _extract_named_date_property(
        page_data,
        "Fecha",
        "Date",
        "Fecha de transcripcion",
        "Meeting Date",
    )


def _extract_named_date_property(page_data: Dict[str, Any], *names: str) -> str:
    properties = page_data.get("properties") or {}
    for candidate in names:
        prop = properties.get(candidate)
        if isinstance(prop, dict) and prop.get("type") == "date":
            return ((prop.get("date") or {}).get("start") or "").strip()
    return ""


def _extract_select_value(page_data: Dict[str, Any], *names: str) -> str:
    properties = page_data.get("properties") or {}
    for candidate in names:
        prop = properties.get(candidate)
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        if prop_type == "select":
            return ((prop.get("select") or {}).get("name") or "").strip()
        if prop_type == "status":
            return ((prop.get("status") or {}).get("name") or "").strip()
        if prop_type == "rich_text":
            parts: list[str] = []
            for item in prop.get("rich_text") or []:
                if isinstance(item, dict):
                    parts.append(item.get("plain_text", item.get("text", {}).get("content", "")))
            return "".join(parts).strip()
    return ""


def _extract_relation_values(page_data: Dict[str, Any], *names: str) -> list[str]:
    properties = page_data.get("properties") or {}
    for candidate in names:
        prop = properties.get(candidate)
        if not isinstance(prop, dict) or prop.get("type") != "relation":
            continue
        resolved: list[str] = []
        for item in prop.get("relation") or []:
            if isinstance(item, dict):
                item_id = str(item.get("id") or "").strip()
                if item_id:
                    resolved.append(item_id)
        if resolved:
            return resolved
    return []


def _compact_excerpt(text: str, limit: int = 280) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _expected_block_signature(blocks: list[Dict[str, Any]]) -> list[tuple[str, str]]:
    signature: list[tuple[str, str]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type") or "").strip()
        payload = block.get(block_type) or {}
        rich_text = payload.get("rich_text") if isinstance(payload, dict) else None
        text = ""
        if isinstance(rich_text, list):
            text = "".join(
                item.get("plain_text", item.get("text", {}).get("content", ""))
                for item in rich_text
                if isinstance(item, dict)
            )
        signature.append((block_type, text))
    return signature


def _verify_raw_page_persistence(
    *,
    page_id: str,
    expected_blocks: list[Dict[str, Any]],
) -> Dict[str, Any]:
    snapshot = notion_client.read_page_full(page_id)
    actual_signature = [
        (str(item.get("type") or "").strip(), str(item.get("text") or ""))
        for item in (snapshot.get("blocks") or [])
        if isinstance(item, dict)
    ]
    expected_signature = _expected_block_signature(expected_blocks)
    verification: Dict[str, Any] = {
        "ok": actual_signature == expected_signature,
        "expected_block_count": len(expected_signature),
        "actual_block_count": len(actual_signature),
        "page_id": page_id,
        "page_url": str(snapshot.get("url") or ""),
        "plain_text_length": len(str(snapshot.get("plain_text") or "")),
    }

    if verification["ok"]:
        return verification

    mismatch_index = 0
    max_index = min(len(expected_signature), len(actual_signature))
    while mismatch_index < max_index and expected_signature[mismatch_index] == actual_signature[mismatch_index]:
        mismatch_index += 1

    expected_block = expected_signature[mismatch_index] if mismatch_index < len(expected_signature) else ("", "")
    actual_block = actual_signature[mismatch_index] if mismatch_index < len(actual_signature) else ("", "")
    verification.update(
        {
            "mismatch_index": mismatch_index,
            "expected_excerpt": _compact_excerpt(expected_block[1], limit=180),
            "actual_excerpt": _compact_excerpt(actual_block[1], limit=180),
        }
    )
    return verification


def _alert_raw_integrity_failure(
    *,
    title: str,
    granola_document_id: str,
    verification: Dict[str, Any],
) -> None:
    parts = [
        "ALERTA integridad Granola raw.",
        f"Título: {title}",
        f"granola_document_id: {granola_document_id or '(missing)'}",
        f"page_id: {verification.get('page_id') or '(missing)'}",
        f"expected_blocks={verification.get('expected_block_count')} actual_blocks={verification.get('actual_block_count')}",
    ]
    if verification.get("mismatch_index") is not None:
        parts.append(f"mismatch_index={verification.get('mismatch_index')}")
    if verification.get("page_url"):
        parts.append(f"page_url: {verification['page_url']}")
    expected_excerpt = str(verification.get("expected_excerpt") or "").strip()
    actual_excerpt = str(verification.get("actual_excerpt") or "").strip()
    if expected_excerpt:
        parts.append(f"expected_excerpt: {expected_excerpt}")
    if actual_excerpt:
        parts.append(f"actual_excerpt: {actual_excerpt}")

    try:
        notion_client.add_comment(page_id=None, text="\n".join(parts))
    except Exception as exc:
        logger.error("Failed to notify raw integrity failure for %s: %s", title, exc)


def _normalize_lookup_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def _extract_date_start(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("start") or "").strip()
    return str(value or "").strip()


def _extract_page_text_property(page_data: Dict[str, Any], *names: str) -> str:
    properties = page_data.get("properties") or {}
    for candidate in names:
        prop = properties.get(candidate)
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        if prop_type == "url":
            return str(prop.get("url") or "").strip()
        if prop_type in {"title", "rich_text"}:
            key = "title" if prop_type == "title" else "rich_text"
            parts: list[str] = []
            for item in prop.get(key) or []:
                if isinstance(item, dict):
                    parts.append(item.get("plain_text", item.get("text", {}).get("content", "")))
            return "".join(parts).strip()
    return ""


def _append_context(existing: str, extra: str) -> str:
    base = (existing or "").strip()
    addon = (extra or "").strip()
    if not addon:
        return base
    if not base:
        return addon
    return f"{base}\n\n{addon}"


def _comment_safe(page_id: str | None, text: str) -> bool:
    if not page_id or not text.strip():
        return False
    try:
        notion_client.add_comment(page_id=page_id, text=text)
        return True
    except Exception as exc:
        logger.warning("Failed to add traceability comment to %s: %s", page_id, exc)
        return False


def _leave_review_comment(
    page_id: str | None,
    *,
    source_evidence: str,
    intended_target: str,
    blocking_ambiguity: str,
    next_review: str,
) -> bool:
    comment = (
        "Revisión requerida.\n"
        f"1. Evidencia fuente: {source_evidence}\n"
        f"2. Destino intencionado: {intended_target}\n"
        f"3. Bloqueo: {blocking_ambiguity}\n"
        f"4. Siguiente revisión necesaria: {next_review}"
    )
    return _comment_safe(page_id, comment)


def _result_page_id(result: Dict[str, Any] | None) -> str:
    if not isinstance(result, dict):
        return ""
    direct = str(result.get("page_id") or "").strip()
    if direct:
        return direct
    nested = result.get("result")
    if isinstance(nested, dict):
        inner_page_id = str(nested.get("page_id") or "").strip()
        if inner_page_id:
            return inner_page_id
        notion_result = nested.get("notion_result")
        if isinstance(notion_result, dict):
            return str(notion_result.get("page_id") or "").strip()
    return ""


def _today_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _page_schema_from_page(page_data: Dict[str, Any]) -> Dict[str, str]:
    properties = page_data.get("properties") or {}
    schema: Dict[str, str] = {}
    for name, meta in properties.items():
        if not isinstance(meta, dict):
            continue
        prop_type = str(meta.get("type") or "").strip()
        if prop_type:
            schema[name] = prop_type
    return schema


def _schema_property_name(
    schema: Dict[str, str],
    candidates: list[str],
    expected_types: set[str] | None = None,
) -> str | None:
    for candidate in candidates:
        prop_type = str(schema.get(candidate) or "").strip()
        if not prop_type:
            continue
        if expected_types and prop_type not in expected_types:
            continue
        return candidate
    return None


def _extract_content_metadata_value(content: str, label: str) -> str:
    escaped = re.escape(label)
    patterns = (
        rf"\*\*{escaped}\s*:\*\*\s*(.+)",
        rf"-\s*\*\*{escaped}\s*:\*\*\s*(.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _resolve_granola_document_id(input_data: Dict[str, Any], content: str) -> str:
    value = str(input_data.get("granola_document_id") or "").strip()
    if value:
        return value
    metadata = input_data.get("metadata")
    if isinstance(metadata, dict):
        value = str(metadata.get("granola_document_id") or "").strip()
        if value:
            return value
    return _extract_content_metadata_value(content, "Granola Document ID")


def _resolve_source_updated_at(input_data: Dict[str, Any], content: str) -> str:
    value = str(input_data.get("source_updated_at") or "").strip()
    if value:
        return value
    metadata = input_data.get("metadata")
    if isinstance(metadata, dict):
        value = str(metadata.get("updated_at") or "").strip()
        if value:
            return value
    return _extract_content_metadata_value(content, "Updated At")


def _resolve_source_url(input_data: Dict[str, Any]) -> str:
    value = str(input_data.get("source_url") or "").strip()
    if value:
        return value
    metadata = input_data.get("metadata")
    if isinstance(metadata, dict):
        return str(metadata.get("source_url") or "").strip()
    return ""


def _resolve_metadata_value(input_data: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(input_data.get(key) or "").strip()
        if value:
            return value

    metadata = input_data.get("metadata")
    if isinstance(metadata, dict):
        for key in keys:
            value = str(metadata.get(key) or "").strip()
            if value:
                return value
    return ""


def _build_raw_traceability_text(
    *,
    granola_document_id: str,
    source_updated_at: str,
    source_url: str,
    extra_fields: Dict[str, str] | None = None,
) -> str:
    parts: list[str] = []
    if granola_document_id:
        parts.append(f"granola_document_id={granola_document_id}")
    if source_updated_at:
        parts.append(f"source_updated_at={source_updated_at}")
    if source_url:
        parts.append(f"source_url={source_url}")
    for key in (
        "export_signature",
        "content_hash",
        "shared_folder_path",
        "sha1",
        "char_count",
        "segment_count",
        "ingested_at",
        "reconciled_at",
        "truncation_detected",
        "truncation_reason",
    ):
        value = str((extra_fields or {}).get(key) or "").strip()
        if value:
            parts.append(f"{key}={value}")
    if not parts:
        return ""
    parts.append("ingest_path=granola.process_transcript")
    return "\n".join(parts)


def _parse_traceability_text(value: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for line in (value or "").splitlines():
        key, _, raw_value = line.partition("=")
        clean_key = key.strip()
        clean_value = raw_value.strip()
        if clean_key and clean_value:
            parsed[clean_key] = clean_value
    return parsed


def _build_transcript_paragraph_blocks(content: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for i in range(0, len(content), 2000):
        chunk = content[i : i + 2000]
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                },
            }
        )
    return blocks


def _extract_raw_traceability(page_data: Dict[str, Any]) -> Dict[str, str]:
    raw = _extract_page_text_property(page_data, "Trazabilidad", "Traceability")
    return _parse_traceability_text(raw)


def _extract_raw_candidate_value(
    page_data: Dict[str, Any],
    traceability: Dict[str, str],
    *,
    traceability_key: str,
    candidates: list[str],
) -> str:
    direct = _extract_page_text_property(page_data, *candidates)
    if direct:
        return direct
    return str(traceability.get(traceability_key) or "").strip()


def _build_existing_raw_candidate(page_data: Dict[str, Any]) -> Dict[str, Any]:
    traceability = _extract_raw_traceability(page_data)
    title = _extract_title_from_page(page_data)

    def _traceability_int(key: str) -> int:
        raw = str(traceability.get(key) or "").strip()
        if not raw:
            return 0
        try:
            return int(raw)
        except ValueError:
            return 0

    truncation_raw = str(traceability.get("truncation_detected") or "").strip().lower()
    truncation_detected = truncation_raw in {"true", "1", "yes"}

    return {
        "page_id": str(page_data.get("id") or "").strip(),
        "url": str(page_data.get("url") or "").strip(),
        "title": title,
        "normalized_title": _normalize_lookup_text(title),
        "date": _extract_date_from_page(page_data),
        "last_edited_time": str(page_data.get("last_edited_time") or "").strip(),
        "traceability": traceability,
        "granola_document_id": _extract_raw_candidate_value(
            page_data,
            traceability,
            traceability_key="granola_document_id",
            candidates=[
                "Granola Document ID",
                "Document ID",
                "ID documento Granola",
                "ID documento",
            ],
        ),
        "source_updated_at": _extract_raw_candidate_value(
            page_data,
            traceability,
            traceability_key="source_updated_at",
            candidates=[
                "Source Updated At",
                "Updated At",
                "Ultima actualizacion fuente",
                "Última actualización fuente",
            ],
        ),
        "source_url": _extract_raw_candidate_value(
            page_data,
            traceability,
            traceability_key="source_url",
            candidates=[
                "Source URL",
                "URL fuente",
                "URL Fuente",
                "Meeting URL",
            ],
        ),
        "export_signature": _extract_raw_candidate_value(
            page_data,
            traceability,
            traceability_key="export_signature",
            candidates=["Export Signature", "Signature"],
        ),
        "content_hash": _extract_raw_candidate_value(
            page_data,
            traceability,
            traceability_key="content_hash",
            candidates=["Content Hash", "SHA1", "Sha1"],
        ),
        "shared_folder_path": _extract_raw_candidate_value(
            page_data,
            traceability,
            traceability_key="shared_folder_path",
            candidates=["Shared Folder Path", "Ruta carpeta compartida"],
        ),
        "sha1": _extract_raw_candidate_value(
            page_data,
            traceability,
            traceability_key="sha1",
            candidates=["SHA1", "Sha1"],
        ),
        "imported_at": _extract_named_date_property(
            page_data,
            "Fecha que Rick pasó a Notion",
            "Fecha que Rick paso a Notion",
            "Fecha que Rick pas? a Notion",
            "Imported At",
        ),
        "processed_at": _extract_named_date_property(
            page_data,
            "Fecha que el agente procesó",
            "Fecha que el agente proceso",
            "Fecha que el agente proces?",
            "Processed At",
        ),
        "char_count": _traceability_int("char_count"),
        "segment_count": _traceability_int("segment_count"),
        "truncation_detected": truncation_detected,
        "ingested_at": str(traceability.get("ingested_at") or "").strip(),
        "reconciled_at": str(traceability.get("reconciled_at") or "").strip(),
    }


def _select_preferred_raw_candidate(
    candidates: list[Dict[str, Any]],
    *,
    title: str,
    source_url: str,
    source_updated_at: str,
) -> Dict[str, Any] | None:
    if not candidates:
        return None

    ranked = sorted(candidates, key=lambda item: item.get("page_id") or "")
    ranked = sorted(ranked, key=lambda item: item.get("last_edited_time") or "", reverse=True)
    if title:
        normalized_title = _normalize_lookup_text(title)
        ranked = sorted(
            ranked,
            key=lambda item: item.get("normalized_title") != normalized_title,
        )
    if source_updated_at:
        ranked = sorted(
            ranked,
            key=lambda item: item.get("source_updated_at") != source_updated_at,
        )
    if source_url:
        ranked = sorted(
            ranked,
            key=lambda item: item.get("source_url") != source_url,
        )
    return ranked[0]


def _find_existing_raw_candidate(
    candidates: list[Dict[str, Any]],
    *,
    title: str,
    transcript_date: str,
    granola_document_id: str,
    source_url: str,
    source_updated_at: str,
    export_signature: str,
    content_hash: str,
    shared_folder_path: str,
    sha1: str,
) -> tuple[Dict[str, Any] | None, str]:
    if granola_document_id:
        exact_matches = [
            item
            for item in candidates
            if item.get("granola_document_id") == granola_document_id
        ]
        selected = _select_preferred_raw_candidate(
            exact_matches,
            title=title,
            source_url=source_url,
            source_updated_at=source_updated_at,
        )
        if selected:
            return selected, "granola_document_id"

    if source_url:
        exact_matches = [
            item for item in candidates if item.get("source_url") == source_url
        ]
        selected = _select_preferred_raw_candidate(
            exact_matches,
            title=title,
            source_url=source_url,
            source_updated_at=source_updated_at,
        )
        if selected:
            return selected, "source_url"

    if export_signature:
        exact_matches = [
            item
            for item in candidates
            if item.get("export_signature") == export_signature
        ]
        selected = _select_preferred_raw_candidate(
            exact_matches,
            title=title,
            source_url=source_url,
            source_updated_at=source_updated_at,
        )
        if selected:
            return selected, "export_signature"

    if content_hash and source_updated_at:
        exact_matches = [
            item
            for item in candidates
            if item.get("content_hash") == content_hash
            and item.get("source_updated_at") == source_updated_at
        ]
        selected = _select_preferred_raw_candidate(
            exact_matches,
            title=title,
            source_url=source_url,
            source_updated_at=source_updated_at,
        )
        if selected:
            return selected, "content_hash_source_updated_at"

    if shared_folder_path and sha1:
        exact_matches = [
            item
            for item in candidates
            if item.get("shared_folder_path") == shared_folder_path
            and item.get("sha1") == sha1
        ]
        selected = _select_preferred_raw_candidate(
            exact_matches,
            title=title,
            source_url=source_url,
            source_updated_at=source_updated_at,
        )
        if selected:
            return selected, "shared_folder_path_sha1"

    if shared_folder_path and source_updated_at:
        exact_matches = [
            item
            for item in candidates
            if item.get("shared_folder_path") == shared_folder_path
            and item.get("source_updated_at") == source_updated_at
        ]
        selected = _select_preferred_raw_candidate(
            exact_matches,
            title=title,
            source_url=source_url,
            source_updated_at=source_updated_at,
        )
        if selected:
            return selected, "shared_folder_path_source_updated_at"

    if transcript_date:
        # When the incoming payload carries a non-empty granola_document_id,
        # we MUST NOT fall back to a title/date match against a page that is
        # already bound to a different non-empty granola_document_id. Doing
        # otherwise would merge two distinct Granola meetings (same title and
        # date but different recordings) into a single raw page.
        #
        # Legacy rows without a granola_document_id are still eligible so the
        # historical backfill path keeps working.
        def _fallback_allows(candidate: Dict[str, Any]) -> bool:
            candidate_doc_id = str(candidate.get("granola_document_id") or "").strip()
            if not granola_document_id:
                return True
            if not candidate_doc_id:
                return True
            return candidate_doc_id == granola_document_id

        exact_title_matches = [
            item
            for item in candidates
            if item.get("date") == transcript_date
            and item.get("title") == title
            and _fallback_allows(item)
        ]
        if len(exact_title_matches) == 1:
            return exact_title_matches[0], "exact_title_date"

        normalized_title = _normalize_lookup_text(title)
        normalized_matches = [
            item
            for item in candidates
            if item.get("date") == transcript_date
            and item.get("normalized_title") == normalized_title
            and _fallback_allows(item)
        ]
        if len(normalized_matches) == 1:
            return normalized_matches[0], "normalized_title_date"

    return None, ""


def _title_family_index(title: str, base_title: str) -> int | None:
    normalized_base = _normalize_lookup_text(base_title)
    if not normalized_base:
        return None
    if _normalize_lookup_text(title) == normalized_base:
        return 1

    canonical_match = re.match(r"^(?P<base>.+?)\s\[(?P<index>\d+)\]$", title.strip())
    if canonical_match and _normalize_lookup_text(canonical_match.group("base")) == normalized_base:
        try:
            parsed = int(canonical_match.group("index"))
        except ValueError:
            parsed = 0
        return parsed if parsed >= 2 else None

    legacy_match = re.match(r"^(?P<base>.+?)\s(?P<index>\d+)$", title.strip())
    if legacy_match and _normalize_lookup_text(legacy_match.group("base")) == normalized_base:
        try:
            parsed = int(legacy_match.group("index"))
        except ValueError:
            parsed = 0
        return parsed if parsed >= 2 else None

    return None


def _resolve_new_raw_title(
    title: str,
    candidates: list[Dict[str, Any]],
) -> str:
    family_candidates: list[Dict[str, Any]] = []
    for item in candidates:
        family_index = _title_family_index(str(item.get("title") or ""), title)
        if family_index is not None:
            family_candidates.append({**item, "family_index": family_index})

    if not family_candidates:
        return title

    base_candidate = next(
        (
            item
            for item in family_candidates
            if int(item.get("family_index") or 0) == 1
        ),
        None,
    )
    canonical_base = str((base_candidate or {}).get("title") or "").strip() or title
    next_index = max(int(item.get("family_index") or 1) for item in family_candidates) + 1
    return f"{canonical_base} [{next_index}]"


def _build_raw_transcript_properties(
    *,
    schema: Dict[str, str],
    title: str,
    source: str,
    date: str,
    traceability_text: str,
    granola_document_id: str,
    source_updated_at: str,
    source_url: str,
    extra_traceability: Dict[str, str],
    is_create: bool,
    existing_imported_at: str = "",
    existing_processed_at: str = "",
) -> tuple[Dict[str, Any], list[str]]:
    properties: Dict[str, Any] = {}
    used_fields: list[str] = []

    _set_schema_property(
        properties,
        schema,
        ["Name", "Nombre", "Título", "Title"],
        title,
        expected_types={"title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Date", "Fecha", "Fecha de transcripción", "Fecha de reunion", "Meeting Date"],
        date,
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Source", "Fuente"],
        source,
        expected_types={"select", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tags", "Etiquetas"],
        [source],
        expected_types={"multi_select"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Trazabilidad", "Traceability"],
        traceability_text,
        expected_types={"rich_text", "url", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Granola Document ID", "Document ID", "ID documento Granola", "ID documento"],
        granola_document_id,
        expected_types={"rich_text", "title", "url"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        [
            "Source Updated At",
            "Updated At",
            "Ultima actualizacion fuente",
            "Última actualización fuente",
        ],
        source_updated_at,
        expected_types={"rich_text", "date", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Source URL", "URL fuente", "URL Fuente", "Meeting URL"],
        source_url,
        expected_types={"url", "rich_text", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Ingest Path", "Ruta de ingesta"],
        "granola.process_transcript",
        expected_types={"rich_text", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Shared Folder Path", "Ruta carpeta compartida"],
        extra_traceability.get("shared_folder_path"),
        expected_types={"rich_text", "url", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["SHA1", "Sha1"],
        extra_traceability.get("sha1"),
        expected_types={"rich_text", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Content Hash"],
        extra_traceability.get("content_hash"),
        expected_types={"rich_text", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Export Signature", "Signature"],
        extra_traceability.get("export_signature"),
        expected_types={"rich_text", "title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Char Count", "Transcript Char Count"],
        extra_traceability.get("char_count"),
        expected_types={"number", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Segment Count", "Transcript Segment Count"],
        extra_traceability.get("segment_count"),
        expected_types={"number", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Ingested At"],
        extra_traceability.get("ingested_at"),
        expected_types={"date", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Reconciled At"],
        extra_traceability.get("reconciled_at"),
        expected_types={"date", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Truncation Detected", "Truncado"],
        extra_traceability.get("truncation_detected"),
        expected_types={"checkbox", "select", "rich_text"},
        used_fields=used_fields,
    )

    if is_create:
        today = _today_date()
        _set_schema_property(
            properties,
            schema,
            ["Estado", "Status"],
            "Pendiente",
            expected_types={"select", "status", "rich_text"},
            used_fields=used_fields,
        )
        _set_schema_property(
            properties,
            schema,
            [
                "Fecha que Rick pasó a Notion",
                "Fecha que Rick paso a Notion",
                "Fecha que Rick pas? a Notion",
                "Imported At",
            ],
            today,
            expected_types={"date"},
            used_fields=used_fields,
        )
        _set_schema_property(
            properties,
            schema,
            [
                "Fecha que el agente procesó",
                "Fecha que el agente proceso",
                "Fecha que el agente proces?",
                "Processed At",
            ],
            today,
            expected_types={"date"},
            used_fields=used_fields,
        )

    if not is_create and not existing_imported_at:
        _set_schema_property(
            properties,
            schema,
            [
                "Fecha que Rick pasÃ³ a Notion",
                "Fecha que Rick paso a Notion",
                "Fecha que Rick pas? a Notion",
                "Imported At",
            ],
            _today_date(),
            expected_types={"date"},
            used_fields=used_fields,
        )

    if not is_create and not existing_processed_at:
        _set_schema_property(
            properties,
            schema,
            [
                "Fecha que el agente procesÃ³",
                "Fecha que el agente proceso",
                "Fecha que el agente proces?",
                "Processed At",
            ],
            _today_date(),
            expected_types={"date"},
            used_fields=used_fields,
        )

    return properties, used_fields


def _iso_now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _upsert_raw_transcript_page(
    *,
    title: str,
    content: str,
    source: str,
    date: str,
    traceability_text: str,
    granola_document_id: str,
    source_updated_at: str,
    source_url: str,
    extra_traceability: Dict[str, str],
    stability_window: int | None = None,
    min_chars: int | None = None,
    force_reconcile: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Upsert a Granola raw transcript page with finality + reconciliation checks.

    When ``dry_run`` is truthy the function computes the decision and resolved
    traceability but performs **no writes** against Notion (the DB schema is still
    read so the preview is realistic). The return dict always contains the full
    ``reconciliation`` summary so callers can audit what would happen.
    """
    db_snapshot = notion_client.read_database(config.NOTION_GRANOLA_DB_ID, max_items=1)
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read Granola raw DB schema")

    existing_pages = notion_client.query_database(config.NOTION_GRANOLA_DB_ID)
    candidates = [
        _build_existing_raw_candidate(page)
        for page in existing_pages
        if isinstance(page, dict)
    ]

    existing_match, match_strategy = _find_existing_raw_candidate(
        candidates,
        title=title,
        transcript_date=date,
        granola_document_id=granola_document_id,
        source_url=source_url,
        source_updated_at=source_updated_at,
        export_signature=str(extra_traceability.get("export_signature") or "").strip(),
        content_hash=str(extra_traceability.get("content_hash") or "").strip(),
        shared_folder_path=str(extra_traceability.get("shared_folder_path") or "").strip(),
        sha1=str(extra_traceability.get("sha1") or "").strip(),
    )

    decision = decide_reconciliation(
        existing=existing_match,
        new_content=content,
        source_updated_at=source_updated_at,
        stability_window=stability_window,
        min_chars=min_chars,
        force_reconcile=force_reconcile,
    )
    decision_dict = decision.as_dict()

    resolved_title = (
        str(existing_match.get("title") or "").strip()
        if existing_match
        else _resolve_new_raw_title(title, candidates)
    ) or title

    if decision.action in {"defer", "noop"}:
        return {
            "page_id": str((existing_match or {}).get("page_id") or ""),
            "url": str((existing_match or {}).get("url") or ""),
            "created": False,
            "updated": False,
            "matched_existing": existing_match is not None,
            "match_strategy": match_strategy,
            "resolved_title": resolved_title,
            "schema_fields_used": [],
            "reconciliation": decision_dict,
            "dry_run": bool(dry_run),
        }

    now_iso = _iso_now_utc()
    merged_traceability = dict(extra_traceability or {})
    new_metrics = decision_dict.get("new_metrics") or {}
    char_count_val = str(new_metrics.get("char_count") or "").strip()
    segment_count_val = str(new_metrics.get("segment_count") or "").strip()
    content_hash_from_metrics = str(new_metrics.get("content_hash") or "").strip()
    if char_count_val:
        merged_traceability.setdefault("char_count", char_count_val)
    if segment_count_val:
        merged_traceability.setdefault("segment_count", segment_count_val)
    if content_hash_from_metrics and not merged_traceability.get("content_hash"):
        merged_traceability["content_hash"] = content_hash_from_metrics
    truncation = decision_dict.get("truncation") or {}
    if truncation.get("truncated"):
        merged_traceability["truncation_detected"] = "true"
        reason = str(truncation.get("reason") or "").strip()
        if reason:
            merged_traceability["truncation_reason"] = reason
    else:
        merged_traceability.setdefault("truncation_detected", "false")

    if decision.action == "create":
        merged_traceability.setdefault("ingested_at", now_iso)
    elif decision.action == "reconcile":
        merged_traceability["reconciled_at"] = now_iso
        if existing_match and existing_match.get("ingested_at"):
            merged_traceability.setdefault("ingested_at", existing_match["ingested_at"])
        else:
            merged_traceability.setdefault("ingested_at", now_iso)

    effective_traceability_text = traceability_text
    if not effective_traceability_text:
        effective_traceability_text = _build_raw_traceability_text(
            granola_document_id=granola_document_id,
            source_updated_at=source_updated_at,
            source_url=source_url,
            extra_fields=merged_traceability,
        )
    else:
        parsed_existing = _parse_traceability_text(effective_traceability_text)
        extra_additions: list[str] = []
        for key in (
            "content_hash",
            "char_count",
            "segment_count",
            "ingested_at",
            "reconciled_at",
            "truncation_detected",
            "truncation_reason",
        ):
            value = str(merged_traceability.get(key) or "").strip()
            if value and not parsed_existing.get(key):
                extra_additions.append(f"{key}={value}")
        if extra_additions:
            effective_traceability_text = "\n".join(
                [effective_traceability_text, *extra_additions]
            )

    blocks = _build_transcript_paragraph_blocks(content)
    properties, used_fields = _build_raw_transcript_properties(
        schema=schema,
        title=resolved_title,
        source=source,
        date=date,
        traceability_text=effective_traceability_text,
        granola_document_id=granola_document_id,
        source_updated_at=source_updated_at,
        source_url=source_url,
        extra_traceability=merged_traceability,
        is_create=existing_match is None,
        existing_imported_at=str(existing_match.get("imported_at") or "").strip()
        if existing_match
        else "",
        existing_processed_at=str(existing_match.get("processed_at") or "").strip()
        if existing_match
        else "",
    )

    if dry_run:
        preview_page_id = str((existing_match or {}).get("page_id") or "")
        preview_url = str((existing_match or {}).get("url") or "")
        return {
            "page_id": preview_page_id,
            "url": preview_url,
            "created": existing_match is None,
            "updated": existing_match is not None,
            "matched_existing": existing_match is not None,
            "match_strategy": match_strategy,
            "resolved_title": resolved_title,
            "schema_fields_used": used_fields,
            "reconciliation": decision_dict,
            "dry_run": True,
            "preview_properties": properties,
            "preview_block_count": len(blocks),
            "effective_traceability_text": effective_traceability_text,
        }

    if existing_match:
        page_id = str(existing_match.get("page_id") or "").strip()
        if not page_id:
            raise RuntimeError("Matched raw page is missing page_id")
        notion_result = notion_client.update_page_properties(page_id, properties=properties)
        notion_client.replace_blocks_in_page(page_id=page_id, blocks=blocks)
        notion_result["created"] = False
        notion_result["updated"] = True
        notion_result["page_id"] = page_id
        notion_result["url"] = notion_result.get("url") or existing_match.get("url", "")
    else:
        notion_result = notion_client.create_database_page(
            config.NOTION_GRANOLA_DB_ID,
            properties=properties,
            children=blocks,
        )
        notion_result["updated"] = False

    identity_sync = _sync_visible_notion_page_id(
        str(notion_result.get("page_id") or "").strip(),
        schema,
    )
    notion_result["notion_page_id_sync"] = identity_sync
    for field_name in identity_sync.get("schema_fields_used") or []:
        if field_name not in used_fields:
            used_fields.append(field_name)

    notion_result["matched_existing"] = existing_match is not None
    notion_result["match_strategy"] = match_strategy
    notion_result["resolved_title"] = resolved_title
    notion_result["schema_fields_used"] = used_fields
    notion_result["reconciliation"] = decision_dict
    notion_result["dry_run"] = False
    verification = _verify_raw_page_persistence(
        page_id=str(notion_result.get("page_id") or "").strip(),
        expected_blocks=blocks,
    )
    notion_result["content_verification"] = verification
    if not verification.get("ok"):
        _alert_raw_integrity_failure(
            title=resolved_title,
            granola_document_id=granola_document_id,
            verification=verification,
        )
        raise RuntimeError(
            "Notion transcript integrity check failed after raw page upsert"
        )
    return notion_result


def _pick_best_existing_curated_session(
    candidates: list[Dict[str, Any]],
    *,
    session_name: str,
    transcript_date: str,
    transcript_url: str,
    source_prop: str | None,
) -> tuple[Dict[str, Any] | None, str]:
    normalized_target = _normalize_lookup_text(session_name)
    ranked: list[tuple[tuple[int, int, int], Dict[str, Any], str]] = []

    for candidate in candidates:
        candidate_title = _extract_title_from_page(candidate)
        candidate_date = _extract_date_from_page(candidate)
        candidate_source = (
            _extract_page_text_property(candidate, source_prop) if source_prop else ""
        )

        same_source = bool(transcript_url and candidate_source == transcript_url)
        exact_title = bool(session_name and candidate_title == session_name)
        normalized_title = bool(
            normalized_target
            and candidate_title
            and _normalize_lookup_text(candidate_title) == normalized_target
        )
        same_date = bool(transcript_date and candidate_date == transcript_date)

        match_strategy = ""
        if same_source:
            match_strategy = "source_url"
            primary_rank = 0
        elif exact_title:
            match_strategy = "exact_title"
            primary_rank = 1
        elif normalized_title and same_date:
            match_strategy = "normalized_title_date"
            primary_rank = 2
        else:
            continue

        mangled_penalty = 1 if "?" in candidate_title else 0
        date_penalty = 0 if same_date or not transcript_date else 1
        ranked.append(
            ((primary_rank, mangled_penalty, date_penalty), candidate, match_strategy)
        )

    if not ranked:
        return None, ""

    ranked.sort(key=lambda item: item[0])
    return ranked[0][1], ranked[0][2]


def _relation_ids(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        clean = value.strip()
        return [clean] if clean else []
    if isinstance(value, dict):
        return _relation_ids(value.get("id") or value.get("page_id"))
    if isinstance(value, list):
        resolved: list[str] = []
        for item in value:
            resolved.extend(_relation_ids(item))
        seen: set[str] = set()
        unique: list[str] = []
        for item in resolved:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique
    return []


def _set_schema_property(
    payload: Dict[str, Any],
    schema: Dict[str, str],
    candidates: list[str],
    value: Any,
    *,
    expected_types: set[str] | None = None,
    used_fields: list[str] | None = None,
) -> str | None:
    if value in (None, "", []):
        return None

    prop_name = _schema_property_name(schema, candidates, expected_types)
    if not prop_name:
        return None

    prop_type = schema[prop_name]
    if prop_type == "title":
        payload[prop_name] = {"title": [{"text": {"content": str(value)[:2000]}}]}
    elif prop_type == "rich_text":
        payload[prop_name] = {"rich_text": [{"text": {"content": str(value)[:2000]}}]}
    elif prop_type == "date":
        payload[prop_name] = {"date": {"start": str(value)}}
    elif prop_type == "select":
        payload[prop_name] = {"select": {"name": str(value)}}
    elif prop_type == "status":
        payload[prop_name] = {"status": {"name": str(value)}}
    elif prop_type == "multi_select":
        if isinstance(value, list):
            options = [str(item).strip() for item in value if str(item).strip()]
        else:
            options = [str(value).strip()] if str(value).strip() else []
        if not options:
            return None
        payload[prop_name] = {"multi_select": [{"name": item} for item in options]}
    elif prop_type == "url":
        payload[prop_name] = {"url": str(value)}
    elif prop_type == "relation":
        ids = _relation_ids(value)
        if not ids:
            return None
        payload[prop_name] = {"relation": [{"id": item} for item in ids]}
    elif prop_type == "checkbox":
        if isinstance(value, str):
            payload[prop_name] = {
                "checkbox": value.strip().lower() in {"true", "1", "yes", "on"}
            }
        else:
            payload[prop_name] = {"checkbox": bool(value)}
    elif prop_type == "number":
        try:
            payload[prop_name] = {"number": float(value)}
        except (TypeError, ValueError):
            return None
    else:
        return None

    if used_fields is not None:
        used_fields.append(prop_name)
    return prop_name


def _build_visible_notion_page_id_properties(
    schema: Dict[str, str],
    page_id: str,
) -> tuple[Dict[str, Any], list[str]]:
    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        [
            "ID interno Notion",
            "ID interno de Notion",
            "Notion Page ID",
            "Notion ID",
            "Page ID",
        ],
        page_id,
        expected_types={"rich_text", "title"},
        used_fields=used_fields,
    )
    return properties, used_fields


def _sync_visible_notion_page_id(
    page_id: str,
    schema: Dict[str, str],
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if not page_id:
        return {
            "ok": False,
            "page_id": "",
            "updated": False,
            "dry_run": dry_run,
            "schema_fields_used": [],
        }

    properties, used_fields = _build_visible_notion_page_id_properties(schema, page_id)
    if dry_run or not properties:
        return {
            "ok": True,
            "page_id": page_id,
            "updated": bool(properties),
            "dry_run": dry_run,
            "schema_fields_used": used_fields,
            "properties": properties,
        }

    result = notion_client.update_page_properties(page_id, properties=properties)
    result["ok"] = True
    result["dry_run"] = False
    result["schema_fields_used"] = used_fields
    return result


def _sync_raw_promotion_state(
    raw_page_id: str,
    raw_page_data: Dict[str, Any],
    *,
    curated_url: str = "",
    dry_run: bool = False,
) -> Dict[str, Any]:
    raw_schema = _page_schema_from_page(raw_page_data)
    properties: Dict[str, Any] = {}
    used_fields: list[str] = []

    _set_schema_property(
        properties,
        raw_schema,
        ["Estado", "Status"],
        "Procesada",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        [
            "Fecha que el agente procesó",
            "Fecha que el agente proceso",
            "Fecha que el agente proces?",
            "Processed At",
        ],
        _today_date(),
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["URL artefacto", "Artifact URL", "Artifact Link"],
        curated_url,
        expected_types={"url", "rich_text"},
        used_fields=used_fields,
    )

    if dry_run:
        return {
            "ok": True,
            "page_id": raw_page_id,
            "updated": bool(properties),
            "dry_run": True,
            "properties": properties,
            "schema_fields_used": used_fields,
        }

    if not properties:
        return {
            "ok": True,
            "page_id": raw_page_id,
            "updated": False,
            "dry_run": False,
            "properties": {},
            "schema_fields_used": used_fields,
        }

    result = notion_client.update_page_properties(raw_page_id, properties=properties)
    result["ok"] = True
    result["dry_run"] = False
    result["schema_fields_used"] = used_fields
    return result


def _build_transcript_blocks(parsed: Dict[str, Any]) -> list[dict[str, Any]]:
    """Build Notion blocks from parsed transcript data."""
    blocks: list[dict[str, Any]] = []

    # Attendees callout
    attendees = parsed.get("attendees", [])
    if attendees:
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"Participantes: {', '.join(attendees)}"}}],
                "icon": {"type": "emoji", "emoji": "👥"},
                "color": "gray_background",
            },
        })

    # Content via markdown converter
    content = parsed.get("content", "")
    if content:
        content_blocks = markdown_to_blocks(content)
        blocks.extend(content_blocks)

    # Action items section
    action_items = parsed.get("action_items", [])
    if action_items:
        blocks.append({"object": "block", "type": "divider", "divider": {}})
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Action Items"}}],
                "color": "default",
            },
        })
        for item in action_items:
            text = item.get("text", "")
            assignee = item.get("assignee", "")
            due = item.get("due", "")
            suffix = ""
            if assignee:
                suffix += f" — {assignee}"
            if due:
                suffix += f" (vence: {due})"
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"{text}{suffix}"}}],
                    "checked": False,
                    "color": "default",
                },
            })

    return blocks


# ---------------------------------------------------------------------------
# granola.process_transcript
# ---------------------------------------------------------------------------

def handle_granola_process_transcript(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline completo: transcripción de Granola → Notion.

    Input:
        title (str, required): Título de la reunión.
        content (str, required): Contenido/transcripción en markdown.
        date (str, optional): Fecha ISO (default: hoy UTC).
        attendees (list[str], optional): Lista de participantes.
        action_items (list[dict], optional): Action items pre-parseados
            [{text, assignee, due}]. Si no se proporcionan, se extraen del content.
        source (str, optional): Fuente (default: "granola").
        notify_enlace (bool, optional): Notificar a Enlace (default: true).

    Returns:
        page_id (str): ID de la página creada en Notion.
        url (str): URL de la página.
        action_items_created (int): Número de action items creados como tareas.
        notification_sent (bool): Si se notificó a Enlace.
    """
    title = input_data.get("title", "").strip()
    content = input_data.get("content", "").strip()
    if not title:
        raise ValueError("'title' is required in input")
    if not content:
        raise ValueError("'content' is required in input")

    date = input_data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    attendees = input_data.get("attendees", [])
    source = input_data.get("source", "granola")
    notify_enlace = input_data.get("notify_enlace", True)
    allow_legacy_raw_task_writes = bool(input_data.get("allow_legacy_raw_task_writes"))
    dry_run = bool(input_data.get("dry_run") or input_data.get("audit"))
    force_reconcile = bool(input_data.get("force_reconcile"))
    stability_window = input_data.get("stability_window_seconds")
    min_chars_override = input_data.get("min_stable_chars")
    granola_document_id = _resolve_granola_document_id(input_data, content)
    source_updated_at = _resolve_source_updated_at(input_data, content)
    source_url = _resolve_source_url(input_data)
    extra_traceability = {
        "export_signature": _resolve_metadata_value(input_data, "export_signature"),
        "content_hash": _resolve_metadata_value(input_data, "content_hash"),
        "shared_folder_path": _resolve_metadata_value(input_data, "shared_folder_path"),
        "sha1": _resolve_metadata_value(input_data, "sha1", "shared_folder_sha1"),
    }
    traceability_text = _build_raw_traceability_text(
        granola_document_id=granola_document_id,
        source_updated_at=source_updated_at,
        source_url=source_url,
        extra_fields=extra_traceability,
    )

    # Action items: use provided or extract from content
    action_items = input_data.get("action_items")
    if not action_items:
        action_items = _extract_action_items_from_content(content)
        logger.info("Extracted %d action items from content", len(action_items))

    # Step 1: Upsert transcript page in Notion raw DB
    logger.info(
        "Upserting Granola transcript raw page: %s (dry_run=%s, force=%s)",
        title,
        dry_run,
        force_reconcile,
    )
    page_result = _upsert_raw_transcript_page(
        title=title,
        content=content,
        source=source,
        date=date,
        traceability_text=traceability_text,
        granola_document_id=granola_document_id,
        source_updated_at=source_updated_at,
        source_url=source_url,
        extra_traceability=extra_traceability,
        stability_window=stability_window,
        min_chars=min_chars_override,
        force_reconcile=force_reconcile,
        dry_run=dry_run,
    )
    page_id = page_result["page_id"]
    page_url = page_result.get("url", "")
    reconciliation = page_result.get("reconciliation") or {}
    action = str(reconciliation.get("action") or "").strip()
    logger.info(
        "Granola raw action=%s reason=%s page_id=%s url=%s dry_run=%s",
        action or "unknown",
        str(reconciliation.get("reason") or "")[:200],
        page_id,
        page_url,
        dry_run,
    )

    skip_downstream = action in {"defer", "noop"} or dry_run

    action_items_for_tasks = (
        action_items if (allow_legacy_raw_task_writes and not skip_downstream) else []
    )
    if action_items and not action_items_for_tasks:
        if skip_downstream:
            logger.info(
                "Skipping %d raw action items because action=%s (dry_run=%s)",
                len(action_items),
                action,
                dry_run,
            )
        else:
            logger.info(
                "Skipping %d raw action items for transcript %s due to V1 guardrail",
                len(action_items),
                page_id,
            )

    # Step 2: Create action items as Notion tasks
    ai_created = 0
    for item in action_items_for_tasks:
        try:
            task_name = (item.get("text", "Action item") or "Action item").strip()[:200] or "Action item"
            assignee = (item.get("assignee", "sin asignar") or "sin asignar").strip() or "sin asignar"
            due = (item.get("due") or "").strip()
            summary = (
                f"De reunión: {title} ({date}). "
                f"Responsable sugerido: {assignee}. "
                f"Ref: {page_url or page_id}"
            )
            if due:
                summary += f". Vence: {due}"
            handle_notion_upsert_task(
                {
                    "task_id": _build_action_item_task_id(title, date, item),
                    "status": "queued",
                    "team": assignee,
                    "task": "granola.action_item",
                    "task_name": f"[Granola] {task_name}",
                    "project_name": "Proyecto Granola",
                    "input_summary": summary,
                    "source": "granola_process_transcript",
                    "source_kind": "action_item",
                }
            )
            ai_created += 1
        except Exception as e:
            logger.warning("Failed to create action item task: %s", e)

    # Step 3: Notify Enlace in Control Room (literal @Enlace per convention)
    notification_sent = False
    if notify_enlace and not skip_downstream:
        try:
            attendees_str = f" ({', '.join(attendees)})" if attendees else ""
            transcript_ref = page_url or page_id
            reconciled_suffix = ""
            if action == "reconcile":
                reconciled_suffix = " (reconciliada — transcript actualizado)"
            comment_text = (
                f"Hola @Enlace, transcripción lista para revisar{reconciled_suffix}: "
                f"{title}{attendees_str} — {date}. "
                f"Página: {transcript_ref}. "
                f"{len(action_items)} action items identificados."
            )
            notion_client.add_comment(page_id=None, text=comment_text)
            notification_sent = True
            logger.info("Enlace notified in Control Room for transcript %s", page_id)
        except Exception as e:
            logger.warning("Failed to notify Enlace: %s", e)

    return {
        "page_id": page_id,
        "url": page_url,
        "action_items_detected": len(action_items),
        "action_items_created": ai_created,
        "legacy_raw_task_writes_enabled": allow_legacy_raw_task_writes,
        "granola_document_id": granola_document_id,
        "source_updated_at": source_updated_at,
        "source_url": source_url,
        "traceability_written": bool(traceability_text),
        "matched_existing": bool(page_result.get("matched_existing")),
        "match_strategy": str(page_result.get("match_strategy") or ""),
        "resolved_title": str(page_result.get("resolved_title") or title),
        "notion_page_id_sync": page_result.get("notion_page_id_sync") or {},
        "content_verification": page_result.get("content_verification") or {},
        "notification_sent": notification_sent,
        "reconciliation": reconciliation,
        "reconciliation_action": action or "unknown",
        "dry_run": bool(dry_run),
        "deferred": action == "defer",
        "noop": action == "noop",
    }


# ---------------------------------------------------------------------------
# V2 classification — taxonomy and LLM classifier
# ---------------------------------------------------------------------------

_V2_DOMINIO_VALUES = {"Docencia", "Operacion", "Sistemas", "Marca", "Mixto"}
_V2_TIPO_VALUES = {"Clase", "Sesión", "Reunión", "Tutoría", "Workshop", "Llamada", "Revisión", "Otro"}
_V2_DESTINO_VALUES = {"Tarea", "Proyecto", "Entregable", "Programa", "Recurso", "Ignorar"}
_V2_DESTINO_REVIEW_ONLY = {"Programa", "Recurso"}  # read-only targets → always review

_CLASSIFY_RETRY_DELAY = 2.0  # seconds between retry attempts
_CLASSIFY_FALLBACK_MODEL = "gemini_pro"  # fallback when primary model fails

# Map V2 destino to the explicit target flags that would satisfy it
_V2_DESTINO_TARGET_MAP: Dict[str, list[str]] = {
    "Tarea": ["bridge_item", "followup"],
    "Proyecto": ["project"],
    "Entregable": ["deliverable"],
}


def _classify_gate(
    classification_result: Dict[str, Any],
    *,
    wants_project: bool,
    wants_deliverable: bool,
    wants_bridge: bool,
    wants_followup: bool,
) -> Dict[str, str]:
    """Evaluate classification against explicit targets. Returns action + reason + advisory."""
    classification = classification_result.get("classification") or {}
    destino = str(classification.get("destino") or "").strip()

    if not destino:
        return {"action": "proceed", "reason": "", "advisory": ""}

    # Hard block: Ignorar
    if destino == "Ignorar":
        return {
            "action": "skip",
            "reason": "Clasificación V2: destino=Ignorar — sin contenido accionable",
            "advisory": "",
        }

    # Hard block: Programa / Recurso
    if destino in _V2_DESTINO_REVIEW_ONLY:
        return {
            "action": "block",
            "reason": f"Clasificación V2: destino={destino} — requiere revisión humana",
            "advisory": "",
        }

    # Soft advisory: check if explicit targets align with destino
    have = {
        "project": wants_project,
        "deliverable": wants_deliverable,
        "bridge_item": wants_bridge,
        "followup": wants_followup,
    }
    expected_targets = _V2_DESTINO_TARGET_MAP.get(destino, [])

    # Block: destino mapped but no compatible target provided
    if expected_targets and not any(have.get(t) for t in expected_targets):
        expected_names = ", ".join(expected_targets)
        return {
            "action": "block",
            "reason": (
                f"Clasificación V2: destino={destino} pero falta target compatible "
                f"({expected_names}) — requiere revisión"
            ),
            "advisory": "",
        }

    # Block: incompatible targets provided (targets that don't match destino)
    if expected_targets:
        incompatible = [
            t for t, present in have.items()
            if present and t not in expected_targets
        ]
        if incompatible:
            incompatible_names = ", ".join(incompatible)
            return {
                "action": "block",
                "reason": (
                    f"Clasificación V2: destino={destino} incompatible con targets "
                    f"explícitos ({incompatible_names}) — requiere revisión"
                ),
                "advisory": "",
            }

    return {"action": "proceed", "reason": "", "advisory": ""}

_CLASSIFY_SYSTEM_PROMPT = """\
Eres un clasificador de transcripciones de reuniones.
Dada una transcripcion, devuelve SOLO un JSON valido con estos 4 campos:

{
  "dominio": "Docencia" | "Operacion" | "Sistemas" | "Marca" | "Mixto",
  "tipo": "Clase" | "Sesión" | "Reunión" | "Tutoría" | "Workshop" | "Llamada" | "Revisión" | "Otro",
  "destino": "Tarea" | "Proyecto" | "Entregable" | "Programa" | "Recurso" | "Ignorar",
  "resumen": "<resumen en español, 1-3 oraciones, máximo 280 caracteres>"
}

Reglas:
- dominio: area principal de la reunion (Docencia=cursos/clases, Operacion=proyectos/asesoria, Sistemas=automatizacion/tech, Marca=branding/comercial, Mixto=multiples areas)
- tipo: formato de la sesion
- destino: objeto canonico mas probable que se derivaria de esta reunion
  - Si hay action items claros → Tarea
  - Si se discute un proyecto con decisiones o scope → Proyecto
  - Si hay un entregable concreto mencionado → Entregable
  - Si es contenido docente o de programa → Programa
  - Si es material reutilizable o caso de estudio → Recurso
  - Si no hay contenido accionable → Ignorar
- resumen: resumen ejecutivo util para David (el dueño del workspace). En español.
- Si tienes duda entre dos opciones, elige la mas conservadora.
- Devuelve SOLO el JSON, sin markdown ni explicaciones.\
"""


def _build_classify_prompt(title: str, content: str, attendees: List[str]) -> str:
    parts = [f"Titulo: {title}"]
    if attendees:
        parts.append(f"Asistentes: {', '.join(attendees)}")
    # Truncate content to ~3000 chars to keep LLM cost low
    excerpt = content[:3000]
    if len(content) > 3000:
        excerpt += "\n[... contenido truncado]"
    parts.append(f"Contenido:\n{excerpt}")
    return "\n\n".join(parts)


def _parse_classification(raw_text: str) -> Dict[str, str] | None:
    """Parse LLM JSON response, tolerating markdown fences."""
    text = raw_text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _validate_classification(data: Dict[str, str]) -> Dict[str, str]:
    """Validate and sanitize classification against V2 taxonomy. Returns cleaned dict."""
    result: Dict[str, str] = {}
    raw_dominio = str(data.get("dominio") or "").strip()
    result["dominio"] = raw_dominio if raw_dominio in _V2_DOMINIO_VALUES else ""
    raw_tipo = str(data.get("tipo") or "").strip()
    result["tipo"] = raw_tipo if raw_tipo in _V2_TIPO_VALUES else ""
    raw_destino = str(data.get("destino") or "").strip()
    result["destino"] = raw_destino if raw_destino in _V2_DESTINO_VALUES else ""
    result["resumen"] = str(data.get("resumen") or "").strip()[:280]
    return result


def handle_granola_classify_raw(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    V2 classifier: classify a raw Granola page and populate V2 fields.

    Reads the raw page, calls LLM for classification, validates against
    taxonomy, and updates the raw page properties.

    Input:
        page_id (str, required): Raw transcript page ID.
        dry_run (bool, optional): If true, classify but don't update Notion.
        model (str, optional): LLM model alias (default: gemini_flash).

    Returns:
        classification (dict): dominio, tipo, destino, resumen
        fields_updated (list): V2 fields actually written to Notion
        needs_review (bool): True if classification requires human review
        review_reason (str): Why review is needed, if applicable
    """
    from .llm import handle_llm_generate

    page_id = (
        input_data.get("page_id")
        or input_data.get("transcript_page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not page_id:
        raise ValueError("'page_id' is required")

    dry_run = bool(input_data.get("dry_run"))
    model = str(input_data.get("model") or "gemini_flash").strip()

    # Step 1: Read the raw page
    page_snapshot = notion_client.read_page(page_id, max_blocks=80)
    page_data = notion_client.get_page(page_id)

    title = (
        (page_snapshot.get("title") or "").strip()
        or _extract_title_from_page(page_data)
        or "Reunión"
    )
    content = (page_snapshot.get("plain_text") or "").strip()
    if not content:
        return {
            "page_id": page_id,
            "classification": {},
            "fields_updated": [],
            "needs_review": True,
            "review_reason": "No content available for classification",
            "dry_run": dry_run,
        }

    # Extract attendees from page properties if available
    attendees: List[str] = []
    props = page_data.get("properties") or {}
    for key in ("Asistentes", "Attendees", "Participantes"):
        att_prop = props.get(key)
        if att_prop and att_prop.get("type") == "rich_text":
            att_text = "".join(
                rt.get("plain_text", "") for rt in (att_prop.get("rich_text") or [])
            ).strip()
            if att_text:
                attendees = [a.strip() for a in att_text.split(",") if a.strip()]
                break

    # Step 2: Call LLM for classification (retry + fallback)
    classify_prompt = _build_classify_prompt(title, content, attendees)
    logger.info("Classifying raw page %s: '%s'", page_id[:8], title[:60])

    llm_params = {
        "prompt": classify_prompt,
        "system": _CLASSIFY_SYSTEM_PROMPT,
        "max_tokens": 300,
        "temperature": 0.0,
    }

    raw_response = ""
    model_used = model
    classify_attempts = 0
    last_error: Optional[Exception] = None

    # Attempt 1: primary model
    classify_attempts += 1
    try:
        llm_result = handle_llm_generate({**llm_params, "model": model})
        raw_response = llm_result.get("text") or ""
        last_error = None
    except Exception as exc:
        last_error = exc
        logger.warning(
            "classify %s attempt %d failed (model=%s): %s",
            page_id[:8], classify_attempts, model, exc,
        )

    # Attempt 2: retry primary model after backoff
    if last_error is not None:
        time.sleep(_CLASSIFY_RETRY_DELAY)
        classify_attempts += 1
        try:
            llm_result = handle_llm_generate({**llm_params, "model": model})
            raw_response = llm_result.get("text") or ""
            last_error = None
            logger.info(
                "classify %s retry succeeded (model=%s, attempt=%d)",
                page_id[:8], model, classify_attempts,
            )
        except Exception as exc:
            last_error = exc
            logger.warning(
                "classify %s attempt %d failed (model=%s): %s",
                page_id[:8], classify_attempts, model, exc,
            )

    # Attempt 3: fallback model
    fallback_model = str(input_data.get("fallback_model") or _CLASSIFY_FALLBACK_MODEL).strip()
    if last_error is not None and fallback_model != model:
        classify_attempts += 1
        model_used = fallback_model
        try:
            llm_result = handle_llm_generate({**llm_params, "model": fallback_model})
            raw_response = llm_result.get("text") or ""
            last_error = None
            logger.info(
                "classify %s fallback succeeded (model=%s, attempt=%d)",
                page_id[:8], fallback_model, classify_attempts,
            )
        except Exception as exc:
            last_error = exc
            logger.warning(
                "classify %s fallback failed (model=%s, attempt=%d): %s",
                page_id[:8], fallback_model, classify_attempts, exc,
            )

    if last_error is not None:
        logger.error(
            "classify %s FAILED after %d attempts (primary=%s, fallback=%s): %s",
            page_id[:8], classify_attempts, model, fallback_model, last_error,
        )
        return {
            "page_id": page_id,
            "classification": {},
            "fields_updated": [],
            "needs_review": True,
            "review_reason": f"LLM call failed: {last_error}",
            "dry_run": dry_run,
            "error": str(last_error),
            "classify_attempts": classify_attempts,
            "model_used": model_used,
        }

    # Step 3: Parse and validate
    parsed = _parse_classification(raw_response)
    if not parsed:
        logger.warning("Failed to parse LLM classification for %s: %s", page_id[:8], raw_response[:200])
        return {
            "page_id": page_id,
            "classification": {},
            "raw_response": raw_response[:500],
            "fields_updated": [],
            "needs_review": True,
            "review_reason": "LLM response not valid JSON",
            "dry_run": dry_run,
        }

    classification = _validate_classification(parsed)
    logger.info(
        "Classification for %s: dominio=%s, tipo=%s, destino=%s",
        page_id[:8], classification["dominio"], classification["tipo"], classification["destino"],
    )

    # Step 4: Determine review status
    needs_review = False
    review_reason = ""

    missing_fields = []
    if not classification["dominio"]:
        missing_fields.append("dominio")
    if not classification["tipo"]:
        missing_fields.append("tipo")
    if not classification["destino"]:
        missing_fields.append("destino")
    if not classification["resumen"]:
        missing_fields.append("resumen")

    if missing_fields:
        needs_review = True
        review_reason = f"Classification incomplete: missing {', '.join(missing_fields)}"
    elif classification["destino"] in _V2_DESTINO_REVIEW_ONLY:
        needs_review = True
        review_reason = f"Destino '{classification['destino']}' is read-only — requires human review"

    # Step 5: Update raw page properties
    agent_status = "Revision requerida" if needs_review else "Procesada"
    agent_action = "Bloqueado por ambiguedad" if needs_review else "Resumen generado"

    if not dry_run:
        raw_schema = _page_schema_from_page(page_data)
        update_props: Dict[str, Any] = {}
        fields_updated: List[str] = []

        if classification["dominio"]:
            _set_schema_property(
                update_props, raw_schema,
                ["Dominio propuesto"],
                classification["dominio"],
                expected_types={"select", "status", "rich_text"},
                used_fields=fields_updated,
            )
        if classification["tipo"]:
            _set_schema_property(
                update_props, raw_schema,
                ["Tipo propuesto"],
                classification["tipo"],
                expected_types={"select", "status", "rich_text"},
                used_fields=fields_updated,
            )
        if classification["destino"]:
            _set_schema_property(
                update_props, raw_schema,
                ["Destino canonico", "Destino canónico"],
                classification["destino"],
                expected_types={"select", "status", "rich_text"},
                used_fields=fields_updated,
            )
        if classification["resumen"]:
            _set_schema_property(
                update_props, raw_schema,
                ["Resumen agente"],
                classification["resumen"],
                expected_types={"rich_text"},
                used_fields=fields_updated,
            )
        _set_schema_property(
            update_props, raw_schema,
            ["Estado agente"],
            agent_status,
            expected_types={"select", "status"},
            used_fields=fields_updated,
        )
        _set_schema_property(
            update_props, raw_schema,
            ["Accion agente", "Acción agente"],
            agent_action,
            expected_types={"select", "status"},
            used_fields=fields_updated,
        )

        if update_props:
            notion_client.update_page_properties(page_id, properties=update_props)
            logger.info("Updated %d V2 fields on raw page %s", len(fields_updated), page_id[:8])
    else:
        fields_updated = []

    return {
        "page_id": page_id,
        "title": title,
        "classification": classification,
        "fields_updated": fields_updated,
        "needs_review": needs_review,
        "review_reason": review_reason,
        "agent_status": agent_status,
        "agent_action": agent_action,
        "dry_run": dry_run,
        "classify_attempts": classify_attempts,
        "model_used": model_used,
    }


# ---------------------------------------------------------------------------
# granola.capitalize_raw
# ---------------------------------------------------------------------------

def handle_granola_capitalize_raw(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Capitalize an existing raw Granola page into stack-governed canonical objects.

    This handler is intentionally explicit:
    - reads the raw page for evidence and traceability
    - only writes to destinations requested in the payload
    - does not auto-promote into the human curated sessions DB yet

    V2 integration: if 'auto_classify' is true (default), runs classify_raw
    first to populate V2 fields before attempting capitalization.
    """
    transcript_page_id = (
        input_data.get("transcript_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")

    allow_legacy_raw_to_canonical = bool(input_data.get("allow_legacy_raw_to_canonical"))
    auto_classify = input_data.get("auto_classify", False)
    wants_project = bool((input_data.get("project_name") or "").strip())
    wants_deliverable = bool((input_data.get("deliverable_name") or "").strip())
    wants_bridge = bool((input_data.get("bridge_item_name") or "").strip())
    wants_followup = bool((input_data.get("followup_type") or "").strip())

    if allow_legacy_raw_to_canonical and not any((wants_project, wants_deliverable, wants_bridge, wants_followup)):
        raise ValueError(
            "At least one explicit destination is required: project_name, "
            "deliverable_name, bridge_item_name or followup_type"
        )

    page_snapshot = notion_client.read_page(transcript_page_id, max_blocks=80)
    page_data = notion_client.get_page(transcript_page_id)

    # V2: auto-classify the raw page before capitalization
    classification_result: Dict[str, Any] = {}
    _classify_failed = False
    if auto_classify and allow_legacy_raw_to_canonical:
        try:
            classification_result = handle_granola_classify_raw({
                "page_id": transcript_page_id,
                "dry_run": False,
                "model": input_data.get("classify_model") or "gemini_flash",
            })
            if classification_result.get("needs_review"):
                logger.info(
                    "Classification requires review for %s: %s",
                    transcript_page_id[:8],
                    classification_result.get("review_reason", ""),
                )
        except Exception as exc:
            logger.warning("Auto-classify failed for %s: %s", transcript_page_id[:8], exc)
            classification_result = {"error": str(exc)}

    # V2.1: detect classification unavailable (for return dict observability)
    _classify_failed = bool(
        auto_classify
        and allow_legacy_raw_to_canonical
        and classification_result.get("error")
        and not classification_result.get("classification")
    )
    if _classify_failed:
        logger.warning(
            "capitalize %s proceeding without classification "
            "(attempts=%s, model=%s, error=%s)",
            transcript_page_id[:8],
            classification_result.get("classify_attempts", "?"),
            classification_result.get("model_used", "?"),
            classification_result.get("error", "?"),
        )

    # V2.1: classification gates — block or skip based on destino
    if classification_result.get("classification"):
        gate = _classify_gate(
            classification_result,
            wants_project=wants_project,
            wants_deliverable=wants_deliverable,
            wants_bridge=wants_bridge,
            wants_followup=wants_followup,
        )
        if gate["action"] == "skip":
            logger.info(
                "Skipping capitalization for %s: %s",
                transcript_page_id[:8], gate["reason"],
            )
            return {
                "ok": False,
                "skipped_by_classification": True,
                "reason": gate["reason"],
                "transcript_page_id": transcript_page_id,
                "classification": classification_result,
                "results": {},
                "trace_comments_added": 0,
            }
        if gate["action"] == "block":
            page_title = (
                (page_snapshot.get("title") or "").strip()
                or _extract_title_from_page(page_data)
                or "Reunión"
            )
            page_url = (page_snapshot.get("url") or page_data.get("url") or "").strip()
            page_date = _extract_date_from_page(page_data) or _today_date()
            review_comment_added = _leave_review_comment(
                page_snapshot.get("page_id") or transcript_page_id,
                source_evidence=f"{page_title} ({page_date}) - {page_url or transcript_page_id}",
                intended_target=gate["reason"],
                blocking_ambiguity=gate["reason"],
                next_review="Revisar clasificación V2 y capitalizar manualmente si corresponde.",
            )
            logger.info(
                "Blocking capitalization for %s: %s",
                transcript_page_id[:8], gate["reason"],
            )
            return {
                "ok": False,
                "blocked_by_classification": True,
                "reason": gate["reason"],
                "transcript_page_id": transcript_page_id,
                "classification": classification_result,
                "review_comment_added": review_comment_added,
                "results": {},
                "trace_comments_added": 1 if review_comment_added else 0,
            }

    transcript_title = (
        (page_snapshot.get("title") or "").strip()
        or _extract_title_from_page(page_data)
        or "Reunión"
    )
    transcript_url = (page_snapshot.get("url") or page_data.get("url") or "").strip()
    transcript_date = (
        (input_data.get("date") or "").strip()
        or _extract_date_from_page(page_data)
        or _today_date()
    )
    transcript_source = (
        (input_data.get("source") or "").strip()
        or _extract_select_value(page_data, "Fuente", "Source")
        or "granola"
    )
    context_excerpt = _compact_excerpt(page_snapshot.get("plain_text") or "")

    if not allow_legacy_raw_to_canonical:
        destinations = []
        if wants_project:
            destinations.append(f"Proyecto: {(input_data.get('project_name') or '').strip()}")
        if wants_deliverable:
            destinations.append(f"Entregable: {(input_data.get('deliverable_name') or '').strip()}")
        if wants_bridge:
            destinations.append(f"Puente: {(input_data.get('bridge_item_name') or '').strip()}")
        if wants_followup:
            destinations.append(f"Follow-up: {(input_data.get('followup_type') or '').strip()}")
        intended_target = ", ".join(destinations) if destinations else "Por definir desde session_capitalizable"
        review_comment_added = _leave_review_comment(
            page_snapshot.get("page_id") or transcript_page_id,
            source_evidence=f"{transcript_title} ({transcript_date}) - {transcript_url or transcript_page_id}",
            intended_target=intended_target,
            blocking_ambiguity="V1 no permite raw -> canonical target.",
            next_review="Promover primero a session_capitalizable y decidir la capitalizacion desde esa capa.",
        )
        return {
            "ok": False,
            "blocked_by_policy": True,
            "policy": "raw_to_canonical_disabled_in_v1",
            "review_comment_added": review_comment_added,
            "transcript_page_id": page_snapshot.get("page_id") or transcript_page_id,
            "transcript_url": transcript_url,
            "title": transcript_title,
            "date": transcript_date,
            "source": transcript_source,
            "results": {},
            "trace_comments_added": 1 if review_comment_added else 0,
        }

    results: Dict[str, Any] = {}
    add_trace_comments = input_data.get("add_trace_comments", True)
    trace_comments_added = 0

    project_name = (input_data.get("project_name") or "").strip()
    if project_name:
        project_payload = {
            "name": project_name,
            "estado": input_data.get("project_estado"),
            "responsable": input_data.get("project_responsable"),
            "bloqueos": input_data.get("project_bloqueos"),
            "next_action": input_data.get("project_next_action"),
            "last_update_date": input_data.get("project_last_update_date") or transcript_date,
        }
        results["project"] = handle_notion_upsert_project(
            {k: v for k, v in project_payload.items() if v not in (None, "", [])}
        )

    deliverable_name = (input_data.get("deliverable_name") or "").strip()
    if deliverable_name:
        deliverable_notes = _append_context(
            str(input_data.get("deliverable_notes") or ""),
            f"Origen raw: {transcript_title} ({transcript_date}) - {transcript_url or transcript_page_id}",
        )
        if context_excerpt:
            deliverable_notes = _append_context(
                deliverable_notes,
                f"Contexto observado: {context_excerpt}",
            )
        deliverable_payload = {
            "name": deliverable_name,
            "project_name": (input_data.get("deliverable_project_name") or "").strip() or project_name or None,
            "deliverable_type": input_data.get("deliverable_type"),
            "review_status": input_data.get("deliverable_review_status"),
            "summary": input_data.get("deliverable_summary") or f"Derivado de reunion raw: {transcript_title}",
            "notes": deliverable_notes,
            "next_action": input_data.get("deliverable_next_action"),
            "date": input_data.get("deliverable_date") or transcript_date,
            "source_task_id": input_data.get("source_task_id"),
            "last_update_date": input_data.get("deliverable_last_update_date") or transcript_date,
        }
        results["deliverable"] = handle_notion_upsert_deliverable(
            {k: v for k, v in deliverable_payload.items() if v not in (None, "", [])}
        )

    bridge_name = (input_data.get("bridge_item_name") or "").strip()
    if bridge_name:
        bridge_notes = _append_context(
            str(input_data.get("bridge_notes") or ""),
            f"Origen raw: {transcript_title} ({transcript_date}) - {transcript_url or transcript_page_id}",
        )
        if context_excerpt:
            bridge_notes = _append_context(bridge_notes, f"Contexto observado: {context_excerpt}")
        bridge_payload = {
            "name": bridge_name,
            "status": input_data.get("bridge_status") or "Nuevo",
            "project_name": (input_data.get("bridge_project_name") or "").strip() or project_name or None,
            "priority": input_data.get("bridge_priority") or "Media",
            "source": input_data.get("bridge_source") or "Rick",
            "notes": bridge_notes,
            "next_action": input_data.get("bridge_next_action")
            or "Revisar esta reunion raw y ubicarla en un contenedor canonico.",
            "last_move_date": input_data.get("bridge_last_move_date") or transcript_date,
            "link": input_data.get("bridge_link") or transcript_url or transcript_page_id,
        }
        results["bridge_item"] = handle_notion_upsert_bridge_item(
            {k: v for k, v in bridge_payload.items() if v not in (None, "", [])}
        )

    followup_type = (input_data.get("followup_type") or "").strip()
    if followup_type:
        followup_payload = {
            "transcript_page_id": transcript_page_id,
            "followup_type": followup_type,
            "title": input_data.get("followup_title") or transcript_title,
            "date": input_data.get("followup_date") or transcript_date,
            "notes": input_data.get("followup_notes"),
            "due_date": input_data.get("followup_due_date"),
            "attendees": input_data.get("followup_attendees") or [],
            "action_items": input_data.get("followup_action_items") or [],
            "start": input_data.get("followup_start"),
            "end": input_data.get("followup_end"),
            "timezone": input_data.get("followup_timezone"),
        }
        results["followup"] = handle_granola_create_followup(
            {k: v for k, v in followup_payload.items() if v not in (None, "", [])}
        )

    if add_trace_comments:
        destinations = []
        if project_name:
            destinations.append(f"Proyecto: {project_name}")
        if deliverable_name:
            destinations.append(f"Entregable: {deliverable_name}")
        if bridge_name:
            destinations.append(f"Puente: {bridge_name}")
        if followup_type:
            destinations.append(f"Follow-up: {followup_type}")

        raw_comment = (
            f"Capitalizacion Rick registrada para '{transcript_title}' ({transcript_date}). "
            f"Destino(s): {', '.join(destinations)}."
        )
        if _comment_safe(page_snapshot.get("page_id"), raw_comment):
            trace_comments_added += 1

        target_comment = (
            f"Origen raw Granola: '{transcript_title}' ({transcript_date}). "
            f"Ref: {transcript_url or transcript_page_id}"
        )
        for key in ("project", "deliverable", "bridge_item"):
            target_page_id = _result_page_id(results.get(key))
            if _comment_safe(target_page_id, target_comment):
                trace_comments_added += 1

    result: Dict[str, Any] = {
        "transcript_page_id": page_snapshot.get("page_id") or transcript_page_id,
        "transcript_url": transcript_url,
        "title": transcript_title,
        "date": transcript_date,
        "source": transcript_source,
        "results": results,
        "trace_comments_added": trace_comments_added,
        "classification": classification_result,
    }
    if _classify_failed:
        result["classification_unavailable"] = True
        result["classification_error"] = str(classification_result.get("error", ""))
        result["classification_attempts"] = classification_result.get("classify_attempts", 0)
        result["classification_model_used"] = classification_result.get("model_used", "")
    return result


def handle_granola_promote_curated_session(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Promote an existing raw Granola page into the human curated sessions DB.

    This handler stays conservative by:
    - requiring NOTION_CURATED_SESSIONS_DB_ID
    - reading the raw page as evidence first
    - only populating fields supported by the live curated DB schema
    - only setting relations passed explicitly in the payload
    """
    transcript_page_id = (
        input_data.get("transcript_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")
    session_capitalizable_db_id = config.require_notion_session_capitalizable_db_id()

    page_snapshot = notion_client.read_page(transcript_page_id, max_blocks=80)
    page_data = notion_client.get_page(transcript_page_id)

    transcript_title = (
        (page_snapshot.get("title") or "").strip()
        or _extract_title_from_page(page_data)
        or "Sesión"
    )
    transcript_url = (page_snapshot.get("url") or page_data.get("url") or "").strip()
    transcript_date = (
        (input_data.get("date") or "").strip()
        or _extract_date_from_page(page_data)
        or _today_date()
    )
    transcript_source = (
        (input_data.get("source") or "").strip()
        or _extract_select_value(page_data, "Fuente", "Source")
        or "granola"
    )
    context_excerpt = _compact_excerpt(page_snapshot.get("plain_text") or "")

    session_name = (
        (input_data.get("session_name") or "").strip()
        or (input_data.get("title") or "").strip()
        or transcript_title
    )
    session_summary = (
        (input_data.get("summary") or "").strip()
        or (input_data.get("session_summary") or "").strip()
    )
    session_notes = (
        (input_data.get("notes") or "").strip()
        or (input_data.get("session_notes") or "").strip()
    )
    if not session_notes:
        session_notes = f"Origen raw: {transcript_title} ({transcript_date}) - {transcript_url or transcript_page_id}"
        if context_excerpt:
            session_notes = _append_context(
                session_notes,
                f"Contexto observado: {context_excerpt}",
            )

    db_snapshot = notion_client.read_database(
        session_capitalizable_db_id,
        max_items=100,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read curated sessions DB schema")

    title_prop = _schema_property_name(schema, ["Nombre", "Name", "Title"], {"title"})
    if not title_prop:
        raise RuntimeError("Curated sessions DB does not expose a title property")

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        [title_prop],
        session_name,
        expected_types={"title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha", "Date", "Meeting Date"],
        transcript_date,
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Dominio", "Domain"],
        input_data.get("domain") or input_data.get("session_domain"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        input_data.get("session_type") or input_data.get("type"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        input_data.get("estado") or input_data.get("status"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Origen", "Fuente", "Source"],
        input_data.get("origin") or input_data.get("session_origin") or transcript_source,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        input_data.get("source_url") or transcript_url or transcript_page_id,
        expected_types={"url", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Resumen", "Summary"],
        session_summary,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Notas", "Notes"],
        session_notes,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Transcripción disponible", "Transcripcion disponible", "Transcript available"],
        input_data.get("transcript_available", True),
        expected_types={"checkbox"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Proyecto", "Project"],
        input_data.get("project_page_id"),
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Programa", "Program"],
        input_data.get("program_page_id"),
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Recurso relacionado", "Recurso", "Resource related", "Resource"],
        input_data.get("resource_page_id") or input_data.get("resource_page_ids"),
        expected_types={"relation"},
        used_fields=used_fields,
    )

    source_prop = _schema_property_name(
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        {"url", "rich_text"},
    )
    existing_candidates: list[Dict[str, Any]] = []
    match_strategy = ""

    if source_prop and transcript_url:
        source_prop_type = schema.get(source_prop)
        source_filter: Dict[str, Any] | None = None
        if source_prop_type == "url":
            source_filter = {"property": source_prop, "url": {"equals": transcript_url}}
        elif source_prop_type == "rich_text":
            source_filter = {"property": source_prop, "rich_text": {"equals": transcript_url}}
        if source_filter:
            existing_candidates = notion_client.query_database(
                database_id=session_capitalizable_db_id,
                filter=source_filter,
            )

    existing_match, match_strategy = _pick_best_existing_curated_session(
        existing_candidates,
        session_name=session_name,
        transcript_date=transcript_date,
        transcript_url=transcript_url,
        source_prop=source_prop,
    )

    if not existing_match:
        exact_title_candidates = notion_client.query_database(
            database_id=session_capitalizable_db_id,
            filter={"property": title_prop, "title": {"equals": session_name}},
        )
        existing_match, match_strategy = _pick_best_existing_curated_session(
            exact_title_candidates,
            session_name=session_name,
            transcript_date=transcript_date,
            transcript_url=transcript_url,
            source_prop=source_prop,
        )

    if not existing_match:
        snapshot_candidates: list[Dict[str, Any]] = []
        for item in db_snapshot.get("items") or []:
            title_value = str(item.get("title") or "").strip()
            date_value = _extract_date_start((item.get("properties") or {}).get("Fecha"))
            source_value = (
                str((item.get("properties") or {}).get(source_prop) or "").strip()
                if source_prop
                else ""
            )

            snapshot_properties: Dict[str, Any] = {
                title_prop: {"type": "title", "title": [{"plain_text": title_value}]},
            }
            if date_value:
                snapshot_properties["Fecha"] = {"type": "date", "date": {"start": date_value}}
            if source_prop and source_value:
                source_prop_type = schema.get(source_prop)
                if source_prop_type == "url":
                    snapshot_properties[source_prop] = {"type": "url", "url": source_value}
                elif source_prop_type == "rich_text":
                    snapshot_properties[source_prop] = {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": source_value}],
                    }

            snapshot_candidates.append(
                {
                    "id": item.get("page_id"),
                    "url": item.get("url"),
                    "properties": snapshot_properties,
                }
            )

        existing_match, match_strategy = _pick_best_existing_curated_session(
            snapshot_candidates,
            session_name=session_name,
            transcript_date=transcript_date,
            transcript_url=transcript_url,
            source_prop=source_prop,
        )

    matched_existing = bool(existing_match)
    resolved_session_name = session_name
    if matched_existing:
        existing_title = _extract_title_from_page(existing_match)
        same_normalized_title = bool(
            existing_title
            and _normalize_lookup_text(existing_title) == _normalize_lookup_text(session_name)
        )
        if (
            existing_title
            and existing_title != session_name
            and (
                ("?" in session_name and match_strategy == "source_url")
                or (
                    same_normalized_title
                    and ("?" in session_name or match_strategy in {"source_url", "normalized_title_date"})
                )
            )
        ):
            resolved_session_name = existing_title
            properties[title_prop] = {
                "title": [{"text": {"content": resolved_session_name[:2000]}}]
            }

    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": existing_match["id"] if matched_existing else "",
            "url": existing_match.get("url", "") if matched_existing else "",
            "created": not matched_existing,
            "updated": matched_existing,
            "dry_run": True,
            "properties": properties,
        }
    elif matched_existing:
        notion_result = notion_client.update_page_properties(
            existing_match["id"],
            properties=properties,
        )
        notion_result["created"] = False
    else:
        notion_result = notion_client.create_database_page(
            session_capitalizable_db_id,
            properties=properties,
        )

    curated_identity_sync = _sync_visible_notion_page_id(
        _result_page_id(notion_result) or notion_result.get("page_id", ""),
        schema,
        dry_run=dry_run,
    )
    notion_result["notion_page_id_sync"] = curated_identity_sync
    for field_name in curated_identity_sync.get("schema_fields_used") or []:
        if field_name not in used_fields:
            used_fields.append(field_name)

    raw_status_update: Dict[str, Any]
    try:
        raw_status_update = _sync_raw_promotion_state(
            page_snapshot.get("page_id") or transcript_page_id,
            page_data,
            curated_url=str(notion_result.get("url") or "").strip(),
            dry_run=dry_run,
        )
    except Exception as exc:
        logger.warning(
            "Failed to sync raw Granola state for %s after curated promotion: %s",
            transcript_page_id,
            exc,
        )
        raw_status_update = {
            "ok": False,
            "page_id": page_snapshot.get("page_id") or transcript_page_id,
            "dry_run": dry_run,
            "error": str(exc),
        }

    trace_comments_added = 0
    add_trace_comments = input_data.get("add_trace_comments", True)
    curated_page_id = _result_page_id(notion_result) or notion_result.get("page_id", "")
    if add_trace_comments and not dry_run:
        raw_comment = (
            f"Promocion a capa curada registrada para '{resolved_session_name}' ({transcript_date}). "
            f"Sesion curada: {curated_page_id or 'creada/actualizada'}."
        )
        if _comment_safe(page_snapshot.get("page_id"), raw_comment):
            trace_comments_added += 1

        curated_comment = (
            f"Origen raw Granola: '{transcript_title}' ({transcript_date}). "
            f"Ref: {transcript_url or transcript_page_id}"
        )
        if _comment_safe(curated_page_id, curated_comment):
            trace_comments_added += 1

    return {
        "transcript_page_id": page_snapshot.get("page_id") or transcript_page_id,
        "transcript_url": transcript_url,
        "title": transcript_title,
        "session_name": resolved_session_name,
        "date": transcript_date,
        "source": transcript_source,
        "curated_session": notion_result,
        "raw_status_update": raw_status_update,
        "matched_existing": matched_existing,
        "match_strategy": match_strategy if matched_existing else "",
        "dry_run": dry_run,
        "trace_comments_added": trace_comments_added,
        "schema_fields_used": used_fields,
    }


# ---------------------------------------------------------------------------
# granola.create_human_task_from_curated_session
# ---------------------------------------------------------------------------

def handle_granola_create_human_task_from_curated_session(
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create or update a human task in the personal tasks DB from a curated session page.

    This slice remains conservative:
    - requires NOTION_HUMAN_TASKS_DB_ID
    - reads the curated session page as evidence first
    - requires an explicit task_name/title
    - only populates fields supported by the live human tasks schema
    - only sets explicit or directly inherited relations
    """
    curated_session_page_id = (
        input_data.get("curated_session_page_id")
        or input_data.get("session_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not curated_session_page_id:
        raise ValueError("'curated_session_page_id' is required in input")
    if not config.NOTION_HUMAN_TASKS_DB_ID:
        raise RuntimeError("NOTION_HUMAN_TASKS_DB_ID not configured")

    task_name = (
        (input_data.get("task_name") or "").strip()
        or (input_data.get("title") or "").strip()
    )
    if not task_name:
        raise ValueError("'task_name' is required in input")

    session_snapshot = notion_client.read_page(curated_session_page_id, max_blocks=80)
    session_page = notion_client.get_page(curated_session_page_id)

    session_title = (
        (session_snapshot.get("title") or "").strip()
        or _extract_title_from_page(session_page)
        or "Sesion curada"
    )
    session_url = (session_snapshot.get("url") or session_page.get("url") or "").strip()
    session_date = (
        (input_data.get("session_date") or "").strip()
        or _extract_date_from_page(session_page)
        or _today_date()
    )
    session_domain = (
        (input_data.get("domain") or "").strip()
        or (input_data.get("task_domain") or "").strip()
        or _extract_select_value(session_page, "Dominio", "Domain")
    )
    session_excerpt = _compact_excerpt(session_snapshot.get("plain_text") or "")

    project_relation_ids = _relation_ids(input_data.get("project_page_id"))
    if not project_relation_ids:
        project_relation_ids = _extract_relation_values(session_page, "Proyecto", "Project")

    task_notes = (
        (input_data.get("notes") or "").strip()
        or (input_data.get("task_notes") or "").strip()
    )
    if not task_notes:
        task_notes = (
            f"Derivada de sesion curada: {session_title} ({session_date}) - "
            f"{session_url or curated_session_page_id}"
        )
        if session_excerpt:
            task_notes = _append_context(
                task_notes,
                f"Contexto observado: {session_excerpt}",
            )

    db_snapshot = notion_client.read_database(
        config.NOTION_HUMAN_TASKS_DB_ID,
        max_items=1,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read human tasks DB schema")

    title_prop = _schema_property_name(schema, ["Nombre", "Name", "Title"], {"title"})
    if not title_prop:
        raise RuntimeError("Human tasks DB does not expose a title property")

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        [title_prop],
        task_name,
        expected_types={"title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Dominio", "Domain"],
        session_domain,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Proyecto", "Project"],
        project_relation_ids,
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Sesion relacionada", "Sesión relacionada", "Session related", "Related session"],
        curated_session_page_id,
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        input_data.get("task_type") or input_data.get("type") or "Follow-up",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        input_data.get("estado") or input_data.get("status") or "Pendiente",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Prioridad", "Priority"],
        input_data.get("priority") or input_data.get("prioridad"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha objetivo", "Due date", "Target date"],
        input_data.get("due_date") or input_data.get("target_date"),
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Origen", "Source"],
        input_data.get("origin") or input_data.get("task_origin") or "Sesión",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        input_data.get("source_url") or session_url or curated_session_page_id,
        expected_types={"url", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Notas", "Notes"],
        task_notes,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )

    existing = notion_client.query_database(
        database_id=config.NOTION_HUMAN_TASKS_DB_ID,
        filter={"property": title_prop, "title": {"equals": task_name}},
    )
    matched_existing = bool(existing)
    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": existing[0]["id"] if matched_existing else "",
            "url": existing[0].get("url", "") if matched_existing else "",
            "created": not matched_existing,
            "updated": matched_existing,
            "dry_run": True,
            "properties": properties,
        }
    elif matched_existing:
        notion_result = notion_client.update_page_properties(
            existing[0]["id"],
            properties=properties,
        )
        notion_result["created"] = False
    else:
        notion_result = notion_client.create_database_page(
            config.NOTION_HUMAN_TASKS_DB_ID,
            properties=properties,
        )

    task_identity_sync = _sync_visible_notion_page_id(
        _result_page_id(notion_result) or notion_result.get("page_id", ""),
        schema,
        dry_run=dry_run,
    )
    notion_result["notion_page_id_sync"] = task_identity_sync
    for field_name in task_identity_sync.get("schema_fields_used") or []:
        if field_name not in used_fields:
            used_fields.append(field_name)

    trace_comments_added = 0
    add_trace_comments = input_data.get("add_trace_comments", True)
    human_task_page_id = _result_page_id(notion_result) or notion_result.get("page_id", "")
    if add_trace_comments and not dry_run:
        session_comment = (
            f"Tarea humana registrada desde sesion curada: '{task_name}'. "
            f"Tarea: {human_task_page_id or 'creada/actualizada'}."
        )
        if _comment_safe(session_snapshot.get("page_id"), session_comment):
            trace_comments_added += 1

        task_comment = (
            f"Origen sesion curada: '{session_title}' ({session_date}). "
            f"Ref: {session_url or curated_session_page_id}"
        )
        if _comment_safe(human_task_page_id, task_comment):
            trace_comments_added += 1

    return {
        "curated_session_page_id": session_snapshot.get("page_id") or curated_session_page_id,
        "curated_session_url": session_url,
        "session_title": session_title,
        "task_name": task_name,
        "date": session_date,
        "human_task": notion_result,
        "matched_existing": matched_existing,
        "dry_run": dry_run,
        "trace_comments_added": trace_comments_added,
        "schema_fields_used": used_fields,
    }


# ---------------------------------------------------------------------------
# granola.update_commercial_project_from_curated_session
# ---------------------------------------------------------------------------

def handle_granola_update_commercial_project_from_curated_session(
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update the human commercial projects DB from a curated session.

    This slice stays narrow:
    - requires NOTION_COMMERCIAL_PROJECTS_DB_ID
    - reads the curated session as evidence first
    - requires an explicit project target or a project relation on the session
    - only updates supported commercial fields present in the live schema
    - leaves traceability through comments rather than freeform page content
    """
    curated_session_page_id = (
        input_data.get("curated_session_page_id")
        or input_data.get("session_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not curated_session_page_id:
        raise ValueError("'curated_session_page_id' is required in input")
    if not config.NOTION_COMMERCIAL_PROJECTS_DB_ID:
        raise RuntimeError("NOTION_COMMERCIAL_PROJECTS_DB_ID not configured")

    session_snapshot = notion_client.read_page(curated_session_page_id, max_blocks=80)
    session_page = notion_client.get_page(curated_session_page_id)

    session_title = (
        (session_snapshot.get("title") or "").strip()
        or _extract_title_from_page(session_page)
        or "Sesion curada"
    )
    session_url = (session_snapshot.get("url") or session_page.get("url") or "").strip()
    session_date = (
        (input_data.get("session_date") or "").strip()
        or _extract_date_from_page(session_page)
        or _today_date()
    )
    session_excerpt = _compact_excerpt(session_snapshot.get("plain_text") or "")

    project_page_id = (
        (input_data.get("project_page_id") or "").strip()
        or (_extract_relation_values(session_page, "Proyecto", "Project") or [""])[0]
    )
    if not project_page_id:
        review_comment_added = _leave_review_comment(
            session_snapshot.get("page_id") or curated_session_page_id,
            source_evidence=f"{session_title} ({session_date}) - {session_url or curated_session_page_id}",
            intended_target="Proyecto comercial canonico",
            blocking_ambiguity="No project target verified on the capitalizable session.",
            next_review="Relacionar la sesion con el proyecto correcto o pasar project_page_id verificado.",
        )
        return {
            "ok": False,
            "blocked_by_ambiguity": True,
            "review_comment_added": review_comment_added,
            "curated_session_page_id": session_snapshot.get("page_id") or curated_session_page_id,
            "curated_session_url": session_url,
            "session_title": session_title,
            "date": session_date,
            "trace_comments_added": 1 if review_comment_added else 0,
        }

    update_fields = {
        "Estado": input_data.get("estado") or input_data.get("project_estado"),
        "Acción Requerida": input_data.get("accion_requerida") or input_data.get("project_next_action"),
        "Fecha": input_data.get("fecha") or input_data.get("project_date"),
        "Plazo": input_data.get("plazo") or input_data.get("project_deadline"),
        "Monto": input_data.get("monto") or input_data.get("project_amount"),
        "Tipo": input_data.get("tipo") or input_data.get("project_type"),
        "Cliente": input_data.get("cliente") or input_data.get("project_client"),
    }
    if all(value in (None, "", []) for value in update_fields.values()):
        raise ValueError(
            "At least one explicit commercial field is required: estado, accion_requerida, fecha, plazo, monto, tipo or cliente"
        )

    db_snapshot = notion_client.read_database(
        config.NOTION_COMMERCIAL_PROJECTS_DB_ID,
        max_items=1,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read commercial projects DB schema")

    project_page = notion_client.get_page(project_page_id)
    project_title = _extract_title_from_page(project_page) or "Proyecto comercial"

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        update_fields["Estado"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Acción Requerida", "Accion Requerida", "Next Action"],
        update_fields["Acción Requerida"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha", "Date"],
        update_fields["Fecha"],
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Plazo", "Deadline"],
        update_fields["Plazo"],
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Monto", "Amount"],
        update_fields["Monto"],
        expected_types={"number"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        update_fields["Tipo"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Cliente", "Client"],
        update_fields["Cliente"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )

    if not properties:
        raise RuntimeError("No supported commercial project fields were available to update")

    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": project_page_id,
            "url": project_page.get("url", ""),
            "updated": True,
            "dry_run": True,
            "properties": properties,
        }
    else:
        notion_result = notion_client.update_page_properties(
            project_page_id,
            properties=properties,
        )

    trace_comments_added = 0
    add_trace_comments = input_data.get("add_trace_comments", True)
    if add_trace_comments and not dry_run:
        project_comment_parts = [
            f"Actualizacion comercial desde sesion curada: '{session_title}' ({session_date}).",
        ]
        if update_fields["Estado"]:
            project_comment_parts.append(f"Estado -> {update_fields['Estado']}.")
        if update_fields["Acción Requerida"]:
            project_comment_parts.append(f"Accion requerida -> {update_fields['Acción Requerida']}.")
        if session_excerpt:
            project_comment_parts.append(f"Contexto: {session_excerpt}")
        if _comment_safe(project_page_id, " ".join(project_comment_parts)):
            trace_comments_added += 1

        session_comment = (
            f"Proyecto comercial actualizado: '{project_title}'. "
            f"Ref: {project_page.get('url') or project_page_id}"
        )
        if _comment_safe(session_snapshot.get("page_id"), session_comment):
            trace_comments_added += 1

    return {
        "curated_session_page_id": session_snapshot.get("page_id") or curated_session_page_id,
        "curated_session_url": session_url,
        "session_title": session_title,
        "project_page_id": project_page_id,
        "project_title": project_title,
        "commercial_project": notion_result,
        "dry_run": dry_run,
        "trace_comments_added": trace_comments_added,
        "schema_fields_used": used_fields,
    }


# ---------------------------------------------------------------------------
# granola.promote_operational_slice
# ---------------------------------------------------------------------------

def handle_granola_promote_operational_slice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose explicit human-facing slices from a raw Granola page.

    This orchestrator does not invent classification. It only chains the already
    conservative handlers when the caller supplies explicit sub-payloads.
    """
    transcript_page_id = (
        input_data.get("transcript_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")

    curated_payload = dict(input_data.get("curated_payload") or {})
    human_task_payload = dict(input_data.get("human_task_payload") or {})
    commercial_project_payload = dict(input_data.get("commercial_project_payload") or {})
    dry_run = bool(input_data.get("dry_run"))

    if not curated_payload:
        raise ValueError("'curated_payload' is required")
    if not human_task_payload and not commercial_project_payload:
        raise ValueError("At least one destination payload is required: human_task_payload or commercial_project_payload")

    curated_payload["transcript_page_id"] = transcript_page_id
    if dry_run and "dry_run" not in curated_payload:
        curated_payload["dry_run"] = True
    curated_result = handle_granola_promote_curated_session(curated_payload)
    curated_page_id = _result_page_id(curated_result.get("curated_session")) or ""
    if not curated_page_id and dry_run:
        curated_page_id = (curated_payload.get("curated_session_page_id") or "").strip()
    results: Dict[str, Any] = {"curated": curated_result}
    if not curated_page_id and dry_run:
        skip_reason = "curated_session_page_id_unavailable_in_dry_run_for_new_session"
        if human_task_payload:
            results["human_task"] = {
                "dry_run": True,
                "skipped": True,
                "reason": skip_reason,
            }
        if commercial_project_payload:
            results["commercial_project"] = {
                "dry_run": True,
                "skipped": True,
                "reason": skip_reason,
            }
        return {
            "transcript_page_id": transcript_page_id,
            "curated_session_page_id": "",
            "dry_run": True,
            "results": results,
        }
    if not curated_page_id:
        raise RuntimeError("Could not resolve curated session page id from promote_curated_session result")
    if human_task_payload:
        human_task_payload["curated_session_page_id"] = curated_page_id
        if dry_run and "dry_run" not in human_task_payload:
            human_task_payload["dry_run"] = True
        results["human_task"] = handle_granola_create_human_task_from_curated_session(human_task_payload)
    if commercial_project_payload:
        commercial_project_payload["curated_session_page_id"] = curated_page_id
        if dry_run and "dry_run" not in commercial_project_payload:
            commercial_project_payload["dry_run"] = True
        results["commercial_project"] = handle_granola_update_commercial_project_from_curated_session(commercial_project_payload)

    return {
        "transcript_page_id": transcript_page_id,
        "curated_session_page_id": curated_page_id,
        "dry_run": dry_run,
        "results": results,
    }


# ---------------------------------------------------------------------------
# granola.create_followup
# ---------------------------------------------------------------------------

FOLLOWUP_TYPES = {"reminder", "email_draft", "proposal", "calendar_event"}

PROPOSAL_TEMPLATE = """# Propuesta de Seguimiento

## Reunión: {title}
**Fecha:** {date}
**Participantes:** {attendees}

## Resumen de Compromisos

{action_items_text}

## Próximos Pasos Sugeridos

{next_steps}

---
*Generado automáticamente por Rick a partir de la transcripción de Granola.*
"""

EMAIL_TEMPLATE = """Asunto: Seguimiento — {title} ({date})

Estimado/a equipo,

Gracias por la reunión del {date}. A continuación los puntos clave y compromisos acordados:

{action_items_text}

Quedo atento a sus comentarios.

Saludos cordiales,
David

---
*Borrador generado por Rick a partir de la transcripción de Granola.*
"""


def handle_granola_create_followup(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Follow-up proactivo sobre una transcripción de Granola.

    Input:
        transcript_page_id (str, required): ID de la página de la transcripción en Notion.
        followup_type (str, required): "reminder" | "email_draft" | "proposal".
        title (str, optional): Título de la reunión (para templates).
        date (str, optional): Fecha de la reunión.
        attendees (list[str], optional): Participantes.
        action_items (list[dict], optional): [{text, assignee, due}].
        due_date (str, optional): Fecha límite para reminders (default: +7 días).
        notes (str, optional): Notas adicionales para el follow-up.

    Returns:
        followup_type (str): Tipo de follow-up creado.
        result (dict): Resultado dependiente del tipo.
    """
    transcript_page_id = input_data.get("transcript_page_id", "").strip()
    followup_type = input_data.get("followup_type", "").strip().lower()

    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")
    if followup_type not in FOLLOWUP_TYPES:
        raise ValueError(
            f"'followup_type' must be one of: {', '.join(sorted(FOLLOWUP_TYPES))}"
        )

    title = input_data.get("title", "Reunión")
    date = input_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    attendees = input_data.get("attendees", [])
    action_items = input_data.get("action_items", [])
    notes = input_data.get("notes", "")

    attendees_str = ", ".join(attendees) if attendees else "No especificados"
    action_items_text = "\n".join(
        f"- {item.get('text', '?')} ({item.get('assignee', '?')}, {item.get('due', 'sin fecha')})"
        for item in action_items
    ) if action_items else "- Sin compromisos registrados"

    if followup_type == "reminder":
        return _create_reminder(input_data, title, date, attendees_str, action_items_text, transcript_page_id)
    elif followup_type == "email_draft":
        return _create_email_draft(title, date, action_items_text, notes, transcript_page_id, attendees)
    elif followup_type == "proposal":
        return _create_proposal(title, date, attendees_str, action_items_text, notes, transcript_page_id)
    elif followup_type == "calendar_event":
        return _create_calendar_event(input_data, title, date, attendees, transcript_page_id)

    raise ValueError(f"Unhandled followup_type: {followup_type}")


def _create_reminder(
    input_data: Dict[str, Any],
    title: str,
    date: str,
    attendees_str: str,
    action_items_text: str,
    transcript_page_id: str,
) -> Dict[str, Any]:
    """Create a Notion task as a reminder."""
    due_date = input_data.get("due_date", "")
    if not due_date:
        from datetime import timedelta
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    task_id = str(uuid.uuid4())
    try:
        result = notion_client.upsert_task(
            task_id=task_id,
            status="queued",
            team="david",
            task=f"[Follow-up] {title} — revisar compromisos",
            input_summary=(
                f"Reunión: {title} ({date}). "
                f"Participantes: {attendees_str}. "
                f"Vence: {due_date}. "
                f"Ref: {transcript_page_id}"
            ),
        )
    except Exception as e:
        logger.error("Failed to create reminder task: %s", e)
        result = {"error": str(e)}

    return {
        "followup_type": "reminder",
        "result": {
            "task_id": task_id,
            "due_date": due_date,
            "notion_result": result,
        },
    }


def _create_email_draft(
    title: str,
    date: str,
    action_items_text: str,
    notes: str,
    transcript_page_id: str,
    attendees: List[str] | None = None,
) -> Dict[str, Any]:
    """Generate an email draft from the meeting transcript.

    If GOOGLE_GMAIL_TOKEN is configured and attendees are provided,
    a real Gmail draft is also created via the gmail.create_draft handler.
    """
    draft = EMAIL_TEMPLATE.format(
        title=title,
        date=date,
        action_items_text=action_items_text,
    )
    if notes:
        draft += f"\nNotas adicionales:\n{notes}\n"

    # Save draft as comment on the transcript page
    try:
        notion_client.add_comment(
            page_id=transcript_page_id,
            text=f"📧 Borrador de email generado:\n\n{draft[:1800]}",
        )
        posted = True
    except Exception as e:
        logger.warning("Failed to post email draft to Notion: %s", e)
        posted = False

    email_draft_result = None
    if attendees:
        try:
            from .gmail import handle_gmail_create_draft

            to_addr = attendees[0] if "@" in attendees[0] else ""
            cc_addrs = [a for a in attendees[1:] if "@" in a]
            if to_addr:
                email_draft_result = handle_gmail_create_draft({
                    "to": to_addr,
                    "subject": f"Seguimiento — {title} ({date})",
                    "body": draft,
                    "body_type": "plain",
                    "cc": cc_addrs,
                })
                logger.info("Gmail draft created: %s", email_draft_result)
        except Exception as e:
            logger.warning("Failed to create Gmail draft: %s", e)
            email_draft_result = {"ok": False, "error": str(e)}

    return {
        "followup_type": "email_draft",
        "result": {
            "draft": draft,
            "posted_to_notion": posted,
            "transcript_page_id": transcript_page_id,
            "email_draft": email_draft_result,
        },
    }


def _create_calendar_event(
    input_data: Dict[str, Any],
    title: str,
    date: str,
    attendees: List[str],
    transcript_page_id: str,
) -> Dict[str, Any]:
    """Create a Google Calendar event from the meeting follow-up."""
    from .google_calendar import handle_google_calendar_create_event

    start = input_data.get("start", f"{date}T10:00:00")
    end = input_data.get("end", "")
    tz = input_data.get("timezone", "America/Santiago")
    description = input_data.get("notes", f"Follow-up de reunión: {title}")

    attendee_emails = [a for a in attendees if "@" in a]

    try:
        cal_result = handle_google_calendar_create_event({
            "title": f"Follow-up: {title}",
            "description": description,
            "start": start,
            "end": end,
            "timezone": tz,
            "attendees": attendee_emails,
        })
        logger.info("Calendar event created: %s", cal_result)
    except Exception as e:
        logger.warning("Failed to create calendar event: %s", e)
        cal_result = {"ok": False, "error": str(e)}

    return {
        "followup_type": "calendar_event",
        "result": {
            "calendar_event": cal_result,
            "transcript_page_id": transcript_page_id,
        },
    }


def _create_proposal(
    title: str,
    date: str,
    attendees_str: str,
    action_items_text: str,
    notes: str,
    transcript_page_id: str,
) -> Dict[str, Any]:
    """Generate a proposal document from the meeting transcript."""
    next_steps = notes if notes else (
        "1. Revisar y validar los compromisos con el equipo.\n"
        "2. Agendar reunión de seguimiento.\n"
        "3. Preparar entregables pendientes."
    )

    proposal = PROPOSAL_TEMPLATE.format(
        title=title,
        date=date,
        attendees=attendees_str,
        action_items_text=action_items_text,
        next_steps=next_steps,
    )

    # Create as report page in Notion
    try:
        content_blocks = markdown_to_blocks(proposal)
        result = notion_client.create_report_page(
            parent_page_id=transcript_page_id,
            title=f"Propuesta: {title}",
            content_blocks=content_blocks,
            metadata={
                "type": "proposal",
                "meeting_date": date,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        return {
            "followup_type": "proposal",
            "result": result,
        }
    except Exception as e:
        logger.error("Failed to create proposal page: %s", e)
        return {
            "followup_type": "proposal",
            "result": {
                "proposal_text": proposal,
                "error": str(e),
                "transcript_page_id": transcript_page_id,
            },
        }
