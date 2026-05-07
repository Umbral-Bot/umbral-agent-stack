"""Tests for ``--update-existing`` flag in stage4_push_notion (task 037).

Verifies:
- Default OFF: already_present skips (no PATCH/DELETE — no regression).
- Flag ON + already_present: 1 PATCH /pages + N DELETE + ≥1 PATCH /blocks/children.
- Idempotence: second --update-existing run with same content re-renders
  identical blocks (script reescribe siempre by design; assert content stable).
- Edge: contenido_html=NULL → fallback_no_body_block appended (1 block).
- Rate limit: time.sleep called between every Notion HTTP call.
- include_existing flag in select_pending exposes items with notion_page_id.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import httpx

from scripts.discovery import stage4_push_notion as s4
from scripts.discovery.stage2_ingest import init_sqlite


def _client_with_handler(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return s4.NotionClient("ntn_FAKE", client=http)


def _seed_existing(
    db_path: Path,
    *,
    notion_page_id: str = "EXISTING-PAGE",
    titulo: str = "Post One",
    html: str | None = "<p>fresh body v2</p>",
) -> sqlite3.Connection:
    """Seed one promoted item already linked to a Notion page (post-fase2 state)."""
    conn = init_sqlite(db_path)
    s4.ensure_notion_page_id_column(conn)
    conn.execute(
        "INSERT INTO discovered_items "
        "(url_canonica, referente_id, referente_nombre, canal, titulo, "
        " publicado_en, primera_vez_visto, promovido_a_candidato_at, "
        " contenido_html, contenido_extraido_at, notion_page_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("https://yt.test/v1", "ref1", "Ref One", "youtube", titulo,
         "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z",
         "2024-01-02T00:00:00Z",
         html, "2024-01-01T00:00:00Z" if html else None,
         notion_page_id),
    )
    conn.commit()
    return conn


# ---------- select_pending: include_existing flag ----------


class TestSelectPendingIncludeExisting:
    def test_default_excludes_items_with_notion_page_id(self, tmp_path: Path):
        conn = _seed_existing(tmp_path / "db.sqlite")
        items = s4.select_pending(conn)
        assert items == []

    def test_include_existing_returns_those_items(self, tmp_path: Path):
        conn = _seed_existing(tmp_path / "db.sqlite")
        items = s4.select_pending(conn, include_existing=True)
        assert len(items) == 1
        assert items[0]["notion_page_id"] == "EXISTING-PAGE"


# ---------- Default OFF: no regression on already_present ----------


class TestDefaultOffNoRegression:
    def test_already_present_skips_patch_and_delete(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_existing(tmp_path / "db.sqlite")
        items = s4.select_pending(conn, include_existing=True)

        calls: list[tuple[str, str]] = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append((req.method, req.url.path))
            if req.method == "POST" and req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": [{"id": "EXISTING-PAGE"}]})
            return httpx.Response(404, json={})

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS", referentes_index={"ref one": "REFPAGE"},
                commit=True, update_existing=False,  # explicit default OFF
            )
        finally:
            client.close()

        assert summary.already_present == 1
        assert summary.updated == 0
        assert summary.errors == 0
        # No PATCH and no DELETE issued under default behaviour.
        methods = {m for m, _ in calls}
        assert "PATCH" not in methods
        assert "DELETE" not in methods


# ---------- Flag ON: PATCH page + DELETE blocks + PATCH children ----------


class TestUpdateExistingHappyPath:
    def test_flag_triggers_patch_delete_append(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_existing(tmp_path / "db.sqlite",
                              titulo="Post One [v2-clean]",
                              html="<h2>nuevo</h2><p>cuerpo limpio</p>")
        items = s4.select_pending(conn, include_existing=True)
        assert len(items) == 1

        # Simulate page has 3 stale block children to delete.
        existing_blocks = [{"id": f"BLOCK-{i}"} for i in range(3)]
        calls: list[tuple[str, str, dict | None]] = []

        def handler(req: httpx.Request) -> httpx.Response:
            body = None
            if req.method in {"POST", "PATCH"}:
                try:
                    import json as _json
                    body = _json.loads(req.content) if req.content else None
                except Exception:
                    body = None
            calls.append((req.method, req.url.path, body))

            if req.method == "POST" and req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": [{"id": "EXISTING-PAGE"}]})
            if req.method == "PATCH" and req.url.path == "/v1/pages/EXISTING-PAGE":
                return httpx.Response(200, json={"id": "EXISTING-PAGE"})
            if req.method == "GET" and req.url.path == "/v1/blocks/EXISTING-PAGE/children":
                return httpx.Response(200, json={"results": existing_blocks, "has_more": False})
            if req.method == "DELETE" and req.url.path.startswith("/v1/blocks/BLOCK-"):
                return httpx.Response(200, json={})
            if req.method == "PATCH" and req.url.path == "/v1/blocks/EXISTING-PAGE/children":
                return httpx.Response(200, json={})
            return httpx.Response(404, json={"path": str(req.url.path)})

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS", referentes_index={"ref one": "REFPAGE"},
                commit=True, update_existing=True,
            )
        finally:
            client.close()

        assert summary.updated == 1
        assert summary.already_present == 0
        assert summary.errors == 0

        outcome = next(o for o in summary.items if o.sqlite_id == items[0]["rowid"])
        assert outcome.status == "updated"
        assert outcome.deleted_blocks == 3
        assert outcome.appended_blocks >= 1

        methods = [m for m, _, _ in calls]
        assert methods.count("PATCH") == 2  # /pages/{id} + /blocks/{id}/children
        assert methods.count("DELETE") == 3
        assert methods.count("GET") >= 1

        # PATCH /pages payload includes the (still-suffixed) title from sqlite.
        patch_pages = [(m, p, b) for m, p, b in calls
                       if m == "PATCH" and p == "/v1/pages/EXISTING-PAGE"]
        assert patch_pages, "no PATCH /pages issued"
        title_content = (
            patch_pages[0][2]["properties"]["Título"]["title"][0]["text"]["content"]
        )
        assert title_content == "Post One [v2-clean]"


class TestUpdateExistingPaginatedChildren:
    def test_paginated_get_blocks_then_delete_all(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_existing(tmp_path / "db.sqlite")
        items = s4.select_pending(conn, include_existing=True)

        # 1st page: 2 blocks, has_more=True; 2nd page: 1 block, has_more=False.
        get_calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.method == "POST" and req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": [{"id": "EXISTING-PAGE"}]})
            if req.method == "PATCH":
                return httpx.Response(200, json={})
            if req.method == "GET" and "/blocks/EXISTING-PAGE/children" in req.url.path:
                get_calls["n"] += 1
                if get_calls["n"] == 1:
                    return httpx.Response(200, json={
                        "results": [{"id": "B1"}, {"id": "B2"}],
                        "has_more": True, "next_cursor": "CUR1",
                    })
                return httpx.Response(200, json={
                    "results": [{"id": "B3"}], "has_more": False,
                })
            if req.method == "DELETE":
                return httpx.Response(200, json={})
            return httpx.Response(404, json={})

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS", referentes_index={},
                commit=True, update_existing=True,
            )
        finally:
            client.close()

        outcome = next(o for o in summary.items if o.sqlite_id == items[0]["rowid"])
        assert outcome.deleted_blocks == 3  # 2 from page 1 + 1 from page 2


# ---------- Edge: contenido_html=NULL ----------


class TestUpdateExistingNullBody:
    def test_null_html_falls_back_to_no_body_block(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_existing(tmp_path / "db.sqlite", html=None)
        items = s4.select_pending(conn, include_existing=True)

        appended_payload: dict[str, Any] = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.method == "POST" and req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": [{"id": "EXISTING-PAGE"}]})
            if req.method == "PATCH" and req.url.path == "/v1/blocks/EXISTING-PAGE/children":
                import json as _json
                appended_payload.update(_json.loads(req.content))
                return httpx.Response(200, json={})
            if req.method == "PATCH":
                return httpx.Response(200, json={})
            if req.method == "GET":
                return httpx.Response(200, json={"results": [], "has_more": False})
            if req.method == "DELETE":
                return httpx.Response(200, json={})
            return httpx.Response(404, json={})

        client = _client_with_handler(handler)
        try:
            summary = s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS", referentes_index={},
                commit=True, update_existing=True,
            )
        finally:
            client.close()

        outcome = next(o for o in summary.items if o.sqlite_id == items[0]["rowid"])
        assert outcome.status == "updated"
        assert outcome.appended_blocks == 1
        assert appended_payload["children"] == [s4.fallback_no_body_block()]


# ---------- Rate limit ----------


class TestUpdateExistingRateLimit:
    def test_sleep_called_between_calls(self, tmp_path: Path, monkeypatch):
        sleeps: list[float] = []
        monkeypatch.setattr(s4.time, "sleep", lambda s: sleeps.append(s))
        conn = _seed_existing(tmp_path / "db.sqlite")
        items = s4.select_pending(conn, include_existing=True)

        def handler(req: httpx.Request) -> httpx.Response:
            if req.method == "POST" and req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": [{"id": "EXISTING-PAGE"}]})
            if req.method == "GET":
                return httpx.Response(200, json={
                    "results": [{"id": "B1"}], "has_more": False,
                })
            return httpx.Response(200, json={})

        client = _client_with_handler(handler)
        try:
            s4.process_items(
                client=client, conn=conn, items=items,
                data_source_id="DS", referentes_index={},
                commit=True, update_existing=True,
            )
        finally:
            client.close()

        # Expect at least one sleep at RATE_LIMIT_SLEEP_S between each Notion call:
        # query, patch_page, get_children, delete_block, append_children → ≥5.
        rl_sleeps = [s for s in sleeps if s == s4.RATE_LIMIT_SLEEP_S]
        assert len(rl_sleeps) >= 5, f"too few rate-limit sleeps: {rl_sleeps}"


# ---------- Idempotence: 2nd run renders identical content ----------


class TestUpdateExistingIdempotent:
    def test_double_run_renders_identical_appended_payload(
        self, tmp_path: Path, monkeypatch,
    ):
        """Double run with same sqlite state → same rendered children both times.

        Note: this script does NOT short-circuit on identical content (by design,
        keeps stage4 simple). Test asserts the payload is byte-identical so an
        operator can confirm 'no drift' without diffing Notion responses.
        """
        monkeypatch.setattr(s4.time, "sleep", lambda s: None)
        conn = _seed_existing(tmp_path / "db.sqlite",
                              html="<p>cuerpo estable</p>")
        items = s4.select_pending(conn, include_existing=True)

        captured: list[dict] = []

        def handler(req: httpx.Request) -> httpx.Response:
            if req.method == "POST" and req.url.path.endswith("/data_sources/DS/query"):
                return httpx.Response(200, json={"results": [{"id": "EXISTING-PAGE"}]})
            if req.method == "PATCH" and req.url.path == "/v1/blocks/EXISTING-PAGE/children":
                import json as _json
                captured.append(_json.loads(req.content))
                return httpx.Response(200, json={})
            if req.method == "PATCH":
                return httpx.Response(200, json={})
            if req.method == "GET":
                return httpx.Response(200, json={"results": [], "has_more": False})
            if req.method == "DELETE":
                return httpx.Response(200, json={})
            return httpx.Response(404, json={})

        client = _client_with_handler(handler)
        try:
            for _ in range(2):
                # Reload items to simulate a fresh run.
                items_run = s4.select_pending(conn, include_existing=True)
                s4.process_items(
                    client=client, conn=conn, items=items_run,
                    data_source_id="DS", referentes_index={},
                    commit=True, update_existing=True,
                )
        finally:
            client.close()

        assert len(captured) == 2
        assert captured[0] == captured[1], "payload drifted between runs"
