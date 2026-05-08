#!/usr/bin/env python3
"""Spike 030 — Deterministic stripper for YouTube description noise.

Read-only A/B analysis over the YouTube items already enriched in
``~/.cache/rick-discovery/state.sqlite``. For every item this script:

1. Loads ``contenido_html`` (the structural HTML produced by
   ``backfill_youtube_content.py``: header + <h2>Descripción</h2> + description
   paragraphs + optional <h2>Capítulos</h2> + bulleted timestamps).
2. Identifies the description region (paragraphs after the first ``<h2>``
   and before the optional ``<h2>Capítulos</h2>``).
3. Applies a candidate noise-stripping regex set on that region only,
   keeping header + capítulos intact.
4. Re-runs ``html_to_notion_blocks`` on both the original and the stripped
   HTML and reports block counts, removed-line samples and false-positive
   candidates.

NO writes to SQLite, NO writes to Notion, NO LLM calls. Pure analysis.

Output: ``reports/030-stripper-spike-<timestamp>.json``.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make sibling modules importable when run as a script.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.discovery.html_to_notion_blocks import (  # noqa: E402
    fallback_no_body_block,
    html_to_notion_blocks,
)

SQLITE_PATH = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"

# ---------------------------------------------------------------------------
# Stripper regex set (conservative first pass).
# Each entry: (label, compiled regex, scope)
#   scope = "line"  → drop the entire <p>…</p> if regex matches its inner text.
#   scope = "para"  → drop entire paragraph if first ~80 chars match.
#
# Patterns are intentionally conservative: prefer leaving doubtful lines in
# than barring real content.
# ---------------------------------------------------------------------------

# Section headers that introduce noise blocks. Matched as the *whole*
# trimmed inner text (case-insensitive, optional trailing punctuation).
SECTION_HEADERS = [
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
]
SECTION_HEADER_RE = re.compile(
    r"^\s*(?:[\W_]*)(?:" + "|".join(SECTION_HEADERS) + r")\s*[:\-–—]?\s*$",
    re.IGNORECASE,
)

# Sponsor/promo markers — match anywhere in the line, but require strong cue.
PROMO_KEYWORDS_RE = re.compile(
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

# Sponsor / social-only domains. If a paragraph is *dominated* by these
# (≥1 link AND no other substantive text length), drop it.
SPONSOR_DOMAINS = [
    r"surfshark\.com",
    r"nordvpn\.com",
    r"expressvpn\.com",
    r"squarespace\.com",
    r"skillshare\.com",
    r"brilliant\.org",
    r"audible\.com",
    r"hellofresh\.com",
    r"manscaped\.com",
]
SOCIAL_DOMAINS = [
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
]
SHORTLINK_DOMAINS = [
    r"bit\.ly",
    r"amzn\.to",
    r"amzn\.com",
    r"coursera\.pxf\.io",
    r"linktr\.ee",
    r"lnk\.to",
    r"geni\.us",
    r"go\.magik\.ly",
]

PROMO_DOMAIN_RE = re.compile(
    r"https?://[^\s<>'\"]*(?:" + "|".join(SPONSOR_DOMAINS + SHORTLINK_DOMAINS) + r")",
    re.IGNORECASE,
)
SOCIAL_DOMAIN_RE = re.compile(
    r"https?://[^\s<>'\"]*(?:" + "|".join(SOCIAL_DOMAINS) + r")",
    re.IGNORECASE,
)
ANY_URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)

# Legal/disclaimer boilerplate.
LEGAL_RE = re.compile(
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

# Hashtag-only paragraph (e.g. "#linux #bim #construction").
HASHTAG_ONLY_RE = re.compile(r"^\s*(?:#[\w\-áéíóúñÁÉÍÓÚÑ]+\s*)+$")

# Strip outer paragraph tags helper.
P_TAG_RE = re.compile(r"^<p[^>]*>(.*)</p>\s*$", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove tags and collapse whitespace, keep entities raw."""
    return TAG_RE.sub("", text).strip()


def _split_paragraphs(html_region: str) -> list[str]:
    """Split a region into <p>...</p> chunks (and stray text)."""
    # Naive but effective: split on </p> while keeping markers.
    parts = re.split(r"(?i)(</p>)", html_region)
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


def _classify_paragraph(p_html: str) -> tuple[bool, str | None]:
    """Return (drop, reason). reason is None if kept.

    Conservative: only drop on strong cues. When in doubt, keep.
    """
    inner = _strip_html(p_html)
    if not inner:
        # Empty paragraph after tag-stripping: drop silently (no reason).
        return True, "empty"

    # 1. Section headers ("BECOME A MEMBER", "RESOURCES:", etc.) — these mark
    #    boilerplate sections; drop the header itself.
    if SECTION_HEADER_RE.match(inner):
        return True, "section_header"

    # 2. Hashtag-only line: drop. (Future: capture as Notion tags.)
    if HASHTAG_ONLY_RE.match(inner):
        return True, "hashtag_only"

    # 3. Strong promo keyword present: drop.
    if PROMO_KEYWORDS_RE.search(inner):
        return True, "promo_keyword"

    # 4. Legal/disclaimer language: drop.
    if LEGAL_RE.search(inner):
        return True, "legal_disclaimer"

    # 5. Sponsor-domain dominated paragraph (e.g. "Mi VPN: surfshark.com/x").
    #    Drop only if a sponsor/shortlink is present AND the non-link text
    #    is short (< 60 chars), so we don't barre prose that happens to cite
    #    a bit.ly link.
    if PROMO_DOMAIN_RE.search(inner):
        non_link = ANY_URL_RE.sub("", inner).strip(" ·-—–|:•\t")
        if len(non_link) < 60:
            return True, "sponsor_domain_only"

    # 6. Social-domain dominated paragraph (Instagram/Twitter/Twitch list).
    #    Same idea: only drop if the paragraph is "links + tiny labels".
    socials = SOCIAL_DOMAIN_RE.findall(inner)
    if len(socials) >= 2:
        non_link = ANY_URL_RE.sub("", inner).strip(" ·-—–|:•\t")
        if len(non_link) < 80:
            return True, "social_links_only"

    return False, None


def _split_html_regions(html: str) -> tuple[str, str, str]:
    """Split contenido_html into (header, description_region, capitulos_region).

    Backfill_youtube_content always emits the structure:

        <p><em>Duración: …</em></p>   ← header
        <h2>Descripción</h2>
        <p>…</p> <p>…</p> …            ← description (subject to stripping)
        [<h2>Capítulos</h2>            ← optional, must be preserved
         <ul>…</ul>]
    """
    desc_match = re.search(r"<h2[^>]*>\s*Descripci[oó]n\s*</h2>", html, re.IGNORECASE)
    cap_match = re.search(r"<h2[^>]*>\s*Cap[ií]tulos?\s*</h2>", html, re.IGNORECASE)

    if not desc_match:
        # No standard structure; treat all as description.
        return "", html, ""

    header = html[: desc_match.start()]
    if cap_match and cap_match.start() > desc_match.end():
        description = html[desc_match.end() : cap_match.start()]
        capitulos = html[cap_match.start() :]
    else:
        description = html[desc_match.end() :]
        capitulos = ""

    # Re-attach the <h2>Descripción</h2> marker to the header so we keep it
    # rendering on the cleaned output.
    header_plus_marker = header + html[desc_match.start() : desc_match.end()]
    return header_plus_marker, description, capitulos


def strip_description_noise(html: str) -> tuple[str, list[dict[str, Any]]]:
    """Apply the conservative stripper. Return (clean_html, removals)."""
    header, description, capitulos = _split_html_regions(html)
    paragraphs = _split_paragraphs(description)
    kept: list[str] = []
    removals: list[dict[str, Any]] = []
    for p in paragraphs:
        drop, reason = _classify_paragraph(p)
        if drop and reason != "empty":
            removals.append({"reason": reason, "text": _strip_html(p)[:200]})
        elif drop and reason == "empty":
            pass  # silently drop empty paragraphs
        else:
            kept.append(p)
    clean_description = " ".join(kept)
    return header + clean_description + capitulos, removals


# ---------------------------------------------------------------------------
# A/B reporting
# ---------------------------------------------------------------------------


def _block_text(b: dict[str, Any]) -> str:
    btype = b.get("type", "?")
    payload = b.get(btype, {})
    rt = payload.get("rich_text", [])
    return "".join(
        span.get("text", {}).get("content", "")
        for span in rt
        if span.get("type") == "text"
    )


def _convert(html: str | None) -> list[dict[str, Any]]:
    try:
        blocks = html_to_notion_blocks(html)
        if not blocks:
            return [fallback_no_body_block()]
        return blocks
    except Exception:
        return [fallback_no_body_block()]


def analyze(rowid: int, conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT rowid, titulo, referente_nombre, url_canonica, contenido_html "
        "FROM discovered_items WHERE rowid = ?",
        (rowid,),
    ).fetchone()
    if not row:
        return {"sqlite_id": rowid, "error": "not_found"}

    raw_html = row["contenido_html"]
    clean_html, removals = strip_description_noise(raw_html)

    pre_blocks = _convert(raw_html)
    post_blocks = _convert(clean_html)

    return {
        "sqlite_id": int(row["rowid"]),
        "referente": row["referente_nombre"],
        "titulo": row["titulo"],
        "url": row["url_canonica"],
        "html_chars_pre": len(raw_html),
        "html_chars_post": len(clean_html),
        "blocks_pre": len(pre_blocks),
        "blocks_post": len(post_blocks),
        "blocks_delta": len(pre_blocks) - len(post_blocks),
        "removed_count": len(removals),
        "removed_sample": removals[:5],
        "removed_reasons_histogram": _histogram(r["reason"] for r in removals),
        "kept_blocks_preview": [
            {
                "type": b.get("type"),
                "text": _block_text(b)[:140],
            }
            for b in post_blocks[:8]
        ],
    }


def _histogram(items: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        out[it] = out.get(it, 0) + 1
    return out


def main() -> int:
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row

    rowids = [
        r["rowid"]
        for r in conn.execute(
            "SELECT rowid FROM discovered_items "
            "WHERE canal='youtube' AND contenido_html IS NOT NULL "
            "ORDER BY rowid"
        ).fetchall()
    ]

    items = [analyze(rid, conn) for rid in rowids]

    summary = {
        "items_analyzed": len(items),
        "avg_blocks_pre": round(sum(i["blocks_pre"] for i in items) / max(len(items), 1), 2),
        "avg_blocks_post": round(sum(i["blocks_post"] for i in items) / max(len(items), 1), 2),
        "avg_block_reduction_pct": round(
            100
            * sum(i["blocks_delta"] for i in items)
            / max(sum(i["blocks_pre"] for i in items), 1),
            2,
        ),
        "total_removals": sum(i["removed_count"] for i in items),
        "global_reasons_histogram": _histogram(
            r["reason"] for i in items for r in i["removed_sample"]
        ),
        "top3_reduction": sorted(items, key=lambda x: -x["blocks_delta"])[:3],
        "items_with_zero_removals": [
            {"sqlite_id": i["sqlite_id"], "titulo": i["titulo"]}
            for i in items
            if i["removed_count"] == 0
        ],
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path("reports") / f"030-stripper-spike-{timestamp}.json"
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w") as fh:
        json.dump({"summary": summary, "items": items}, fh, indent=2, ensure_ascii=False)

    print(f"Wrote {out_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
