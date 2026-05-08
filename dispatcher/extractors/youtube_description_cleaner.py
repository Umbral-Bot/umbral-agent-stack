"""Deterministic noise stripper for YouTube description HTML.

Permanent module spun out of ``scripts/discovery/spike_030_youtube_description_stripper.py``
after the spike analyzed 16 enriched items (PR #347, merged 2026-05-07).

Operates on the structural HTML produced by
``scripts/discovery/backfill_youtube_content.py``::

    <p><em>Duración: …</em></p>            ← header (preserved intact)
    <h2>Descripción</h2>
    <p>…</p> <p>…</p> …                    ← description (subject to stripping)
    [<h2>Capítulos</h2>                    ← preserved intact when present
     <ul>…</ul>]

Six conservative classifiers drop noise paragraphs only on a strong cue:

* ``section_header`` — boilerplate headers ("BECOME A MEMBER", "RESOURCES:"…)
* ``hashtag_only`` — paragraph composed solely of #hashtags
* ``promo_keyword`` — sponsorship / affiliate language
* ``legal_disclaimer`` — copyright / "not financial advice" boilerplate
* ``sponsor_domain_only`` — sponsor/shortlink URL with <60 chars of non-link text
* ``social_links_only`` — ≥2 social URLs with <80 chars of non-link text

Empty paragraphs are dropped silently (no removal record emitted).

Public API
----------

* :func:`clean_html` — primary entrypoint; returns ``(cleaned_html, removals)``.
* :class:`Removal` — dataclass describing a removed paragraph.

This module performs **zero** I/O, **zero** LLM calls, and **zero** external
network access. It is safe to import in any pipeline stage.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Final

__all__ = ["Removal", "clean_html", "REASONS"]


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


REASONS: Final[tuple[str, ...]] = (
    "section_header",
    "hashtag_only",
    "promo_keyword",
    "legal_disclaimer",
    "sponsor_domain_only",
    "social_links_only",
)


@dataclass(frozen=True)
class Removal:
    """A single paragraph dropped by :func:`clean_html`.

    Attributes:
        text: Plain-text content of the removed paragraph (truncated at 200 chars).
        reason: One of :data:`REASONS`.
        position: 0-based index of the paragraph within the description region
            (before stripping). Useful for debugging which paragraph was dropped.
    """

    text: str
    reason: str
    position: int

    def to_dict(self) -> dict[str, object]:
        """Return a plain dict (JSON-serialisable)."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Compiled regex constants (module-level for performance)
# ---------------------------------------------------------------------------

_SECTION_HEADERS: Final[tuple[str, ...]] = (
    r"BECOME A MEMBER",
    r"RESOURCES?",
    r"Websites?",
    r"Redes Sociales",
    r"Social Media",
    r"Series de este canal",
    r"Follow (?:us|me)",
    r"Where to find me",
    r"Stay connected",
    r"Mis redes",
    r"Subscr[íi]bete",
    r"Suscr[íi]bete",
)
SECTION_HEADER_RE: Final = re.compile(
    r"^\s*(?:[\W_]*)(?:" + "|".join(_SECTION_HEADERS) + r")\s*[:\-–—]?\s*$",
    re.IGNORECASE,
)

PROMO_KEYWORDS_RE: Final = re.compile(
    r"\b("
    r"sponsor(?:ed|ship)?"
    r"|paid promotion"
    r"|promo code"
    r"|c[oó]digo de descuento"
    r"|usa el c[oó]digo"
    r"|use code"
    r"|use my code"
    r"|usa mi c[oó]digo"
    r"|discount code"
    r"|coupon code"
    r"|aff(?:iliate)? link"
    r"|enlace de afiliado"
    r"|small commission"
    r"|earn a commission"
    r"|may earn a commission"
    r"|this video contains paid promotion"
    r"|este v[ií]deo contiene promoci[óo]n pagada"
    r")\b",
    re.IGNORECASE,
)

_SPONSOR_DOMAINS: Final[tuple[str, ...]] = (
    r"surfshark\.com",
    r"nordvpn\.com",
    r"expressvpn\.com",
    r"squarespace\.com",
    r"skillshare\.com",
    r"brilliant\.org",
    r"audible\.com",
    r"hellofresh\.com",
    r"manscaped\.com",
)
_SOCIAL_DOMAINS: Final[tuple[str, ...]] = (
    r"instagram\.com",
    r"twitter\.com",
    r"x\.com",
    r"twitch\.tv",
    r"patreon\.com",
    r"facebook\.com",
    r"tiktok\.com",
    r"linkedin\.com/in/",
    r"discord\.gg",
    r"discord\.com/invite",
    r"threads\.net",
)
_SHORTLINK_DOMAINS: Final[tuple[str, ...]] = (
    r"bit\.ly",
    r"amzn\.to",
    r"amzn\.com",
    r"coursera\.pxf\.io",
    r"linktr\.ee",
    r"lnk\.to",
    r"geni\.us",
    r"go\.magik\.ly",
)

PROMO_DOMAIN_RE: Final = re.compile(
    r"https?://[^\s<>'\"]*(?:" + "|".join(_SPONSOR_DOMAINS + _SHORTLINK_DOMAINS) + r")",
    re.IGNORECASE,
)
SOCIAL_DOMAIN_RE: Final = re.compile(
    r"https?://[^\s<>'\"]*(?:" + "|".join(_SOCIAL_DOMAINS) + r")",
    re.IGNORECASE,
)
ANY_URL_RE: Final = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)

LEGAL_RE: Final = re.compile(
    r"\b("
    r"all opinions or statements"
    r"|do not reflect the opinion"
    r"|this video is not financial advice"
    r"|not financial advice"
    r"|copyright\s+©?\s*\d{4}"
    r"|©\s*\d{4}"
    r"|all rights reserved"
    r"|t&cs?"
    r"|terms\s+(?:and|&)\s+conditions"
    r"|guidelines for sharing"
    r"|ripping (?:and/?or )?editing this video"
    r"|illegal and will result in legal action"
    r")\b",
    re.IGNORECASE,
)

HASHTAG_ONLY_RE: Final = re.compile(r"^\s*(?:#[\w\-áéíóúñÁÉÍÓÚÑ]+\s*)+$")

# HTML helpers
TAG_RE: Final = re.compile(r"<[^>]+>")
DESC_MARKER_RE: Final = re.compile(
    r"<h2[^>]*>\s*Descripci[oó]n\s*</h2>", re.IGNORECASE
)
CAP_MARKER_RE: Final = re.compile(
    r"<h2[^>]*>\s*Cap[ií]tulos?\s*</h2>", re.IGNORECASE
)
P_SPLIT_RE: Final = re.compile(r"(?i)(</p>)")

# Sponsor / social heuristics thresholds
SPONSOR_NON_LINK_MAX_CHARS: Final = 60
SOCIAL_NON_LINK_MAX_CHARS: Final = 80
SOCIAL_MIN_LINKS: Final = 2

# Whitespace characters stripped from non-link text before measuring length.
_NON_LINK_STRIP: Final = " ·-—–|:•\t"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace; entities are kept raw."""
    return TAG_RE.sub("", text).strip()


def _split_paragraphs(html_region: str) -> list[str]:
    """Split a region into ``<p>…</p>`` chunks, preserving stray text."""
    parts = P_SPLIT_RE.split(html_region)
    out: list[str] = []
    buf = ""
    for part in parts:
        buf += part
        if part.lower() == "</p>":
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return [p for p in out if p]


def _split_html_regions(html: str) -> tuple[str, str, str]:
    """Split ``contenido_html`` into ``(header_with_marker, description, capitulos)``.

    The description region is what gets noise-stripped. ``capitulos`` (when
    present) is preserved verbatim because it's the structured timestamps
    list. ``header_with_marker`` keeps the ``<h2>Descripción</h2>`` heading
    attached so the cleaned HTML still renders the section title.

    If the standard structure is not found (no ``<h2>Descripción</h2>``),
    the entire input is treated as the description region.
    """
    desc_match = DESC_MARKER_RE.search(html)
    cap_match = CAP_MARKER_RE.search(html)

    if not desc_match:
        return "", html, ""

    header = html[: desc_match.start()]
    if cap_match and cap_match.start() > desc_match.end():
        description = html[desc_match.end() : cap_match.start()]
        capitulos = html[cap_match.start() :]
    else:
        description = html[desc_match.end() :]
        capitulos = ""

    header_plus_marker = header + html[desc_match.start() : desc_match.end()]
    return header_plus_marker, description, capitulos


def _classify_paragraph(p_html: str) -> tuple[bool, str | None]:
    """Classify a single paragraph.

    Returns:
        ``(drop, reason)``. ``reason`` is ``None`` when the paragraph is kept.
        For empty paragraphs the function returns ``(True, "empty")`` —
        callers should treat ``"empty"`` as a silent drop (no Removal record).

    The classifier is intentionally conservative: only drops on strong cues.
    When in doubt, it keeps the paragraph.
    """
    inner = _strip_html(p_html)
    if not inner:
        return True, "empty"

    if SECTION_HEADER_RE.match(inner):
        return True, "section_header"

    if HASHTAG_ONLY_RE.match(inner):
        return True, "hashtag_only"

    if PROMO_KEYWORDS_RE.search(inner):
        return True, "promo_keyword"

    if LEGAL_RE.search(inner):
        return True, "legal_disclaimer"

    if PROMO_DOMAIN_RE.search(inner):
        non_link = ANY_URL_RE.sub("", inner).strip(_NON_LINK_STRIP)
        if len(non_link) < SPONSOR_NON_LINK_MAX_CHARS:
            return True, "sponsor_domain_only"

    socials = SOCIAL_DOMAIN_RE.findall(inner)
    if len(socials) >= SOCIAL_MIN_LINKS:
        non_link = ANY_URL_RE.sub("", inner).strip(_NON_LINK_STRIP)
        if len(non_link) < SOCIAL_NON_LINK_MAX_CHARS:
            return True, "social_links_only"

    return False, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def clean_html(html: str) -> tuple[str, list[Removal]]:
    """Strip noise paragraphs from a YouTube ``contenido_html`` payload.

    The header (``<p><em>Duración: …</em></p>`` + ``<h2>Descripción</h2>``)
    and the chapters region (``<h2>Capítulos</h2><ul>…</ul>``) are preserved
    verbatim. Only paragraphs inside the description region are evaluated.

    Args:
        html: Source HTML produced by ``backfill_youtube_content.py``.
            May be empty or non-standard; the function never raises.

    Returns:
        ``(clean_html, removals)`` where ``clean_html`` is the reconstructed
        HTML (header + filtered description + capítulos) and ``removals`` is
        the ordered list of dropped paragraphs (excluding empty ones).
    """
    if not html:
        return "", []

    header, description, capitulos = _split_html_regions(html)
    paragraphs = _split_paragraphs(description)
    kept: list[str] = []
    removals: list[Removal] = []
    for idx, p in enumerate(paragraphs):
        drop, reason = _classify_paragraph(p)
        if drop and reason and reason != "empty":
            removals.append(
                Removal(
                    text=_strip_html(p)[:200],
                    reason=reason,
                    position=idx,
                )
            )
        elif drop:
            # silent drop (empty paragraph) — no Removal record
            continue
        else:
            kept.append(p)
    clean_description = " ".join(kept)
    return header + clean_description + capitulos, removals
