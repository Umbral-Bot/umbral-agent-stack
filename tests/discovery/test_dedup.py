"""Tests for ``scripts.discovery.lib.dedup`` — pure-function primitives."""

from __future__ import annotations

import sqlite3

import pytest

from scripts.discovery.lib import dedup


# --------------------------------------------------------------------------- #
# normalize_text
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Hello", "hello"),
        ("  spaced  out  ", "spaced out"),
        ("MiXeD\tCaSe\nNewline", "mixed case newline"),
        ("", ""),
        (None, ""),
        (123, "123"),
        ("Caf\u00e9 Crema", "caf\u00e9 crema"),
    ],
)
def test_normalize_text(raw, expected):
    assert dedup.normalize_text(raw) == expected


# --------------------------------------------------------------------------- #
# content_hash / idempotency_key
# --------------------------------------------------------------------------- #


def test_content_hash_deterministic():
    a = dedup.compute_content_hash("https://x/y", "Title", "Body")
    b = dedup.compute_content_hash("https://x/y", "Title", "Body")
    assert a == b
    assert len(a) == 64


def test_content_hash_normalizes_title_excerpt():
    a = dedup.compute_content_hash("https://x/y", "Hello World", "Body Text")
    b = dedup.compute_content_hash("https://x/y", "  hello   WORLD ", " body   text ")
    assert a == b


def test_content_hash_differs_on_url_change():
    a = dedup.compute_content_hash("https://x/y", "T", "E")
    b = dedup.compute_content_hash("https://x/z", "T", "E")
    assert a != b


def test_content_hash_differs_on_title_change():
    a = dedup.compute_content_hash("u", "Title A", "E")
    b = dedup.compute_content_hash("u", "Title B", "E")
    assert a != b


def test_content_hash_differs_on_excerpt_change():
    a = dedup.compute_content_hash("u", "T", "Body A")
    b = dedup.compute_content_hash("u", "T", "Body B")
    assert a != b


def test_idempotency_key_deterministic():
    ch = dedup.compute_content_hash("u", "t", "e")
    a = dedup.compute_idempotency_key("u", ch)
    b = dedup.compute_idempotency_key("u", ch)
    assert a == b
    assert len(a) == 64


def test_idempotency_key_changes_with_url():
    ch = dedup.compute_content_hash("u1", "t", "e")
    a = dedup.compute_idempotency_key("u1", ch)
    b = dedup.compute_idempotency_key("u2", ch)
    assert a != b


def test_idempotency_key_changes_with_hash():
    a = dedup.compute_idempotency_key("u", "h1")
    b = dedup.compute_idempotency_key("u", "h2")
    assert a != b


# --------------------------------------------------------------------------- #
# is_duplicate / register_published
# --------------------------------------------------------------------------- #


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


def test_is_duplicate_missing_table_returns_false(conn):
    assert dedup.is_duplicate(conn, "abc") is False


def test_is_duplicate_empty_hash_returns_false(conn):
    dedup.ensure_published_history_schema(conn)
    assert dedup.is_duplicate(conn, "") is False


def test_register_then_is_duplicate(conn):
    ch = "deadbeef"
    assert dedup.is_duplicate(conn, ch) is False
    dedup.register_published(conn, ch, "https://pub/x", "linkedin")
    assert dedup.is_duplicate(conn, ch) is True


def test_register_published_idempotent(conn):
    ch = "abc123"
    dedup.register_published(conn, ch, "https://pub/x", "linkedin")
    dedup.register_published(conn, ch, "https://pub/y", "notion")
    rows = list(conn.execute("SELECT content_hash, published_url, platform FROM published_history"))
    assert rows == [(ch, "https://pub/x", "linkedin")]


@pytest.mark.parametrize(
    "ch,url,platform",
    [
        ("", "https://x", "p"),
        ("h", "", "p"),
        ("h", "https://x", ""),
    ],
)
def test_register_published_rejects_empty(conn, ch, url, platform):
    with pytest.raises(ValueError):
        dedup.register_published(conn, ch, url, platform)


def test_ensure_published_history_schema_idempotent(conn):
    dedup.ensure_published_history_schema(conn)
    dedup.ensure_published_history_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(published_history)")}
    assert {"content_hash", "published_url", "published_at", "platform"} <= cols
