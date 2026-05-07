"""Unit tests for scripts/discovery/stage2_ingest.py helpers.

Covers (per task .agents/tasks/2026-05-06-013c-stage2-ingest-script.md):
- canonicalize_url: strip utm_*, fbclid, fragment, trailing slash.
- canonicalize_url: youtu.be -> www.youtube.com/watch?v=ID.
- parse_youtube_channel_id: /channel/UC..., /c/Name, /@handle returns None.
- should_skip_recent: true/false depending on delta vs threshold.
- init_sqlite: idempotent (second call does not fail).
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from discovery import stage2_ingest as s2  # noqa: E402


# ---------- canonicalize_url ----------

class TestCanonicalizeUrl:
    def test_strips_utm_params(self):
        url = "https://example.com/post?utm_source=tw&utm_medium=social&id=42"
        assert s2.canonicalize_url(url) == "https://example.com/post?id=42"

    def test_strips_fbclid(self):
        url = "https://example.com/x?fbclid=ABC&keep=1"
        assert s2.canonicalize_url(url) == "https://example.com/x?keep=1"

    def test_strips_gclid_and_ref(self):
        url = "https://example.com/x?gclid=Z&ref=newsletter&keep=2"
        assert s2.canonicalize_url(url) == "https://example.com/x?keep=2"

    def test_strips_fragment(self):
        url = "https://example.com/post#section-1"
        assert s2.canonicalize_url(url) == "https://example.com/post"

    def test_strips_trailing_slash(self):
        url = "https://example.com/path/"
        assert s2.canonicalize_url(url) == "https://example.com/path"

    def test_keeps_root_slash(self):
        url = "https://example.com/"
        assert s2.canonicalize_url(url) == "https://example.com/"

    def test_lowercases_scheme_and_host(self):
        url = "HTTPS://Example.COM/Path"
        # Path case is preserved; only scheme + host are lowercased.
        assert s2.canonicalize_url(url) == "https://example.com/Path"

    def test_youtu_be_normalized_to_youtube(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert s2.canonicalize_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_watch_normalized_strips_extras(self):
        url = "https://www.youtube.com/watch?v=ABC123&t=10s&utm_source=x"
        assert s2.canonicalize_url(url) == "https://www.youtube.com/watch?v=ABC123"

    def test_empty_input_returns_empty(self):
        assert s2.canonicalize_url("") == ""


# ---------- parse_youtube_channel_id ----------

class TestParseYoutubeChannelId:
    def test_channel_id_uc(self):
        result = s2.parse_youtube_channel_id(
            "https://www.youtube.com/channel/UCabc123_DEF"
        )
        assert result == ("UCabc123_DEF", "channel")

    def test_custom_c_name(self):
        result = s2.parse_youtube_channel_id("https://www.youtube.com/c/SomeName")
        assert result == ("SomeName", "c")

    def test_legacy_user(self):
        result = s2.parse_youtube_channel_id("https://www.youtube.com/user/legacyName")
        assert result == ("legacyName", "user")

    def test_handle_returns_handle_kind(self):
        # /@handle is parseable via RSSHub /youtube/user/@HANDLE.
        result = s2.parse_youtube_channel_id("https://www.youtube.com/@somehandle")
        assert result == ("somehandle", "handle")

    def test_non_youtube_returns_none(self):
        assert s2.parse_youtube_channel_id("https://example.com/channel/UCabc") is None

    def test_empty_returns_none(self):
        assert s2.parse_youtube_channel_id("") is None


# ---------- should_skip_recent ----------

class TestShouldSkipRecent:
    def test_no_previous_returns_false(self):
        assert s2.should_skip_recent(None, 30) is False

    def test_threshold_zero_returns_false(self):
        prev = "2026-05-06T10:00:00Z"
        now = datetime(2026, 5, 6, 10, 5, tzinfo=timezone.utc)
        assert s2.should_skip_recent(prev, 0, now=now) is False

    def test_within_threshold_returns_true(self):
        prev = "2026-05-06T10:00:00Z"
        now = datetime(2026, 5, 6, 10, 15, tzinfo=timezone.utc)  # 15 min later
        assert s2.should_skip_recent(prev, 30, now=now) is True

    def test_beyond_threshold_returns_false(self):
        prev = "2026-05-06T10:00:00Z"
        now = datetime(2026, 5, 6, 10, 45, tzinfo=timezone.utc)  # 45 min later
        assert s2.should_skip_recent(prev, 30, now=now) is False

    def test_invalid_iso_returns_false(self):
        assert s2.should_skip_recent("not-a-date", 30) is False

    def test_naive_iso_treated_as_utc(self):
        prev = "2026-05-06T10:00:00"
        now = datetime(2026, 5, 6, 10, 10, tzinfo=timezone.utc)
        assert s2.should_skip_recent(prev, 30, now=now) is True


# ---------- init_sqlite (idempotent) ----------

class TestInitSqlite:
    def test_creates_tables(self, tmp_path: Path):
        db = tmp_path / "state.sqlite"
        conn = s2.init_sqlite(db)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert "discovered_items" in tables
            assert "fetch_log" in tables
        finally:
            conn.close()

    def test_idempotent(self, tmp_path: Path):
        db = tmp_path / "state.sqlite"
        conn1 = s2.init_sqlite(db)
        conn1.close()
        # Second call must not raise.
        conn2 = s2.init_sqlite(db)
        try:
            tables = {
                row[0]
                for row in conn2.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert "discovered_items" in tables
            assert "fetch_log" in tables
        finally:
            conn2.close()

    def test_indices_present(self, tmp_path: Path):
        db = tmp_path / "state.sqlite"
        conn = s2.init_sqlite(db)
        try:
            indices = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
            assert "idx_discovered_referente" in indices
            assert "idx_fetch_log_recent" in indices
        finally:
            conn.close()
