"""
Granola cache exporter.

Reads Granola's local cache (`cache-v6.json`), extracts exportable meeting
documents, renders structured Markdown compatible with `granola_watcher.py`,
and writes one `.md` file per meeting into `GRANOLA_EXPORT_DIR`.

This is the first ingestion leg only:

    cache-v6.json -> structured .md -> granola_watcher.py -> Worker

Modes:
    python granola_cache_exporter.py             # Poll cache continuously
    python granola_cache_exporter.py --once      # Export pending items and exit
    python granola_cache_exporter.py --once --dry-run --limit 3
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.vm.granola_watcher_env_loader import load_env

DEFAULT_ENV_FILE = r"C:\Granola\.env"
DEFAULT_LOG_FILE = r"C:\Granola\cache_exporter.log"
DEFAULT_POLL_INTERVAL = 30
DEFAULT_SUPABASE_PATH = os.path.join(os.environ.get("APPDATA", ""), "Granola", "supabase.json")
MANIFEST_VERSION = 1
MIN_CONTENT_LENGTH = 20

_ENV_PATH = os.environ.get("GRANOLA_ENV_FILE", DEFAULT_ENV_FILE)
load_env(_ENV_PATH)


@dataclass
class ExportCandidate:
    document_id: str
    title: str
    meeting_date: str
    attendees: list[str]
    notes_markdown: str
    transcript_markdown: str
    action_items: list[str]
    created_at: str
    updated_at: str
    filename: str
    content_hash: str
    signature: str
    metadata: dict[str, str]

    @property
    def has_content(self) -> bool:
        notes = self.notes_markdown.strip()
        transcript = self.transcript_markdown.strip()
        action_items = bool(self.action_items)
        return bool(notes or transcript or action_items)

    def build_markdown(self) -> str:
        lines: list[str] = [f"# {self.title}", ""]

        lines.append(f"**Date:** {self.meeting_date}")
        if self.attendees:
            lines.append(f"**Attendees:** {', '.join(self.attendees)}")
        lines.append("**Source:** granola_cache_v6")
        lines.append(f"**Granola Document ID:** {self.document_id}")
        lines.append(f"**Updated At:** {self.updated_at or self.created_at or 'unknown'}")
        lines.append("")

        if self.notes_markdown.strip():
            lines.append("## Notes")
            lines.append("")
            lines.append(self.notes_markdown.strip())
            lines.append("")

        if self.transcript_markdown.strip():
            lines.append("## Transcript")
            lines.append("")
            lines.append(self.transcript_markdown.strip())
            lines.append("")

        if self.action_items:
            lines.append("## Action Items")
            lines.append("")
            lines.extend(self.action_items)
            lines.append("")

        lines.append("## Metadata")
        lines.append("")
        for key, value in self.metadata.items():
            lines.append(f"- **{key}:** {value}")

        return "\n".join(lines).rstrip() + "\n"


class GranolaPrivateApiClient:
    """Best-effort client for Granola's local authenticated API surface."""

    def __init__(self, access_token: str, default_workspace_id: str = "") -> None:
        self.access_token = access_token
        self.default_workspace_id = default_workspace_id.strip()
        self._panels_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._transcript_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}

    @classmethod
    def from_local_state(
        cls,
        supabase_path: Path,
        *,
        default_workspace_id: str = "",
    ) -> "GranolaPrivateApiClient":
        payload = json.loads(supabase_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Granola supabase.json payload is not a JSON object")
        workos_tokens = payload.get("workos_tokens")
        if not isinstance(workos_tokens, str) or not workos_tokens.strip():
            raise ValueError("Granola supabase.json does not contain workos_tokens")
        tokens = json.loads(workos_tokens)
        access_token = _ensure_text(tokens.get("access_token"))
        if not access_token:
            raise ValueError("Granola supabase.json does not contain access_token")
        return cls(access_token, default_workspace_id=default_workspace_id)

    def _headers(self, workspace_id: str = "") -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "X-Client-Version": "granola-cache-exporter",
        }
        effective_workspace_id = workspace_id.strip() or self.default_workspace_id
        if effective_workspace_id:
            headers["X-Granola-Workspace-Id"] = effective_workspace_id
        return headers

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        workspace_id: str = "",
    ) -> Any:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(workspace_id),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8", errors="replace"))

    def fetch_panels(
        self,
        document_id: str,
        *,
        workspace_id: str = "",
    ) -> list[dict[str, Any]]:
        cache_key = (workspace_id or self.default_workspace_id, document_id)
        if cache_key in self._panels_cache:
            return self._panels_cache[cache_key]
        panels = self._post_json(
            "https://api.granola.ai/v1/get-document-panels",
            {"document_id": document_id},
            workspace_id=workspace_id,
        )
        normalized = [panel for panel in panels if isinstance(panel, dict)] if isinstance(panels, list) else []
        self._panels_cache[cache_key] = normalized
        return normalized

    def fetch_transcript_segments(
        self,
        document_id: str,
        *,
        workspace_id: str = "",
    ) -> list[dict[str, Any]]:
        cache_key = (workspace_id or self.default_workspace_id, document_id)
        if cache_key in self._transcript_cache:
            return self._transcript_cache[cache_key]
        transcript = self._post_json(
            "https://api.granola.ai/v1/get-document-transcript",
            {"document_id": document_id},
            workspace_id=workspace_id,
        )
        normalized = [segment for segment in transcript if isinstance(segment, dict)] if isinstance(transcript, list) else []
        self._transcript_cache[cache_key] = normalized
        return normalized


def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("granola_cache_exporter")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(fmt)
    logger.addHandler(stdout_handler)

    log_file = os.environ.get("GRANOLA_EXPORTER_LOG_FILE", DEFAULT_LOG_FILE)
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        logger.debug("Could not open exporter log file %s; using stdout only", log_file)

    return logger


logger = _setup_logging()


def _env(key: str, *fallback_keys: str, default: str = "") -> str:
    value = os.environ.get(key, "")
    if value:
        return value
    for fallback in fallback_keys:
        value = os.environ.get(fallback, "")
        if value:
            return value
    return default


def _get_poll_interval(raw: str | None = None) -> int:
    value = raw or os.environ.get("GRANOLA_CACHE_POLL_INTERVAL", "")
    if not value:
        return DEFAULT_POLL_INTERVAL
    try:
        return max(1, int(value))
    except ValueError:
        return DEFAULT_POLL_INTERVAL


def _slugify(value: str, *, max_length: int = 80) -> str:
    normalized = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    normalized = re.sub(r"[-\s]+", "-", normalized)
    normalized = normalized.strip("-")
    return (normalized or "meeting")[:max_length].rstrip("-")


def _sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_datetime(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _as_iso_date(value: str | None) -> str:
    dt = _parse_datetime(value)
    if dt:
        return dt.strftime("%Y-%m-%d")
    raw = (value or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return ""


def _ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _iter_documents(documents: Any) -> list[dict[str, Any]]:
    if isinstance(documents, dict):
        values = [value for value in documents.values() if isinstance(value, dict)]
    elif isinstance(documents, list):
        values = [value for value in documents if isinstance(value, dict)]
    else:
        raise ValueError("cache.state.documents must be a dict or list")

    def sort_key(doc: dict[str, Any]) -> str:
        return str(doc.get("updated_at") or doc.get("created_at") or "")

    return sorted(values, key=sort_key, reverse=True)


def _load_cache_state(cache_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = cache_path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    state = payload.get("cache", {}).get("state", {})
    documents = _iter_documents(state.get("documents"))
    transcripts = state.get("transcripts") or {}
    if not isinstance(transcripts, dict):
        transcripts = {}
    return documents, transcripts


def _truthy_env(value: str) -> bool:
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _build_default_private_api_client() -> GranolaPrivateApiClient | None:
    if not _truthy_env(os.environ.get("GRANOLA_ENABLE_PRIVATE_API_HYDRATION", "1")):
        return None

    supabase_path = Path(
        _env("GRANOLA_SUPABASE_PATH", default=DEFAULT_SUPABASE_PATH)
    )
    if not supabase_path.is_file():
        return None

    default_workspace_id = _env("GRANOLA_WORKSPACE_ID")
    try:
        client = GranolaPrivateApiClient.from_local_state(
            supabase_path,
            default_workspace_id=default_workspace_id,
        )
        logger.info(
            "Granola private API hydration enabled via %s",
            supabase_path,
        )
        return client
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "Granola private API hydration unavailable (%s): %s",
            supabase_path,
            exc,
        )
        return None


def _name_from_person(person: Any) -> str:
    if isinstance(person, str):
        return person.strip()
    if not isinstance(person, dict):
        return ""

    direct_name = _ensure_text(person.get("name"))
    if direct_name:
        return direct_name

    email = _ensure_text(person.get("email"))
    if email:
        return email

    details = person.get("details")
    if isinstance(details, dict):
        person_details = details.get("person")
        if isinstance(person_details, dict):
            name_info = person_details.get("name")
            if isinstance(name_info, dict):
                full_name = _ensure_text(name_info.get("fullName"))
                if full_name:
                    return full_name

    return ""


def _extract_attendees(doc: dict[str, Any]) -> list[str]:
    attendees: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        normalized = name.strip()
        if not normalized:
            return
        dedup_key = normalized.casefold()
        if dedup_key in seen:
            return
        seen.add(dedup_key)
        attendees.append(normalized)

    people = doc.get("people") or {}
    if isinstance(people, dict):
        creator = people.get("creator")
        add(_name_from_person(creator))

        for attendee in people.get("attendees") or []:
            add(_name_from_person(attendee))

    gcal = doc.get("google_calendar_event") or {}
    if isinstance(gcal, dict):
        organizer = gcal.get("organizer")
        if isinstance(organizer, dict):
            add(_ensure_text(organizer.get("displayName")) or _ensure_text(organizer.get("email")))
        creator = gcal.get("creator")
        if isinstance(creator, dict):
            add(_ensure_text(creator.get("displayName")) or _ensure_text(creator.get("email")))
        for attendee in gcal.get("attendees") or []:
            if isinstance(attendee, dict):
                add(_ensure_text(attendee.get("displayName")) or _ensure_text(attendee.get("email")))

    return attendees


def _extract_meeting_date(doc: dict[str, Any]) -> str:
    gcal = doc.get("google_calendar_event") or {}
    if isinstance(gcal, dict):
        start = gcal.get("start") or {}
        if isinstance(start, dict):
            for key in ("dateTime", "date"):
                parsed = _as_iso_date(start.get(key))
                if parsed:
                    return parsed

    for key in ("updated_at", "created_at"):
        parsed = _as_iso_date(doc.get(key))
        if parsed:
            return parsed

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _speaker_label(source: str, attendees: list[str]) -> str:
    normalized = source.strip().lower()
    if normalized == "microphone":
        return attendees[0] if attendees else "Host"
    if normalized == "system":
        return "Interlocutor"
    if normalized:
        return normalized
    return "Speaker"


def _group_transcript_segments(
    segments: list[dict[str, Any]], attendees: list[str]
) -> list[tuple[str, str, str]]:
    grouped: list[tuple[str, str, str]] = []
    final_segments = [segment for segment in segments if segment.get("is_final", True)]
    source_segments = final_segments or segments

    current_speaker = ""
    current_timestamp = ""
    current_parts: list[str] = []

    def flush() -> None:
        nonlocal current_speaker, current_timestamp, current_parts
        text = " ".join(part.strip() for part in current_parts if part.strip()).strip()
        if text:
            grouped.append((current_speaker or "Speaker", current_timestamp, text))
        current_speaker = ""
        current_timestamp = ""
        current_parts = []

    for segment in source_segments:
        text = _ensure_text(segment.get("text"))
        if not text:
            continue
        speaker = _speaker_label(_ensure_text(segment.get("source")), attendees)
        timestamp_raw = _ensure_text(segment.get("start_timestamp"))
        timestamp = timestamp_raw[11:19] if len(timestamp_raw) >= 19 else ""
        if current_speaker and speaker != current_speaker:
            flush()
        if not current_speaker:
            current_speaker = speaker
            current_timestamp = timestamp
        current_parts.append(text)

    flush()
    return grouped


def render_transcript_markdown(
    segments: Any, attendees: list[str]
) -> str:
    if not isinstance(segments, list):
        return ""

    grouped = _group_transcript_segments(
        [segment for segment in segments if isinstance(segment, dict)],
        attendees,
    )
    if not grouped:
        return ""

    lines: list[str] = []
    for speaker, timestamp, text in grouped:
        prefix = f"[{timestamp}] " if timestamp else ""
        lines.append(f"- **{speaker}:** {prefix}{text}")
    return "\n".join(lines).strip()


def _render_marks(text: str, marks: list[dict[str, Any]] | None) -> str:
    rendered = text
    for mark in marks or []:
        if not isinstance(mark, dict):
            continue
        mark_type = mark.get("type")
        attrs = mark.get("attrs") or {}
        if mark_type == "bold":
            rendered = f"**{rendered}**"
        elif mark_type == "italic":
            rendered = f"*{rendered}*"
        elif mark_type == "strike":
            rendered = f"~~{rendered}~~"
        elif mark_type == "code":
            rendered = f"`{rendered}`"
        elif mark_type == "link":
            href = _ensure_text(attrs.get("href"))
            if href:
                rendered = f"[{rendered}]({href})"
    return rendered


def _render_inline(node: Any) -> str:
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type")
    if node_type == "text":
        return _render_marks(_ensure_text(node.get("text")), node.get("marks"))
    if node_type == "hardBreak":
        return "\n"

    content = node.get("content") or []
    if isinstance(content, list):
        return "".join(_render_inline(child) for child in content)
    return ""


def _render_block(node: Any, depth: int = 0) -> list[str]:
    if not isinstance(node, dict):
        return []

    node_type = node.get("type")
    content = node.get("content") or []

    if node_type == "paragraph":
        text = "".join(_render_inline(child) for child in content).strip()
        return [text] if text else []

    if node_type == "heading":
        attrs = node.get("attrs") or {}
        level = int(attrs.get("level", 1))
        level = max(3, min(level + 2, 6))
        text = "".join(_render_inline(child) for child in content).strip()
        return [f"{'#' * level} {text}"] if text else []

    if node_type in {"bulletList", "orderedList"}:
        lines: list[str] = []
        ordered = node_type == "orderedList"
        for index, child in enumerate(content, start=1):
            lines.extend(_render_list_item(child, ordered=ordered, index=index, depth=depth))
        return lines

    if node_type == "blockquote":
        lines: list[str] = []
        for child in content:
            for line in _render_block(child, depth=depth):
                lines.append(f"> {line}" if line else ">")
        return lines

    if node_type == "codeBlock":
        code = "\n".join(_render_inline(child) for child in content).strip("\n")
        if not code:
            return []
        return ["```", code, "```"]

    if node_type == "horizontalRule":
        return ["---"]

    if node_type == "doc":
        lines: list[str] = []
        for child in content:
            block_lines = _render_block(child, depth=depth)
            if block_lines:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.extend(block_lines)
        while lines and lines[-1] == "":
            lines.pop()
        return lines

    lines: list[str] = []
    for child in content:
        lines.extend(_render_block(child, depth=depth))
    return lines


def _render_list_item(
    node: Any, *, ordered: bool, index: int, depth: int
) -> list[str]:
    if not isinstance(node, dict):
        return []

    bullet = f"{index}." if ordered else "-"
    indent = "  " * depth
    lines: list[str] = []
    nested: list[str] = []

    for child in node.get("content") or []:
        child_type = child.get("type") if isinstance(child, dict) else ""
        if child_type == "paragraph":
            text = "".join(_render_inline(grand) for grand in child.get("content") or []).strip()
            if text:
                lines.append(f"{indent}{bullet} {text}")
        elif child_type in {"bulletList", "orderedList"}:
            nested.extend(_render_block(child, depth=depth + 1))
        else:
            nested.extend(_render_block(child, depth=depth + 1))

    if not lines and nested:
        return nested
    return lines + nested


def render_prosemirror_markdown(node: Any) -> str:
    lines = _render_block(node)
    return "\n".join(lines).strip()


def render_panels_markdown(panels: Any) -> str:
    if not isinstance(panels, list):
        return ""

    sections: list[str] = []
    seen_sections: set[str] = set()
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        content = panel.get("content")
        rendered = render_prosemirror_markdown(content)
        if not rendered:
            continue
        title = _ensure_text(panel.get("title")) or "Panel"
        section = f"### {title}\n\n{rendered}".strip()
        dedupe_key = _sha1_text(section)
        if dedupe_key in seen_sections:
            continue
        seen_sections.add(dedupe_key)
        sections.append(section)

    return "\n\n".join(sections).strip()


def _split_action_items(markdown_body: str) -> tuple[str, list[str]]:
    if not markdown_body.strip():
        return "", []

    lines = markdown_body.splitlines()
    cleaned_notes: list[str] = []
    action_items: list[str] = []
    in_action_items = False

    for line in lines:
        stripped = line.strip()
        heading_match = re.match(r"^#{1,6}\s+(.+)$", stripped)
        if heading_match:
            heading_text = heading_match.group(1).strip().lower()
            if any(
                token in heading_text
                for token in ("action item", "compromiso", "tarea", "to-do", "todo")
            ):
                in_action_items = True
                continue
            if in_action_items:
                in_action_items = False

        if in_action_items:
            checklist_match = re.match(r"^[-*]\s*(\[[ xX]\]\s*.+)$", stripped)
            if checklist_match:
                action_items.append(f"- {checklist_match.group(1).strip()}")
                continue
            item_match = re.match(r"^[-*]\s*(.+)$", stripped)
            if item_match:
                text = item_match.group(1).strip()
                if text:
                    action_items.append(f"- [ ] {text}")
            continue

        cleaned_notes.append(line)

    cleaned = "\n".join(cleaned_notes).strip()
    return cleaned, action_items


def _extract_notes_markdown(doc: dict[str, Any]) -> str:
    for field in ("notes_markdown", "notes_plain", "summary", "overview"):
        value = _ensure_text(doc.get(field))
        if value:
            return value

    notes = doc.get("notes")
    if isinstance(notes, dict):
        rendered = render_prosemirror_markdown(notes)
        if rendered:
            return rendered

    return ""


def _hydrate_notes_markdown(
    doc: dict[str, Any],
    api_client: GranolaPrivateApiClient | None,
) -> tuple[str, str]:
    notes_markdown = _extract_notes_markdown(doc)
    if notes_markdown.strip():
        return notes_markdown, "cache"
    if api_client is None:
        return "", "none"

    document_id = _ensure_text(doc.get("id"))
    workspace_id = _ensure_text(doc.get("workspace_id"))
    try:
        panels = api_client.fetch_panels(document_id, workspace_id=workspace_id)
    except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        logger.warning(
            "Granola panel hydration failed for %s: %s",
            document_id,
            exc,
        )
        return "", "none"

    rendered = render_panels_markdown(panels)
    if rendered:
        logger.info("Hydrated Granola panels for %s via private API", document_id)
        return rendered, "private_api_panels"
    return "", "none"


def _hydrate_transcript_markdown(
    doc: dict[str, Any],
    transcripts: dict[str, Any],
    attendees: list[str],
    api_client: GranolaPrivateApiClient | None,
) -> tuple[str, str]:
    document_id = _ensure_text(doc.get("id"))
    transcript_markdown = render_transcript_markdown(
        transcripts.get(document_id),
        attendees,
    )
    if transcript_markdown.strip():
        return transcript_markdown, "cache"
    if api_client is None:
        return "", "none"

    workspace_id = _ensure_text(doc.get("workspace_id"))
    try:
        segments = api_client.fetch_transcript_segments(
            document_id,
            workspace_id=workspace_id,
        )
    except urllib.error.HTTPError as exc:
        if exc.code not in {400, 403, 404}:
            logger.warning(
                "Granola transcript hydration failed for %s: %s",
                document_id,
                exc,
            )
        return "", "none"
    except (RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.warning(
            "Granola transcript hydration failed for %s: %s",
            document_id,
            exc,
        )
        return "", "none"

    rendered = render_transcript_markdown(segments, attendees)
    if rendered:
        logger.info("Hydrated Granola transcript for %s via private API", document_id)
        return rendered, "private_api_transcript"
    return "", "none"


def _build_filename(title: str, meeting_date: str, document_id: str) -> str:
    prefix = meeting_date or "undated"
    slug = _slugify(title)
    short_id = document_id.split("-")[0]
    return f"{prefix}-{slug}-{short_id}.md"


def _build_candidate(
    doc: dict[str, Any],
    transcripts: dict[str, Any],
    api_client: GranolaPrivateApiClient | None = None,
) -> ExportCandidate | None:
    document_id = _ensure_text(doc.get("id"))
    if not document_id:
        return None
    if _ensure_text(doc.get("type")) not in {"", "meeting"}:
        return None
    if doc.get("deleted_at") or doc.get("was_trashed"):
        return None
    if doc.get("valid_meeting") is False:
        return None

    title = _ensure_text(doc.get("title")) or f"Granola {document_id[:8]}"
    meeting_date = _extract_meeting_date(doc)
    attendees = _extract_attendees(doc)
    notes_markdown, notes_source = _hydrate_notes_markdown(doc, api_client)
    notes_markdown, action_items = _split_action_items(notes_markdown)
    transcript_markdown, transcript_source = _hydrate_transcript_markdown(
        doc,
        transcripts,
        attendees,
        api_client,
    )

    content_parts = [
        title,
        meeting_date,
        notes_markdown,
        transcript_markdown,
        "\n".join(action_items),
    ]
    combined_content = "\n".join(part for part in content_parts if part).strip()
    content_hash = _sha1_text(combined_content)
    if len(combined_content) < MIN_CONTENT_LENGTH and not action_items:
        return None

    updated_at = _ensure_text(doc.get("updated_at"))
    created_at = _ensure_text(doc.get("created_at"))
    signature = _sha1_text(
        "|".join(
            [
                document_id,
                title,
                meeting_date,
                updated_at,
                created_at,
                content_hash,
            ]
        )
    )
    metadata = {
        "granola_document_id": document_id,
        "created_at": created_at or "unknown",
        "updated_at": updated_at or created_at or "unknown",
        "content_hash": content_hash,
        "has_notes": str(bool(notes_markdown.strip())).lower(),
        "has_transcript": str(bool(transcript_markdown.strip())).lower(),
        "notes_source": notes_source,
        "transcript_source": transcript_source,
        "export_signature": signature,
    }

    meeting_url = _ensure_text((doc.get("people") or {}).get("url"))
    if not meeting_url:
        gcal = doc.get("google_calendar_event") or {}
        if isinstance(gcal, dict):
            meeting_url = _ensure_text(gcal.get("htmlLink"))
    if meeting_url:
        metadata["source_url"] = meeting_url

    return ExportCandidate(
        document_id=document_id,
        title=title,
        meeting_date=meeting_date,
        attendees=attendees,
        notes_markdown=notes_markdown,
        transcript_markdown=transcript_markdown,
        action_items=action_items,
        created_at=created_at,
        updated_at=updated_at,
        filename=_build_filename(title, meeting_date, document_id),
        content_hash=content_hash,
        signature=signature,
        metadata=metadata,
    )


def _classify_candidate(
    doc: dict[str, Any],
    transcripts: dict[str, Any],
    api_client: GranolaPrivateApiClient | None = None,
) -> tuple[ExportCandidate | None, str | None]:
    document_id = _ensure_text(doc.get("id"))
    if not document_id:
        return None, "missing_document_id"
    if _ensure_text(doc.get("type")) not in {"", "meeting"}:
        return None, "wrong_type"
    if doc.get("deleted_at") or doc.get("was_trashed"):
        return None, "trashed_or_deleted"
    if doc.get("valid_meeting") is False:
        return None, "invalid_meeting"

    candidate = _build_candidate(doc, transcripts, api_client)
    if candidate is None:
        return None, "content_too_short"
    if not candidate.has_content:
        return None, "metadata_only"
    return candidate, None


def _read_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {"version": MANIFEST_VERSION, "documents": {}}
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Manifest unreadable, rebuilding: %s", manifest_path)
        return {"version": MANIFEST_VERSION, "documents": {}}
    if not isinstance(raw, dict):
        return {"version": MANIFEST_VERSION, "documents": {}}
    raw.setdefault("version", MANIFEST_VERSION)
    raw.setdefault("documents", {})
    if not isinstance(raw["documents"], dict):
        raw["documents"] = {}
    return raw


def _write_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(tmp_path, manifest_path)


def _file_already_accounted_for(
    export_dir: Path, processed_dir: Path, filename: str
) -> bool:
    return (export_dir / filename).exists() or (processed_dir / filename).exists()


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def export_cache_once(
    *,
    cache_path: Path,
    export_dir: Path,
    processed_dir: Path,
    manifest_path: Path,
    dry_run: bool = False,
    force: bool = False,
    limit: int | None = None,
    document_ids: set[str] | None = None,
    api_client: GranolaPrivateApiClient | None = None,
    enable_private_api_hydration: bool = True,
) -> dict[str, Any]:
    documents, transcripts = _load_cache_state(cache_path)
    effective_api_client = None
    if enable_private_api_hydration:
        effective_api_client = (
            api_client if api_client is not None else _build_default_private_api_client()
        )
    manifest = _read_manifest(manifest_path)
    doc_manifest = manifest.setdefault("documents", {})

    exported: list[dict[str, Any]] = []
    skipped_unchanged = 0
    skipped_unusable = 0
    skipped_reason_counts: dict[str, int] = {}

    for doc in documents:
        document_id = _ensure_text(doc.get("id"))
        if document_ids and document_id not in document_ids:
            continue

        candidate, skip_reason = _classify_candidate(
            doc,
            transcripts,
            effective_api_client,
        )
        if candidate is None:
            skipped_unusable += 1
            if skip_reason:
                skipped_reason_counts[skip_reason] = skipped_reason_counts.get(skip_reason, 0) + 1
            continue

        existing = doc_manifest.get(candidate.document_id, {})
        existing_signature = _ensure_text(existing.get("signature"))
        existing_filename = _ensure_text(existing.get("filename")) or candidate.filename

        if (
            not force
            and existing_signature == candidate.signature
            and _file_already_accounted_for(export_dir, processed_dir, existing_filename)
        ):
            skipped_unchanged += 1
            logger.info(
                "Skipping unchanged document %s (%s)",
                candidate.document_id,
                candidate.title,
            )
            continue

        markdown = candidate.build_markdown()
        export_path = export_dir / candidate.filename
        if dry_run:
            logger.info(
                "Dry run: would export %s -> %s",
                candidate.title,
                export_path,
            )
        else:
            _write_text_atomic(export_path, markdown)
            logger.info("Exported %s -> %s", candidate.title, export_path)

        doc_manifest[candidate.document_id] = {
            "title": candidate.title,
            "filename": candidate.filename,
            "meeting_date": candidate.meeting_date,
            "updated_at": candidate.updated_at or candidate.created_at,
            "content_hash": candidate.content_hash,
            "signature": candidate.signature,
            "exported_at": _iso_now(),
            "has_notes": bool(candidate.notes_markdown.strip()),
            "has_transcript": bool(candidate.transcript_markdown.strip()),
            "notes_source": candidate.metadata.get("notes_source", "none"),
            "transcript_source": candidate.metadata.get("transcript_source", "none"),
        }
        exported.append(
            {
                "document_id": candidate.document_id,
                "title": candidate.title,
                "filename": candidate.filename,
                "meeting_date": candidate.meeting_date,
                "has_notes": bool(candidate.notes_markdown.strip()),
                "has_transcript": bool(candidate.transcript_markdown.strip()),
                "notes_source": candidate.metadata.get("notes_source", "none"),
                "transcript_source": candidate.metadata.get("transcript_source", "none"),
                "content_hash": candidate.content_hash,
            }
        )

        if limit is not None and len(exported) >= limit:
            break

    manifest["version"] = MANIFEST_VERSION
    manifest["cache_path"] = str(cache_path)
    manifest["updated_at"] = _iso_now()

    if not dry_run:
        _write_manifest(manifest_path, manifest)

    summary = {
        "scanned": len(documents),
        "exported_count": len(exported),
        "skipped_unchanged": skipped_unchanged,
        "skipped_unusable": skipped_unusable,
        "skipped_reason_counts": skipped_reason_counts,
        "dry_run": dry_run,
        "exports": exported,
    }
    logger.info(
        "Exporter summary: scanned=%d exported=%d skipped_unchanged=%d skipped_unusable=%d dry_run=%s reasons=%s",
        summary["scanned"],
        summary["exported_count"],
        summary["skipped_unchanged"],
        summary["skipped_unusable"],
        summary["dry_run"],
        skipped_reason_counts or {},
    )
    if exported == [] and skipped_reason_counts.get("metadata_only"):
        logger.warning(
            "Granola cache documents look metadata-only: notes/transcripts are not materialized in cache-v6.json for %d documents",
            skipped_reason_counts["metadata_only"],
        )
    return summary


def run_once(args: argparse.Namespace) -> int:
    cache_path = Path(args.cache_path)
    export_dir = Path(args.export_dir)
    processed_dir = Path(args.processed_dir)
    manifest_path = Path(args.manifest_path)

    if not cache_path.is_file():
        logger.error("Granola cache file not found: %s", cache_path)
        return 1
    if not export_dir.is_dir() and not args.dry_run:
        export_dir.mkdir(parents=True, exist_ok=True)

    document_ids = set(args.document_id or [])
    try:
        summary = export_cache_once(
            cache_path=cache_path,
            export_dir=export_dir,
            processed_dir=processed_dir,
            manifest_path=manifest_path,
            dry_run=args.dry_run,
            force=args.force,
            limit=args.limit,
            document_ids=document_ids or None,
            enable_private_api_hydration=not args.no_private_api_hydration,
        )
    except json.JSONDecodeError as exc:
        logger.error("Granola cache is not valid JSON: %s", exc)
        return 1
    except ValueError as exc:
        logger.error("Granola cache structure not recognized: %s", exc)
        return 1
    except OSError as exc:
        logger.error("Granola exporter I/O failure: %s", exc)
        return 1

    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def run_polling(args: argparse.Namespace) -> int:
    interval = _get_poll_interval(str(args.poll_interval) if args.poll_interval else None)
    logger.info(
        "Polling mode: cache=%s export_dir=%s every %ds",
        args.cache_path,
        args.export_dir,
        interval,
    )
    while True:
        exit_code = run_once(args)
        if exit_code != 0:
            logger.warning("Exporter iteration failed; retrying in %ds", interval)
        time.sleep(interval)


def build_arg_parser() -> argparse.ArgumentParser:
    default_cache_path = os.path.join(os.environ.get("APPDATA", ""), "Granola", "cache-v6.json")
    default_export_dir = _env("GRANOLA_EXPORT_DIR")
    default_processed_dir = _env(
        "GRANOLA_PROCESSED_DIR",
        default=str(Path(default_export_dir) / "processed") if default_export_dir else "",
    )
    default_manifest_path = (
        str(Path(default_export_dir) / ".granola-cache-export-manifest.json")
        if default_export_dir
        else ""
    )

    parser = argparse.ArgumentParser(description="Export Granola cache into watcher-compatible Markdown")
    parser.add_argument("--once", action="store_true", help="Export pending items and exit")
    parser.add_argument("--dry-run", action="store_true", help="Preview exports without writing files")
    parser.add_argument("--force", action="store_true", help="Ignore manifest signatures and re-export")
    parser.add_argument("--limit", type=int, help="Export at most N meetings this run")
    parser.add_argument(
        "--document-id",
        action="append",
        help="Export only this Granola document id (repeatable)",
    )
    parser.add_argument(
        "--cache-path",
        default=_env("GRANOLA_CACHE_PATH", default=default_cache_path),
        help="Path to cache-v6.json",
    )
    parser.add_argument(
        "--export-dir",
        default=default_export_dir,
        help="Destination directory for .md exports",
    )
    parser.add_argument(
        "--processed-dir",
        default=default_processed_dir,
        help="Processed directory used by the watcher",
    )
    parser.add_argument(
        "--manifest-path",
        default=_env("GRANOLA_EXPORT_MANIFEST", default=default_manifest_path),
        help="Path to the exporter manifest JSON",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        help="Seconds between cache scans in polling mode",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the run summary as JSON",
    )
    parser.add_argument(
        "--no-private-api-hydration",
        action="store_true",
        help="Disable Granola private API hydration and use cache-v6.json only",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    if not args.export_dir:
        logger.error("GRANOLA_EXPORT_DIR or --export-dir is required")
        return 1
    if not args.processed_dir:
        logger.error("GRANOLA_PROCESSED_DIR or --processed-dir is required")
        return 1
    if not args.manifest_path:
        logger.error("--manifest-path could not be derived; provide it explicitly")
        return 1

    if args.once or args.dry_run:
        return run_once(args)
    return run_polling(args)


if __name__ == "__main__":
    raise SystemExit(main())
