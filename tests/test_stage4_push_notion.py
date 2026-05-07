"""Unit tests for scripts/discovery/stage4_push_notion.py."""

from __future__ import annotations

import io
import json
import sqlite3
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from discovery import stage4_push_notion as s4  # noqa: E402

NOW_ISO = "2026-05-06T20:00:00Z"


# ---------- fixtures ----------


def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE discovered_items (
            url_canonica TEXT PRIMARY KEY,
            referente_id TEXT NOT NULL,
            referente_nombre TEXT NOT NULL,
            canal TEXT NOT NULL,
            titulo TEXT,
            publicado_en TEXT,
            primera_vez_visto TEXT NOT NULL,
            promovido_a_candidato_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return db


def _insert(db: Path, **fields):
    defaults = {
        "url_canonica": "https://example.com/post-1",
        "referente_id": "ref-1",
        "referente_nombre": "Ref One",
        "canal": "youtube",
        "titulo": "Some title",
        "publicado_en": "2026-04-29T22:54:14Z",
        "primera_vez_visto": "2026-05-06T00:00:00Z",
        "promovido_a_candidato_at": NOW_ISO,
    }
    defaults.update(fields)
    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO discovered_items
           (url_canonica, referente_id, referente_nombre, canal, titulo,
            publicado_en, primera_vez_visto, promovido_a_candidato_at)
           VALUES (:url_canonica, :referente_id, :referente_nombre, :canal,
                   :titulo, :publicado_en, :primera_vez_visto,
                   :promovido_a_candidato_at)""",
        defaults,
    )
    conn.commit()
    conn.close()


def _item(rowid=1, url="https://example.com/post-1", titulo="Title 1"):
    return s4.Item(
        rowid=rowid,
        url_canonica=url,
        referente_nombre="Ref One",
        canal="youtube",
        titulo=titulo,
        publicado_en="2026-04-29T22:54:14Z",
    )


# ---------- 1. build_payload ----------


class TestBuildPayload:
    def test_required_properties_present(self):
        item = _item()
        payload = s4.build_payload(item, data_source_id="DS-123")
        assert payload["parent"] == {
            "type": "data_source_id",
            "data_source_id": "DS-123",
        }
        props = payload["properties"]
        assert props["Título"]["title"][0]["text"]["content"] == "Title 1"
        assert props["Fuente primaria"]["url"] == "https://example.com/post-1"
        assert props["idempotency_key"]["rich_text"][0]["text"]["content"] == \
            "https://example.com/post-1"
        assert props["Canal"]["select"]["name"] == "linkedin"
        assert props["Estado"]["status"]["name"] == "Idea"
        assert props["Creado por sistema"]["checkbox"] is True
        assert "[ref: Ref One | sqlite: 1]" in props["Notas"]["rich_text"][0]["text"]["content"]
        # date present (publicado_en parseable)
        assert "Fecha publicación" in props
        assert props["Fecha publicación"]["date"]["start"].startswith("2026-04-29T22:54:14")

    def test_no_date_when_publicado_en_invalid(self):
        item = _item()
        item.publicado_en = "not-a-date"
        payload = s4.build_payload(item, "DS-1")
        assert "Fecha publicación" not in payload["properties"]

    def test_empty_title_falls_back(self):
        item = _item(titulo="   ")
        payload = s4.build_payload(item, "DS-1")
        assert payload["properties"]["Título"]["title"][0]["text"]["content"] == "(sin título)"


# ---------- 2. validate_schema ----------


class TestValidateSchema:
    def test_all_present_no_issues(self):
        observed = {name: t for name, t in s4.REQUIRED_PROPS.items()}
        # add a few extras (should not error)
        observed["Otro"] = "rich_text"
        assert s4.validate_schema(observed) == []

    def test_missing_property_reported(self):
        observed = {name: t for name, t in s4.REQUIRED_PROPS.items()}
        del observed["Título"]
        issues = s4.validate_schema(observed)
        assert len(issues) == 1
        assert "Título" in issues[0]

    def test_type_mismatch_reported(self):
        observed = {name: t for name, t in s4.REQUIRED_PROPS.items()}
        observed["Estado"] = "select"  # spec expects status
        issues = s4.validate_schema(observed)
        assert len(issues) == 1
        assert "Estado" in issues[0]
        assert "status" in issues[0] and "select" in issues[0]


# ---------- 3. query_existing ----------


class TestQueryExisting:
    def _client_returning(self, payload):
        c = MagicMock(spec=s4.NotionClient)
        c.request.return_value = payload
        return c

    def test_match_returns_page_id(self):
        c = self._client_returning(
            {"results": [{"id": "PAGE-AAA", "url": "https://notion.so/PAGE-AAA"}]}
        )
        pid, url = s4.query_existing(c, "DS-1", "https://example.com/x")
        assert pid == "PAGE-AAA"
        assert url == "https://notion.so/PAGE-AAA"
        c.request.assert_called_once()
        args, kwargs = c.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/v1/data_sources/DS-1/query"
        assert kwargs["body"]["filter"]["property"] == "idempotency_key"

    def test_no_match_returns_none(self):
        c = self._client_returning({"results": []})
        pid, url = s4.query_existing(c, "DS-1", "https://example.com/x")
        assert pid is None and url is None


# ---------- 4. create_page ----------


class TestCreatePage:
    def test_returns_id_and_url(self):
        c = MagicMock(spec=s4.NotionClient)
        c.request.return_value = {"id": "PG-1", "url": "https://notion.so/PG-1"}
        pid, url = s4.create_page(c, {"parent": {}, "properties": {}})
        assert pid == "PG-1"
        assert url == "https://notion.so/PG-1"

    def test_raises_on_4xx_non_429(self):
        # Use real NotionClient with a fake opener raising HTTPError 400.
        def bad_open(req, timeout):
            raise urllib.error.HTTPError(
                req.full_url, 400, "Bad Request", hdrs={}, fp=io.BytesIO(b'{"err":"x"}')
            )
        client = s4.NotionClient(token="t", _opener=bad_open, _sleep=lambda s: None)
        with pytest.raises(s4.Stage4Error) as exc_info:
            s4.create_page(client, {"properties": {}})
        assert "400" in str(exc_info.value)


# ---------- 5. 429 backoff retry ----------


class Test429Backoff:
    def test_429_retries_then_succeeds(self):
        calls = {"n": 0}

        def opener(req, timeout):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise urllib.error.HTTPError(
                    req.full_url, 429, "Too Many", hdrs={}, fp=io.BytesIO(b'{"e":"rl"}')
                )
            return _FakeResponse(b'{"id": "PG-X", "url": "u"}')

        sleeps: list[float] = []
        summary = s4.RunSummary()
        client = s4.NotionClient(
            token="t", _opener=opener, _sleep=sleeps.append, summary_ref=summary
        )
        pid, _ = s4.create_page(client, {"properties": {}})
        assert pid == "PG-X"
        assert calls["n"] == 3
        # 2 retries → 2 backoff sleeps (1s, 2s)
        assert sleeps == [1, 2]
        assert summary.retries_429 == 2

    def test_429_persistent_aborts(self):
        def opener(req, timeout):
            raise urllib.error.HTTPError(
                req.full_url, 429, "Too Many", hdrs={}, fp=io.BytesIO(b'')
            )
        client = s4.NotionClient(token="t", _opener=opener, _sleep=lambda s: None)
        with pytest.raises(s4.Stage4Error) as exc_info:
            s4.create_page(client, {"properties": {}})
        assert "persistent 429" in str(exc_info.value)


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body


# ---------- 6. dry-run does NOT call query_existing/create_page ----------


class TestDryRunNoHttpItemCalls:
    def test_dry_run_zero_query_zero_create(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, url_canonica="https://example.com/a", titulo="A")
        _insert(db, url_canonica="https://example.com/b", titulo="B")
        out = tmp_path / "report.json"

        with patch.object(s4, "query_existing") as mock_q, \
             patch.object(s4, "create_page") as mock_c:
            rc = s4.main([
                "--sqlite", str(db),
                "--database-id", "DB-1",
                "--data-source-id", "DS-1",
                "--output", str(out),
            ])
            assert rc == 0
            assert mock_q.call_count == 0
            assert mock_c.call_count == 0

        report = json.loads(out.read_text())
        assert report["mode"] == "dry-run"
        assert report["summary"]["would_create"] == 2
        assert report["summary"]["created"] == 0
        assert report["summary"]["skipped_existing"] == 0
        assert report["overall_pass"] is True


# ---------- 7. mark_persisted updates SQLite ----------


class TestMarkPersisted:
    def test_update_only_when_null(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, url_canonica="https://example.com/p1")
        conn = s4.open_sqlite(db)
        s4.ensure_notion_page_id_column(conn)
        rowid = conn.execute(
            "SELECT rowid FROM discovered_items WHERE url_canonica=?",
            ("https://example.com/p1",),
        ).fetchone()[0]
        s4.mark_persisted(conn, rowid, "PG-1")
        got = conn.execute(
            "SELECT notion_page_id FROM discovered_items WHERE rowid=?", (rowid,)
        ).fetchone()[0]
        assert got == "PG-1"
        # second call should NOT overwrite
        s4.mark_persisted(conn, rowid, "PG-2")
        got2 = conn.execute(
            "SELECT notion_page_id FROM discovered_items WHERE rowid=?", (rowid,)
        ).fetchone()[0]
        assert got2 == "PG-1"
        conn.close()

    def test_dry_run_does_not_mutate(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, url_canonica="https://example.com/p1")
        out = tmp_path / "r.json"
        with patch.object(s4, "query_existing"), patch.object(s4, "create_page"):
            s4.main([
                "--sqlite", str(db), "--database-id", "DB",
                "--data-source-id", "DS-1", "--output", str(out),
            ])
        # column was added (migration always runs), but no row has notion_page_id
        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM discovered_items WHERE notion_page_id IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        assert n == 0


# ---------- 8. idempotency: 2nd commit run = all skipped ----------


class TestIdempotencySecondRun:
    def test_second_run_classifies_as_skipped(self, tmp_path: Path, monkeypatch):
        db = _make_db(tmp_path)
        _insert(db, url_canonica="https://example.com/x", titulo="X")

        monkeypatch.setenv("NOTION_API_KEY", "fake-token-test")
        out1 = tmp_path / "r1.json"
        out2 = tmp_path / "r2.json"

        # First commit run: query → no match, create → page id.
        with patch.object(s4, "resolve_data_source_id", return_value="DS-1"), \
             patch.object(s4, "fetch_schema",
                          return_value={n: t for n, t in s4.REQUIRED_PROPS.items()}), \
             patch.object(s4, "query_existing", return_value=(None, None)) as mock_q, \
             patch.object(s4, "create_page",
                          return_value=("PG-NEW", "https://notion.so/PG-NEW")), \
             patch.object(s4.NotionClient, "sleep_rl", lambda self: None):
            rc = s4.main([
                "--sqlite", str(db), "--database-id", "DB", "--commit",
                "--output", str(out1),
            ])
            assert rc == 0, out1.read_text()
            assert mock_q.call_count == 1

        report1 = json.loads(out1.read_text())
        assert report1["summary"]["created"] == 1
        assert report1["summary"]["skipped_existing"] == 0

        # State: SQLite has notion_page_id set → select_pending should return 0.
        # Run again. We must INSERT another row to actually have something pending,
        # but with same URL it'd violate PK. So simulate idempotency by clearing
        # the SQLite notion_page_id and having Notion lookup return a hit.
        conn = sqlite3.connect(db)
        conn.execute("UPDATE discovered_items SET notion_page_id=NULL")
        conn.commit()
        conn.close()

        with patch.object(s4, "resolve_data_source_id", return_value="DS-1"), \
             patch.object(s4, "fetch_schema",
                          return_value={n: t for n, t in s4.REQUIRED_PROPS.items()}), \
             patch.object(s4, "query_existing",
                          return_value=("PG-NEW", "https://notion.so/PG-NEW")) as mock_q2, \
             patch.object(s4, "create_page") as mock_c2, \
             patch.object(s4.NotionClient, "sleep_rl", lambda self: None):
            rc = s4.main([
                "--sqlite", str(db), "--database-id", "DB", "--commit",
                "--output", str(out2),
            ])
            assert rc == 0
            assert mock_q2.call_count == 1
            assert mock_c2.call_count == 0

        report2 = json.loads(out2.read_text())
        assert report2["summary"]["created"] == 0
        assert report2["summary"]["skipped_existing"] == 1


# ---------- 9. migration idempotent ----------


class TestMigrationIdempotent:
    def test_add_column_twice_is_safe(self, tmp_path: Path):
        db = _make_db(tmp_path)
        conn = s4.open_sqlite(db)
        added1 = s4.ensure_notion_page_id_column(conn)
        added2 = s4.ensure_notion_page_id_column(conn)
        conn.close()
        assert added1 is True
        assert added2 is False
        # column exists
        conn = sqlite3.connect(db)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(discovered_items)")}
        conn.close()
        assert "notion_page_id" in cols
