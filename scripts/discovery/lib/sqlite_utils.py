"""SQLite helpers for the editorial discovery pipeline.

Centralizes two Wave 2 hardening decisions:

- apply ``PRAGMA busy_timeout=5000`` on every discovery-stage connection
- run ordered, recorded SQL migrations via ``schema_migrations``

WAL mode is intentionally left untouched here. The current cron topology is
single-writer and the policy doc keeps rollback-journal mode unless proven
necessary.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BUSY_TIMEOUT_MS = 5000
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_MIGRATION_RE = re.compile(r"^(\d{4}_.+)\.sql$")

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def configure_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Apply shared connection settings for discovery SQLite usage."""
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_MIGRATIONS_DDL)
    conn.commit()


def list_migration_files(migrations_dir: Path = MIGRATIONS_DIR) -> list[Path]:
    if not migrations_dir.exists():
        return []
    files = [
        path for path in migrations_dir.iterdir()
        if path.is_file() and _MIGRATION_RE.match(path.name)
    ]
    return sorted(files, key=lambda path: path.name)


def apply_migrations(
    conn: sqlite3.Connection,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> list[str]:
    """Apply ordered SQL migrations once and record them in ``schema_migrations``.

    Existing databases created before ``schema_migrations`` was introduced are
    handled safely: the historical migrations are re-run once, but they remain
    idempotent because the SQL files use ``IF NOT EXISTS`` guards.
    """
    configure_connection(conn)
    ensure_schema_migrations_table(conn)

    applied_versions = {
        row[0] for row in conn.execute("SELECT version FROM schema_migrations")
    }
    applied_now: list[str] = []

    for migration_path in list_migration_files(migrations_dir):
        version = migration_path.name
        if version in applied_versions:
            continue
        sql = migration_path.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (version, _now_iso()),
        )
        conn.commit()
        applied_now.append(version)
        applied_versions.add(version)

    return applied_now


def open_sqlite(
    path: Path,
    *,
    row_factory: type[sqlite3.Row] | None = sqlite3.Row,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    configure_connection(conn)
    if row_factory is not None:
        conn.row_factory = row_factory
    apply_migrations(conn, migrations_dir=migrations_dir)
    return conn
