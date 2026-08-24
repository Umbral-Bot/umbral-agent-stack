"""
Tests for scripts/vm/granola_notion_raw_snapshot.py.

The snapshot is the Notion half of the gap-check. A short or wrong-shaped one
is worse than none: every page it misses reads as "not in Notion" and the
gap-check proposes a duplicate for it.
"""

import json

import httpx
import pytest

from scripts.vm.granola_notion_raw_snapshot import (
    MAX_REQUESTS,
    build_record,
    build_snapshot,
    fetch_pages,
    resolve_notion_config,
)


def _page(page_id, title, date, *, fuente_prop=None, traceability=""):
    properties = {
        "Nombre": {"type": "title", "title": [{"plain_text": title}]},
        "Fecha": {"type": "date", "date": {"start": date}},
        "Trazabilidad": {"type": "rich_text", "rich_text": [{"plain_text": traceability}]},
    }
    if fuente_prop is not None:
        properties["Fuente"] = fuente_prop
    return {"id": page_id, "url": f"https://notion.so/{page_id}", "properties": properties}


def _select(name):
    return {"type": "select", "select": {"name": name}}


class TestBuildRecord:
    def test_carries_the_fields_the_gap_check_reads(self):
        record = build_record(
            _page(
                "p1",
                "BIM Forum",
                "2026-07-13",
                fuente_prop=_select("granola_mcp"),
                traceability="shared_folder_path=Granola/BIM Forum.md\nsha1=abc",
            )
        )
        assert record["page_id"] == "p1"
        assert record["normalized_title"] == "bim forum"
        assert record["date"] == "2026-07-13"
        assert record["fuente"] == "granola_mcp"
        assert record["shared_folder_path"] == "Granola/BIM Forum.md"
        assert record["sha1"] == "abc"

    def test_fuente_survives_the_column_being_typed_rich_text(self):
        # The worker's write side accepts select/rich_text for this column, so
        # a reader that only understood `select` would silently blank it -- and
        # the gap-check's "this page is a summary from another source" note
        # would stop firing.
        record = build_record(
            _page(
                "p1",
                "X",
                "2026-01-01",
                fuente_prop={"type": "rich_text", "rich_text": [{"plain_text": "granola_mcp"}]},
            )
        )
        assert record["fuente"] == "granola_mcp"

    def test_fuente_falls_back_to_the_english_column_name(self):
        page = _page("p1", "X", "2026-01-01")
        page["properties"]["Source"] = _select("granola")
        assert build_record(page)["fuente"] == "granola"

    def test_a_page_with_no_fuente_at_all_is_blank_not_a_crash(self):
        assert build_record(_page("p1", "X", "2026-01-01"))["fuente"] == ""

    def test_a_page_with_no_sha1_carries_an_empty_one(self):
        # This is what keeps the gap-check's sha1 tier from ever skipping a
        # page written from a different source.
        assert build_record(_page("p1", "X", "2026-01-01"))["sha1"] == ""


class TestBuildSnapshot:
    def test_shape_matches_the_gap_check_contract(self):
        snapshot = build_snapshot([_page("p1", "X", "2026-01-01")])
        assert snapshot["count"] == 1
        assert isinstance(snapshot["records"], list)
        json.dumps(snapshot)  # must stay serializable

    def test_empty_input_yields_an_empty_snapshot(self):
        assert build_snapshot([]) == {"count": 0, "records": []}


class TestFetchPages:
    def test_follows_the_cursor_to_the_end(self):
        batches = [
            {"results": [_page("p1", "A", "2026-01-01")], "has_more": True, "next_cursor": "c1"},
            {"results": [_page("p2", "B", "2026-01-02")], "has_more": False},
        ]
        seen_cursors = []

        def handler(request):
            seen_cursors.append(json.loads(request.content).get("start_cursor"))
            return httpx.Response(200, json=batches[len(seen_cursors) - 1])

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            pages = fetch_pages("key", "db", client=client)
        assert [p["id"] for p in pages] == ["p1", "p2"]
        assert seen_cursors == [None, "c1"]

    def test_raises_on_a_notion_error_instead_of_returning_partial(self):
        def handler(request):
            return httpx.Response(401, text='{"code":"unauthorized"}')

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(RuntimeError, match="401"):
                fetch_pages("key", "db", client=client)

    def test_refuses_an_endless_cursor_walk(self):
        def handler(request):
            return httpx.Response(200, json={"results": [], "has_more": True, "next_cursor": "c"})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(RuntimeError, match="pagination exceeded"):
                fetch_pages("key", "db", client=client)

    def test_has_more_with_no_cursor_raises_rather_than_truncating(self):
        # Returning what we have here would hand the gap-check a short snapshot
        # and it would propose a duplicate for every page not in it.
        def handler(request):
            return httpx.Response(200, json={"results": [], "has_more": True})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(RuntimeError, match="no next_cursor"):
                fetch_pages("key", "db", client=client)

    def test_request_budget_allows_far_more_rows_than_the_db_holds(self):
        # 100 requests x page_size 100; the DB held 134 rows on 2026-08-23.
        assert MAX_REQUESTS * 100 > 10_000 - 1


class TestResolveNotionConfig:
    def test_reads_env_when_no_args(self, monkeypatch):
        monkeypatch.setenv("NOTION_API_KEY", "k")
        monkeypatch.setenv("NOTION_GRANOLA_DB_ID", "d")
        assert resolve_notion_config() == ("k", "d")

    def test_explicit_args_win_over_env(self, monkeypatch):
        monkeypatch.setenv("NOTION_API_KEY", "k")
        monkeypatch.setenv("NOTION_GRANOLA_DB_ID", "d")
        assert resolve_notion_config("k2", "d2") == ("k2", "d2")

    def test_missing_key_fails_loud(self, monkeypatch):
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        monkeypatch.setenv("NOTION_GRANOLA_DB_ID", "d")
        with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
            resolve_notion_config()

    def test_missing_database_id_fails_loud(self, monkeypatch):
        monkeypatch.setenv("NOTION_API_KEY", "k")
        monkeypatch.delenv("NOTION_GRANOLA_DB_ID", raising=False)
        with pytest.raises(RuntimeError, match="NOTION_GRANOLA_DB_ID"):
            resolve_notion_config()
