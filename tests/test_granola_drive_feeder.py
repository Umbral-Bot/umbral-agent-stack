"""
Tests for the recurring Drive->Notion Granola feeder (Q11-T1).

Covers the three things the one-shot P1.1b flow never needed: per-run caps,
the worker-verdict guard before any write, and the Notion snapshot pagination
that a daily run depends on.
"""

import json

import httpx
import pytest

from scripts.vm.granola_drive_feeder import (
    run_item,
    select_items,
    worker_verdict_agrees,
)
from scripts.vm.granola_notion_raw_snapshot import (
    MAX_PAGES,
    build_record,
    build_snapshot,
    fetch_pages,
    resolve_notion_config,
)


def _item(relative_path, action="create"):
    return {
        "relative_path": relative_path,
        "action": action,
        "match_strategy": "",
        "matched_page": None,
        "payload": {"title": relative_path, "content": "x", "dry_run": True},
    }


class TestSelectItems:
    def test_caps_creates_and_defers_the_rest(self):
        batch = [_item(f"Granola/c{i}.md") for i in range(15)]
        selected, deferred = select_items(batch, max_creates=10, max_updates=10)
        assert len(selected) == 10
        assert len(deferred) == 5

    def test_creates_and_updates_have_independent_caps(self):
        batch = [_item(f"Granola/c{i}.md") for i in range(3)]
        batch += [_item(f"Granola/u{i}.md", "update_transcript") for i in range(3)]
        selected, deferred = select_items(batch, max_creates=2, max_updates=1)
        assert [i["action"] for i in selected] == ["create", "create", "update_transcript"]
        assert len(deferred) == 3

    def test_preserves_order_so_a_backlog_drains_oldest_first(self):
        batch = [_item(f"Granola/c{i}.md") for i in range(5)]
        selected, deferred = select_items(batch, max_creates=2, max_updates=0)
        assert [i["relative_path"] for i in selected] == ["Granola/c0.md", "Granola/c1.md"]
        assert [i["relative_path"] for i in deferred] == [
            "Granola/c2.md",
            "Granola/c3.md",
            "Granola/c4.md",
        ]

    def test_unknown_actions_are_never_selected(self):
        batch = [_item("Granola/a.md", "review_ambiguous"), _item("Granola/b.md", "skip")]
        selected, deferred = select_items(batch, max_creates=10, max_updates=10)
        assert selected == []
        assert len(deferred) == 2

    def test_zero_cap_selects_nothing(self):
        batch = [_item("Granola/a.md")]
        selected, deferred = select_items(batch, max_creates=0, max_updates=0)
        assert selected == []
        assert len(deferred) == 1


class TestWorkerVerdict:
    def test_create_agrees_when_worker_matched_nothing(self):
        assert worker_verdict_agrees("create", {"matched_existing": False}) is True

    def test_create_disagrees_when_worker_found_a_page(self):
        assert worker_verdict_agrees("create", {"matched_existing": True}) is False

    def test_update_agrees_only_when_worker_matched(self):
        assert worker_verdict_agrees("update_transcript", {"matched_existing": True}) is True
        assert worker_verdict_agrees("update_transcript", {"matched_existing": False}) is False

    def test_unknown_action_never_agrees(self):
        assert worker_verdict_agrees("skip", {"matched_existing": True}) is False


class _FakeWorker:
    """Records every call so a test can assert no second (write) call happened."""

    def __init__(self, dry_result, execute_result=None, raise_on=None):
        self.dry_result = dry_result
        self.execute_result = execute_result or {}
        self.raise_on = raise_on
        self.calls = []

    def __call__(self, url, token, payload):
        self.calls.append(dict(payload))
        if self.raise_on == len(self.calls):
            raise RuntimeError("boom")
        if payload.get("dry_run"):
            return {"result": self.dry_result}
        return {"result": self.execute_result}


class TestRunItem:
    def test_dry_run_mode_never_sends_a_write(self, monkeypatch):
        fake = _FakeWorker({"matched_existing": False, "reconciliation_action": "create"})
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=False)
        assert row["ok"] is True
        assert row["executed"] is False
        assert len(fake.calls) == 1
        assert fake.calls[0]["dry_run"] is True

    def test_execute_writes_after_a_matching_dry_run(self, monkeypatch):
        fake = _FakeWorker(
            {"matched_existing": False, "reconciliation_action": "create"},
            {"page_id": "p1", "url": "https://notion.so/p1", "reconciliation_action": "create"},
        )
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["executed"] is True
        assert row["page_id"] == "p1"
        assert [c["dry_run"] for c in fake.calls] == [True, False]

    def test_create_whose_dry_run_matched_an_existing_page_is_not_written(self, monkeypatch):
        fake = _FakeWorker({"matched_existing": True, "reconciliation_action": "reconcile"})
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["ok"] is False
        assert row["executed"] is False
        assert "disagrees" in row["error"]
        # The guard has to stop BEFORE the write, not report it afterwards.
        assert len(fake.calls) == 1

    def test_a_failing_dry_run_is_reported_not_raised(self, monkeypatch):
        fake = _FakeWorker({}, raise_on=1)
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["ok"] is False
        assert "dry-run failed" in row["error"]

    def test_a_failing_write_is_reported_not_raised(self, monkeypatch):
        fake = _FakeWorker({"matched_existing": False}, raise_on=2)
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["ok"] is False
        assert row["executed"] is False
        assert "execute failed" in row["error"]


def _notion_page(page_id, title, date, *, fuente="granola_drive_md", length=100, traceability=""):
    return {
        "id": page_id,
        "url": f"https://notion.so/{page_id}",
        "properties": {
            "Nombre": {"type": "title", "title": [{"plain_text": title}]},
            "Fecha": {"type": "date", "date": {"start": date}},
            "Fuente": {"type": "select", "select": {"name": fuente}},
            "Longitud Notion": {"type": "number", "number": length},
            "Trazabilidad": {"type": "rich_text", "rich_text": [{"plain_text": traceability}]},
        },
    }


class TestSnapshot:
    def test_record_carries_the_fields_the_gap_check_reads(self):
        page = _notion_page(
            "p1",
            "BIM Forum",
            "2026-07-13",
            fuente="granola_mcp",
            length=3600,
            traceability="shared_folder_path=Granola/BIM Forum.md\nsha1=abc",
        )
        record = build_record(page)
        assert record["page_id"] == "p1"
        assert record["normalized_title"] == "bim forum"
        assert record["date"] == "2026-07-13"
        assert record["fuente"] == "granola_mcp"
        assert record["longitud_notion"] == 3600
        assert record["shared_folder_path"] == "Granola/BIM Forum.md"
        assert record["sha1"] == "abc"

    def test_missing_length_becomes_zero_not_none(self):
        page = _notion_page("p1", "X", "2026-01-01")
        page["properties"]["Longitud Notion"]["number"] = None
        assert build_record(page)["longitud_notion"] == 0

    def test_snapshot_shape_matches_the_gap_check_contract(self):
        snapshot = build_snapshot([_notion_page("p1", "X", "2026-01-01")])
        assert snapshot["count"] == 1
        assert isinstance(snapshot["records"], list)
        json.dumps(snapshot)  # must stay serializable

    def test_fetch_pages_follows_the_cursor_to_the_end(self):
        batches = [
            {"results": [_notion_page("p1", "A", "2026-01-01")], "has_more": True, "next_cursor": "c1"},
            {"results": [_notion_page("p2", "B", "2026-01-02")], "has_more": False},
        ]
        seen_cursors = []

        def handler(request):
            body = json.loads(request.content)
            seen_cursors.append(body.get("start_cursor"))
            return httpx.Response(200, json=batches[len(seen_cursors) - 1])

        client = httpx.Client(transport=httpx.MockTransport(handler))
        pages = fetch_pages("key", "db", client=client)
        assert [p["id"] for p in pages] == ["p1", "p2"]
        assert seen_cursors == [None, "c1"]

    def test_fetch_pages_raises_on_a_notion_error_instead_of_returning_partial(self):
        def handler(request):
            return httpx.Response(401, text='{"code":"unauthorized"}')

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(RuntimeError, match="401"):
            fetch_pages("key", "db", client=client)

    def test_fetch_pages_refuses_an_endless_cursor_walk(self):
        def handler(request):
            return httpx.Response(200, json={"results": [], "has_more": True, "next_cursor": "c"})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(RuntimeError, match="pagination exceeded"):
            fetch_pages("key", "db", client=client)
        assert MAX_PAGES > 0

    def test_stops_when_has_more_is_true_but_no_cursor_is_given(self):
        def handler(request):
            return httpx.Response(200, json={"results": [], "has_more": True})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        assert fetch_pages("key", "db", client=client) == []


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
