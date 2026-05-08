"""Stage 2 dedup primitives — pure functions, no HTTP.

Public API consumed by Stage 2 (verify), Stage 5 (rank), and Stage 10
(publish). Keep this module side-effect free except for the explicit
SQLite read/write helpers ``is_duplicate`` and ``register_published``.

Hash strategy
-------------
``content_hash`` is sha256 over the *content identity*: canonical URL +
normalized title + normalized excerpt. Two distinct URLs that share the
exact same title+excerpt collide on purpose — that is the duplicate
signal we want.

``idempotency_key`` is sha256 over (canonical_url, content_hash). It is
URL-bound, so a republish from a different canonical URL of the same
content yields a different idempotency key but the same content_hash —
that lets S10 dedup at "have we ever told this story?" granularity
while still keeping per-URL retry idempotency.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone

__all__ = [
    "normalize_text",
    "compute_content_hash",
    "compute_idempotency_key",
    "is_duplicate",
    "register_published",
    "ensure_published_history_schema",
]


_WS_RE = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    """Lowercase, strip, collapse internal whitespace.

    Returns ``""`` for falsy input. Non-string input is coerced via ``str``.
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    return _WS_RE.sub(" ", s.strip().lower())


def _sha256(parts: str) -> str:
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


def compute_content_hash(canonical_url: str, title: str, excerpt: str) -> str:
    """Deterministic sha256 over canonical_url + normalized title + excerpt.

    URL is normalized only by ``strip()`` — canonicalization is the caller's
    responsibility (Stage 2 resolves redirects + ``<link rel="canonical">``
    before calling this).
    """
    url = (canonical_url or "").strip()
    payload = f"{url}\n{normalize_text(title)}\n{normalize_text(excerpt)}"
    return _sha256(payload)


def compute_idempotency_key(canonical_url: str, content_hash: str) -> str:
    """Deterministic sha256 over canonical_url + content_hash."""
    url = (canonical_url or "").strip()
    return _sha256(f"{url}\n{content_hash}")


# --------------------------------------------------------------------------- #
# Published-history helpers
# --------------------------------------------------------------------------- #

_PUBLISHED_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS published_history (
    content_hash    TEXT PRIMARY KEY,
    published_url   TEXT NOT NULL,
    published_at    TEXT NOT NULL,
    platform        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_published_history_platform
    ON published_history(platform);
"""


def ensure_published_history_schema(db_conn: sqlite3.Connection) -> None:
    """Create the ``published_history`` table if missing. Idempotent."""
    db_conn.executescript(_PUBLISHED_HISTORY_DDL)
    db_conn.commit()


def is_duplicate(db_conn: sqlite3.Connection, content_hash: str) -> bool:
    """Return True iff ``content_hash`` is already in ``published_history``.

    Tolerates a missing table by returning False rather than raising — the
    typical caller (Stage 10) is read-only at this point.
    """
    if not content_hash:
        return False
    try:
        row = db_conn.execute(
            "SELECT 1 FROM published_history WHERE content_hash=? LIMIT 1",
            (content_hash,),
        ).fetchone()
    except sqlite3.OperationalError:
        return False
    return row is not None


def register_published(
    db_conn: sqlite3.Connection,
    content_hash: str,
    published_url: str,
    platform: str,
) -> None:
    """Append a publication to ``published_history``. Idempotent on PK.

    Raises ``ValueError`` if any required field is empty — register is
    a write-only signal of "we just published this", and we want callers
    to fail loudly instead of silently logging a sentinel row.
    """
    if not content_hash:
        raise ValueError("content_hash required")
    if not published_url:
        raise ValueError("published_url required")
    if not platform:
        raise ValueError("platform required")
    ensure_published_history_schema(db_conn)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db_conn.execute(
        "INSERT OR IGNORE INTO published_history "
        "(content_hash, published_url, published_at, platform) "
        "VALUES (?,?,?,?)",
        (content_hash, published_url, now, platform),
    )
    db_conn.commit()
