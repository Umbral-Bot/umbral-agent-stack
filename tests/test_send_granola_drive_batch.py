"""
Tests for scripts/vm/send_granola_drive_batch.py (P1.1b Phase 4 sender).
"""

import os
from unittest.mock import patch

import pytest

from scripts.vm.send_granola_drive_batch import (
    resolve_worker_config,
    run_batch,
    select_items,
)


def _item(relative_path, action="update_transcript"):
    return {
        "relative_path": relative_path,
        "action": action,
        "match_strategy": "normalized_title_date",
        "matched_page": {"page_id": "p1", "url": "https://notion.so/p1"},
        "payload": {"title": "X", "content": "Me: hola", "dry_run": True},
    }


class TestResolveWorkerConfig:
    def test_uses_explicit_args_over_env(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://env-url")
        monkeypatch.setenv("WORKER_TOKEN", "env-token")
        url, token = resolve_worker_config("http://explicit-url/", "explicit-token")
        assert url == "http://explicit-url"
        assert token == "explicit-token"

    def test_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://127.0.0.1:8088/")
        monkeypatch.setenv("WORKER_TOKEN", "secret")
        url, token = resolve_worker_config()
        assert url == "http://127.0.0.1:8088"
        assert token == "secret"

    def test_missing_url_raises(self, monkeypatch):
        monkeypatch.delenv("WORKER_URL", raising=False)
        monkeypatch.setenv("WORKER_TOKEN", "secret")
        with pytest.raises(RuntimeError, match="WORKER_URL"):
            resolve_worker_config()

    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://127.0.0.1:8088")
        monkeypatch.delenv("WORKER_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="WORKER_TOKEN"):
            resolve_worker_config()


class TestSelectItems:
    def test_selects_by_relative_paths_preserving_order(self):
        items = [_item("a.md"), _item("b.md"), _item("c.md")]
        selected, missing = select_items(items, relative_paths=["c.md", "a.md"])
        assert [i["relative_path"] for i in selected] == ["c.md", "a.md"]
        assert missing == []

    def test_reports_missing_relative_paths(self):
        items = [_item("a.md")]
        selected, missing = select_items(items, relative_paths=["a.md", "ghost.md"])
        assert [i["relative_path"] for i in selected] == ["a.md"]
        assert missing == ["ghost.md"]

    def test_limit_takes_first_n(self):
        items = [_item("a.md"), _item("b.md"), _item("c.md")]
        selected, missing = select_items(items, limit=2)
        assert [i["relative_path"] for i in selected] == ["a.md", "b.md"]

    def test_no_filter_returns_all(self):
        items = [_item("a.md"), _item("b.md")]
        selected, missing = select_items(items)
        assert selected == items


class TestRunBatch:
    def test_dry_run_forced_true_without_execute(self):
        items = [_item("a.md")]
        with patch("scripts.vm.send_granola_drive_batch.post_task") as mock_post:
            mock_post.return_value = {"result": {"page_id": "p1", "url": "https://notion.so/p1", "dry_run": True}}
            run_batch(items, worker_url="http://x", worker_token="t", execute=False)
        sent_payload = mock_post.call_args[0][2]
        assert sent_payload["dry_run"] is True

    def test_execute_sets_dry_run_false(self):
        items = [_item("a.md")]
        with patch("scripts.vm.send_granola_drive_batch.post_task") as mock_post:
            mock_post.return_value = {"result": {"page_id": "p1", "url": "https://notion.so/p1", "dry_run": False}}
            run_batch(items, worker_url="http://x", worker_token="t", execute=True)
        sent_payload = mock_post.call_args[0][2]
        assert sent_payload["dry_run"] is False

    def test_success_row_shape(self):
        items = [_item("a.md")]
        with patch("scripts.vm.send_granola_drive_batch.post_task") as mock_post:
            mock_post.return_value = {
                "result": {
                    "page_id": "real-page",
                    "url": "https://notion.so/real-page",
                    "reconciliation_action": "reconcile",
                    "matched_existing": True,
                    "match_strategy": "normalized_title_date",
                    "resolved_title": "X",
                    "dry_run": False,
                }
            }
            results = run_batch(items, worker_url="http://x", worker_token="t", execute=True)
        assert results[0]["ok"] is True
        assert results[0]["page_id"] == "real-page"
        assert results[0]["matched_existing"] is True

    def test_one_failure_does_not_abort_remaining_items(self):
        items = [_item("a.md"), _item("b.md")]
        with patch("scripts.vm.send_granola_drive_batch.post_task") as mock_post:
            mock_post.side_effect = [RuntimeError("boom"), {"result": {"page_id": "p2", "url": "u2"}}]
            results = run_batch(items, worker_url="http://x", worker_token="t", execute=True)
        assert results[0]["ok"] is False
        assert "boom" in results[0]["error"]
        assert results[1]["ok"] is True
        assert results[1]["page_id"] == "p2"

    def test_handles_flat_response_without_result_wrapper(self):
        items = [_item("a.md")]
        with patch("scripts.vm.send_granola_drive_batch.post_task") as mock_post:
            mock_post.return_value = {"page_id": "flat-page", "url": "https://notion.so/flat"}
            results = run_batch(items, worker_url="http://x", worker_token="t", execute=True)
        assert results[0]["page_id"] == "flat-page"
