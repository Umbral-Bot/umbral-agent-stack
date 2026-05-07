"""Tests for scripts/discovery/stage7_publish_drafts.py."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.discovery import stage7_publish_drafts as mod


SCHEMA = {
    "Título": "title",
    "idempotency_key": "rich_text",
    "Tipo de contenido": "select",
    "Ángulo editorial": "rich_text",
    "Resumen fuente": "rich_text",
    "Fuente primaria": "url",
    "Creado por sistema": "checkbox",
}


@pytest.fixture
def state_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular TEXT NOT NULL, hook TEXT, angulo TEXT,
            fuentes_urls TEXT NOT NULL, disciplinas TEXT NOT NULL,
            score REAL, ts INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            notion_page_id TEXT, last_error TEXT
        )"""
    )

    def insert(titular, status="draft", page_id=None, fuentes=("https://a.test/1",)):
        conn.execute(
            "INSERT INTO proposals (titular, hook, angulo, fuentes_urls, disciplinas, "
            "score, ts, status, notion_page_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (titular, "h", "a", json.dumps(list(fuentes)), json.dumps(["BIM", "IA"]),
             0.9, 100, status, page_id),
        )

    insert("Pending one")
    insert("Pending two")
    insert("Already published", page_id="page-already-1")
    insert("In other status", status="other")
    conn.commit()
    conn.close()
    return db


def test_proposals_loaded_filtered_by_status(state_db: Path):
    rows = mod.read_pending_proposals(state_db, status="draft", limit=None)
    titulares = [r["titular"] for r in rows]
    assert titulares == ["Pending one", "Pending two"]
    assert all(isinstance(r["fuentes_urls"], list) for r in rows)


def test_already_published_proposal_skipped(state_db: Path):
    rows = mod.read_pending_proposals(state_db, status="draft", limit=None)
    assert "Already published" not in [r["titular"] for r in rows]


def test_page_payload_includes_required_props():
    proposal = {
        "id": 1, "titular": "Mi titular", "hook": "Hook frase",
        "angulo": "Por que importa", "fuentes_urls": ["https://a.test/1", "https://a.test/2"],
        "disciplinas": ["BIM", "IA"], "ts": 12345,
    }
    payload = mod.build_page_payload(
        proposal=proposal, data_source_id="DS-1", schema=SCHEMA,
    )
    assert payload["parent"] == {"type": "data_source_id", "data_source_id": "DS-1"}
    props = payload["properties"]
    assert props["Título"]["title"][0]["text"]["content"] == "Mi titular"
    assert props["idempotency_key"]["rich_text"][0]["text"]["content"]
    assert props["Tipo de contenido"]["select"]["name"] == "linkedin_post"
    assert props["Fuente primaria"]["url"] == "https://a.test/1"
    assert props["Creado por sistema"]["checkbox"] is True
    # blocks include hook + angulo + disciplinas + 2 fuentes (bulleted)
    types = [b["type"] for b in payload["children"]]
    assert "paragraph" in types
    assert types.count("bulleted_list_item") == 2


def test_schema_detected_from_live_query(monkeypatch):
    client = MagicMock()
    client.get.side_effect = [
        {"data_sources": [{"id": "DS-LIVE", "name": "Publicaciones"}]},
        {"properties": {"Título": {"type": "title"}, "Canal": {"type": "select"}}},
    ]
    ds_id = mod.fetch_data_source_id(client, "DB-LIVE")
    schema = mod.fetch_schema(client, ds_id)
    assert ds_id == "DS-LIVE"
    assert schema == {"Título": "title", "Canal": "select"}


def test_create_page_persists_notion_id_to_state(state_db: Path, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-key")

    fake_client = MagicMock()
    fake_client.get.side_effect = [
        {"data_sources": [{"id": "DS-X", "name": "Publicaciones"}]},
        {"properties": {k: {"type": v} for k, v in SCHEMA.items()}},
    ]
    fake_client.post.side_effect = [
        {"id": "page-NEW-1"},
        {"id": "page-NEW-2"},
    ]

    monkeypatch.setattr(mod, "NotionClient", lambda token: fake_client)

    rc = mod.main([
        "--state-db", str(state_db),
        "--limit", "2",
    ])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    rows = list(conn.execute(
        "SELECT titular, status, notion_page_id FROM proposals WHERE titular LIKE 'Pending%'"
    ))
    conn.close()
    assert ("Pending one", "published", "page-NEW-1") in rows
    assert ("Pending two", "published", "page-NEW-2") in rows


def test_dry_run_no_pages_created(state_db: Path, monkeypatch, capsys):
    monkeypatch.setenv("NOTION_API_KEY", "test-key")
    fake_client = MagicMock()
    fake_client.get.side_effect = [
        {"data_sources": [{"id": "DS-X", "name": "Publicaciones"}]},
        {"properties": {k: {"type": v} for k, v in SCHEMA.items()}},
    ]
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake_client)

    rc = mod.main([
        "--state-db", str(state_db),
        "--dry-run",
    ])
    assert rc == 0
    fake_client.post.assert_not_called()
    out = capsys.readouterr().out
    assert "[dry-run]" in out
    # state remained unchanged
    conn = sqlite3.connect(state_db)
    n = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE status='draft' AND notion_page_id IS NULL"
    ).fetchone()[0]
    conn.close()
    assert n == 2
