#!/usr/bin/env python3
"""Stage 2 ingest: fan-out de canales por referente via RSSHub localhost + RSS directo.

Read-only contra Notion (mismo patrón que `scripts/smoke/referentes_rest_read.py`).
Escribe SQLite local (`~/.cache/rick-discovery/state.sqlite`) y reporte JSON en `reports/`.

NO escribe a Notion. NO toca el container RSSHub. NO loggea NOTION_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
import yaml

REGISTRY_KEY = "referencias_referentes"
NOTION_BASE_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_API_VERSION = "2025-09-03"

CHANNEL_RSS = "rss"
CHANNEL_YOUTUBE = "youtube"
CHANNEL_WEB_RSS = "web_rss"
CHANNEL_LINKEDIN = "linkedin"
CHANNEL_OTROS = "otros"

RSS_FEED_SUFFIXES = ("/feed", "/rss", ".xml", ".atom", "/feed/", "/rss/")
TRACKING_PARAM_PREFIXES = ("utm_",)
TRACKING_PARAM_EXACT = {"fbclid", "gclid", "ref"}

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS discovered_items (
  url_canonica       TEXT PRIMARY KEY,
  referente_id       TEXT NOT NULL,
  referente_nombre   TEXT NOT NULL,
  canal              TEXT NOT NULL,
  titulo             TEXT,
  publicado_en       TEXT,
  primera_vez_visto  TEXT NOT NULL,
  promovido_a_candidato_at TEXT,
  contenido_html        TEXT,
  contenido_extraido_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_discovered_referente ON discovered_items(referente_id, canal);
CREATE TABLE IF NOT EXISTS fetch_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  referente_id  TEXT NOT NULL,
  canal         TEXT NOT NULL,
  fetched_at    TEXT NOT NULL,
  status        TEXT NOT NULL,
  items_found   INTEGER DEFAULT 0,
  error         TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetch_log_recent ON fetch_log(referente_id, canal, fetched_at);
"""


class IngestSetupError(RuntimeError):
    """Raised when prerequisites (RSSHub, env, registry) are missing."""


# ---------- URL normalization ----------

def canonicalize_url(url: str) -> str:
    """Normalize URL for dedup.

    - Lowercase scheme + host.
    - Strip query params with tracking prefixes/keys.
    - Strip trailing slash from path (except root '/').
    - Strip fragment.
    - YouTube: youtu.be/ID  ->  https://www.youtube.com/watch?v=ID.
    """
    if not url:
        return ""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or ""

    if netloc == "youtu.be" and path.strip("/"):
        video_id = path.strip("/").split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    if netloc in {"youtube.com", "m.youtube.com", "www.youtube.com"} and path == "/watch":
        qs = dict(parse_qsl(parsed.query, keep_blank_values=False))
        v = qs.get("v")
        if v:
            return f"https://www.youtube.com/watch?v={v}"

    cleaned_query = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if not _is_tracking_param(k)
    ]
    query = urlencode(cleaned_query)

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def _is_tracking_param(key: str) -> bool:
    k = key.lower()
    if k in TRACKING_PARAM_EXACT:
        return True
    return any(k.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES)


# ---------- YouTube parsing ----------

_YT_CHANNEL_RE = re.compile(r"^/channel/(UC[\w-]+)/?")
_YT_USER_RE = re.compile(r"^/user/([\w.-]+)/?")
_YT_C_RE = re.compile(r"^/c/([\w.-]+)/?")
_YT_HANDLE_RE = re.compile(r"^/@([\w.-]+)/?")


def parse_youtube_channel_id(url: str) -> tuple[str, str] | None:
    """Return (id_or_name, kind) for a YouTube channel URL.

    Kinds: 'channel' (UC...), 'c' (custom URL), 'user' (legacy), 'handle' (@name).
    Returns None for unknown shapes and non-YouTube URLs.
    """
    if not url:
        return None
    parsed = urlparse(url.strip())
    if parsed.netloc.lower() not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        return None
    path = parsed.path or "/"
    if m := _YT_CHANNEL_RE.match(path):
        return (m.group(1), "channel")
    if m := _YT_C_RE.match(path):
        return (m.group(1), "c")
    if m := _YT_USER_RE.match(path):
        return (m.group(1), "user")
    if m := _YT_HANDLE_RE.match(path):
        return (m.group(1), "handle")
    return None


def youtube_rsshub_path(channel_id: str, kind: str) -> str:
    if kind == "channel":
        return f"/youtube/channel/{channel_id}"
    if kind == "c":
        return f"/youtube/c/{channel_id}"
    if kind == "user":
        return f"/youtube/user/{channel_id}"
    if kind == "handle":
        return f"/youtube/user/@{channel_id}"
    raise ValueError(f"unknown youtube kind: {kind}")


# ---------- skip-if-recent ----------

def should_skip_recent(
    last_fetched_at: str | None,
    threshold_minutes: int,
    *,
    now: datetime | None = None,
) -> bool:
    """Return True if last_fetched_at is within threshold_minutes of `now`."""
    if not last_fetched_at or threshold_minutes <= 0:
        return False
    try:
        prev = datetime.fromisoformat(last_fetched_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if prev.tzinfo is None:
        prev = prev.replace(tzinfo=timezone.utc)
    cur = now or datetime.now(timezone.utc)
    delta_min = (cur - prev).total_seconds() / 60.0
    return delta_min < threshold_minutes


# ---------- SQLite ----------

def init_sqlite(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_DDL)
    # Idempotent migrations for pre-existing DBs (013-F).
    cols = {row[1] for row in conn.execute("PRAGMA table_info(discovered_items)")}
    if "contenido_html" not in cols:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN contenido_html TEXT")
    if "contenido_extraido_at" not in cols:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN contenido_extraido_at TEXT")
    if "notion_page_id" not in cols:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN notion_page_id TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_discovered_notion_page "
            "ON discovered_items(notion_page_id)"
        )
    conn.commit()
    return conn


def get_last_fetch_ok(conn: sqlite3.Connection, referente_id: str, canal: str) -> str | None:
    cur = conn.execute(
        "SELECT fetched_at FROM fetch_log WHERE referente_id=? AND canal=? AND status='ok' "
        "ORDER BY fetched_at DESC LIMIT 1",
        (referente_id, canal),
    )
    row = cur.fetchone()
    return row[0] if row else None


def record_fetch(
    conn: sqlite3.Connection,
    *,
    referente_id: str,
    canal: str,
    status: str,
    items_found: int = 0,
    error: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO fetch_log(referente_id,canal,fetched_at,status,items_found,error) "
        "VALUES (?,?,?,?,?,?)",
        (referente_id, canal, _now_iso(), status, items_found, error),
    )
    conn.commit()


def upsert_item(
    conn: sqlite3.Connection,
    *,
    url_canonica: str,
    referente_id: str,
    referente_nombre: str,
    canal: str,
    titulo: str | None,
    publicado_en: str | None,
    contenido_html: str | None = None,
) -> bool:
    """Insert if new. Returns True if a new row was created.

    On INSERT, persists ``contenido_html`` (may be NULL) and stamps
    ``contenido_extraido_at`` with the current time iff content was captured.
    """
    extraido_at = _now_iso() if contenido_html else None
    cur = conn.execute(
        "INSERT OR IGNORE INTO discovered_items "
        "(url_canonica, referente_id, referente_nombre, canal, titulo, "
        " publicado_en, primera_vez_visto, contenido_html, contenido_extraido_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (url_canonica, referente_id, referente_nombre, canal, titulo, publicado_en,
         _now_iso(), contenido_html, extraido_at),
    )
    return cur.rowcount > 0


# ---------- Feed parsing ----------

def parse_feed_xml(text: str) -> list[dict[str, Any]]:
    """Parse RSS 2.0 or Atom 1.0 feed XML. Returns list of {titulo, url, publicado_en}."""
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"feed_parse_error: {exc}") from exc

    tag = root.tag.lower()

    if tag.endswith("rss") or tag.endswith("rdf"):
        for item in root.iter():
            if not item.tag.lower().endswith("item"):
                continue
            items.append(_extract_rss_item(item))
    elif tag.endswith("feed"):
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(f"{ns}entry"):
            items.append(_extract_atom_entry(entry, ns))
    else:
        for item in root.iter():
            local = item.tag.split("}", 1)[-1].lower()
            if local == "item":
                items.append(_extract_rss_item(item))
            elif local == "entry":
                items.append(_extract_atom_entry(item, "{http://www.w3.org/2005/Atom}"))

    return [it for it in items if it.get("url")]


def _extract_rss_item(item: ET.Element) -> dict[str, Any]:
    from .content_extractor import extract_html_from_rss_item

    title = _find_text(item, "title")
    link = _find_text(item, "link")
    pub = _find_text(item, "pubDate") or _find_text(item, "{http://purl.org/dc/elements/1.1/}date")
    contenido_html = extract_html_from_rss_item(item)
    return {"titulo": title, "url": link, "publicado_en": pub,
            "contenido_html": contenido_html}


def _extract_atom_entry(entry: ET.Element, ns: str) -> dict[str, Any]:
    from .content_extractor import extract_html_from_atom_entry

    title_el = entry.find(f"{ns}title")
    title = (title_el.text or "").strip() if title_el is not None else None
    url = None
    for link in entry.findall(f"{ns}link"):
        rel = link.attrib.get("rel", "alternate")
        if rel == "alternate" and link.attrib.get("href"):
            url = link.attrib["href"]
            break
    if not url:
        link = entry.find(f"{ns}link")
        if link is not None:
            url = link.attrib.get("href") or (link.text or "").strip() or None
    pub_el = entry.find(f"{ns}published") or entry.find(f"{ns}updated")
    pub = (pub_el.text or "").strip() if pub_el is not None else None
    contenido_html = extract_html_from_atom_entry(entry)
    return {"titulo": title, "url": url, "publicado_en": pub,
            "contenido_html": contenido_html}


def _find_text(item: ET.Element, tag: str) -> str | None:
    for child in item:
        local = child.tag.split("}", 1)[-1] if "}" in child.tag else child.tag
        full = child.tag
        if local == tag.split("}", 1)[-1] or full == tag:
            text = (child.text or "").strip()
            if text:
                return text
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return None


# ---------- Notion read-only ----------

def _notion_headers(api_key: str, api_version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": api_version,
        "Content-Type": "application/json",
    }


def fetch_referentes(
    *,
    data_source_id: str,
    api_key: str,
    api_version: str,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Read-only paginated query over Notion data source. Mirrors smoke script."""
    rows: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout, headers=_notion_headers(api_key, api_version)) as client:
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            r = client.post(f"{NOTION_BASE_URL}/data_sources/{data_source_id}/query", json=payload)
            if r.status_code >= 400:
                raise IngestSetupError(f"Notion query failed ({r.status_code}): {r.text[:300]}")
            data = r.json()
            rows.extend(data.get("results") or [])
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
    return rows


def _extract_property_text(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    t = prop.get("type")
    if t == "title":
        return ("".join(item.get("plain_text", "") for item in prop.get("title") or [])).strip() or None
    if t == "rich_text":
        return ("".join(item.get("plain_text", "") for item in prop.get("rich_text") or [])).strip() or None
    if t == "url":
        v = prop.get("url")
        return v.strip() if isinstance(v, str) and v.strip() else None
    return None


@dataclass(frozen=True)
class ReferenteRow:
    id: str
    nombre: str
    rss_url: str | None
    youtube_url: str | None
    web_url: str | None
    linkedin_url: str | None
    otros_url: str | None


def normalize_referente(row: dict[str, Any]) -> ReferenteRow:
    props = row.get("properties") or {}
    return ReferenteRow(
        id=str(row.get("id") or ""),
        nombre=_extract_property_text(props.get("Nombre")) or "(sin nombre)",
        rss_url=_extract_property_text(props.get("RSS feed")),
        youtube_url=_extract_property_text(props.get("YouTube channel")),
        web_url=_extract_property_text(props.get("Web / Newsletter")),
        linkedin_url=_extract_property_text(props.get("LinkedIn activity feed")),
        otros_url=_extract_property_text(props.get("Otros canales")),
    )


# ---------- Registry ----------

def load_registry(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for section in ("critical_databases", "reference_systems"):
        section_data = data.get(section) or {}
        entry = section_data.get(REGISTRY_KEY)
        if isinstance(entry, dict) and entry.get("data_source_id"):
            return {
                "data_source_id": str(entry["data_source_id"]),
                "database_id": str(entry.get("database_id") or "") or None,
                "registry_path": str(path),
            }
    raise IngestSetupError(f"Registry entry '{REGISTRY_KEY}' not found in {path}")


# ---------- Channel handlers ----------

def fetch_via_http(
    client: httpx.Client,
    url: str,
) -> tuple[str, str | None]:
    """Fetch a URL. Returns (status, error_msg). status in {'ok', 'http_error', 'timeout', 'parse_error'}.

    On 'ok', body is also returned via attribute on client (callers use _last_body).
    """
    raise NotImplementedError("use _fetch_and_parse instead")


def _fetch_and_parse(
    client: httpx.Client, url: str
) -> tuple[str, list[dict[str, Any]] | None, str | None]:
    """Fetch URL + parse as RSS/Atom. Returns (status, items_or_None, error)."""
    try:
        r = client.get(url, follow_redirects=True)
    except httpx.TimeoutException as exc:
        return ("timeout", None, f"timeout: {exc.__class__.__name__}")
    except httpx.HTTPError as exc:
        return ("http_error", None, f"http: {exc.__class__.__name__}")
    if r.status_code >= 400:
        return ("http_error", None, f"HTTP {r.status_code}")
    try:
        items = parse_feed_xml(r.text)
    except ValueError as exc:
        return ("parse_error", None, str(exc)[:200])
    return ("ok", items, None)


def is_direct_rss_candidate(url: str) -> bool:
    if not url:
        return False
    u = url.lower().split("?", 1)[0].split("#", 1)[0]
    return any(u.endswith(suf.rstrip("/")) or u.endswith(suf) for suf in RSS_FEED_SUFFIXES)


# ---------- Per-channel processing ----------

def process_channel(
    *,
    conn: sqlite3.Connection,
    client: httpx.Client,
    referente_id: str,
    referente_nombre: str,
    canal: str,
    fetch_url: str | None,
    skip_minutes: int,
) -> dict[str, Any]:
    """Process a single channel for a referente. Writes fetch_log + items.

    Returns per-channel summary dict for the JSON report.
    """
    if not fetch_url:
        record_fetch(conn, referente_id=referente_id, canal=canal, status="sin_acceso")
        return {"canal": canal, "status": "sin_acceso", "items_found": 0, "items_new": 0}

    last = get_last_fetch_ok(conn, referente_id, canal)
    if should_skip_recent(last, skip_minutes):
        record_fetch(conn, referente_id=referente_id, canal=canal, status="skip_recent")
        return {"canal": canal, "status": "skip_recent", "items_found": 0, "items_new": 0}

    status, items, error = _fetch_and_parse(client, fetch_url)
    if status != "ok":
        record_fetch(
            conn, referente_id=referente_id, canal=canal,
            status=status, items_found=0, error=error,
        )
        return {"canal": canal, "status": status, "items_found": 0, "items_new": 0, "error": error}

    items_found = 0
    items_new = 0
    for it in items or []:
        url = (it.get("url") or "").strip()
        if not url:
            continue
        items_found += 1
        canon = canonicalize_url(url)
        if not canon:
            continue
        if upsert_item(
            conn,
            url_canonica=canon,
            referente_id=referente_id,
            referente_nombre=referente_nombre,
            canal=canal,
            titulo=(it.get("titulo") or None),
            publicado_en=(it.get("publicado_en") or None),
            contenido_html=(it.get("contenido_html") or None),
        ):
            items_new += 1

    record_fetch(
        conn, referente_id=referente_id, canal=canal,
        status="ok", items_found=items_found,
    )
    return {"canal": canal, "status": "ok", "items_found": items_found, "items_new": items_new}


# ---------- Orchestration ----------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_runtime_notion_api_key() -> str:
    from worker import config
    api_key = config.NOTION_API_KEY
    if not api_key:
        raise IngestSetupError(
            "NOTION_API_KEY not present in worker runtime env. "
            "Source ~/.config/openclaw/env in the same shell as the worker."
        )
    return api_key


def verify_rsshub(rsshub_base: str, *, timeout: float = 5.0) -> None:
    try:
        r = httpx.get(f"{rsshub_base}/", timeout=timeout)
    except httpx.HTTPError as exc:
        raise IngestSetupError(
            f"RSSHub base {rsshub_base} unreachable ({exc.__class__.__name__}). "
            "Container must be Up at 127.0.0.1:1200 (Fase A)."
        ) from exc
    if r.status_code >= 400:
        raise IngestSetupError(f"RSSHub base {rsshub_base} returned HTTP {r.status_code}")


def run_ingest(
    *,
    registry_path: Path,
    rsshub_base: str,
    sqlite_path: Path,
    skip_recent_minutes: int,
    request_timeout: float = 20.0,
) -> dict[str, Any]:
    started = _now_iso()
    registry = load_registry(registry_path)
    api_key = get_runtime_notion_api_key()
    api_version = DEFAULT_NOTION_API_VERSION

    verify_rsshub(rsshub_base)

    raw_rows = fetch_referentes(
        data_source_id=registry["data_source_id"],
        api_key=api_key,
        api_version=api_version,
    )
    referentes = [normalize_referente(r) for r in raw_rows]

    conn = init_sqlite(sqlite_path)

    summary = {
        "referentes_processed": 0,
        "channels_attempted": 0,
        "channels_ok": 0,
        "channels_skip_recent": 0,
        "channels_sin_acceso": 0,
        "channels_error": 0,
        "channels_parse_error": 0,
        "items_total_seen": 0,
        "items_new_this_run": 0,
    }
    per_referente: list[dict[str, Any]] = []
    errors_sample: list[dict[str, Any]] = []

    with httpx.Client(timeout=request_timeout, headers={"User-Agent": "umbral-stage2-ingest/1.0"}) as client:
        for ref in referentes:
            summary["referentes_processed"] += 1
            channels_report = []

            # RSS direct
            channels_report.append(_process_and_track(
                summary, errors_sample, ref,
                process_channel(
                    conn=conn, client=client,
                    referente_id=ref.id, referente_nombre=ref.nombre,
                    canal=CHANNEL_RSS, fetch_url=ref.rss_url,
                    skip_minutes=skip_recent_minutes,
                ),
            ))

            # YouTube via RSSHub
            channels_report.append(_process_youtube(
                summary, errors_sample, ref,
                conn=conn, client=client,
                rsshub_base=rsshub_base,
                skip_minutes=skip_recent_minutes,
            ))

            # Web / Newsletter only if explicit feed URL
            web_url = ref.web_url if (ref.web_url and is_direct_rss_candidate(ref.web_url)) else None
            channels_report.append(_process_and_track(
                summary, errors_sample, ref,
                process_channel(
                    conn=conn, client=client,
                    referente_id=ref.id, referente_nombre=ref.nombre,
                    canal=CHANNEL_WEB_RSS, fetch_url=web_url,
                    skip_minutes=skip_recent_minutes,
                ),
            ))

            # LinkedIn (Fase B not done) → sin_acceso always
            channels_report.append(_process_and_track(
                summary, errors_sample, ref,
                process_channel(
                    conn=conn, client=client,
                    referente_id=ref.id, referente_nombre=ref.nombre,
                    canal=CHANNEL_LINKEDIN, fetch_url=None,
                    skip_minutes=skip_recent_minutes,
                ),
            ))

            # Otros → sin_acceso (no estructurado en Stage 2)
            channels_report.append(_process_and_track(
                summary, errors_sample, ref,
                process_channel(
                    conn=conn, client=client,
                    referente_id=ref.id, referente_nombre=ref.nombre,
                    canal=CHANNEL_OTROS, fetch_url=None,
                    skip_minutes=skip_recent_minutes,
                ),
            ))

            per_referente.append({
                "referente_id_tail": ref.id[-8:] if ref.id else None,
                "nombre": ref.nombre,
                "channels": channels_report,
            })

    conn.close()

    finished = _now_iso()
    overall_pass = (
        summary["referentes_processed"] == 26
        and summary["channels_ok"] >= 5
        and summary["items_new_this_run"] >= 10
    )

    return {
        "overall_pass": overall_pass,
        "run_started_at": started,
        "run_finished_at": finished,
        "registry": {
            "data_source_id": registry["data_source_id"],
            "row_count": len(referentes),
        },
        "rsshub_base": rsshub_base,
        "skip_recent_minutes": skip_recent_minutes,
        "summary": summary,
        "per_referente": per_referente,
        "errors_sample": errors_sample[:20],
    }


def _process_and_track(
    summary: dict[str, int],
    errors_sample: list[dict[str, Any]],
    ref: ReferenteRow,
    channel_result: dict[str, Any],
) -> dict[str, Any]:
    summary["channels_attempted"] += 1
    status = channel_result["status"]
    if status == "ok":
        summary["channels_ok"] += 1
        summary["items_total_seen"] += channel_result.get("items_found", 0)
        summary["items_new_this_run"] += channel_result.get("items_new", 0)
    elif status == "skip_recent":
        summary["channels_skip_recent"] += 1
    elif status == "sin_acceso":
        summary["channels_sin_acceso"] += 1
    elif status == "parse_error":
        summary["channels_parse_error"] += 1
        if "error" in channel_result:
            errors_sample.append({
                "referente_nombre": ref.nombre,
                "canal": channel_result["canal"],
                "error": channel_result["error"],
            })
    else:
        summary["channels_error"] += 1
        if "error" in channel_result:
            errors_sample.append({
                "referente_nombre": ref.nombre,
                "canal": channel_result["canal"],
                "error": channel_result["error"],
            })
    return channel_result


def _process_youtube(
    summary: dict[str, int],
    errors_sample: list[dict[str, Any]],
    ref: ReferenteRow,
    *,
    conn: sqlite3.Connection,
    client: httpx.Client,
    rsshub_base: str,
    skip_minutes: int,
) -> dict[str, Any]:
    if not ref.youtube_url:
        return _process_and_track(
            summary, errors_sample, ref,
            process_channel(
                conn=conn, client=client,
                referente_id=ref.id, referente_nombre=ref.nombre,
                canal=CHANNEL_YOUTUBE, fetch_url=None,
                skip_minutes=skip_minutes,
            ),
        )
    parsed = parse_youtube_channel_id(ref.youtube_url)
    if parsed is None:
        record_fetch(
            conn, referente_id=ref.id, canal=CHANNEL_YOUTUBE,
            status="parse_error", error=f"unparseable youtube url: {ref.youtube_url[:80]}",
        )
        result = {
            "canal": CHANNEL_YOUTUBE, "status": "parse_error",
            "items_found": 0, "items_new": 0, "error": "unparseable youtube url",
        }
        return _process_and_track(summary, errors_sample, ref, result)
    chan_id, kind = parsed
    rsshub_url = f"{rsshub_base.rstrip('/')}{youtube_rsshub_path(chan_id, kind)}"
    return _process_and_track(
        summary, errors_sample, ref,
        process_channel(
            conn=conn, client=client,
            referente_id=ref.id, referente_nombre=ref.nombre,
            canal=CHANNEL_YOUTUBE, fetch_url=rsshub_url,
            skip_minutes=skip_minutes,
        ),
    )


# ---------- CLI ----------

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage 2 ingest: discovery via RSSHub + RSS direct.")
    p.add_argument("--registry", required=True, help="Path al registry yaml.")
    p.add_argument("--rsshub-base", required=True, help="Base URL del RSSHub localhost.")
    p.add_argument("--sqlite", required=True, help="Path al state.sqlite local.")
    p.add_argument("--skip-recent-minutes", type=int, default=30)
    p.add_argument("--output", required=True, help="Path al JSON report de salida.")
    p.add_argument("--request-timeout", type=float, default=20.0)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = run_ingest(
            registry_path=Path(args.registry).expanduser(),
            rsshub_base=args.rsshub_base,
            sqlite_path=Path(args.sqlite).expanduser(),
            skip_recent_minutes=args.skip_recent_minutes,
            request_timeout=args.request_timeout,
        )
        exit_code = 0 if report["overall_pass"] else 2
    except IngestSetupError as exc:
        report = {
            "overall_pass": False,
            "setup_error": str(exc),
        }
        exit_code = 3
    except Exception as exc:  # pragma: no cover
        report = {
            "overall_pass": False,
            "runtime_error": f"{exc.__class__.__name__}: {exc}",
        }
        exit_code = 4

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
