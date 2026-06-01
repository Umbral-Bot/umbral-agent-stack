from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from scripts.discovery import stage2_verify_sources as s2
from scripts.discovery.lib.sqlite_utils import BUSY_TIMEOUT_MS
from scripts.discovery.stage0_load_referentes import apply_migrations, open_sqlite

EXPECTED_MIGRATIONS = [
    "0001_referentes_signals.sql",
    "0002_signals_verified_published_history.sql",
]


def test_open_sqlite_sets_busy_timeout_and_records_migrations(tmp_path: Path):
    conn = open_sqlite(tmp_path / "state.sqlite")
    try:
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        versions = [
            row[0]
            for row in conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        ]
    finally:
        conn.close()

    assert busy_timeout == BUSY_TIMEOUT_MS
    assert versions == EXPECTED_MIGRATIONS


def test_apply_migrations_is_idempotent_and_ordered(tmp_path: Path):
    conn = sqlite3.connect(tmp_path / "state.sqlite")
    try:
        apply_migrations(conn)
        apply_migrations(conn)
        rows = conn.execute(
            "SELECT version, COUNT(*) FROM schema_migrations "
            "GROUP BY version ORDER BY version"
        ).fetchall()
    finally:
        conn.close()

    assert rows == [(version, 1) for version in EXPECTED_MIGRATIONS]


def test_stage2_ensure_schema_bootstraps_plain_connection():
    conn = sqlite3.connect(":memory:")
    try:
        s2.ensure_schema(conn)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        versions = [
            row[0]
            for row in conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        ]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    finally:
        conn.close()

    assert {"referentes_snapshot", "signals_raw", "signals_verified", "published_history", "schema_migrations"} <= tables
    assert versions == EXPECTED_MIGRATIONS
    assert busy_timeout == BUSY_TIMEOUT_MS


def test_busy_timeout_allows_short_lock_to_clear(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    holder = open_sqlite(db)
    try:
        holder.execute("BEGIN IMMEDIATE")
        holder.execute(
            "INSERT INTO referentes_snapshot(referente_id, nombre, canal_tipo, canal_url, snapshot_at) "
            "VALUES (?,?,?,?,?)",
            ("holder", "Holder", "rss", "https://example.com/holder", "2026-06-01T00:00:00+00:00"),
        )

        result: dict[str, object] = {}

        def writer() -> None:
            started = time.monotonic()
            conn = open_sqlite(db)
            try:
                conn.execute(
                    "INSERT INTO referentes_snapshot(referente_id, nombre, canal_tipo, canal_url, snapshot_at) "
                    "VALUES (?,?,?,?,?)",
                    ("writer", "Writer", "rss", "https://example.com/writer", "2026-06-01T00:00:00+00:00"),
                )
                conn.commit()
                result["elapsed"] = time.monotonic() - started
                result["error"] = None
            except Exception as exc:  # noqa: BLE001
                result["elapsed"] = time.monotonic() - started
                result["error"] = exc
            finally:
                conn.close()

        thread = threading.Thread(target=writer)
        thread.start()
        time.sleep(0.25)
        holder.commit()
        thread.join(timeout=2)

        assert not thread.is_alive()
        assert result["error"] is None
        assert float(result["elapsed"]) >= 0.2

        check = sqlite3.connect(db)
        try:
            count = check.execute(
                "SELECT COUNT(*) FROM referentes_snapshot WHERE referente_id IN ('holder', 'writer')"
            ).fetchone()[0]
        finally:
            check.close()
        assert count == 2
    finally:
        holder.close()
