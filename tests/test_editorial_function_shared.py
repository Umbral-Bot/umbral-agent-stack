"""Unit tests for functions/editorial-publish/shared.py (pure, stdlib-only).

Loaded by file path so we don't need the Azure Functions runtime on sys.path.
Validates payload checks, content-hash parity with the worker, and the
idempotent index.json upsert (no duplicate slugs, published_at desc order).
"""

import importlib.util
from pathlib import Path

import pytest

_SHARED_PATH = (
    Path(__file__).resolve().parent.parent
    / "functions"
    / "editorial-publish"
    / "shared.py"
)


def _load_shared():
    spec = importlib.util.spec_from_file_location("editorial_shared", _SHARED_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared = _load_shared()


def _valid_payload(**overrides):
    p = {
        "slug": "mi-slug",
        "title": "Mi título",
        "body_markdown": "## Cuerpo",
        "notion_page_id": "11111111-1111-1111-1111-111111111111",
        "content_hash": "abc123",
        "excerpt": "Una bajada",
        "tags": ["BIM", "IA"],
    }
    p.update(overrides)
    return p


class TestValidatePayload:
    def test_happy(self):
        clean = shared.validate_payload(_valid_payload())
        assert clean["slug"] == "mi-slug"
        assert clean["tags"] == ["BIM", "IA"]

    def test_missing_required(self):
        with pytest.raises(shared.PayloadError, match="missing required"):
            shared.validate_payload({"slug": "x"})

    @pytest.mark.parametrize("bad", ["Mi Slug", "slug_underscore", "-leading", "trailing-", "UPPER"])
    def test_bad_slug(self, bad):
        with pytest.raises(shared.PayloadError, match="slug"):
            shared.validate_payload(_valid_payload(slug=bad))

    def test_tags_must_be_list(self):
        with pytest.raises(shared.PayloadError, match="tags"):
            shared.validate_payload(_valid_payload(tags="BIM"))

    def test_tags_dedup(self):
        clean = shared.validate_payload(_valid_payload(tags=["BIM", "BIM", "IA"]))
        assert clean["tags"] == ["BIM", "IA"]


class TestContentHash:
    def test_deterministic(self):
        a = shared.compute_content_hash("body", "title", "excerpt")
        b = shared.compute_content_hash("body", "title", "excerpt")
        assert a == b and len(a) == 64

    def test_parity_with_worker(self):
        from worker.tasks.editorial_publish import _content_hash

        assert shared.compute_content_hash("b", "t", "e") == _content_hash("b", "t", "e")


class TestBuildPostDocument:
    def test_fills_defaults(self):
        doc = shared.build_post_document(
            _valid_payload(), canonical_base_url="https://umbralbim.io", now="2026-06-07T12:00:00Z"
        )
        assert doc["schema_version"] == 1
        assert doc["author"] == "David Moreira"
        assert doc["published_at"] == "2026-06-07T12:00:00Z"
        assert doc["updated_at"] == "2026-06-07T12:00:00Z"
        assert doc["canonical_url"] == "https://umbralbim.io/noticias/mi-slug"

    def test_respects_provided_canonical(self):
        doc = shared.build_post_document(
            _valid_payload(canonical_url="https://x.io/n/mi-slug"),
            canonical_base_url="https://umbralbim.io",
        )
        assert doc["canonical_url"] == "https://x.io/n/mi-slug"


class TestIndexUpsert:
    def _entry(self, slug, npid, pub, ch="h1"):
        return {
            "slug": slug,
            "title": slug,
            "excerpt": "",
            "hero_image_url": "",
            "published_at": pub,
            "tags": [],
            "notion_page_id": npid,
            "content_hash": ch,
        }

    def test_insert_into_empty(self):
        items, changed = shared.upsert_index(None, self._entry("a", "n1", "2026-01-01"))
        assert changed is True
        assert len(items) == 1

    def test_idempotent_no_change(self):
        e = self._entry("a", "n1", "2026-01-01")
        items, _ = shared.upsert_index([], e)
        items2, changed = shared.upsert_index(items, dict(e))
        assert changed is False
        assert len(items2) == 1

    def test_update_by_notion_id_on_slug_rename(self):
        items, _ = shared.upsert_index([], self._entry("old-slug", "n1", "2026-01-01"))
        items, changed = shared.upsert_index(items, self._entry("new-slug", "n1", "2026-01-02"))
        assert changed is True
        assert len(items) == 1  # no duplicate; replaced in place
        assert items[0]["slug"] == "new-slug"

    def test_update_by_slug_when_no_notion_match(self):
        items, _ = shared.upsert_index([], self._entry("a", "n1", "2026-01-01", ch="h1"))
        items, changed = shared.upsert_index(items, self._entry("a", "n2", "2026-01-01", ch="h2"))
        assert changed is True
        assert len(items) == 1
        assert items[0]["content_hash"] == "h2"

    def test_sorted_published_at_desc(self):
        items = []
        items, _ = shared.upsert_index(items, self._entry("a", "n1", "2026-01-01"))
        items, _ = shared.upsert_index(items, self._entry("c", "n3", "2026-03-01"))
        items, _ = shared.upsert_index(items, self._entry("b", "n2", "2026-02-01"))
        assert [x["slug"] for x in items] == ["c", "b", "a"]

    def test_index_entry_is_light(self):
        doc = shared.build_post_document(
            _valid_payload(), canonical_base_url="https://umbralbim.io", now="2026-06-07T12:00:00Z"
        )
        entry = shared.index_entry_from_post(doc)
        assert set(entry.keys()) == set(shared.INDEX_FIELDS)
        assert "body_markdown" not in entry
