"""Tests for scripts/discovery/stage8_image_generator."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.discovery import stage8_image_generator as mod


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def state_db(tmp_path: Path) -> Path:
    """Create a state.sqlite mirroring Stage 6's proposals DDL."""
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular TEXT NOT NULL,
            hook TEXT,
            angulo TEXT,
            fuentes_urls TEXT NOT NULL,
            disciplinas TEXT NOT NULL,
            score REAL,
            ts INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            notion_page_id TEXT,
            last_error TEXT
        )"""
    )
    rows = [
        # id, titular, hook, angulo, urls, disciplinas, score, ts, status, page
        (1, "BIM y nubes de puntos en obra civil", "Hook 1", "Ángulo A",
         json.dumps(["https://a.test/1"]), json.dumps(["BIM", "Civil"]),
         0.9, 1700000000, "published", "page-aaa-111"),
        (2, "Plugin low-code para Revit", "Hook 2", "Ángulo B",
         json.dumps(["https://a.test/2"]), json.dumps(["Revit"]),
         0.8, 1700000100, "published", "page-bbb-222"),
        (3, "Borrador sin página", "Hook 3", "Ángulo C",
         json.dumps([]), json.dumps([]),
         0.7, 1700000200, "draft", None),
    ]
    conn.executemany(
        "INSERT INTO proposals(id,titular,hook,angulo,fuentes_urls,disciplinas,"
        "score,ts,status,notion_page_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def published_proposal() -> dict:
    return {
        "id": 42,
        "titular": "BIM y nubes de puntos en obra civil",
        "hook": "Las herramientas open-source maduran",
        "angulo": "Cómo afecta esto a estudios pequeños",
        "fuentes_urls": ["https://a.test/1"],
        "disciplinas": ["BIM", "Civil"],
        "notion_page_id": "page-aaa-111",
        "image_status": None,
        "image_last_attempt_at": None,
    }


# --------------------------------------------------------------------------
# Test 1 — prompt build
# --------------------------------------------------------------------------

def test_build_image_prompt_uses_titular_angulo_disciplinas(published_proposal):
    p = mod.build_image_prompt(published_proposal)
    assert "BIM y nubes de puntos en obra civil" in p
    assert "Cómo afecta esto a estudios pequeños" in p
    assert "BIM" in p and "Civil" in p
    # editorial style guard rails always present
    assert "no text" in p.lower()
    assert "no watermarks" in p.lower()


def test_build_image_prompt_rejects_missing_titular():
    with pytest.raises(ValueError):
        mod.build_image_prompt({"titular": "", "angulo": "x", "disciplinas": []})


def test_build_image_prompt_handles_empty_optional_fields():
    p = mod.build_image_prompt({
        "titular": "Solo titular",
        "angulo": None,
        "disciplinas": [],
    })
    assert "Solo titular" in p
    # style suffix still present
    assert "Editorial illustration" in p


# --------------------------------------------------------------------------
# Test 2 — schema migration (idempotent)
# --------------------------------------------------------------------------

def test_ensure_image_columns_adds_missing_columns(state_db):
    mod.ensure_image_columns(state_db)
    conn = sqlite3.connect(state_db)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(proposals)")}
    finally:
        conn.close()
    for new_col in mod.IMAGE_COLUMNS:
        assert new_col in cols


def test_ensure_image_columns_is_idempotent(state_db):
    mod.ensure_image_columns(state_db)
    mod.ensure_image_columns(state_db)  # second run must not raise
    mod.ensure_image_columns(state_db)
    conn = sqlite3.connect(state_db)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(proposals)")]
    finally:
        conn.close()
    # no duplicate columns
    for col in mod.IMAGE_COLUMNS:
        assert cols.count(col) == 1


def test_ensure_image_columns_fails_when_table_missing(tmp_path):
    db = tmp_path / "empty.sqlite"
    sqlite3.connect(db).close()
    with pytest.raises(RuntimeError, match="proposals"):
        mod.ensure_image_columns(db)


# --------------------------------------------------------------------------
# Test 3 — candidate selection (idempotency / retry / force)
# --------------------------------------------------------------------------

def test_read_candidate_proposals_skips_unpublished_and_already_ok(state_db):
    mod.ensure_image_columns(state_db)
    # mark proposal id=1 as already ok → must be skipped
    mod.mark_image_ok(state_db, 1, image_url="https://x", image_prompt="p")
    cands = mod.read_candidate_proposals(state_db, limit=None, force=False)
    ids = [c["id"] for c in cands]
    assert ids == [2]  # id=1 ok, id=3 unpublished


def test_read_candidate_proposals_force_returns_all_published(state_db):
    mod.ensure_image_columns(state_db)
    mod.mark_image_ok(state_db, 1, image_url="https://x", image_prompt="p")
    cands = mod.read_candidate_proposals(state_db, limit=None, force=True)
    ids = sorted(c["id"] for c in cands)
    assert ids == [1, 2]  # id=3 unpublished still excluded (no notion_page_id)


def test_read_candidate_proposals_retries_failed_after_window(state_db):
    mod.ensure_image_columns(state_db)
    # fail proposal 1 with last_attempt = recent → must be skipped
    mod.mark_image_failed(state_db, 1, "boom")
    cands = mod.read_candidate_proposals(state_db, limit=None, force=False)
    assert 1 not in [c["id"] for c in cands]

    # backdate last_attempt to 25 h ago → must be retried
    conn = sqlite3.connect(state_db)
    conn.execute(
        "UPDATE proposals SET image_last_attempt_at=? WHERE id=1",
        (int(time.time()) - 25 * 3600,),
    )
    conn.commit()
    conn.close()
    cands = mod.read_candidate_proposals(state_db, limit=None, force=False)
    assert 1 in [c["id"] for c in cands]


# --------------------------------------------------------------------------
# Test 4 — cost guard
# --------------------------------------------------------------------------

def test_cost_guard_aborts_when_exceeds_cap():
    with pytest.raises(RuntimeError, match="Cost guard"):
        mod.cost_guard(n_proposals=5, cost_per_image=0.50, max_per_image=0.20)


def test_cost_guard_allows_when_under_cap():
    # must not raise
    mod.cost_guard(n_proposals=10, cost_per_image=0.04, max_per_image=0.20)


# --------------------------------------------------------------------------
# Test 5 — dry-run does NOT call worker / Notion
# --------------------------------------------------------------------------

def test_process_proposal_dry_run_does_not_call_worker(
    state_db, published_proposal, tmp_path
):
    mod.ensure_image_columns(state_db)
    fake_handle = MagicMock()
    with patch(
        "worker.tasks.google_image.handle_google_image_generate", fake_handle
    ):
        res = mod.process_proposal(
            client=None,
            db_path=state_db,
            proposal=published_proposal,
            image_dir=tmp_path / "img",
            model="m",
            size="1024x1024",
            schema_props={"Visual asset URL": "url"},
            dry_run=True,
        )
    assert res["dry_run"] is True
    assert "prompt" in res
    fake_handle.assert_not_called()


# --------------------------------------------------------------------------
# Test 6 — full process_proposal happy path with mocks
# --------------------------------------------------------------------------

def test_process_proposal_happy_path_marks_ok(
    state_db, published_proposal, tmp_path, monkeypatch
):
    mod.ensure_image_columns(state_db)
    # patch the proposal id to match table row id=1
    published_proposal["id"] = 1

    # Stub the in-process worker handler.
    fake_image_path = tmp_path / "fake.png"
    fake_image_path.write_bytes(b"\x89PNG fake")

    def fake_handle(payload):
        return {
            "ok": True,
            "model": payload["model"],
            "size": payload["size"],
            "count": 1,
            "images": [
                {
                    "index": 0,
                    "output_path": str(fake_image_path),
                    "mime_type": "image/png",
                    "size_bytes": fake_image_path.stat().st_size,
                }
            ],
        }

    # Stub NotionClient methods.
    client = MagicMock(spec=mod.NotionClient)
    client.upload_file.return_value = {"id": "upload-xyz", "status": "uploaded"}
    client.patch.return_value = {}
    client.get.return_value = {
        "cover": {"file": {"url": "https://files.notion.so/abc.png"}}
    }

    with patch(
        "worker.tasks.google_image.handle_google_image_generate", fake_handle
    ):
        res = mod.process_proposal(
            client=client,
            db_path=state_db,
            proposal=published_proposal,
            image_dir=tmp_path / "img",
            model="gemini-3-pro-image-preview",
            size="1024x1024",
            schema_props={"Visual asset URL": "url"},
            dry_run=False,
        )

    assert "error" not in res
    assert res["notion_url"] == "https://files.notion.so/abc.png"
    # state DB updated
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT image_status, image_url FROM proposals WHERE id=1"
    ).fetchone()
    conn.close()
    assert row == ("ok", "https://files.notion.so/abc.png")

    # Cover patch + insert child block + URL prop patch + GET = 4 patches/posts
    client.upload_file.assert_called_once()
    # at least cover + body insert + URL prop = 3 patches
    assert client.patch.call_count >= 3


# --------------------------------------------------------------------------
# Test 7 — schema gap (Visual asset URL absent) does not abort
# --------------------------------------------------------------------------

def test_attach_image_skips_url_prop_when_missing_in_schema(
    tmp_path, caplog
):
    fake_file = tmp_path / "f.png"
    fake_file.write_bytes(b"\x89PNG")

    client = MagicMock(spec=mod.NotionClient)
    client.upload_file.return_value = {"id": "u-1"}
    client.patch.return_value = {}
    client.get.return_value = {"cover": {"file": {"url": "https://x"}}}

    # schema without 'Visual asset URL'
    schema = {"Título": "title", "Estado": "status"}
    url = mod.attach_image_to_notion(
        client,
        page_id="page-zzz",
        file_path=fake_file,
        caption="caption",
        schema_props=schema,
    )
    assert url == "https://x"
    # Must have set cover + inserted body block, but NOT updated URL prop.
    # We can verify by counting patch calls (cover + body = 2; URL prop adds 3).
    assert client.patch.call_count == 2


# --------------------------------------------------------------------------
# Test 8 — process_proposal failure path marks failed and does not raise
# --------------------------------------------------------------------------

def test_process_proposal_failure_marks_failed(
    state_db, published_proposal, tmp_path
):
    mod.ensure_image_columns(state_db)
    published_proposal["id"] = 2

    def fake_handle(_payload):
        raise RuntimeError("gemini boom")

    client = MagicMock(spec=mod.NotionClient)

    with patch(
        "worker.tasks.google_image.handle_google_image_generate", fake_handle
    ):
        res = mod.process_proposal(
            client=client,
            db_path=state_db,
            proposal=published_proposal,
            image_dir=tmp_path / "img",
            model="m",
            size="1024x1024",
            schema_props={"Visual asset URL": "url"},
            dry_run=False,
        )

    assert "error" in res
    assert "gemini boom" in res["error"]
    # state DB reflects failure
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT image_status, image_last_error FROM proposals WHERE id=2"
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "gemini boom" in (row[1] or "")
    # Notion client must NOT have been touched (failure occurred at gen step).
    client.upload_file.assert_not_called()
