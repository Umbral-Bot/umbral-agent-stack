"""Tests for the Stage 7.5 'Copy review pending' tab in the dashboard."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.discovery import stageX_pipeline_dashboard as mod


def _create_proposals(
    db: Path, *, with_copy_cols: bool, with_linkedin_col: bool = True
) -> None:
    extra_cols = []
    if with_copy_cols:
        extra_cols.extend(
            [
                "copy_status TEXT",
                "copy_linkedin TEXT",
                "copy_model_used TEXT",
                "copy_last_attempt_at INTEGER",
                "copy_cost_usd_estimate REAL",
            ]
        )
    if with_linkedin_col:
        extra_cols.append("linkedin_status TEXT")
    extra = ("," + ",".join(extra_cols)) if extra_cols else ""
    conn = sqlite3.connect(db)
    conn.execute(
        f"""CREATE TABLE proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular TEXT NOT NULL, hook TEXT, angulo TEXT,
            fuentes_urls TEXT NOT NULL, disciplinas TEXT NOT NULL,
            score REAL, ts INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            notion_page_id TEXT, last_error TEXT,
            image_status TEXT, image_url TEXT,
            image_prompt TEXT, image_last_attempt_at INTEGER,
            image_last_error TEXT
            {extra}
        )"""
    )
    conn.commit()
    conn.close()


def _insert_pending_copy(
    db: Path,
    *,
    titular: str,
    page_id: str,
    copy_status: str = "copy_ready",
    copy_text: str = "X" * 1500,
    copy_model: str = "claude-sonnet-4.5",
    cost: float = 0.012,
    linkedin_status: str | None = None,
    attempt_at: int = 1715000000,
) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO proposals
            (titular, hook, angulo, fuentes_urls, disciplinas, score, ts,
             status, notion_page_id, copy_status, copy_linkedin,
             copy_model_used, copy_last_attempt_at, copy_cost_usd_estimate,
             linkedin_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            titular, "h", "a",
            json.dumps(["https://x/x"]), json.dumps(["BIM"]),
            0.5, 1715000000, "published", page_id,
            copy_status, copy_text, copy_model, attempt_at, cost,
            linkedin_status,
        ),
    )
    conn.commit()
    conn.close()


def test_copy_review_unavailable_when_columns_missing(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=False)
    pending = mod.collect_copy_review_pending(db)
    assert pending.available is False
    assert pending.rows == []
    md = mod.render_copy_review_markdown(pending)
    assert "esperando Stage 7.5 core" in md


def test_copy_review_zero_rows(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=True)
    pending = mod.collect_copy_review_pending(db)
    assert pending.available is True
    assert pending.rows == []
    md = mod.render_copy_review_markdown(pending)
    assert "Total esperando revisión: **0**" in md
    assert "sin pages pendientes" in md


def test_copy_review_one_row(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=True)
    _insert_pending_copy(db, titular="Caso 1", page_id="page-aaa")
    pending = mod.collect_copy_review_pending(db)
    assert len(pending.rows) == 1
    r = pending.rows[0]
    assert r.titular == "Caso 1"
    assert r.copy_len == 1500
    assert r.copy_model_used == "claude-sonnet-4.5"
    assert r.notion_page_url.endswith("pageaaa")
    assert pending.total_cost_usd == pytest.approx(0.012)
    md = mod.render_copy_review_markdown(pending)
    assert "Caso 1" in md
    assert "1500" in md
    assert "$0.0120" in md


def test_copy_review_excludes_when_linkedin_already_set(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=True)
    _insert_pending_copy(db, titular="Pendiente", page_id="page-1")
    _insert_pending_copy(db, titular="Ya draft",
                         page_id="page-2", linkedin_status="draft_ready")
    _insert_pending_copy(db, titular="Otro estado", page_id="page-3",
                         copy_status="copy_writing")
    pending = mod.collect_copy_review_pending(db)
    titulares = [r.titular for r in pending.rows]
    assert titulares == ["Pendiente"]


def test_copy_review_n_rows_total_cost(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=True)
    for i in range(3):
        _insert_pending_copy(
            db, titular=f"Item {i}", page_id=f"page-{i}", cost=0.01 * (i + 1)
        )
    pending = mod.collect_copy_review_pending(db)
    assert len(pending.rows) == 3
    assert pending.total_cost_usd == pytest.approx(0.06)
    md = mod.render_copy_review_markdown(pending)
    assert "Total esperando revisión: **3**" in md
    assert "$0.0600" in md


def test_copy_review_blocks_when_unavailable(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=False)
    pending = mod.collect_copy_review_pending(db)
    blocks = mod.build_copy_review_blocks(pending)
    # First block is heading, second is the placeholder paragraph.
    assert blocks[0]["type"] == "heading_2"
    assert blocks[1]["type"] == "paragraph"
    assert "copy_*" in blocks[1]["paragraph"]["rich_text"][0]["text"]["content"]


def test_copy_review_blocks_with_rows(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=True)
    _insert_pending_copy(db, titular="Caso A", page_id="page-z")
    pending = mod.collect_copy_review_pending(db)
    blocks = mod.build_copy_review_blocks(pending)
    types = [b["type"] for b in blocks]
    assert "heading_2" in types
    assert "table" in types
    table_block = next(b for b in blocks if b["type"] == "table")
    rows = table_block["table"]["children"]
    # 1 header + 1 data row
    assert len(rows) == 2


def test_dashboard_markdown_includes_review_section(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    _create_proposals(db, with_copy_cols=True)
    _insert_pending_copy(db, titular="Render check", page_id="page-rc")
    metrics = mod.collect_metrics(
        db, cron_log_path=tmp_path / "cron.log",
        now=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
    )
    md = mod.render_markdown(metrics)
    assert "Copy review pending (Stage 7.5)" in md
    assert "Render check" in md
