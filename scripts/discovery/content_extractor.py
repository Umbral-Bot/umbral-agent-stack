"""Helpers to extract HTML content from RSS/Atom feed items.

Pure functions over either xml.etree.ElementTree.Element or pre-parsed dicts.
Used by:
- stage2_ingest.py during normal ingest.
- backfill_content_for_promoted.py for the cohort already promoted.

Strategy (in order):
1. <content:encoded> (RSS namespace http://purl.org/rss/1.0/modules/content/)
2. <description> (RSS) or <summary>/<content> (Atom)
3. None  → caller persists NULL.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
ATOM_NS = "http://www.w3.org/2005/Atom"


def extract_html_from_rss_item(item: ET.Element) -> str | None:
    """Pick best-available HTML body for an RSS <item>.

    Prefers <content:encoded>, falls back to <description>. Returns None if neither
    has a non-empty value.
    """
    # content:encoded (namespaced)
    for child in item:
        local = child.tag.split("}", 1)[-1]
        ns = child.tag.split("}", 1)[0].lstrip("{") if "}" in child.tag else ""
        if local == "encoded" and ns == CONTENT_NS:
            txt = (child.text or "").strip()
            if txt:
                return txt
    # description (no namespace, or any namespace — RSS 2.0 puts it in default ns)
    for child in item:
        local = child.tag.split("}", 1)[-1]
        if local == "description":
            txt = (child.text or "").strip()
            if txt:
                return txt
    return None


def extract_html_from_atom_entry(entry: ET.Element) -> str | None:
    """Pick best-available HTML body for an Atom <entry>.

    Prefers <content type="html">, falls back to <summary>.
    """
    ns = "{" + ATOM_NS + "}"
    content = entry.find(f"{ns}content")
    if content is not None:
        txt = (content.text or "").strip()
        if txt:
            return txt
    summary = entry.find(f"{ns}summary")
    if summary is not None:
        txt = (summary.text or "").strip()
        if txt:
            return txt
    return None
