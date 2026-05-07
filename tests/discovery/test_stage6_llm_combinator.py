"""Tests for scripts/discovery/stage6_llm_combinator.py."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.discovery import stage6_llm_combinator as mod


@pytest.fixture
def state_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE discovered_items (
            url_canonica TEXT PRIMARY KEY,
            referente_id TEXT, referente_nombre TEXT, canal TEXT, titulo TEXT,
            publicado_en TEXT, primera_vez_visto TEXT,
            promovido_a_candidato_at TEXT, notion_page_id TEXT,
            contenido_html TEXT, contenido_extraido_at TEXT,
            description_cleaned_at TEXT, description_removals_count INTEGER,
            ranking_score REAL, ranking_reason TEXT, ranking_at TEXT
        )"""
    )
    items = [
        ("https://a.test/1", "AI in BIM revolution", "blog", "Alice", 0.95, "alta novedad", "2026-05-07"),
        ("https://a.test/2", "Low-code Revit plugin", "youtube", "Bob", 0.90, "tendencia", "2026-05-06"),
        ("https://a.test/3", "Automating clash detection", "linkedin", "Carol", 0.85, "caso real", "2026-05-05"),
        ("https://a.test/4", "Off-topic news", "blog", "Dan", 0.50, "ruido", "2026-05-04"),
    ]
    for url, titulo, canal, ref, score, reason, prom in items:
        conn.execute(
            "INSERT INTO discovered_items (url_canonica, titulo, canal, referente_nombre, "
            "ranking_score, ranking_reason, promovido_a_candidato_at) VALUES (?,?,?,?,?,?,?)",
            (url, titulo, canal, ref, score, reason, prom),
        )
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def cache_db(tmp_path: Path) -> Path:
    return tmp_path / "llm_cache.sqlite"


def test_top_n_loaded_correctly(state_db: Path):
    rows = mod.read_stage5_output(state_db, top_n=3)
    assert len(rows) == 3
    # ordered by ranking_score DESC
    assert rows[0]["url_canonica"] == "https://a.test/1"
    assert rows[2]["url_canonica"] == "https://a.test/3"


def test_prompt_includes_all_items(state_db: Path):
    rows = mod.read_stage5_output(state_db, top_n=3)
    prompt = mod.build_prompt(rows)
    for r in rows:
        assert r["url_canonica"] in prompt
    assert "JSON" in prompt
    assert "disciplinas" in prompt


def test_llm_response_parsed_to_proposals():
    raw = json.dumps({
        "proposals": [
            {
                "titular": "BIM se cruza con IA generativa",
                "hook": "Y cambia la forma de auditar planos.",
                "angulo": "Hoy, no en 5 anios.",
                "fuentes_urls": ["https://a.test/1", "https://a.test/2"],
                "disciplinas": ["BIM", "IA"],
                "score_relevancia": 0.92,
            }
        ]
    })
    out = mod.parse_proposals(raw)
    assert len(out) == 1
    p = out[0]
    assert p["titular"].startswith("BIM")
    assert p["fuentes_urls"] == ["https://a.test/1", "https://a.test/2"]
    assert p["disciplinas"] == ["BIM", "IA"]


def test_malformed_llm_output_skipped_with_warn():
    # No titular and no fuentes -> filtered out
    raw = json.dumps({
        "proposals": [
            {"titular": "", "fuentes_urls": ["https://a.test/1"]},
            {"titular": "OK title", "fuentes_urls": []},
            {"titular": "good", "fuentes_urls": ["https://a.test/3"], "disciplinas": ["BIM", "IA"]},
        ]
    })
    out = mod.parse_proposals(raw)
    assert len(out) == 1
    assert out[0]["titular"] == "good"


def test_cache_hit_skips_llm_call(cache_db: Path):
    mod.cache_put(cache_db, "openclaw/main", "PROMPT-XYZ", "CACHED-RESPONSE")
    hit = mod.cache_get(cache_db, "openclaw/main", "PROMPT-XYZ")
    assert hit == "CACHED-RESPONSE"


def test_cache_miss_calls_llm_and_persists(cache_db: Path):
    miss = mod.cache_get(cache_db, "openclaw/main", "fresh-prompt")
    assert miss is None
    mod.cache_put(cache_db, "openclaw/main", "fresh-prompt", "first")
    assert mod.cache_get(cache_db, "openclaw/main", "fresh-prompt") == "first"


def test_force_refresh_cache_bypasses_hit(cache_db: Path, state_db: Path, monkeypatch):
    """When --force-refresh-cache is set, even an existing cache entry must not be used."""
    prompt_holder = {}

    rows = mod.read_stage5_output(state_db, top_n=3)
    real_prompt = mod.build_prompt(rows)
    mod.cache_put(cache_db, "openclaw/main", real_prompt, json.dumps({
        "proposals": [{"titular": "STALE", "fuentes_urls": ["https://a.test/1"]}]
    }))

    fresh = json.dumps({
        "proposals": [{"titular": "FRESH", "fuentes_urls": ["https://a.test/2"], "disciplinas": ["BIM", "IA"]}]
    })

    def fake_llm(*, prompt, model, gateway_url, auth_token, timeout_s=120.0):
        prompt_holder["called"] = True
        return fresh

    monkeypatch.setattr(mod, "llm_call", fake_llm)
    monkeypatch.setattr(mod, "_gateway_token", lambda: "fake-token")

    rc = mod.main([
        "--top-n", "3",
        "--force-refresh-cache",
        "--state-db", str(state_db),
        "--cache-db", str(cache_db),
        "--dry-run",
    ])
    assert rc == 0
    assert prompt_holder.get("called") is True
    # cache should now hold the fresh response
    assert mod.cache_get(cache_db, "openclaw/main", real_prompt) == fresh


def test_proposals_persisted_to_state_with_status_draft(state_db: Path, cache_db: Path, monkeypatch):
    fresh = json.dumps({
        "proposals": [
            {
                "titular": "P1", "hook": "h1", "angulo": "a1",
                "fuentes_urls": ["https://a.test/1"], "disciplinas": ["BIM", "IA"],
                "score_relevancia": 0.8,
            }
        ]
    })
    monkeypatch.setattr(mod, "llm_call", lambda **kw: fresh)
    monkeypatch.setattr(mod, "_gateway_token", lambda: "fake-token")

    rc = mod.main([
        "--top-n", "3",
        "--state-db", str(state_db),
        "--cache-db", str(cache_db),
    ])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    rows = list(conn.execute("SELECT titular, status, fuentes_urls, disciplinas FROM proposals"))
    conn.close()
    assert len(rows) == 1
    titular, status, fuentes_json, disc_json = rows[0]
    assert titular == "P1"
    assert status == "draft"
    assert json.loads(fuentes_json) == ["https://a.test/1"]
    assert json.loads(disc_json) == ["BIM", "IA"]
