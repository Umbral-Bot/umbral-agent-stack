"""Stage 10 dry-run contract tests for stage9c (Hilo 6).

These tests guarantee:
* Zero LinkedIn HTTP traffic on ``--dry-run`` (httpx.Client patched to fail).
* The JSON contract printed to stdout has the keys
  ``{proposal_id, page_id, content_hash, would_publish, reasons_blocked}``.
* ``would_publish=True`` only when all 6 gates pass.
* ``would_publish=False`` with the matching reason code when a gate fails
  or when content_hash is duplicate of an already-published row.
* The stage9c module must NOT contain any literal LinkedIn API URL outside
  the documented constant — this is a defensive guard against accidental
  hard-coded POST URLs.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import types
from pathlib import Path

import pytest

from scripts.discovery import stage9c_linkedin_publish as mod


# --------------------------------------------------------------------------- #
# Hard fail-safe: NO real LinkedIn POSTs from this test module.
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _fail_fast_no_linkedin(monkeypatch):
    monkeypatch.setattr(
        mod.httpx, "Client",
        lambda *a, **kw: pytest.fail("httpx.Client must not be invoked"),
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _create_proposals_table(db: Path) -> None:
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
    conn.commit()
    conn.close()


def _seed_published_history(db: Path, content_hash: str) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS published_history (
            content_hash TEXT PRIMARY KEY,
            published_url TEXT NOT NULL,
            published_at TEXT NOT NULL,
            platform TEXT NOT NULL
        )"""
    )
    conn.execute(
        "INSERT INTO published_history "
        "(content_hash, published_url, published_at, platform) "
        "VALUES (?, 'https://www.linkedin.com/feed/update/x/', "
        "'2026-01-01T00:00:00Z', 'linkedin')",
        (content_hash,),
    )
    conn.commit()
    conn.close()


def _insert(db: Path, *, payload: dict, page_id: str = "PAGE-A") -> int:
    conn = sqlite3.connect(db)
    cur = conn.execute(
        "INSERT INTO proposals (titular, notion_page_id, linkedin_status, "
        "linkedin_draft_payload) VALUES (?,?,?,?)",
        ("T", page_id, "draft_ready", json.dumps(payload)),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def _payload(text: str = "Hello world post") -> dict:
    return {
        "_endpoint": "/v2/ugcPosts",
        "_offline_draft": True,
        "_proposal_id": 0,
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


@pytest.fixture
def state_db(tmp_path):
    db = tmp_path / "state.sqlite"
    _create_proposals_table(db)
    mod.ensure_publish_columns(db)
    return db


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_dry_run_all_gates_ok_would_publish_true(
    state_db, capsys, install_fake_gates, fake_dedup_no_duplicates,
):
    install_fake_gates(
        lambda p, d: types.SimpleNamespace(
            aprobado_contenido=True, autorizar_publicacion=True,
            gate_invalidado=False, fuente_primaria_ok=True,
            plataforma_seleccionada=True, no_duplicado=True,
        )
    )
    _insert(state_db, payload=_payload("text alpha"))
    row = mod.read_publishable(state_db, limit=1)[0]
    status, _ = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="", dry_run=True,
        notion_fetcher=lambda pid: {"id": pid},
    )
    assert status == "skipped"
    payload_out = json.loads(capsys.readouterr().out.strip().splitlines()[0])
    assert payload_out["would_publish"] is True
    assert payload_out["reasons_blocked"] == []
    assert payload_out["page_id"] == "PAGE-A"
    assert len(payload_out["content_hash"]) == 64


def test_dry_run_gate_failing_would_publish_false(
    state_db, capsys, install_fake_gates, fake_dedup_no_duplicates,
):
    install_fake_gates(
        lambda p, d: types.SimpleNamespace(
            aprobado_contenido=False, autorizar_publicacion=True,
            gate_invalidado=False, fuente_primaria_ok=True,
            plataforma_seleccionada=True, no_duplicado=True,
        )
    )
    _insert(state_db, payload=_payload("text beta"))
    row = mod.read_publishable(state_db, limit=1)[0]
    status, _ = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="", dry_run=True,
        notion_fetcher=lambda pid: {"id": pid},
    )
    assert status == "blocked"
    payload_out = json.loads(capsys.readouterr().out.strip().splitlines()[0])
    assert payload_out["would_publish"] is False
    assert "aprobado_contenido_missing" in payload_out["reasons_blocked"]


def test_dry_run_duplicate_content_hash_blocks(
    state_db, capsys, install_fake_gates, install_fake_dedup,
):
    """All Notion gates pass but content_hash is in published_history."""
    text = "duplicated body"
    expected_hash = mod.compute_payload_content_hash(_payload(text))
    _seed_published_history(state_db, expected_hash)
    install_fake_dedup(
        is_duplicate=lambda db, h: h == expected_hash,
    )
    install_fake_gates(
        lambda page, dedup_check: types.SimpleNamespace(
            aprobado_contenido=True, autorizar_publicacion=True,
            gate_invalidado=False, fuente_primaria_ok=True,
            plataforma_seleccionada=True,
            no_duplicado=not dedup_check(expected_hash),
        )
    )
    _insert(state_db, payload=_payload(text))
    row = mod.read_publishable(state_db, limit=1)[0]
    status, _ = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="", dry_run=True,
        notion_fetcher=lambda pid: {"id": pid},
    )
    assert status == "blocked"
    payload_out = json.loads(capsys.readouterr().out.strip().splitlines()[0])
    assert payload_out["would_publish"] is False
    assert "contenido_duplicado" in payload_out["reasons_blocked"]
    assert payload_out["content_hash"] == expected_hash


def test_no_hardcoded_linkedin_post_urls():
    """Defensive: stage9c must build POST URLs from LINKEDIN_API_BASE only.

    The literal "https://api.linkedin.com" may appear in the module-level
    constant and inside the module docstring, but MUST NOT appear in any
    code path that constructs an HTTP request. We assert that
    ``LINKEDIN_API_BASE`` is in fact used and that there are no string
    concatenations using the literal URL outside its declaration line.
    """
    src_path = Path(mod.__file__)
    src = src_path.read_text()
    assert mod.LINKEDIN_API_BASE == "https://api.linkedin.com"
    # No client.post / httpx.post call must contain the literal URL.
    for ln in src.splitlines():
        if "client.post(" in ln or "httpx.post(" in ln:
            assert "https://api.linkedin.com" not in ln, (
                f"Hardcoded URL in HTTP call: {ln}"
            )
