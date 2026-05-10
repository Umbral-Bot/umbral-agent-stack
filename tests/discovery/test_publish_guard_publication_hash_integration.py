"""Integration test for #402 publication_content_hash × #405 PublishFlags.

Verifies the contract orderings declared in
``docs/editorial-pipeline/publication-content-hash-contract.md`` §
"Integration with #405 stop button":

  1. Flags blocking + duplicate publication → ``PublishBlockedError``
     (flag check fires first; ``is_duplicate_publication`` is never
     consulted).
  2. Flags allowing + duplicate publication → guard passes, the
     publisher-side check (``is_duplicate_publication``) flags it.
  3. Flags allowing + fresh copy → guard passes, publisher-side check is
     False (would proceed to POST in a real publisher; this test stops
     short of any HTTP).
  4. ``flags=None`` (legacy) + fresh copy → byte-identical to the pre-#402
     publish-guard pass path (single ``publish_guard.pass`` log entry, no
     change to back-compat).

The publication-grade dedup is intentionally NOT inside ``publish_guard``;
the guard remains signal-grade. This test exercises a publisher-style
caller pattern by composing both functions explicitly.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from scripts.discovery.lib.dedup import register_published
from scripts.discovery.lib.publication_hash import (
    compute_publication_content_hash,
    is_duplicate_publication,
)
from scripts.discovery.lib.publish_flags import PublishFlags
from scripts.discovery.lib.publish_guard import (
    PublishBlockedError,
    assert_can_publish,
)


SOURCE_HASH = "s" * 64
PAGE_ID = "page-402"


def _all_ok_page() -> dict:
    return {
        "id": PAGE_ID,
        "properties": {
            "aprobado_contenido": {"checkbox": True},
            "autorizar_publicacion": {"checkbox": True},
            "gate_invalidado": {"checkbox": False},
            "Fuente primaria": {"url": "https://example.com/source"},
            "Canal": {"select": {"name": "linkedin"}},
            "content_hash": SOURCE_HASH,
        },
    }


def _read_log(path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln]


def _open_db(tmp_path):
    return sqlite3.connect(tmp_path / "state.sqlite")


def _seed_existing_publication(db, pub_hash: str) -> None:
    """Seed one row in published_history with a publication_content_hash."""
    register_published(
        db,
        SOURCE_HASH,
        "https://linkedin.example/posts/seed",
        "linkedin",
        publication_content_hash=pub_hash,
    )


# --------------------------------------------------------------------------- #
# 1. Flags blocking + duplicate publication → BLOCK before publication-hash
# --------------------------------------------------------------------------- #


def test_flags_block_fires_before_publication_hash_check(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    flags = PublishFlags(
        publish_enabled=False,
        dry_run=True,
        max_posts=1,
        max_posts_per_day=1,
    )
    pub_hash = compute_publication_content_hash(
        "linkedin",
        "Cuerpo aprobado para LinkedIn",
        title="Título",
        source_content_hash=SOURCE_HASH,
    )
    db = _open_db(tmp_path)
    try:
        _seed_existing_publication(db, pub_hash)
        # Even though the publication is a duplicate, the flag-block must
        # raise FIRST without ever consulting is_duplicate_publication.
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), SOURCE_HASH, db, flags=flags)
    finally:
        db.close()

    assert "publish_disabled" in exc.value.reasons
    assert "dry_run_enabled" in exc.value.reasons
    events = [e["event"] for e in _read_log(isolate_ops_log)]
    assert events == ["publish_guard.runtime_block"]


# --------------------------------------------------------------------------- #
# 2. Flags allowing + duplicate publication → guard pass, publisher blocks
# --------------------------------------------------------------------------- #


def test_flags_allow_then_publisher_detects_duplicate_publication(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    flags = PublishFlags(
        publish_enabled=True,
        dry_run=False,
        max_posts=1,
        max_posts_per_day=1,
    )
    pub_hash = compute_publication_content_hash(
        "linkedin",
        "Cuerpo aprobado para LinkedIn",
        title="Título",
        source_content_hash=SOURCE_HASH,
    )
    db = _open_db(tmp_path)
    try:
        _seed_existing_publication(db, pub_hash)
        # Guard passes (signal-grade): no runtime block, no editorial block,
        # no signal-grade dedup hit (fake_dedup_no_duplicates).
        result = assert_can_publish(_all_ok_page(), SOURCE_HASH, db, flags=flags)
        assert result is None
        # Publisher-side check now stops the would-be publish.
        assert is_duplicate_publication(db, pub_hash) is True
    finally:
        db.close()

    events = [e["event"] for e in _read_log(isolate_ops_log)]
    assert events == ["publish_guard.pass"]


# --------------------------------------------------------------------------- #
# 3. Flags allowing + fresh copy → guard pass, publisher would proceed
# --------------------------------------------------------------------------- #


def test_flags_allow_and_fresh_copy_publisher_would_proceed(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    flags = PublishFlags(
        publish_enabled=True,
        dry_run=False,
        max_posts=1,
        max_posts_per_day=1,
    )
    seeded_pub_hash = compute_publication_content_hash(
        "linkedin",
        "Versión vieja del cuerpo",
        title="Título",
        source_content_hash=SOURCE_HASH,
    )
    fresh_pub_hash = compute_publication_content_hash(
        "linkedin",
        "Versión nueva del cuerpo",
        title="Título",
        source_content_hash=SOURCE_HASH,
    )
    assert seeded_pub_hash != fresh_pub_hash

    db = _open_db(tmp_path)
    try:
        _seed_existing_publication(db, seeded_pub_hash)
        result = assert_can_publish(_all_ok_page(), SOURCE_HASH, db, flags=flags)
        assert result is None
        # The new copy is NOT a duplicate publication → publisher would POST.
        assert is_duplicate_publication(db, fresh_pub_hash) is False
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# 4. flags=None (legacy) + fresh copy → byte-identical to pre-#402 path
# --------------------------------------------------------------------------- #


def test_legacy_call_path_unchanged_when_flags_omitted(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    db = _open_db(tmp_path)
    try:
        result = assert_can_publish(_all_ok_page(), SOURCE_HASH, db)
        assert result is None
    finally:
        db.close()

    entries = _read_log(isolate_ops_log)
    assert len(entries) == 1
    assert entries[0]["event"] == "publish_guard.pass"
