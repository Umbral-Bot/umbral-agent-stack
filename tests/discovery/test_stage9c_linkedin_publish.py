"""Tests for scripts/discovery/stage9c_linkedin_publish.py."""
from __future__ import annotations

import json
import sqlite3
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from scripts.discovery import stage9c_linkedin_publish as mod
from scripts.discovery import stage9b_linkedin_oauth as oauth


@pytest.fixture(autouse=True)
def _stub_guard_dependencies(monkeypatch):
    """Install fake gates/dedup so the stage10 publish-guard always passes.

    These tests pre-date Hilo 6 and exercise stage9c HTTP/state behaviour
    only. The dedicated guard tests live in test_publish_guard.py and the
    dry-run/idempotency contracts in test_stage9c_dry_run.py /
    test_stage9c_idempotency.py.
    """
    gmod = types.ModuleType("scripts.discovery.lib.gates")

    def _ev(_p, _d):
        return types.SimpleNamespace(
            aprobado_contenido=True, autorizar_publicacion=True,
            gate_invalidado=False, fuente_primaria_ok=True,
            plataforma_seleccionada=True, no_duplicado=True,
        )
    gmod.evaluate_gates = _ev
    gmod.can_publish = lambda s: (True, [])
    monkeypatch.setitem(sys.modules, "scripts.discovery.lib.gates", gmod)

    dmod = types.ModuleType("scripts.discovery.lib.dedup")
    dmod.is_duplicate = lambda db, h: False
    dmod.register_published = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "scripts.discovery.lib.dedup", dmod)



# ---------- Helpers ----------

def _create_proposals_table(db: Path, *, with_publish_cols: bool = False) -> None:
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
    if with_publish_cols:
        conn.execute("ALTER TABLE proposals ADD COLUMN linkedin_post_urn TEXT")
        conn.execute(
            "ALTER TABLE proposals ADD COLUMN linkedin_published_at TEXT"
        )
    conn.commit()
    conn.close()


def _insert_draft(
    db: Path, *, titular: str = "T", page_id: str = "PAGE",
    status: str | None = "draft_ready", payload: dict | None = None,
) -> int:
    payload = payload if payload is not None else {
        "_endpoint": "/v2/ugcPosts",
        "_offline_draft": True,
        "_built_at": "2026-05-07T00:00:00+00:00",
        "_proposal_id": 0,
        "_notion_page_id": page_id,
        "author": "urn:li:person:__TODO_RESOLVE_AT_PUBLISH__",
        "lifecycleState": "DRAFT",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": "hello world"},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }
    conn = sqlite3.connect(db)
    cur = conn.execute(
        "INSERT INTO proposals (titular, notion_page_id, linkedin_status, "
        "linkedin_draft_payload) VALUES (?,?,?,?)",
        (titular, page_id, status, json.dumps(payload)),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


@pytest.fixture
def state_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    _create_proposals_table(db)
    return db


# ---------- Migration ----------

def test_ensure_publish_columns_idempotent(state_db: Path):
    mod.ensure_publish_columns(state_db)
    mod.ensure_publish_columns(state_db)  # second call: no-op
    conn = sqlite3.connect(state_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(proposals)")}
    conn.close()
    assert "linkedin_post_urn" in cols
    assert "linkedin_published_at" in cols


def test_ensure_publish_columns_missing_table_raises(tmp_path: Path):
    bad = tmp_path / "empty.sqlite"
    sqlite3.connect(bad).close()
    with pytest.raises(RuntimeError, match="proposals"):
        mod.ensure_publish_columns(bad)


# ---------- Sanitisation ----------

def test_strip_meta_keys_removes_all_underscored():
    payload = {
        "_endpoint": "/v2/ugcPosts",
        "_offline_draft": True,
        "_built_at": "x",
        "_proposal_id": 1,
        "_notion_page_id": "p",
        "_anything_else": "x",
        "author": "urn:li:person:abc",
        "lifecycleState": "DRAFT",
    }
    clean = mod.strip_meta_keys(payload)
    assert all(not k.startswith("_") for k in clean)
    assert clean["author"] == "urn:li:person:abc"


def test_resolve_author_replaces_placeholder():
    payload = {"author": mod.AUTHOR_URN_PLACEHOLDER, "x": 1}
    out = mod.resolve_author(payload, author_urn="urn:li:person:rick")
    assert out["author"] == "urn:li:person:rick"
    # original unchanged (shallow copy)
    assert payload["author"] == mod.AUTHOR_URN_PLACEHOLDER


def test_resolve_author_empty_raises():
    with pytest.raises(ValueError):
        mod.resolve_author({"author": "x"}, author_urn="")


# ---------- read_publishable / idempotency ----------

def test_read_publishable_skips_published(state_db):
    mod.ensure_publish_columns(state_db)
    _insert_draft(state_db, status="draft_ready")
    p2 = _insert_draft(state_db, status="published")
    rows = mod.read_publishable(state_db, limit=10)
    assert len(rows) == 1
    assert rows[0]["id"] != p2


def test_is_already_published(state_db):
    mod.ensure_publish_columns(state_db)
    pid = _insert_draft(state_db, status="published")
    assert mod.is_already_published(state_db, pid) is True
    pid2 = _insert_draft(state_db, status="draft_ready")
    assert mod.is_already_published(state_db, pid2) is False


# ---------- mark_published / mark_failed ----------

def test_mark_published_updates_row(state_db):
    mod.ensure_publish_columns(state_db)
    pid = _insert_draft(state_db, status="draft_ready")
    mod.mark_published(state_db, pid, post_urn="urn:li:share:777")
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT linkedin_status, linkedin_post_urn, linkedin_published_at "
        "FROM proposals WHERE id=?", (pid,),
    ).fetchone()
    conn.close()
    assert row[0] == "published"
    assert row[1] == "urn:li:share:777"
    assert row[2]  # ISO timestamp set


def test_mark_failed_truncates_long_error(state_db):
    mod.ensure_publish_columns(state_db)
    pid = _insert_draft(state_db, status="draft_ready")
    mod.mark_failed(state_db, pid, error="x" * 9999)
    conn = sqlite3.connect(state_db)
    err = conn.execute(
        "SELECT linkedin_last_error FROM proposals WHERE id=?", (pid,),
    ).fetchone()[0]
    conn.close()
    assert len(err) == 500


# ---------- publish_one ----------

def _mock_httpx_post(monkeypatch, *, status_code=201,
                     post_urn="urn:li:share:abc123",
                     body=None):
    body = body if body is not None else {"id": post_urn}
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {"x-restli-id": post_urn} if status_code == 201 else {}
    resp.content = json.dumps(body).encode()
    resp.text = json.dumps(body)
    resp.json.return_value = body
    client = MagicMock(spec=httpx.Client)
    client.__enter__ = lambda s: s
    client.__exit__ = lambda *a: None
    client.post.return_value = resp
    monkeypatch.setattr(mod.httpx, "Client", lambda *a, **kw: client)
    return client


def test_publish_one_success_marks_published(state_db, monkeypatch):
    mod.ensure_publish_columns(state_db)
    pid = _insert_draft(state_db, status="draft_ready")
    client = _mock_httpx_post(monkeypatch, post_urn="urn:li:share:888")
    row = mod.read_publishable(state_db, limit=1)[0]
    status, msg = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="AT-fake", dry_run=False,
    )
    assert status == "published"
    assert msg == "urn:li:share:888"
    # The POSTed payload must have NO meta keys + correct author.
    sent_payload = client.post.call_args.kwargs["json"]
    assert all(not k.startswith("_") for k in sent_payload)
    assert sent_payload["author"] == "urn:li:person:rick"
    # Headers must contain X-Restli-Protocol-Version + Bearer auth.
    headers = client.post.call_args.kwargs["headers"]
    assert headers["X-Restli-Protocol-Version"] == "2.0.0"
    assert headers["Authorization"].startswith("Bearer ")
    # DB updated
    assert mod.is_already_published(state_db, pid) is True


def test_publish_one_skips_already_published(state_db, monkeypatch):
    mod.ensure_publish_columns(state_db)
    _insert_draft(state_db, status="published")
    # Force read by selecting raw row directly (bypassing read_publishable)
    conn = sqlite3.connect(state_db)
    conn.row_factory = sqlite3.Row
    row = dict(conn.execute(
        "SELECT id, titular, notion_page_id, linkedin_status, "
        "linkedin_draft_payload FROM proposals"
    ).fetchone())
    conn.close()
    status, msg = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="AT-fake", dry_run=False,
    )
    assert status == "skipped"


def test_publish_one_http_400_marks_failed(state_db, monkeypatch):
    mod.ensure_publish_columns(state_db)
    pid = _insert_draft(state_db, status="draft_ready")
    _mock_httpx_post(
        monkeypatch, status_code=400,
        body={"message": "Field 'specificContent' invalid", "status": 400},
    )
    row = mod.read_publishable(state_db, limit=1)[0]
    status, msg = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="AT-fake", dry_run=False,
    )
    assert status == "failed"
    assert "HTTP 400" in msg
    conn = sqlite3.connect(state_db)
    new_status, err = conn.execute(
        "SELECT linkedin_status, linkedin_last_error FROM proposals WHERE id=?",
        (pid,),
    ).fetchone()
    conn.close()
    assert new_status == "failed"
    assert "400" in err


def test_publish_one_dry_run_no_post(state_db, monkeypatch, capsys):
    mod.ensure_publish_columns(state_db)
    _insert_draft(state_db, status="draft_ready")
    # If httpx.Client is invoked, fail loudly:
    monkeypatch.setattr(mod.httpx, "Client",
                        lambda *a, **kw: pytest.fail("httpx not allowed"))
    row = mod.read_publishable(state_db, limit=1)[0]
    status, msg = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="", dry_run=True,
    )
    assert status == "skipped"
    out = capsys.readouterr().out
    # Hilo 6 dry-run JSON contract: would_publish + content_hash + reasons.
    payload = json.loads(out.strip().splitlines()[0])
    assert payload["would_publish"] is True
    assert payload["reasons_blocked"] == []
    assert len(payload["content_hash"]) == 64
    # Old payload-dump output must NOT appear.
    assert "_offline_draft" not in out
    assert "_built_at" not in out


def test_publish_one_bad_json_marks_failed(state_db):
    mod.ensure_publish_columns(state_db)
    pid = _insert_draft(state_db, status="draft_ready")
    # Corrupt the payload column.
    conn = sqlite3.connect(state_db)
    conn.execute(
        "UPDATE proposals SET linkedin_draft_payload=? WHERE id=?",
        ("{not json", pid),
    )
    conn.commit()
    conn.close()
    row = mod.read_publishable(state_db, limit=1)[0]
    status, msg = mod.publish_one(
        row=row, state_db=state_db,
        author_urn="urn:li:person:rick",
        access_token="AT-fake", dry_run=False,
    )
    assert status == "failed"
    assert "JSON" in msg


# ---------- main() / refresh-on-expired integration ----------

def test_main_dry_run_uses_member_urn_from_tokens(
    state_db, tmp_path, monkeypatch, capsys,
):
    mod.ensure_publish_columns(state_db)
    _insert_draft(state_db, status="draft_ready")
    tokens_path = tmp_path / "linkedin-tokens.json"
    tokens_path.write_text(json.dumps({
        "access_token": "AT", "refresh_token": "RT",
        "access_token_expires_at": "2099-01-01T00:00:00+00:00",
        "refresh_token_expires_at": "2099-01-01T00:00:00+00:00",
        "obtained_at": "2026-05-07T00:00:00+00:00",
        "member_urn": "urn:li:person:tokens-urn",
    }))
    rc = mod.main([
        "--state-db", str(state_db),
        "--tokens-path", str(tokens_path),
        "--dry-run", "--max-posts", "1",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # Hilo 6: dry-run prints the JSON contract (no payload dump). The
    # author URN is no longer echoed in stdout — it goes into the actual
    # POSTed payload only on real publish.
    assert "would_publish" in out
    assert "content_hash" in out


def test_main_refreshes_expired_token(
    state_db, tmp_path, monkeypatch,
):
    """When access_token is expired, main() must call refresh internally."""
    mod.ensure_publish_columns(state_db)
    _insert_draft(state_db, status="draft_ready")
    tokens_path = tmp_path / "linkedin-tokens.json"
    # Already expired.
    tokens_path.write_text(json.dumps({
        "access_token": "AT-old", "refresh_token": "RT-still-good",
        "access_token_expires_at": "2020-01-01T00:00:00+00:00",
        "refresh_token_expires_at": "2099-01-01T00:00:00+00:00",
        "obtained_at": "2020-01-01T00:00:00+00:00",
        "member_urn": "urn:li:person:rick",
    }))
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret")

    refresh_calls = {"n": 0}

    def fake_exchange(**kwargs):
        refresh_calls["n"] += 1
        assert kwargs["grant_type"] == "refresh_token"
        return {"access_token": "AT-fresh", "expires_in": 5184000}

    monkeypatch.setattr(oauth, "_exchange", fake_exchange)
    # Mock the actual UGC POST.
    posted_token = {"value": ""}

    def fake_post_ugc(*, payload, access_token, client=None):
        posted_token["value"] = access_token
        return 201, "urn:li:share:refreshed", {"id": "urn:li:share:refreshed"}

    monkeypatch.setattr(mod, "post_ugc", fake_post_ugc)

    rc = mod.main([
        "--state-db", str(state_db),
        "--tokens-path", str(tokens_path),
        "--max-posts", "1",
    ])
    assert rc == 0
    assert refresh_calls["n"] == 1
    assert posted_token["value"] == "AT-fresh"
    # Tokens file updated.
    new = json.loads(tokens_path.read_text())
    assert new["access_token"] == "AT-fresh"


def test_main_no_author_urn_fails(state_db, tmp_path, monkeypatch):
    mod.ensure_publish_columns(state_db)
    _insert_draft(state_db, status="draft_ready")
    tokens_path = tmp_path / "linkedin-tokens.json"
    tokens_path.write_text(json.dumps({
        "access_token": "AT", "refresh_token": "RT",
        "access_token_expires_at": "2099-01-01T00:00:00+00:00",
        "refresh_token_expires_at": "2099-01-01T00:00:00+00:00",
        "obtained_at": "2026-05-07T00:00:00+00:00",
        # NO member_urn, NO env, NO --author-urn.
    }))
    monkeypatch.delenv("LINKEDIN_AUTHOR_URN", raising=False)
    rc = mod.main([
        "--state-db", str(state_db),
        "--tokens-path", str(tokens_path),
        "--dry-run", "--max-posts", "1",
    ])
    assert rc == 2


def test_main_no_drafts_returns_0(state_db, tmp_path):
    mod.ensure_publish_columns(state_db)
    rc = mod.main([
        "--state-db", str(state_db),
        "--tokens-path", str(tmp_path / "tk.json"),
        "--dry-run", "--max-posts", "1",
    ])
    assert rc == 0
