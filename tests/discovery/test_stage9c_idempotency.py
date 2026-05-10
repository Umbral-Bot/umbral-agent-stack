"""Stage 10/Hilo 6 idempotency tests for stage9c.

Two flows:

1. Successful POST → ``register_published`` is invoked exactly once with
   the LinkedIn feed URL derived from the returned ``post_urn``.
2. A second run with the same ``content_hash`` is blocked by the guard
   (``contenido_duplicado``) BEFORE any HTTP traffic — preventing duplicate
   publishes even if the proposals row was reset to ``draft_ready``.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from scripts.discovery import stage9c_linkedin_publish as mod


def _make_table(db: Path) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular TEXT NOT NULL,
            notion_page_id TEXT,
            linkedin_status TEXT,
            linkedin_draft_payload TEXT,
            linkedin_last_attempt_at INTEGER,
            linkedin_last_error TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS published_history (
            content_hash TEXT PRIMARY KEY,
            published_url TEXT NOT NULL,
            published_at TEXT NOT NULL,
            platform TEXT NOT NULL
        )"""
    )
    conn.commit()
    conn.close()


def _payload(text: str) -> dict:
    return {
        "_offline_draft": True,
        "author": "urn:li:person:__TODO_RESOLVE_AT_PUBLISH__",
        "lifecycleState": "DRAFT",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }


def _insert(db: Path, *, text: str, page: str = "PAGE-IDEMP") -> int:
    conn = sqlite3.connect(db)
    cur = conn.execute(
        "INSERT INTO proposals (titular, notion_page_id, linkedin_status, "
        "linkedin_draft_payload) VALUES (?,?,?,?)",
        ("T", page, "draft_ready", json.dumps(_payload(text))),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


@pytest.fixture
def db_path(tmp_path):
    db = tmp_path / "state.sqlite"
    _make_table(db)
    mod.ensure_publish_columns(db)
    return db


def _gates_pass_all(install_fake_gates, install_fake_dedup):
    install_fake_dedup(is_duplicate=lambda db, h: False)
    install_fake_gates(
        lambda p, d: types.SimpleNamespace(
            aprobado_contenido=True, autorizar_publicacion=True,
            gate_invalidado=False, fuente_primaria_ok=True,
            plataforma_seleccionada=True, no_duplicado=True,
        )
    )


def test_successful_post_calls_register_published(
    db_path, monkeypatch, install_fake_gates, install_fake_dedup,
):
    """201 Created → register_published(content_hash, feed_url, 'linkedin')."""
    register_calls: list[tuple] = []
    fake_dedup = install_fake_dedup(
        is_duplicate=lambda db, h: False,
        register=lambda db, h, url, plat: register_calls.append(
            (h, url, plat)
        ),
    )
    install_fake_gates(
        lambda p, d: types.SimpleNamespace(
            aprobado_contenido=True, autorizar_publicacion=True,
            gate_invalidado=False, fuente_primaria_ok=True,
            plataforma_seleccionada=True, no_duplicado=True,
        )
    )
    _insert(db_path, text="alpha post")

    # Mock the actual HTTP call → 201 Created.
    def fake_post_ugc(*, payload, access_token, client=None):
        return 201, "urn:li:share:9999", {"id": "urn:li:share:9999"}

    monkeypatch.setattr(mod, "post_ugc", fake_post_ugc)

    row = mod.read_publishable(db_path, limit=1)[0]
    status, msg = mod.publish_one(
        row=row, state_db=db_path,
        author_urn="urn:li:person:rick",
        access_token="AT-fake", dry_run=False,
        notion_fetcher=lambda pid: {"id": pid},
        dedup_module=fake_dedup,
    )
    assert status == "published"
    assert msg == "urn:li:share:9999"
    assert len(register_calls) == 1
    h, url, plat = register_calls[0]
    assert len(h) == 64
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:9999/"
    assert plat == "linkedin"


def test_second_run_with_same_content_hash_is_blocked(
    db_path, monkeypatch, install_fake_gates, install_fake_dedup,
):
    """If published_history already has the hash, guard blocks before POST."""
    text = "duplicate prevention text"
    expected_hash = mod.compute_payload_content_hash(_payload(text))

    # Pre-seed published_history so dedup says duplicate.
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO published_history "
        "(content_hash, published_url, published_at, platform) "
        "VALUES (?, ?, ?, ?)",
        (
            expected_hash,
            "https://www.linkedin.com/feed/update/urn:li:share:1/",
            "2026-01-01T00:00:00Z",
            "linkedin",
        ),
    )
    conn.commit()
    conn.close()

    install_fake_dedup(
        is_duplicate=lambda db, h: h == expected_hash,
    )
    install_fake_gates(
        lambda p, d: types.SimpleNamespace(
            aprobado_contenido=True, autorizar_publicacion=True,
            gate_invalidado=False, fuente_primaria_ok=True,
            plataforma_seleccionada=True, no_duplicado=False,
        )
    )

    # Hard fail-safe: any HTTP call must crash the test.
    monkeypatch.setattr(
        mod.httpx, "Client",
        lambda *a, **kw: pytest.fail("httpx must not be invoked"),
    )

    _insert(db_path, text=text)
    row = mod.read_publishable(db_path, limit=1)[0]
    status, msg = mod.publish_one(
        row=row, state_db=db_path,
        author_urn="urn:li:person:rick",
        access_token="AT-fake", dry_run=False,
        notion_fetcher=lambda pid: {"id": pid},
    )
    assert status == "blocked"
    assert "contenido_duplicado" in msg
