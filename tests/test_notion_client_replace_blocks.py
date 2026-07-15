"""
Tests for worker/notion_client.py::replace_blocks_in_page.

Covers the P1.1b fix: large legacy block counts (previously a fully
sequential per-block DELETE loop with no retry, which could exceed any
caller timeout and leave the page half-updated) now delete with bounded
concurrency and retry on 429 with backoff.
"""

from __future__ import annotations

import json as _json
import threading

import httpx
import pytest

from worker import config, notion_client


# Captured before any test monkeypatches notion_client.httpx.Client — since
# `notion_client.httpx` is the same shared module object as the top-level
# `httpx` import here, patching one patches the other, and a factory that
# calls `httpx.Client(...)` at call-time would recurse into itself.
_RealClient = httpx.Client


def _client_factory(handler):
    def factory(*args, **kwargs):
        return _RealClient(transport=httpx.MockTransport(handler))
    return factory


@pytest.fixture(autouse=True)
def _notion_api_key(monkeypatch):
    monkeypatch.setattr(config, "NOTION_API_KEY", "test-key")


class TestReplaceBlocksInPageValidation:
    def test_requires_api_key(self, monkeypatch):
        monkeypatch.setattr(config, "NOTION_API_KEY", None)
        with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
            notion_client.replace_blocks_in_page("page-1", [{"type": "paragraph"}])

    def test_requires_page_id(self):
        with pytest.raises(ValueError, match="page_id is required"):
            notion_client.replace_blocks_in_page("", [{"type": "paragraph"}])

    def test_requires_non_empty_blocks(self):
        with pytest.raises(ValueError, match="blocks must be a non-empty list"):
            notion_client.replace_blocks_in_page("page-1", [])


class TestReplaceBlocksInPage:
    def test_small_page_deletes_all_and_creates_new(self, monkeypatch):
        existing = [{"id": f"old-{i}"} for i in range(5)]
        deleted_ids: list[str] = []
        lock = threading.Lock()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and "/children" in str(request.url):
                return httpx.Response(200, json={"results": existing, "has_more": False})
            if request.method == "DELETE":
                block_id = str(request.url).rsplit("/", 1)[-1]
                with lock:
                    deleted_ids.append(block_id)
                return httpx.Response(200, json={"id": block_id})
            if request.method == "PATCH":
                return httpx.Response(200, json={"results": []})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))

        result = notion_client.replace_blocks_in_page(
            "page-1", [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        )

        assert sorted(deleted_ids) == sorted(f"old-{i}" for i in range(5))
        assert result == {"blocks_replaced": 1, "blocks_removed": 5, "page_id": "page-1"}

    def test_large_legacy_block_count_all_deleted_exactly_once(self, monkeypatch):
        n = 250
        existing = [{"id": f"old-{i}"} for i in range(n)]
        deleted_ids: list[str] = []
        lock = threading.Lock()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"results": existing, "has_more": False})
            if request.method == "DELETE":
                block_id = str(request.url).rsplit("/", 1)[-1]
                with lock:
                    deleted_ids.append(block_id)
                return httpx.Response(200, json={"id": block_id})
            if request.method == "PATCH":
                return httpx.Response(200, json={"results": []})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))

        result = notion_client.replace_blocks_in_page(
            "page-1", [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        )

        assert len(deleted_ids) == n
        assert len(set(deleted_ids)) == n  # no double-deletes from concurrency
        assert result["blocks_removed"] == n

    def test_paginates_existing_block_listing(self, monkeypatch):
        page1 = [{"id": "a"}]
        page2 = [{"id": "b"}]
        get_calls: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                get_calls.append(dict(request.url.params))
                if "start_cursor" not in request.url.params:
                    return httpx.Response(
                        200, json={"results": page1, "has_more": True, "next_cursor": "cursor-1"}
                    )
                return httpx.Response(200, json={"results": page2, "has_more": False})
            if request.method in ("DELETE", "PATCH"):
                return httpx.Response(200, json={})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))
        result = notion_client.replace_blocks_in_page("page-1", [{"type": "paragraph"}])

        assert result["blocks_removed"] == 2
        assert len(get_calls) == 2
        assert get_calls[1]["start_cursor"] == "cursor-1"

    def test_retries_on_429_then_succeeds(self, monkeypatch):
        sleep_calls: list[float] = []
        monkeypatch.setattr(notion_client.time, "sleep", lambda s: sleep_calls.append(s))
        attempts = {"delete": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"results": [{"id": "old-1"}], "has_more": False})
            if request.method == "DELETE":
                attempts["delete"] += 1
                if attempts["delete"] == 1:
                    return httpx.Response(429, headers={"Retry-After": "2"}, json={})
                return httpx.Response(200, json={})
            if request.method == "PATCH":
                return httpx.Response(200, json={})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))
        result = notion_client.replace_blocks_in_page("page-1", [{"type": "paragraph"}])

        assert attempts["delete"] == 2
        assert sleep_calls == [2.0]
        assert result["blocks_removed"] == 1

    def test_429_without_retry_after_uses_exponential_backoff(self, monkeypatch):
        sleep_calls: list[float] = []
        monkeypatch.setattr(notion_client.time, "sleep", lambda s: sleep_calls.append(s))
        attempts = {"delete": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"results": [{"id": "old-1"}], "has_more": False})
            if request.method == "DELETE":
                attempts["delete"] += 1
                if attempts["delete"] <= 2:
                    return httpx.Response(429, json={})
                return httpx.Response(200, json={})
            if request.method == "PATCH":
                return httpx.Response(200, json={})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))
        result = notion_client.replace_blocks_in_page("page-1", [{"type": "paragraph"}])

        assert attempts["delete"] == 3
        assert sleep_calls == [1.0, 2.0]
        assert result["blocks_removed"] == 1

    def test_429_exhausts_retries_raises_runtime_error(self, monkeypatch):
        monkeypatch.setattr(notion_client.time, "sleep", lambda s: None)
        monkeypatch.setattr(notion_client, "MAX_429_RETRIES", 1)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"results": [{"id": "old-1"}], "has_more": False})
            if request.method == "DELETE":
                return httpx.Response(429, json={})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))

        with pytest.raises(RuntimeError, match="429"):
            notion_client.replace_blocks_in_page("page-1", [{"type": "paragraph"}])

    def test_no_existing_blocks_skips_delete_phase(self, monkeypatch):
        delete_calls: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"results": [], "has_more": False})
            if request.method == "DELETE":
                delete_calls.append(1)
                return httpx.Response(200, json={})
            if request.method == "PATCH":
                return httpx.Response(200, json={})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))
        result = notion_client.replace_blocks_in_page("page-1", [{"type": "paragraph"}])

        assert delete_calls == []
        assert result["blocks_removed"] == 0

    def test_skips_blocks_with_missing_id_but_counts_them_removed(self, monkeypatch):
        existing = [{"id": "old-1"}, {}]
        deleted_urls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"results": existing, "has_more": False})
            if request.method == "DELETE":
                deleted_urls.append(str(request.url))
                return httpx.Response(200, json={})
            if request.method == "PATCH":
                return httpx.Response(200, json={})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))
        result = notion_client.replace_blocks_in_page("page-1", [{"type": "paragraph"}])

        assert len(deleted_urls) == 1
        assert result["blocks_removed"] == 2  # preserves prior counting semantics

    def test_creates_new_blocks_in_chunks_of_100(self, monkeypatch):
        patch_bodies: list[list] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"results": [], "has_more": False})
            if request.method == "PATCH":
                patch_bodies.append(_json.loads(request.content)["children"])
                return httpx.Response(200, json={})
            return httpx.Response(404)

        monkeypatch.setattr(notion_client.httpx, "Client", _client_factory(handler))
        blocks = [{"type": "paragraph", "n": i} for i in range(250)]
        result = notion_client.replace_blocks_in_page("page-1", blocks)

        assert [len(b) for b in patch_bodies] == [100, 100, 50]
        assert result["blocks_replaced"] == 250
