"""Unit tests for content extraction in Stage 2.

Covers:
- ``content_extractor.extract_html_from_rss_item`` / ``extract_html_from_atom_entry``
- ``stage2_ingest.parse_feed_xml`` returns ``contenido_html`` field.
- SQLite schema migration is idempotent (adds ``contenido_html`` /
  ``contenido_extraido_at`` if missing).
- ``upsert_item`` persists ``contenido_html`` and stamps ``contenido_extraido_at``.
"""

from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.discovery import content_extractor
from scripts.discovery.stage2_ingest import (
    init_sqlite,
    parse_feed_xml,
    upsert_item,
)


RSS_WITH_CONTENT_ENCODED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Demo</title>
    <item>
      <title>Post A</title>
      <link>https://blog.test/a</link>
      <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
      <description>short summary</description>
      <content:encoded><![CDATA[<p>full <strong>body</strong></p>]]></content:encoded>
    </item>
  </channel>
</rss>
"""

RSS_DESCRIPTION_ONLY = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Post B</title>
      <link>https://blog.test/b</link>
      <description><![CDATA[<p>only description</p>]]></description>
    </item>
  </channel>
</rss>
"""

ATOM_WITH_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Post C</title>
    <link href="https://blog.test/c" rel="alternate"/>
    <published>2024-01-01T00:00:00Z</published>
    <content type="html">&lt;p&gt;atom body&lt;/p&gt;</content>
  </entry>
</feed>
"""


class TestExtractor:
    def test_rss_prefers_content_encoded(self):
        root = ET.fromstring(RSS_WITH_CONTENT_ENCODED)
        item = next(el for el in root.iter() if el.tag.endswith("item"))
        html = content_extractor.extract_html_from_rss_item(item)
        assert html is not None and "<strong>" in html

    def test_rss_fallback_description(self):
        root = ET.fromstring(RSS_DESCRIPTION_ONLY)
        item = next(el for el in root.iter() if el.tag.endswith("item"))
        html = content_extractor.extract_html_from_rss_item(item)
        assert html == "<p>only description</p>"

    def test_atom_extracts_content(self):
        root = ET.fromstring(ATOM_WITH_CONTENT)
        ns = "{http://www.w3.org/2005/Atom}"
        entry = root.find(f"{ns}entry")
        html = content_extractor.extract_html_from_atom_entry(entry)
        assert html == "<p>atom body</p>"

    def test_returns_none_when_empty(self):
        root = ET.fromstring(
            '<rss version="2.0"><channel><item><title>x</title>'
            '<link>https://x.test</link></item></channel></rss>'
        )
        item = next(el for el in root.iter() if el.tag.endswith("item"))
        assert content_extractor.extract_html_from_rss_item(item) is None


class TestParseFeedXml:
    def test_rss_items_have_contenido_html(self):
        items = parse_feed_xml(RSS_WITH_CONTENT_ENCODED)
        assert len(items) == 1
        assert items[0]["url"] == "https://blog.test/a"
        assert "strong" in items[0]["contenido_html"]

    def test_atom_items_have_contenido_html(self):
        items = parse_feed_xml(ATOM_WITH_CONTENT)
        assert len(items) == 1
        assert items[0]["contenido_html"] == "<p>atom body</p>"


class TestSqliteMigrationIdempotent:
    def test_adds_columns_to_legacy_db(self, tmp_path: Path):
        db = tmp_path / "legacy.sqlite"
        # Build a legacy schema (no contenido_html / contenido_extraido_at / notion_page_id).
        conn = sqlite3.connect(str(db))
        conn.executescript("""
            CREATE TABLE discovered_items (
              url_canonica TEXT PRIMARY KEY,
              referente_id TEXT NOT NULL,
              referente_nombre TEXT NOT NULL,
              canal TEXT NOT NULL,
              titulo TEXT,
              publicado_en TEXT,
              primera_vez_visto TEXT NOT NULL,
              promovido_a_candidato_at TEXT
            );
        """)
        conn.commit()
        conn.close()

        # init_sqlite must add the missing columns.
        conn = init_sqlite(db)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(discovered_items)")}
        assert "contenido_html" in cols
        assert "contenido_extraido_at" in cols
        assert "notion_page_id" in cols
        conn.close()

        # Second run is a no-op.
        conn = init_sqlite(db)
        cols2 = {row[1] for row in conn.execute("PRAGMA table_info(discovered_items)")}
        assert cols == cols2
        conn.close()


class TestUpsertItemPersistsContent:
    def test_insert_with_html_stamps_extraido_at(self, tmp_path: Path):
        db = tmp_path / "x.sqlite"
        conn = init_sqlite(db)
        created = upsert_item(
            conn,
            url_canonica="https://blog.test/a",
            referente_id="ref1",
            referente_nombre="Ref One",
            canal="rss",
            titulo="Post A",
            publicado_en="2024-01-01T00:00:00Z",
            contenido_html="<p>x</p>",
        )
        assert created
        row = conn.execute(
            "SELECT contenido_html, contenido_extraido_at FROM discovered_items "
            "WHERE url_canonica = ?", ("https://blog.test/a",)
        ).fetchone()
        assert row[0] == "<p>x</p>"
        assert row[1] is not None and row[1].endswith("Z")

    def test_insert_without_html_leaves_extraido_at_null(self, tmp_path: Path):
        db = tmp_path / "y.sqlite"
        conn = init_sqlite(db)
        upsert_item(
            conn,
            url_canonica="https://blog.test/b",
            referente_id="ref1",
            referente_nombre="Ref One",
            canal="rss",
            titulo="Post B",
            publicado_en=None,
            contenido_html=None,
        )
        row = conn.execute(
            "SELECT contenido_html, contenido_extraido_at FROM discovered_items "
            "WHERE url_canonica = ?", ("https://blog.test/b",)
        ).fetchone()
        assert row[0] is None
        assert row[1] is None
