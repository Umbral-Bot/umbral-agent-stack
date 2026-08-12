"""Minimal read-only Notion helper for S0/S1 discovery.

Scope:
- Paginated query over a Notion data source (POST /v1/data_sources/{id}/query).
- Property extraction helpers tailored to the `👤 Referentes` schema.

Hard rules:
- Read-only. Never PATCH, POST page create, or DELETE.
- Never logs `NOTION_API_KEY`.
- No imports from `worker` (keeps discovery package decoupled).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import httpx

NOTION_BASE_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_API_VERSION = "2025-09-03"

# Property names in the live `👤 Referentes` data source (verified 2026-05-08).
NAME_PROP = "Nombre"
RSS_PROP = "RSS feed"
WEB_PROP = "Web / Newsletter"
YOUTUBE_PROP = "YouTube channel"
LINKEDIN_FEED_PROP = "LinkedIn activity feed"
LINKEDIN_PROP = "LinkedIn"
OTROS_PROP = "Otros canales"
PLATAFORMAS_PROP = "Plataformas"
CONFIANZA_PROP = "Confianza canales"
FLAGS_PROP = "Flags canales"
IDIOMA_PROP = "Idioma"
CATEGORIA_PROP = "Categoría"

# Activo/Pausado interpretation:
# `👤 Referentes` does NOT have explicit Activo/Pausado boolean fields.
# We derive them from `Confianza canales` and `Flags canales`:
#   - DUPLICADO confianza or DUP flag    → excluded (not activo).
#   - REQUIERE_VERIFICACION_MANUAL flag  → pausado.
#   - everything else                    → activo.
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
    linkedin_url: str | None
    linkedin_feed_url: str | None
    otros: str | None
    plataformas: tuple[str, ...]
    confianza: str | None
    flags: tuple[str, ...]
    idioma: tuple[str, ...]
    categoria: str | None

    @property
    def is_excluded(self) -> bool:
        if self.confianza and self.confianza.upper() in EXCLUDED_CONFIANZA:
            return True
        if any(f.upper() in EXCLUDED_FLAGS for f in self.flags):
            return True
        return False

    @property
    def is_pausado(self) -> bool:
        return any(f.upper() in PAUSADO_FLAGS for f in self.flags)

    @property
    def is_activo(self) -> bool:
        return not self.is_excluded and not self.is_pausado


def _notion_headers(api_key: str, api_version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": api_version,
        "Content-Type": "application/json",
    }


def query_data_source(
    *,
    data_source_id: str,
    api_key: str,
    api_version: str = DEFAULT_NOTION_API_VERSION,
    timeout: float = 30.0,
    client: httpx.Client | None = None,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """Read-only paginated query. Returns the raw `results` list."""
    rows: list[dict[str, Any]] = []
    own_client = client is None
    c = client or httpx.Client(
        timeout=timeout, headers=_notion_headers(api_key, api_version)
    )
    try:
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": page_size}
            if cursor:
                payload["start_cursor"] = cursor
            r = c.post(
                f"{NOTION_BASE_URL}/data_sources/{data_source_id}/query",
                json=payload,
            )
            if r.status_code >= 400:
                raise RuntimeError(
                    f"Notion query failed ({r.status_code}): {r.text[:300]}"
                )
            data = r.json()
            rows.extend(data.get("results") or [])
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
    finally:
        if own_client:
            c.close()
    return rows


# ---------- Property extractors ----------

def _text(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    t = prop.get("type")
    if t == "title":
        s = "".join(it.get("plain_text", "") for it in prop.get("title") or [])
    elif t == "rich_text":
        s = "".join(it.get("plain_text", "") for it in prop.get("rich_text") or [])
    elif t == "url":
        v = prop.get("url")
        s = v if isinstance(v, str) else ""
    else:
        return None
    s = (s or "").strip()
    return s or None


def _select(prop: dict[str, Any] | None) -> str | None:
    if not prop or prop.get("type") != "select":
        return None
    sel = prop.get("select")
    return (sel or {}).get("name") if sel else None


def _multi(prop: dict[str, Any] | None) -> tuple[str, ...]:
    if not prop or prop.get("type") != "multi_select":
        return ()
    return tuple(it.get("name", "") for it in (prop.get("multi_select") or []) if it.get("name"))


def normalize_referente(page: dict[str, Any]) -> ReferenteRow:
    props = page.get("properties") or {}
    return ReferenteRow(
        referente_id=str(page.get("id") or ""),
        nombre=_text(props.get(NAME_PROP)) or "(sin nombre)",
        rss_url=_text(props.get(RSS_PROP)),
        web_url=_text(props.get(WEB_PROP)),
        youtube_url=_text(props.get(YOUTUBE_PROP)),
        linkedin_url=_text(props.get(LINKEDIN_PROP)),
        linkedin_feed_url=_text(props.get(LINKEDIN_FEED_PROP)),
        otros=_text(props.get(OTROS_PROP)),
        plataformas=_multi(props.get(PLATAFORMAS_PROP)),
        confianza=_select(props.get(CONFIANZA_PROP)),
        flags=_multi(props.get(FLAGS_PROP)),
        idioma=_multi(props.get(IDIOMA_PROP)),
        categoria=_select(props.get(CATEGORIA_PROP)),
    )


def fan_out_channels(ref: ReferenteRow) -> list[tuple[str, str]]:
    """Return list of (canal_tipo, canal_url) tuples for a referente.

    LinkedIn URLs are returned with canal_tipo='linkedin' so the snapshot
    records them, but Stage 1 will refuse to fetch them.
    """
    out: list[tuple[str, str]] = []
    if ref.rss_url:
        out.append(("rss", ref.rss_url))
    if ref.web_url:
        out.append(("web", ref.web_url))
    if ref.youtube_url:
        out.append(("youtube", ref.youtube_url))
    if ref.linkedin_feed_url:
        out.append(("linkedin", ref.linkedin_feed_url))
    if ref.linkedin_url and ref.linkedin_url != ref.linkedin_feed_url:
        out.append(("linkedin", ref.linkedin_url))
    return out
