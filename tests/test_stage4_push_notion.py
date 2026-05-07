"""Unit tests for ``scripts.discovery.stage4_push_notion`` (013-F)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import httpx
import pytest

from scripts.discovery import stage4_push_notion as s4
from scripts.discovery.stage2_ingest import init_sqlite


# ---------- Helpers ----------

class FakeTransport(httpx.MockTransport):
    pass


def _client_with_handler(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return s4.NotionClient("ntn_FAKE", client=http)


def _seed_promoted(db_path: Path, *, n: int = 1, with_html: bool = True,
                   referente_nombre: str = "Ref One",
                   canal: str = "rss") -> sqlite3.Connection:
    conn = init_sqlite(db_path)
    for i in range(n):
        url = f"https://blog.test/post-{i}"
        conn.execute(
            "INSERT INTO discovered_items "
            "(url_canonica, referente_id, referente_nombre, canal, titulo, "
            " publicado_en, primera_vez_visto, promovido_a_candidato_at, "
            " contenido_html, contenido_extraido_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (url, "ref1", referente_nombre, canal, f"Post {i}",
             "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z",
             "2024-01-02T00:00:00Z",
             "<p>body</p>" if with_html else None,
             "2024-01-01T00:00:00Z" if with_html else None),
        )
    conn.commit()
    return conn


# ---------- BuildPayload ----------

class TestBuildPayload:
    def test_basic_payload_structure(self):
        item = {
            "rowid": 42,
            "url_canonica": "https://blog.test/x",
            "referente_id": "r1",
            "referente_nombre": "Ref One",
            "canal": "rss",
            "titulo": "Hola",
            "publicado_en": "2024-03-15T00:00:00Z",
            "contenido_html": "<p>x</p>",
        }
        payload = s4.build_payload(
            item=item, data_source_id="DS",
            referente_page_id="REFPAGE", children=[{"foo": 1}],
        )
        assert payload["parent"] == {"type": "data_source_id", "data_source_id": "DS"}
        props = payload["properties"]
        assert props["Título"]["title"][0]["text"]["content"] == "Hola"
        assert props["Enlace"]["url"] == "https://blog.test/x"
        assert props["Canal"]["select"]["name"] == "blog"  # rss → blog
        assert props["Estado revisión"]["select"]["name"] == "Sin revisar"
        assert props["Sqlite ID"]["number"] == 42
        assert props["Creado por sistema"]["checkbox"] is True
        assert props["idempotency_key"]["rich_text"][0]["text"]["content"] == \
            "https://blog.test/x"
        assert props["Fecha publicación"]["date"]["start"] == "2024-03-15"
        assert props["Referente"]["relation"] == [{"id": "REFPAGE"}]
        assert payload["children"] == [{"foo": 1}]

    def test_canal_youtube_passthrough(self):
        item = {
            "rowid": 1, "url_canonica": "https://x", "referente_nombre": "R",
            "canal": "youtube", "titulo": "t", "publicado_en": None,
        }
        p = s4.build_payload(item=item, data_source_id="DS",
                             referente_page_id=None, children=[])
        assert p["properties"]["Canal"]["select"]["name"] == "youtube"

    def test_canal_unknown_falls_to_otro(self):
        item = {"rowid": 1, "url_canonica": "https://x", "referente_nombre": "R",
                "canal": "weirdfeed", "titulo": "t", "publicado_en": None}
        p = s4.build_payload(item=item, data_source_id="DS",
                             referente_page_id=None, children=[])
        assert p["properties"]["Canal"]["select"]["name"] == "otro"

    def test_no_referente_omits_relation(self):
        item = {"rowid": 1, "url_canonica": "https://x", "referente_nombre": "?",
                "canal": "rss", "titulo": "t", "publicado_en": None}
        p = s4.build_payload(item=item, data_source_id="DS",
                             referente_page_id=None, children=[])
        assert "Referente" not in p["properties"]

    def test_invalid_date_omits_fecha(self):
        item = {"rowid": 1, "url_canonica": "https://x", "referente_nombre": "R",
                "canal": "rss", "titulo": "t", "publicado_en": "garbage"}
        p = s4.build_payload(item=item, data_source_id="DS",
                             referente_page_id=None, children=[])
        assert "Fecha publicación" not in p["properties"]

    def test_rfc822_date_normalized(self):
        item = {"rowid": 1, "url_canonica": "https://x", "referente_nombre": "R",
                "canal": "rss", "titulo": "t",
                "publicado_en": "Mon, 15 Mar 2024 10:00:00 GMT"}
        p = s4.build_payload(item=item, data_source_id="DS",
                             referente_page_id=None, children=[])
        assert p["properties"]["Fecha publicación"]["date"]["start"] == "2024-03-15"

    def test_title_fallback_to_url(self):
        item = {"rowid": 1, "url_canonica": "https://blog.test/abc",
                "referente_nombre": "R", "canal": "rss", "titulo": None,
                "publicado_en": None}
        p = s4.build_payload(item=item, data_source_id="DS",
                             referente_page_id=None, children=[])
        assert p["properties"]["Título"]["title"][0]["text"]["content"] == \
            "https://blog.test/abc"


# ---------- Schema validation ----------

class TestValidateSchema:
    def test_all_present(self):
        ds = {"properties": {name: {"type": t} for name, t in s4.EXPECTED_PROPS.items()}}
        assert s4.validate_schema(ds) == []

    def test_missing_property(self):
        ds = {"properties": {name: {"type": t} for name, t in s4.EXPECTED_PROPS.items()
                              if name != "Canal"}}
        issues = s4.validate_schema(ds)
        assert any("missing_property:Canal" in i for i in issues)

    def test_wrong_type(self):
        props = {name: {"type": t} for name, t in s4.EXPECTED_PROPS.items()}
        props["Canal"] = {"type": "rich_text"}
        issues = s4.validate_schema({"properties": props})
        assert any("wrong_type:Canal" in i for i in issues)


# ---------- Idempotency / query_existing ----------

class TestQueryExisting:
    def test_returns_id_when_match(self):
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.url.path.endswith("/data_sources/DS/query")
            body = req.read().decode()
            assert "idempotency_key" in body
            return httpx.Response(200, json={"results": [{"id": "EXISTING"}]})
        client = _client_with_handler(handler)
        try:
            assert s4.query_existing(client, data_source_id="DS",
                                      url_canonica="https://blog.test/a") == "EXISTING"
        finally:
            client.close()

    def test_returns_none_when_no_results(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"results": []})
        client = _client_with_handler(handler)
        try:
            assert s4.query_existing(client, data_source_id="DS",
                                      url_canonica="https://blog.test/a") is None
        finally:
            client.close()


# ---------- Token redaction ----------

class TestTokenRedaction:
    def test_repr_redacts_token(self):
        c = s4.NotionClient("ntn_SUPER_SECRET", client=httpx.Client())
        try:
            assert "SECRET" not in repr(c)
            assert "REDACTED" in repr(c)
        finally:
            c.close()


# ---------- 429 backoff ----------

class Test429Backoff:
    def test_retries_then_succeeds(self, monkeypatch):
        sleeps: list[float] = []
        monkeypatch.setattr(s4.time, "sleep", lambda s: sleeps.append(s))
        calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] <= 2:
                return httpx.Response(429, json={})
            return httpx.Response(200, json={"results": []})

        client = _client_with_handler(handler)
        try:
            r = client.get("/data_sources/DS")
        finally:
            client.close()
        assert r.status_code == 200
        assert calls["n"] == 3
        assert sleeps == [1.0, 2.0]


# ---------- Dry-run: no /pages calls ----------

class TestDryRunNoPagesCall:
    def test_dry_run_does_not_post_pages(self, tmp_path: Path):
        conn = _seed_promoted(tmp_path / "db.sqlite", n=2)
        s4.ensure_notion_page_id_column(conn)
        items = s4.select_pending(conn)
        assert len(items) == 2

        forbidden = []

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path.endswith("/pages"):
                forbidden.append(str(req.url))
            return httpx.Response(200, json={"results": []})

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS",
                referentes_index={"ref one": "REFPAGE"},
                commit=False,
            )
        finally:
            client.close()
        assert forbidden == []
        assert summary.would_create == 2
        assert summary.created == 0
        assert summary.dry_run is True


# ---------- Commit path: marks SQLite ----------

class TestCommitMarksPersisted:
    def test_create_marks_notion_page_id(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_promoted(tmp_path / "db.sqlite", n=1)
        s4.ensure_notion_page_id_column(conn)
        items = s4.select_pending(conn)

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": []})
            if req.url.path.endswith("/pages"):
                return httpx.Response(200, json={"id": "NEW-PAGE-ID"})
            return httpx.Response(404)

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS",
                referentes_index={"ref one": "REFPAGE"},
                commit=True,
            )
        finally:
            client.close()
        assert summary.created == 1
        row = conn.execute(
            "SELECT notion_page_id FROM discovered_items WHERE rowid = ?",
            (items[0]["rowid"],),
        ).fetchone()
        assert row[0] == "NEW-PAGE-ID"


# ---------- Idempotency on rerun ----------

class TestIdempotencySecondRun:
    def test_already_present_does_not_create(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_promoted(tmp_path / "db.sqlite", n=1)
        s4.ensure_notion_page_id_column(conn)
        items = s4.select_pending(conn)

        post_pages_count = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": [{"id": "OLD-PAGE"}]})
            if req.url.path.endswith("/pages"):
                post_pages_count["n"] += 1
                return httpx.Response(200, json={"id": "SHOULD-NOT-HAPPEN"})
            return httpx.Response(404)

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS",
                referentes_index={"ref one": "REFPAGE"},
                commit=True,
            )
        finally:
            client.close()
        assert summary.already_present == 1
        assert summary.created == 0
        assert post_pages_count["n"] == 0
        row = conn.execute(
            "SELECT notion_page_id FROM discovered_items WHERE rowid = ?",
            (items[0]["rowid"],),
        ).fetchone()
        assert row[0] == "OLD-PAGE"


# ---------- Migration idempotent ----------

class TestMigrationIdempotent:
    def test_ensure_notion_page_id_column_twice(self, tmp_path: Path):
        db = tmp_path / "m.sqlite"
        conn = init_sqlite(db)  # init_sqlite already adds the column.
        s4.ensure_notion_page_id_column(conn)
        s4.ensure_notion_page_id_column(conn)  # second call is no-op
        cols = {row[1] for row in conn.execute("PRAGMA table_info(discovered_items)")}
        assert "notion_page_id" in cols


# ---------- created_no_body fallback ----------

class TestCreatedNoBody:
    def test_no_html_yields_created_no_body(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_promoted(tmp_path / "db.sqlite", n=1, with_html=False)
        s4.ensure_notion_page_id_column(conn)
        items = s4.select_pending(conn)

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": []})
            if req.url.path.endswith("/pages"):
                body = req.read().decode()
                assert "created_no_body" in body
                return httpx.Response(200, json={"id": "P1"})
            return httpx.Response(404)

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS",
                referentes_index={"ref one": "REFPAGE"},
                commit=True,
            )
        finally:
            client.close()
        assert summary.created_no_body == 1
        assert summary.created == 0
