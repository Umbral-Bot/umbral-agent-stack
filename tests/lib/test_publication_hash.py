"""Unit tests for ``scripts.discovery.lib.publication_hash``.

Covers:
  * ``normalize_publication_text`` rules from the contract.
  * ``compute_publication_content_hash`` determinism, channel sensitivity,
    body sensitivity, title sensitivity, source-binding sensitivity.
  * Distinctness from ``compute_source_content_hash`` for the same source.
  * ``ensure_publication_hash_column`` idempotency.
  * ``register_publication_hash`` updates an existing row.
  * ``is_duplicate_publication`` round-trip + missing-column / missing-table
    tolerance.
  * ``register_published(..., publication_content_hash=...)`` extended
    insert path persists the new field.

See ``docs/editorial-pipeline/publication-content-hash-contract.md``.
"""

from __future__ import annotations

import sqlite3

import pytest

from scripts.discovery.lib.dedup import (
    compute_source_content_hash,
    register_published,
)
from scripts.discovery.lib.publication_hash import (
    compute_publication_content_hash,
    ensure_publication_hash_column,
    is_duplicate_publication,
    normalize_publication_text,
    register_publication_hash,
)


# --------------------------------------------------------------------------- #
# normalize_publication_text
# --------------------------------------------------------------------------- #


class TestNormalizePublicationText:
    def test_none_returns_empty(self):
        assert normalize_publication_text(None) == ""

    def test_non_string_coerced(self):
        assert normalize_publication_text(123) == "123"

    def test_preserves_case(self):
        assert normalize_publication_text("BIM ISO 19650") == "BIM ISO 19650"

    def test_collapses_internal_horizontal_whitespace(self):
        assert normalize_publication_text("a    b\tc") == "a b c"

    def test_strips_per_line_trailing_whitespace(self):
        assert (
            normalize_publication_text("hola   \nmundo  \t\n")
            == "hola\nmundo"
        )

    def test_normalizes_crlf_and_cr(self):
        assert (
            normalize_publication_text("a\r\nb\rc")
            == "a\nb\nc"
        )

    def test_collapses_three_or_more_blank_lines(self):
        text = "p1\n\n\n\np2\n\n\np3"
        assert normalize_publication_text(text) == "p1\n\np2\n\np3"

    def test_preserves_single_blank_line(self):
        assert normalize_publication_text("p1\n\np2") == "p1\n\np2"

    def test_strips_outer_blank_lines(self):
        assert normalize_publication_text("\n\nhola\n\n") == "hola"

    def test_idempotent(self):
        text = "Header   1\n\n\n\nbody  with   spaces  \n"
        once = normalize_publication_text(text)
        twice = normalize_publication_text(once)
        assert once == twice


# --------------------------------------------------------------------------- #
# compute_publication_content_hash
# --------------------------------------------------------------------------- #


class TestComputePublicationContentHash:
    def test_deterministic(self):
        a = compute_publication_content_hash("linkedin", "Hola mundo", "T")
        b = compute_publication_content_hash("linkedin", "Hola mundo", "T")
        assert a == b
        assert len(a) == 64  # sha256 hex

    def test_channel_case_insensitive(self):
        a = compute_publication_content_hash("LinkedIn", "x")
        b = compute_publication_content_hash("linkedin", "x")
        assert a == b

    def test_channel_separates_hashes(self):
        a = compute_publication_content_hash("linkedin", "Same body")
        b = compute_publication_content_hash("blog", "Same body")
        assert a != b

    def test_body_case_flips_hash(self):
        a = compute_publication_content_hash("linkedin", "BIM matters")
        b = compute_publication_content_hash("linkedin", "bim matters")
        assert a != b

    def test_whitespace_only_edits_do_not_flip(self):
        a = compute_publication_content_hash(
            "linkedin", "Hola   mundo  \n\nsegunda  línea"
        )
        b = compute_publication_content_hash(
            "linkedin", "Hola mundo\n\nsegunda línea"
        )
        assert a == b

    def test_extra_blank_lines_collapsed(self):
        a = compute_publication_content_hash("blog", "p1\n\n\n\np2")
        b = compute_publication_content_hash("blog", "p1\n\np2")
        assert a == b

    def test_title_changes_flip_hash(self):
        a = compute_publication_content_hash(
            "blog", "body", title="Original"
        )
        b = compute_publication_content_hash(
            "blog", "body", title="Edited"
        )
        assert a != b

    def test_source_binding_separates_unrelated_signals(self):
        # Two unrelated signals that happen to produce identical copy
        # MUST hash distinctly when source_content_hash is included.
        signal_a = compute_source_content_hash(
            "https://a.example/x", "Title A", "Excerpt A"
        )
        signal_b = compute_source_content_hash(
            "https://b.example/y", "Title B", "Excerpt B"
        )
        assert signal_a != signal_b
        a = compute_publication_content_hash(
            "linkedin", "Same final copy", source_content_hash=signal_a
        )
        b = compute_publication_content_hash(
            "linkedin", "Same final copy", source_content_hash=signal_b
        )
        assert a != b

    def test_distinct_from_source_content_hash(self):
        # publication_content_hash MUST NOT equal source_content_hash for
        # the same source — they hash different payloads.
        url = "https://example.com/post"
        title = "T"
        excerpt = "E"
        source_hash = compute_source_content_hash(url, title, excerpt)
        pub_hash = compute_publication_content_hash(
            "linkedin", excerpt, title=title, source_content_hash=source_hash
        )
        assert pub_hash != source_hash

    def test_none_inputs_safe(self):
        # Channel / body / title accept None gracefully.
        h = compute_publication_content_hash(None, None, title=None)  # type: ignore[arg-type]
        assert isinstance(h, str)
        assert len(h) == 64


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


class TestEnsurePublicationHashColumn:
    def test_no_op_when_table_missing(self, db):
        # Should not raise.
        ensure_publication_hash_column(db)

    def test_adds_column_when_missing(self, db):
        from scripts.discovery.lib.dedup import ensure_published_history_schema

        ensure_published_history_schema(db)
        cols_before = [r[1] for r in db.execute("PRAGMA table_info(published_history)").fetchall()]
        assert "publication_content_hash" not in cols_before
        ensure_publication_hash_column(db)
        cols_after = [r[1] for r in db.execute("PRAGMA table_info(published_history)").fetchall()]
        assert "publication_content_hash" in cols_after

    def test_idempotent_when_column_exists(self, db):
        from scripts.discovery.lib.dedup import ensure_published_history_schema

        ensure_published_history_schema(db)
        ensure_publication_hash_column(db)
        # Second call must not raise.
        ensure_publication_hash_column(db)


class TestRegisterPublicationHash:
    def test_requires_content_hash(self, db):
        with pytest.raises(ValueError, match="content_hash"):
            register_publication_hash(db, "", "pub_hash_x")

    def test_requires_publication_content_hash(self, db):
        with pytest.raises(ValueError, match="publication_content_hash"):
            register_publication_hash(db, "src_hash_x", "")

    def test_updates_existing_row(self, db):
        register_published(db, "src_hash", "https://x", "linkedin")
        register_publication_hash(db, "src_hash", "pub_hash_v1")
        row = db.execute(
            "SELECT publication_content_hash FROM published_history "
            "WHERE content_hash=?",
            ("src_hash",),
        ).fetchone()
        assert row[0] == "pub_hash_v1"

    def test_update_idempotent(self, db):
        register_published(db, "src_hash", "https://x", "linkedin")
        register_publication_hash(db, "src_hash", "pub_hash_v1")
        register_publication_hash(db, "src_hash", "pub_hash_v1")
        row = db.execute(
            "SELECT COUNT(*) FROM published_history WHERE content_hash=?",
            ("src_hash",),
        ).fetchone()
        assert row[0] == 1


class TestIsDuplicatePublication:
    def test_empty_hash_returns_false(self, db):
        assert is_duplicate_publication(db, "") is False

    def test_missing_table_returns_false(self, db):
        assert is_duplicate_publication(db, "anything") is False

    def test_round_trip_match(self, db):
        register_published(db, "src", "https://x", "linkedin")
        register_publication_hash(db, "src", "pub_v1")
        assert is_duplicate_publication(db, "pub_v1") is True

    def test_round_trip_no_match(self, db):
        register_published(db, "src", "https://x", "linkedin")
        register_publication_hash(db, "src", "pub_v1")
        assert is_duplicate_publication(db, "pub_v2") is False

    def test_legacy_row_without_pub_hash(self, db):
        # A row inserted without publication_content_hash must NOT match
        # any non-empty publication hash query.
        register_published(db, "src", "https://x", "linkedin")
        ensure_publication_hash_column(db)
        assert is_duplicate_publication(db, "anything") is False


class TestRegisterPublishedExtendedInsert:
    def test_optional_param_persisted(self, db):
        register_published(
            db,
            "src",
            "https://x",
            "linkedin",
            publication_content_hash="pub_v1",
        )
        row = db.execute(
            "SELECT content_hash, publication_content_hash "
            "FROM published_history WHERE content_hash=?",
            ("src",),
        ).fetchone()
        assert row == ("src", "pub_v1")

    def test_legacy_call_path_unchanged(self, db):
        # No publication_content_hash param → legacy schema path. Must NOT
        # add the column (lazy: only added when actually needed).
        register_published(db, "src", "https://x", "linkedin")
        cols = [r[1] for r in db.execute(
            "PRAGMA table_info(published_history)"
        ).fetchall()]
        assert "publication_content_hash" not in cols
