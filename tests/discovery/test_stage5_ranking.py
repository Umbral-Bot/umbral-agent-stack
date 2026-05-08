"""Tests para Stage 5 ranking determinístico.

Cubre:
- Pesos individuales (cada peso aislado, otros en 0).
- Reproducibilidad bit-for-bit.
- Edge cases (0 items, 1 item, título vacío).
- Precision@5 sobre dataset sintético (≥80%).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts.discovery import stage5_rank_candidates as s5


REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "evals" / "stage5_ranking" / "dataset.jsonl"
CONFIG = REPO_ROOT / "config" / "aec_keywords.yaml"

FIXED_NOW = datetime(2026, 5, 7, 18, 0, 0, tzinfo=timezone.utc)


def _config_with_weights(tmp_path: Path, **weights_override) -> Path:
    """Build a config YAML with custom weights, keeping bucket content."""
    base = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    base["weights"].update(weights_override)
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    return p


def _make_db(tmp_path: Path, rows: list[dict]) -> Path:
    db = tmp_path / "state.sqlite"
    con = sqlite3.connect(db)
    con.execute(
        """CREATE TABLE discovered_items(
            url_canonica TEXT PRIMARY KEY,
            referente_id TEXT NOT NULL,
            referente_nombre TEXT NOT NULL,
            canal TEXT NOT NULL,
            titulo TEXT,
            publicado_en TEXT,
            primera_vez_visto TEXT NOT NULL,
            promovido_a_candidato_at TEXT,
            notion_page_id TEXT,
            contenido_html TEXT,
            contenido_extraido_at TEXT
        )"""
    )
    for r in rows:
        con.execute(
            "INSERT INTO discovered_items(url_canonica, referente_id, referente_nombre, "
            "canal, titulo, publicado_en, primera_vez_visto, promovido_a_candidato_at, "
            "contenido_html) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["url"],
                r.get("ref_id", "ref_x"),
                r.get("ref_nombre", "Ref X"),
                r.get("canal", "rss"),
                r.get("titulo"),
                r.get("publicado_en"),
                "2026-05-01T00:00:00Z",
                r.get("promovido", "2026-05-02T00:00:00Z"),
                r.get("contenido_html"),
            ),
        )
    con.commit()
    con.close()
    return db


# ---------------------------------------------------------------------------
# 1. Peso w1 (core_aec) aislado
# ---------------------------------------------------------------------------


def test_w1_core_aec_isolated(tmp_path: Path):
    cfg_path = _config_with_weights(
        tmp_path,
        w1_core_aec=1.0,
        w2_adyacente=0.0,
        w3_recency=0.0,
        w4_referente=0.0,
    )
    cfg = s5.load_config(cfg_path)
    db = _make_db(
        tmp_path,
        [
            {"url": "u1", "titulo": "BIM y Revit en obra", "publicado_en": "2026-05-06T00:00:00Z"},
            {"url": "u2", "titulo": "Receta de cocina", "publicado_en": "2026-05-06T00:00:00Z"},
        ],
    )
    con = sqlite3.connect(db)
    cands = s5.fetch_candidates(con, rerank=False)
    ranked = s5.rank(cands, cfg, now=FIXED_NOW)
    con.close()
    assert ranked[0]["url_canonica"] == "u1"
    assert ranked[0]["ranking_score"] > 0
    assert ranked[1]["ranking_score"] == 0.0


def test_w2_adyacente_isolated(tmp_path: Path):
    cfg_path = _config_with_weights(
        tmp_path, w1_core_aec=0.0, w2_adyacente=1.0, w3_recency=0.0, w4_referente=0.0
    )
    cfg = s5.load_config(cfg_path)
    db = _make_db(
        tmp_path,
        [
            {"url": "u1", "titulo": "automatizacion con RPA y low-code"},
            {"url": "u2", "titulo": "BIM Revit IFC"},  # no debería puntuar (sin adyacente)
        ],
    )
    con = sqlite3.connect(db)
    ranked = s5.rank(s5.fetch_candidates(con, rerank=False), cfg, now=FIXED_NOW)
    con.close()
    assert ranked[0]["url_canonica"] == "u1"
    assert ranked[1]["ranking_score"] == 0.0


def test_w3_recency_isolated(tmp_path: Path):
    cfg_path = _config_with_weights(
        tmp_path, w1_core_aec=0.0, w2_adyacente=0.0, w3_recency=1.0, w4_referente=0.0
    )
    cfg = s5.load_config(cfg_path)
    fresh = (FIXED_NOW - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = (FIXED_NOW - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    db = _make_db(
        tmp_path,
        [
            {"url": "u_fresh", "titulo": "X", "publicado_en": fresh},
            {"url": "u_old", "titulo": "X", "publicado_en": old},
        ],
    )
    con = sqlite3.connect(db)
    ranked = s5.rank(s5.fetch_candidates(con, rerank=False), cfg, now=FIXED_NOW)
    con.close()
    assert ranked[0]["url_canonica"] == "u_fresh"
    assert ranked[1]["ranking_score"] == 0.0


def test_w4_referente_isolated(tmp_path: Path):
    cfg_path = _config_with_weights(
        tmp_path, w1_core_aec=0.0, w2_adyacente=0.0, w3_recency=0.0, w4_referente=1.0
    )
    cfg = s5.load_config(cfg_path)
    db = _make_db(
        tmp_path,
        [
            {"url": "u_yt", "titulo": "X", "canal": "youtube"},
            {"url": "u_otros", "titulo": "X", "canal": "otros"},
        ],
    )
    con = sqlite3.connect(db)
    ranked = s5.rank(s5.fetch_candidates(con, rerank=False), cfg, now=FIXED_NOW)
    con.close()
    assert ranked[0]["url_canonica"] == "u_yt"
    assert ranked[0]["ranking_score"] > ranked[1]["ranking_score"]


# ---------------------------------------------------------------------------
# 2. Reproducibilidad bit-for-bit
# ---------------------------------------------------------------------------


def test_reproducibilidad_bit_for_bit(tmp_path: Path):
    cfg = s5.load_config(CONFIG)
    rows = [
        {"url": "a", "titulo": "BIM Revit MEP", "publicado_en": "2026-05-05T00:00:00Z", "canal": "youtube"},
        {"url": "b", "titulo": "automatizacion RPA", "publicado_en": "2026-04-01T00:00:00Z", "canal": "rss"},
        {"url": "c", "titulo": "off topic", "publicado_en": "2026-05-06T00:00:00Z", "canal": "otros"},
    ]
    db = _make_db(tmp_path, rows)
    con = sqlite3.connect(db)
    cands = s5.fetch_candidates(con, rerank=False)
    r1 = s5.rank(cands, cfg, now=FIXED_NOW)
    r2 = s5.rank(cands, cfg, now=FIXED_NOW)
    con.close()
    s1 = json.dumps(r1, ensure_ascii=False, sort_keys=True)
    s2 = json.dumps(r2, ensure_ascii=False, sort_keys=True)
    assert s1 == s2


# ---------------------------------------------------------------------------
# 3. Edge cases
# ---------------------------------------------------------------------------


def test_edge_zero_items(tmp_path: Path):
    cfg = s5.load_config(CONFIG)
    db = _make_db(tmp_path, [])
    con = sqlite3.connect(db)
    ranked = s5.rank(s5.fetch_candidates(con, rerank=False), cfg, now=FIXED_NOW)
    con.close()
    assert ranked == []
    rep = s5.build_report(ranked, cfg, mode="dry-run", top_n=10, now=FIXED_NOW)
    assert rep["stats"]["candidates_total"] == 0
    assert rep["items"] == []


def test_edge_one_item(tmp_path: Path):
    cfg = s5.load_config(CONFIG)
    db = _make_db(tmp_path, [{"url": "u1", "titulo": "BIM", "canal": "youtube"}])
    con = sqlite3.connect(db)
    ranked = s5.rank(s5.fetch_candidates(con, rerank=False), cfg, now=FIXED_NOW)
    con.close()
    assert len(ranked) == 1
    assert ranked[0]["ranking_score"] > 0


def test_edge_empty_titulo(tmp_path: Path):
    cfg = s5.load_config(CONFIG)
    db = _make_db(
        tmp_path,
        [
            {"url": "u_empty", "titulo": None, "contenido_html": None, "canal": "otros"},
            {"url": "u_full", "titulo": "BIM Revit", "canal": "youtube"},
        ],
    )
    con = sqlite3.connect(db)
    ranked = s5.rank(s5.fetch_candidates(con, rerank=False), cfg, now=FIXED_NOW)
    con.close()
    by_url = {r["url_canonica"]: r for r in ranked}
    # Empty title/contenido: keyword scores are 0; only referente weight applies.
    # canal=otros => 0.3 * w4(0.1) = 0.03.
    assert by_url["u_empty"]["ranking_score"] == pytest.approx(0.03, abs=1e-6)
    assert by_url["u_full"]["ranking_score"] > by_url["u_empty"]["ranking_score"]


# ---------------------------------------------------------------------------
# 4. Precision@5 sobre dataset
# ---------------------------------------------------------------------------


def test_precision_at_5_top_bucket(tmp_path: Path):
    cfg = s5.load_config(CONFIG)
    rows = []
    with DATASET.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            pub_dt = FIXED_NOW - timedelta(days=ex["publicado_en_offset_days"])
            rows.append(
                {
                    "url": ex["id"],
                    "titulo": ex["titulo"],
                    "contenido_html": ex.get("contenido_html"),
                    "publicado_en": pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "canal": ex["canal"],
                    "ref_nombre": ex["id"],
                }
            )
    db = _make_db(tmp_path, rows)
    bucket_by_id = {
        json.loads(line)["id"]: json.loads(line)["expected_rank_bucket"]
        for line in DATASET.open(encoding="utf-8")
        if line.strip()
    }
    con = sqlite3.connect(db)
    ranked = s5.rank(s5.fetch_candidates(con, rerank=False), cfg, now=FIXED_NOW)
    con.close()
    top5_ids = [r["url_canonica"] for r in ranked[:5]]
    correct = sum(1 for uid in top5_ids if bucket_by_id[uid] == "top")
    precision = correct / 5
    assert precision >= 0.8, f"precision@5={precision}; top5={top5_ids}"


# ---------------------------------------------------------------------------
# 5. Modo --commit escribe columnas + idempotencia
# ---------------------------------------------------------------------------


def test_commit_writes_columns_and_idempotent(tmp_path: Path, monkeypatch):
    db = _make_db(
        tmp_path,
        [
            {"url": "u1", "titulo": "BIM Revit", "canal": "youtube",
             "publicado_en": "2026-05-06T00:00:00Z"},
        ],
    )
    report_dir = tmp_path / "reports"
    args = [
        "--db", str(db),
        "--config", str(CONFIG),
        "--report-dir", str(report_dir),
        "--now", "2026-05-07T18:00:00Z",
        "--commit",
    ]
    rc = s5.main(args)
    assert rc == 0
    con = sqlite3.connect(db)
    row = con.execute(
        "SELECT ranking_score, ranking_reason, ranking_at FROM discovered_items "
        "WHERE url_canonica='u1'"
    ).fetchone()
    con.close()
    assert row[0] is not None and row[0] > 0
    assert json.loads(row[1])["total"] == row[0]
    assert row[2].endswith("Z")

    # Segunda corrida sin --rerank: no re-escribe (filtro NULL).
    rc2 = s5.main(args)
    assert rc2 == 0
    con = sqlite3.connect(db)
    row2 = con.execute(
        "SELECT ranking_score, ranking_at FROM discovered_items WHERE url_canonica='u1'"
    ).fetchone()
    con.close()
    assert row2[1] == row[2]  # ranking_at no cambió
