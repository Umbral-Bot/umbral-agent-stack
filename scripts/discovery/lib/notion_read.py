"""Notion read-only helpers for Wave1 H2 (S0/S1 Discovery).

Reads the `👤 Referentes` data source. Does NOT write to Notion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterator

import httpx

log = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com"
NOTION_VERSION = "2025-09-03"

# Property names in `👤 Referentes` (as in the live DB).
NAME_PROP = "Nombre"
RSS_PROP = "RSS feed"
WEB_PROP = "Web / Newsletter"
YOUTUBE_PROP = "YouTube channel"
LINKEDIN_FEED_PROP = "LinkedIn activity feed"
LINKEDIN_PROP = "LinkedIn"
CONFIANZA_PROP = "Confianza canales"
FLAGS_PROP = "Flags canales"

# Activo/Pausado interpretation (DB has no explicit booleans).
EXCLUDED_CONFIANZA = {"DUPLICADO"}
EXCLUDED_FLAGS = {"DUP"}
PAUSADO_FLAGS = {"REQUIERE_VERIFICACION_MANUAL"}


@dataclass(frozen=True)
class ReferenteRow:
    referente_id: str
    nombre: str
    rss_url: str | None
    web_url: str | None
    youtube_url: str | None
    linkedin_feed_url: str | None
    linkedin_url: str | None
    confianza: str | None
    flags: tuple[str, ...]

    @property
    def is_excluded(self) -> bool:
        if self.confianza and self.confianza.upper() in EXCLUDED_CONFIANZA:
            return True
        return any(f.upper() in EXCLUDED_FLAGS for f in self.flags)

    @property
    def is_pausado(self) -> bool:
        return any(f.upper() in PAUSADO_FLAGS for f in self.flags)

    @property
    def is_activo(self) -> bool:
        return not (self.is_excluded or self.is_pausado)


def _plain(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    t = prop.get("type")
    if t == "title":
        arr = prop.get("title") or []
    elif t == "rich_text":
        arr = prop.get("rich_text") or []
    else:
        return None
    if not arr:
        return None
    return "".join(x.get("plain_text", "") for x in arr).strip() or None


def _url(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    val = prop.get("url")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


def _select_name(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    sel = prop.get("select")
    if isinstance(sel, dict):
        n = sel.get("name")
        return n.strip() if isinstance(n, str) and n.strip() else None
    return None


def _multi_select_names(prop: dict[str, Any] | None) -> tuple[str, ...]:
    if not prop:
        return ()
    arr = prop.get("multi_select") or []
    out: list[str] = []
    for x in arr:
        n = x.get("name")
        if isinstance(n, str) and n.strip():
            out.append(n.strip())
    return tuple(out)


def normalize_referente(page: dict[str, Any]) -> ReferenteRow:
    """Convert a Notion page object into a ``ReferenteRow``."""
    props = page.get("properties") or {}
    return ReferenteRow(
        referente_id=page.get("id", ""),
        nombre=_plain(props.get(NAME_PROP)) or "",
        rss_url=_url(props.get(RSS_PROP)),
        web_url=_url(props.get(WEB_PROP)),
        youtube_url=_url(props.get(YOUTUBE_PROP)),
        linkedin_feed_url=_url(props.get(LINKEDIN_FEED_PROP)),
        linkedin_url=_url(props.get(LINKEDIN_PROP)),
        confianza=_select_name(props.get(CONFIANZA_PROP)),
        flags=_multi_select_names(props.get(FLAGS_PROP)),
    )


def fan_out_channels(ref: ReferenteRow) -> list[tuple[str, str]]:
    """Emit (canal_tipo, canal_url) per referente. Up to 5 rows.

    LinkedIn URL == LinkedIn activity feed URL is deduped to avoid double rows.
    """
    rows: list[tuple[str, str]] = []
    if ref.rss_url:
        rows.append(("rss", ref.rss_url))
    if ref.web_url:
        rows.append(("web", ref.web_url))
    if ref.youtube_url:
        rows.append(("youtube", ref.youtube_url))
    if ref.linkedin_feed_url:
        rows.append(("linkedin", ref.linkedin_feed_url))
    if ref.linkedin_url and ref.linkedin_url != ref.linkedin_feed_url:
        rows.append(("linkedin", ref.linkedin_url))
    return rows


def query_data_source(
    *,
    data_source_id: str,
    api_key: str,
    page_size: int = 100,
    client: httpx.Client | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield every page from the given Notion data source (paginated)."""
    owns = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns = True
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    url = f"{NOTION_API}/v1/data_sources/{data_source_id}/query"
    cursor: str | None = None
    try:
        while True:
            payload: dict[str, Any] = {"page_size": page_size}
            if cursor:
                payload["start_cursor"] = cursor
            r = client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                raise RuntimeError(
                    f"Notion query failed: HTTP {r.status_code}: {r.text[:500]}"
                )
            data = r.json()
            for p in data.get("results", []) or []:
                yield p
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
    finally:
        if owns:
            client.close()
