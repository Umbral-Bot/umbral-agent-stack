"""Tests for scripts/discovery/stage9_linkedin_draft.py (offline scaffold)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.discovery import stage9_linkedin_draft as mod


# ---------- Fixtures ----------

def _create_proposals_table(db: Path) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular TEXT NOT NULL,
            hook TEXT, angulo TEXT,
            fuentes_urls TEXT NOT NULL,
            disciplinas TEXT NOT NULL,
            score REAL, ts INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            notion_page_id TEXT, last_error TEXT
        )"""
    )
    conn.commit()
    conn.close()


def _insert(db: Path, **kwargs):
    conn = sqlite3.connect(db)
    cols = ["titular", "hook", "angulo", "fuentes_urls", "disciplinas",
            "score", "ts", "status", "notion_page_id"]
    defaults = {
        "titular": "T", "hook": "h", "angulo": "a",
        "fuentes_urls": json.dumps(["https://src.test/x"]),
        "disciplinas": json.dumps(["BIM"]),
        "score": 0.5, "ts": 100, "status": "published",
        "notion_page_id": None,
    }
    defaults.update(kwargs)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT INTO proposals ({','.join(cols)}) VALUES ({placeholders})",
        tuple(defaults[c] for c in cols),
    )
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return pid


@pytest.fixture
def state_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    _create_proposals_table(db)
    return db


def _set_image_status(db: Path, pid: int, status: str = "ok") -> None:
    mod.ensure_linkedin_columns(db)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE proposals SET image_status=? WHERE id=?", (status, pid))
    conn.commit()
    conn.close()


def _make_page(estado: str = "Autorizado", *, copy_linkedin: str = "",
               cover_url: str = "", title: str = "Mi titular",
               source: str = "https://src.test/article") -> dict:
    props: dict = {
        "Estado": {"type": "status", "status": {"name": estado}},
        "Título": {"type": "title", "title": [{"plain_text": title}]},
        "Fuente primaria": {"type": "url", "url": source},
    }
    if copy_linkedin:
        props["Copy LinkedIn"] = {
            "type": "rich_text",
            "rich_text": [{"plain_text": copy_linkedin}],
        }
    page: dict = {"id": "page-X", "properties": props}
    if cover_url:
        page["cover"] = {"type": "external", "external": {"url": cover_url}}
    return page


# ---------- Tests ----------

def test_migration_idempotent(state_db: Path):
    mod.ensure_linkedin_columns(state_db)
    mod.ensure_linkedin_columns(state_db)  # second run must not fail
    conn = sqlite3.connect(state_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(proposals)")}
    conn.close()
    for c in ("linkedin_status", "linkedin_draft_payload",
              "linkedin_last_attempt_at", "linkedin_last_error",
              "image_status"):
        assert c in cols, c


def test_candidate_selection_requires_image_ok(state_db: Path):
    p_ok = _insert(state_db, titular="OK candidate",
                   notion_page_id="page-ok-1")
    _insert(state_db, titular="No image",
            notion_page_id="page-noimg")
    _insert(state_db, titular="No notion page", notion_page_id=None)
    _set_image_status(state_db, p_ok, "ok")
    rows = mod.read_pending_proposals(state_db, force=False, limit=10)
    titulares = [r["titular"] for r in rows]
    assert titulares == ["OK candidate"]


def test_skip_when_already_draft_ready(state_db: Path):
    pid = _insert(state_db, titular="Already drafted",
                  notion_page_id="page-1")
    _set_image_status(state_db, pid, "ok")
    conn = sqlite3.connect(state_db)
    conn.execute(
        "UPDATE proposals SET linkedin_status='draft_ready' WHERE id=?",
        (pid,),
    )
    conn.commit()
    conn.close()
    rows = mod.read_pending_proposals(state_db, force=False, limit=10)
    assert rows == []
    rows_force = mod.read_pending_proposals(state_db, force=True, limit=10)
    assert [r["id"] for r in rows_force] == [pid]


def test_dry_run_does_not_write_state(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Dry-run candidate",
                  notion_page_id="page-DR-1")
    _set_image_status(state_db, pid, "ok")
    monkeypatch.setenv("NOTION_API_KEY", "test-key")

    fake_client = MagicMock()
    fake_client.get.return_value = _make_page(
        copy_linkedin="hook line\n\nbody paragraph",
    )
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake_client)

    rc = mod.main([
        "--state-db", str(state_db), "--dry-run", "--max-drafts", "5",
    ])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT linkedin_status, linkedin_draft_payload FROM proposals WHERE id=?",
        (pid,),
    ).fetchone()
    conn.close()
    assert row == (None, None)


def test_post_text_hook_url_and_max_chars():
    text = mod.build_post_text(
        copy_linkedin="", body_lines=["Una intro corta.", "Detalle dos."],
        source_url="https://src.test/article",
        titular="Mi titular", hook="Hook frase",
    )
    assert text.split("\n", 1)[0] == "Una intro corta."
    assert text.endswith("https://src.test/article")
    assert len(text) <= mod.MAX_POST_CHARS

    long_body = "x" * (mod.MAX_POST_CHARS + 500)
    text2 = mod.build_post_text(
        copy_linkedin=long_body, body_lines=[],
        source_url="https://src.test/long",
        titular="t", hook="",
    )
    assert len(text2) <= mod.MAX_POST_CHARS
    assert text2.endswith("https://src.test/long")


def test_force_regenerates_existing_draft(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Regen me", notion_page_id="page-RG-1")
    _set_image_status(state_db, pid, "ok")
    conn = sqlite3.connect(state_db)
    conn.execute(
        "UPDATE proposals SET linkedin_status='draft_ready', "
        "linkedin_draft_payload='{\"old\":true}' WHERE id=?",
        (pid,),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("NOTION_API_KEY", "test-key")
    fake_client = MagicMock()
    fake_client.get.return_value = _make_page(copy_linkedin="new hook")
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake_client)

    rc = mod.main(["--state-db", str(state_db), "--force", "--max-drafts", "5"])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    payload_json = conn.execute(
        "SELECT linkedin_draft_payload FROM proposals WHERE id=?", (pid,),
    ).fetchone()[0]
    conn.close()
    payload = json.loads(payload_json)
    assert payload["_offline_draft"] is True
    assert "old" not in payload
    text = payload["specificContent"]["com.linkedin.ugc.ShareContent"][
        "shareCommentary"]["text"]
    assert text.startswith("new hook")


def test_failed_when_page_fetch_404(state_db: Path, monkeypatch):
    import httpx
    pid = _insert(state_db, titular="404 page", notion_page_id="page-404")
    _set_image_status(state_db, pid, "ok")
    monkeypatch.setenv("NOTION_API_KEY", "test-key")

    fake_resp = MagicMock(status_code=404, text="not found")
    fake_client = MagicMock()
    fake_client.get.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=fake_resp,
    )
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake_client)

    rc = mod.main(["--state-db", str(state_db), "--max-drafts", "5"])
    assert rc == 1
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT linkedin_status, linkedin_last_error FROM proposals WHERE id=?",
        (pid,),
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "404" in (row[1] or "")


def test_max_drafts_limit_respected(state_db: Path, monkeypatch):
    pids = []
    for i in range(5):
        p = _insert(state_db, titular=f"row {i}",
                    notion_page_id=f"page-many-{i}")
        pids.append(p)
    for p in pids:
        _set_image_status(state_db, p, "ok")

    monkeypatch.setenv("NOTION_API_KEY", "test-key")
    fake_client = MagicMock()
    fake_client.get.return_value = _make_page(copy_linkedin="hi")
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake_client)

    rc = mod.main(["--state-db", str(state_db), "--max-drafts", "2"])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    n_done = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE linkedin_status='draft_ready'"
    ).fetchone()[0]
    conn.close()
    assert n_done == 2


def test_awaiting_approval_when_estado_not_approved(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="not yet approved",
                  notion_page_id="page-AW-1")
    _set_image_status(state_db, pid, "ok")
    monkeypatch.setenv("NOTION_API_KEY", "test-key")
    fake_client = MagicMock()
    fake_client.get.return_value = _make_page(estado="Borrador",
                                              copy_linkedin="hi")
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake_client)

    rc = mod.main(["--state-db", str(state_db), "--max-drafts", "5"])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT linkedin_status, linkedin_draft_payload FROM proposals WHERE id=?",
        (pid,),
    ).fetchone()
    conn.close()
    assert row[0] == "awaiting_approval"
    assert row[1] is None
