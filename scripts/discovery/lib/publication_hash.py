"""Publication-grade content hashing for Stage 10 / future publishers.

Pure functions. Zero HTTP, zero Notion writes. Distinct from
``lib.dedup.compute_source_content_hash`` (= signal identity); this module
hashes the **copy approved for a specific channel**.

See ``docs/editorial-pipeline/publication-content-hash-contract.md`` for
the full contract. Companion to #405 stop button (`PublishFlags`,
`publish_guard.runtime_block`) and #404-lite observability log.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3

__all__ = [
    "normalize_publication_text",
    "compute_publication_content_hash",
    "ensure_publication_hash_column",
    "register_publication_hash",
    "is_duplicate_publication",
]


# Horizontal whitespace inside a single line (NOT newlines).
_HWS_RE = re.compile(r"[ \t\f\v]+")
# Three or more consecutive blank lines collapse to exactly two newlines
# (= one blank line between paragraphs).
_BLANK_RUN_RE = re.compile(r"\n{3,}")


def normalize_publication_text(s: object) -> str:
    """Normalize a publication body / title for hashing.

    Rules:
      * ``None`` and non-string falsy → ``""``.
      * Non-string → coerced via ``str``.
      * Replaces CRLF / CR with LF.
      * Strips trailing horizontal whitespace per line.
      * Collapses runs of horizontal whitespace inside a line to ONE space.
      * Collapses runs of 3+ blank lines to exactly two newlines.
      * Strips leading / trailing blank lines and outer whitespace.
      * **Preserves case** — publication copy treats casing as semantic.
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    # Normalize line endings first.
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse horizontal whitespace per line and strip per-line trailing WS.
    lines = [_HWS_RE.sub(" ", line).rstrip() for line in s.split("\n")]
    s = "\n".join(lines)
    # Collapse blank-line runs.
    s = _BLANK_RUN_RE.sub("\n\n", s)
    # Strip outer whitespace / leading-trailing blank lines.
    return s.strip()


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_publication_content_hash(
    channel: str,
    body_text: str,
    title: str = "",
    source_content_hash: str = "",
) -> str:
    """Deterministic sha256 over the approved publication copy.

    See contract for the full payload definition. Briefly:

        payload = "\\n".join([
            channel.strip().lower(),
            normalize_publication_text(title),
            normalize_publication_text(body_text),
            source_content_hash.strip(),
        ])
    """
    parts = [
        (channel or "").strip().lower(),
        normalize_publication_text(title),
        normalize_publication_text(body_text),
        (source_content_hash or "").strip(),
    ]
    return _sha256("\n".join(parts))


# --------------------------------------------------------------------------- #
# published_history additive migration + duplicate check
# --------------------------------------------------------------------------- #

_PUB_HASH_COLUMN = "publication_content_hash"
_PUB_HASH_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS idx_published_history_pub_hash "
    "ON published_history(publication_content_hash)"
)


def _column_exists(db_conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db_conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def ensure_publication_hash_column(db_conn: sqlite3.Connection) -> None:
    """Idempotent additive migration for ``publication_content_hash``.

    Assumes ``published_history`` already exists (callers are expected to
    invoke ``lib.dedup.ensure_published_history_schema`` first). If it does
    not exist, this is a no-op — the column will be added on the next
    invocation after the table is created.
    """
    try:
        if not _column_exists(db_conn, "published_history", _PUB_HASH_COLUMN):
            db_conn.execute(
                f"ALTER TABLE published_history ADD COLUMN {_PUB_HASH_COLUMN} TEXT"
            )
        db_conn.execute(_PUB_HASH_INDEX_DDL)
        db_conn.commit()
    except sqlite3.OperationalError:
        # Table missing or some other migration race — be conservative.
        return


def register_publication_hash(
    db_conn: sqlite3.Connection,
    content_hash: str,
    publication_content_hash: str,
) -> None:
    """Update an existing ``published_history`` row with the publication hash.

    Idempotent: if the row already has the same value, the UPDATE is a
    no-op. Raises ``ValueError`` for empty inputs (consistent with
    ``lib.dedup.register_published``).
    """
    if not content_hash:
        raise ValueError("content_hash required")
    if not publication_content_hash:
        raise ValueError("publication_content_hash required")
    ensure_publication_hash_column(db_conn)
    db_conn.execute(
        "UPDATE published_history SET publication_content_hash=? "
        "WHERE content_hash=?",
        (publication_content_hash, content_hash),
    )
    db_conn.commit()


def is_duplicate_publication(
    db_conn: sqlite3.Connection,
    publication_content_hash: str,
) -> bool:
    """Return True iff a row matches the given ``publication_content_hash``.

    Tolerates a missing column or table by returning ``False`` — consistent
    with ``lib.dedup.is_duplicate``. The typical caller is read-only at this
    point.
    """
    if not publication_content_hash:
        return False
    try:
        row = db_conn.execute(
            "SELECT 1 FROM published_history "
            "WHERE publication_content_hash=? LIMIT 1",
            (publication_content_hash,),
        ).fetchone()
    except sqlite3.OperationalError:
        return False
    return row is not None
