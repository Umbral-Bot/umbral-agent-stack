"""Tests for scripts/discovery/stage7_5_post_review_comment.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from scripts.discovery import stage7_5_post_review_comment as mod


class _FakeClient:
    def __init__(self, existing_comments: list[dict] | None = None):
        self.existing = existing_comments or []
        self.posted: list[dict] = []

    def get(self, path: str, params=None, **kwargs):
        assert path == "/comments"
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"results": self.existing, "has_more": False}
        return resp

    def post(self, path: str, json=None, **kwargs):
        assert path == "/comments"
        self.posted.append(json)
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"id": "comment-new", "object": "comment"}
        return resp


def _comment(text: str) -> dict:
    return {
        "id": "c1",
        "rich_text": [{"type": "text", "plain_text": text}],
    }


def test_posts_comment_when_no_existing():
    client = _FakeClient()
    result = mod.post_review_comment(client, "page-x", "Mi copy linkedin de prueba")
    assert result["action"] == "posted"
    assert result["comment_id"] == "comment-new"
    assert client.posted, "expected one POST"
    body = client.posted[0]
    assert body["parent"] == {"page_id": "page-x"}
    assert body["rich_text"][0]["type"] == "text"
    assert mod.REVIEW_COMMENT_MARKER in body["rich_text"][0]["text"]["content"]


def test_skips_when_duplicate_exists():
    preview = "Mi copy linkedin de prueba"
    existing_text = mod.render_comment_text(preview)
    client = _FakeClient(existing_comments=[_comment(existing_text)])
    result = mod.post_review_comment(client, "page-x", preview)
    assert result["action"] == "skipped"
    assert result["reason"] == "duplicate_marker_and_preview"
    assert client.posted == []


def test_reposts_when_preview_changed():
    old_preview = "Old copy preview"
    new_preview = "Brand new copy preview"
    existing = _comment(mod.render_comment_text(old_preview))
    client = _FakeClient(existing_comments=[existing])
    result = mod.post_review_comment(client, "page-x", new_preview)
    assert result["action"] == "posted"
    assert client.posted, "should re-post when preview content changed"


def test_truncates_long_copy_to_preview_limit():
    long_copy = "A" * (mod.PREVIEW_LIMIT + 100)
    client = _FakeClient()
    result = mod.post_review_comment(client, "page-x", long_copy)
    assert result["preview"].endswith("…")
    assert len(result["preview"]) <= mod.PREVIEW_LIMIT + 1  # +1 for ellipsis char


def test_uses_real_user_mention_when_id_provided():
    client = _FakeClient()
    mod.post_review_comment(
        client, "page-x", "Preview", david_user_id="user-david-uuid"
    )
    rt = client.posted[0]["rich_text"]
    types = [n["type"] for n in rt]
    assert "mention" in types
    mention_node = next(n for n in rt if n["type"] == "mention")
    assert mention_node["mention"]["type"] == "user"
    assert mention_node["mention"]["user"]["id"] == "user-david-uuid"
    # The literal '@David' should NOT appear inside any text node when a
    # mention is used.
    text_blob = "".join(
        n["text"]["content"] for n in rt if n["type"] == "text"
    )
    assert "@David" not in text_blob


def test_falls_back_to_literal_mention_when_no_user_id():
    client = _FakeClient()
    mod.post_review_comment(client, "page-x", "Preview")
    rt = client.posted[0]["rich_text"]
    assert all(n["type"] == "text" for n in rt)
    assert "@David" in rt[0]["text"]["content"]


def test_truncate_preview_unit():
    s = mod._truncate_preview("hello\nworld   ", limit=20)
    assert "\n" not in s
    assert s == "hello world"


def test_render_comment_text_contains_marker():
    txt = mod.render_comment_text("preview")
    assert mod.REVIEW_COMMENT_MARKER in txt
    assert "preview" in txt
    assert "Estado=Autorizado" in txt
    assert "Estado=Rechazado" in txt
