"""Tests for `parse_youtube_channel_id` in `scripts.discovery.stage2_ingest`.

Hardening defensivo (task copilot-vps/033, audit 2026-05-08): el parser
actual sólo está validado contra `https://www.youtube.com/@handle`. David
podría rellenar las 13 columnas vacías en Notion con formatos diversos.
Estos tests cubren los formatos esperables más:

- regression: el formato actual (`https://www.youtube.com/@handle`) sigue OK
- sin scheme: `youtube.com/@x`
- handle suelto: `@x`
- `m.youtube.com`, `youtube.com`, `www.youtube.com`
- `/c/`, `/user/`, `/channel/UC...`
- trailing slash, query params, fragment
- mixed case
- HTML escaped `&amp;` en path
- edge cases: `""`, `None`, "no es una url", `https://example.com/@x`

Casos reales de FASE 1 (task 033 audit): NO HAY casos no-estándar en Notion
hoy. Todos los OK son `https://www.youtube.com/@handle`. Los tests
representativos son de los 13 OK.
"""

from __future__ import annotations

import pytest

from scripts.discovery.stage2_ingest import (
    parse_youtube_channel_id,
    youtube_rsshub_path,
)


# ---------- Regression: 13 OK referentes (todos formato URL handle) ----------


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://www.youtube.com/@AlexTheAnalyst", "AlexTheAnalyst"),
        ("https://www.youtube.com/@nategentile7", "nategentile7"),
        ("https://www.youtube.com/@TheCodingTrain", "TheCodingTrain"),
        ("https://www.youtube.com/@BalkanArchitect", "BalkanArchitect"),
        ("https://www.youtube.com/@3blue1brown", "3blue1brown"),
        ("https://www.youtube.com/@DotCSV", "DotCSV"),
        ("https://www.youtube.com/@SoyDalto", "SoyDalto"),
        ("https://www.youtube.com/@Deeplearningai", "Deeplearningai"),
        ("https://www.youtube.com/@TheB1M", "TheB1M"),
        ("https://www.youtube.com/@storytellingwithdata", "storytellingwithdata"),
        ("https://www.youtube.com/@BernardMarr", "BernardMarr"),
        ("https://www.youtube.com/@curbal", "curbal"),
        ("https://www.youtube.com/@QuantumFracture", "QuantumFracture"),
    ],
)
def test_real_referentes_handle_ok(url: str, expected_id: str) -> None:
    """Regression: los 13 OK actuales en SQLite siguen parseando OK."""
    parsed = parse_youtube_channel_id(url)
    assert parsed == (expected_id, "handle")


# ---------- Variantes URL handle ----------


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/@handle",
        "https://www.youtube.com/@handle",
        "https://m.youtube.com/@handle",
        "http://www.youtube.com/@handle",
        "https://www.youtube.com/@handle/",
        "https://www.youtube.com/@handle?si=tracking",
        "https://www.youtube.com/@handle#about",
        "https://www.youtube.com/@handle/?si=tracking",
        "https://www.YouTube.com/@handle",
        "https://WWW.youtube.com/@handle",
    ],
)
def test_handle_variants_ok(url: str) -> None:
    parsed = parse_youtube_channel_id(url)
    assert parsed == ("handle", "handle"), f"failed for {url!r}: {parsed}"


def test_handle_without_scheme() -> None:
    """Hardening: David podría pegar `youtube.com/@handle` sin scheme."""
    assert parse_youtube_channel_id("youtube.com/@handle") == ("handle", "handle")
    assert parse_youtube_channel_id("www.youtube.com/@handle") == ("handle", "handle")
    assert parse_youtube_channel_id("m.youtube.com/@handle") == ("handle", "handle")


def test_bare_handle() -> None:
    """Hardening: David podría pegar sólo `@handle` (handle suelto)."""
    assert parse_youtube_channel_id("@handle") == ("handle", "handle")
    assert parse_youtube_channel_id("@AlexTheAnalyst") == ("AlexTheAnalyst", "handle")


# ---------- /c/, /user/, /channel/UC... ----------


def test_channel_id_uc() -> None:
    parsed = parse_youtube_channel_id(
        "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
    )
    assert parsed == ("UCxxxxxxxxxxxxxxxxxxxxxx", "channel")


def test_channel_id_uc_trailing_slash_query() -> None:
    parsed = parse_youtube_channel_id(
        "https://www.youtube.com/channel/UC1234567890ABCDEFGHIJKL/?si=x"
    )
    assert parsed == ("UC1234567890ABCDEFGHIJKL", "channel")


def test_legacy_c() -> None:
    assert parse_youtube_channel_id(
        "https://www.youtube.com/c/LegacyChannel"
    ) == ("LegacyChannel", "c")


def test_legacy_user() -> None:
    assert parse_youtube_channel_id(
        "https://www.youtube.com/user/legacyUser"
    ) == ("legacyUser", "user")


# ---------- Edge cases (must return None gracefully) ----------


@pytest.mark.parametrize(
    "url",
    [
        "",
        None,
        "no es una url",
        "https://example.com/@handle",
        "https://vimeo.com/@handle",
        "https://www.facebook.com/@handle",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch?v=abc",  # video URL, not channel
        "https://youtu.be/abc",  # short video URL
        "  ",  # whitespace
    ],
)
def test_invalid_returns_none(url: str | None) -> None:
    assert parse_youtube_channel_id(url) is None


# ---------- Whitespace / leading-trailing ----------


def test_whitespace_stripped() -> None:
    assert parse_youtube_channel_id(
        "  https://www.youtube.com/@handle  "
    ) == ("handle", "handle")


# ---------- HTML escaped (defensive) ----------


def test_html_escaped_ampersand_in_query() -> None:
    """Si David pega URL con &amp; en query (Notion no escapa pero por las dudas)."""
    parsed = parse_youtube_channel_id(
        "https://www.youtube.com/@handle?si=x&amp;feature=y"
    )
    assert parsed == ("handle", "handle")


# ---------- youtube_rsshub_path() integración ----------


@pytest.mark.parametrize(
    "channel_id,kind,expected",
    [
        ("UC123", "channel", "/youtube/channel/UC123"),
        ("MyChan", "c", "/youtube/c/MyChan"),
        ("legacyUser", "user", "/youtube/user/legacyUser"),
        ("handle", "handle", "/youtube/user/@handle"),
    ],
)
def test_rsshub_path(channel_id: str, kind: str, expected: str) -> None:
    assert youtube_rsshub_path(channel_id, kind) == expected


def test_rsshub_path_unknown_kind_raises() -> None:
    with pytest.raises(ValueError, match="unknown youtube kind"):
        youtube_rsshub_path("x", "vimeo")
