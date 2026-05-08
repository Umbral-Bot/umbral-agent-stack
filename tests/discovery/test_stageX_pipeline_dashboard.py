"""Tests for scripts/discovery/stageX_pipeline_dashboard.py."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.discovery import stageX_pipeline_dashboard as mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 5, 7, 22, 30, 0, tzinfo=timezone.utc)


def _create_proposals_table(conn: sqlite3.Connection, *, with_linkedin: bool) -> None:
    extra = ", linkedin_status TEXT" if with_linkedin else ""
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


def _insert(
    conn: sqlite3.Connection,
    titular: str,
    *,
    status: str = "draft",
    page_id: str | None = None,
    image_status: str | None = None,
    linkedin_status: str | None = None,
    ts: int | None = None,
    has_linkedin: bool = False,
) -> None:
    cols = (
        "titular, hook, angulo, fuentes_urls, disciplinas, score, ts, status, "
        "notion_page_id, image_status"
    )
    vals = [
        titular,
        "h",
        "a",
        json.dumps(["https://x/" + titular]),
        json.dumps(["BIM"]),
        0.5,
        ts if ts is not None else int(NOW.timestamp()),
        status,
        page_id,
        image_status,
    ]
    if has_linkedin:
        cols += ", linkedin_status"
        vals.append(linkedin_status)
    placeholders = ",".join(["?"] * len(vals))
    conn.execute(f"INSERT INTO proposals ({cols}) VALUES ({placeholders})", vals)


@pytest.fixture
def state_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    _create_proposals_table(conn, with_linkedin=False)
    # 2 published recent + 1 draft recent + 1 published old (>24h)
    old_ts = int((NOW - timedelta(hours=48)).timestamp())
    _insert(conn, "p1", status="published", page_id="page-1", image_status="ok")
    _insert(conn, "p2", status="published", page_id="page-2", image_status="ok")
    _insert(conn, "p3", status="draft", image_status=None)
    _insert(conn, "p4", status="published", page_id="page-4", ts=old_ts,
            image_status="failed")
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def state_db_with_linkedin(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    _create_proposals_table(conn, with_linkedin=True)
    _insert(conn, "p1", status="published", page_id="page-1",
            image_status="ok", linkedin_status="published", has_linkedin=True)
    _insert(conn, "p2", status="published", page_id="page-2",
            image_status="ok", linkedin_status="draft_ready", has_linkedin=True)
    _insert(conn, "p3", status="draft",
            image_status=None, linkedin_status=None, has_linkedin=True)
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def cron_log(tmp_path: Path) -> Path:
    log = tmp_path / "discovery_publish.log"
    log.write_text(
        "[2026-05-07T18:25:11Z] discovery-publish: start\n"
        "[2026-05-07T18:25:13Z] discovery-publish: stage4: OK\n"
        "[2026-05-07T18:25:13Z] discovery-publish: done\n"
        "[2026-05-07T22:15:02Z] discovery-publish: start\n"
        "[2026-05-07T22:15:06Z] discovery-publish: done\n",
        encoding="utf-8",
    )
    return log


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_collect_metrics_basic(state_db: Path, cron_log: Path) -> None:
    m = mod.collect_metrics(state_db, cron_log_path=cron_log, now=NOW)
    assert m.total == 4
    assert m.status == {"published": 3, "draft": 1}
    assert m.image_status == {"ok": 2, "(null)": 1, "failed": 1}
    assert m.has_linkedin_column is False
    # Last 24h: p1, p2, p3 (p4 is 48h old)
    assert m.last_24h_proposals == 3
    assert m.last_24h_notion_pages == 2
    assert m.last_24h_linkedin == 0
    assert m.cron_last_run == "2026-05-07T22:15:06+00:00"


def test_collect_metrics_with_linkedin_column(
    state_db_with_linkedin: Path, cron_log: Path
) -> None:
    m = mod.collect_metrics(state_db_with_linkedin, cron_log_path=cron_log, now=NOW)
    assert m.has_linkedin_column is True
    assert m.linkedin_status == {"published": 1, "draft_ready": 1, "(null)": 1}
    assert m.last_24h_linkedin == 2


def test_compute_next_cron_run() -> None:
    # 22:30 UTC → next slot is 00:15 next day
    now = datetime(2026, 5, 7, 22, 30, tzinfo=timezone.utc)
    nxt = mod.compute_next_cron_run(now)
    assert nxt == datetime(2026, 5, 8, 0, 15, tzinfo=timezone.utc)

    # 05:00 UTC → next slot is 06:15 same day
    now2 = datetime(2026, 5, 7, 5, 0, tzinfo=timezone.utc)
    assert mod.compute_next_cron_run(now2) == datetime(
        2026, 5, 7, 6, 15, tzinfo=timezone.utc
    )


def test_parse_last_cron_run_missing_file(tmp_path: Path) -> None:
    assert mod.parse_last_cron_run(tmp_path / "does-not-exist.log") is None


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def test_render_markdown_contains_dimensions(state_db: Path, cron_log: Path) -> None:
    m = mod.collect_metrics(state_db, cron_log_path=cron_log, now=NOW)
    md = mod.render_markdown(m)
    assert "## status" in md
    assert "## image_status" in md
    assert "## linkedin_status" in md
    # Linkedin column missing → schema note rendered
    assert "columna no presente" in md
    assert "Última actualización" in md
    assert "15 */6 * * *" in md


def test_build_blocks_structure(state_db: Path, cron_log: Path) -> None:
    m = mod.collect_metrics(state_db, cron_log_path=cron_log, now=NOW)
    blocks = mod.build_blocks(m)
    # First block is total paragraph
    assert blocks[0]["type"] == "paragraph"
    types = [b["type"] for b in blocks]
    assert "heading_2" in types
    assert "table" in types
    # Every table has table_row children with proper cells
    for b in blocks:
        if b["type"] == "table":
            children = b["table"]["children"]
            assert all(c["type"] == "table_row" for c in children)
            width = b["table"]["table_width"]
            for row in children:
                assert len(row["table_row"]["cells"]) == width


# ---------------------------------------------------------------------------
# Upsert (Notion mock)
# ---------------------------------------------------------------------------

def test_upsert_creates_when_missing() -> None:
    client = MagicMock()
    # find_subpage_id → 1 page of children, none matching
    client.get.side_effect = [
        {"results": [
            {"type": "child_page", "id": "other-id",
             "child_page": {"title": "Other subpage"}}
        ], "has_more": False},
    ]
    client.post.return_value = {"id": "new-page-id"}
    client.patch.return_value = {}

    page_id, action = mod.upsert_dashboard_subpage(
        client, "parent-id", "📊 Dash", [mod._paragraph("hi")]
    )
    assert action == "created"
    assert page_id == "new-page-id"
    # post called for /pages, patch for appending blocks
    client.post.assert_called_once()
    assert client.post.call_args[0][0] == "/pages"
    client.patch.assert_called_once()
    assert "/blocks/new-page-id/children" in client.patch.call_args[0][0]


def test_upsert_updates_when_subpage_exists() -> None:
    client = MagicMock()
    target_id = "existing-page-id"
    client.get.side_effect = [
        # find_subpage_id: matches on first page
        {"results": [
            {"type": "child_page", "id": target_id,
             "child_page": {"title": "📊 Dash"}}
        ], "has_more": False},
        # archive_children: existing children
        {"results": [
            {"id": "old-block-1"},
            {"id": "old-block-2"},
        ], "has_more": False},
    ]
    client.delete.return_value = {}
    client.patch.return_value = {}

    page_id, action = mod.upsert_dashboard_subpage(
        client, "parent-id", "📊 Dash", [mod._paragraph("hi")]
    )
    assert action == "updated"
    assert page_id == target_id
    # No /pages POST: subpage already existed
    client.post.assert_not_called()
    # 2 deletes for the 2 old blocks
    assert client.delete.call_count == 2
    # Append happened on the existing page id
    client.patch.assert_called_once()
    assert f"/blocks/{target_id}/children" in client.patch.call_args[0][0]


def test_find_subpage_id_paginates() -> None:
    client = MagicMock()
    client.get.side_effect = [
        {"results": [
            {"type": "child_page", "id": "a",
             "child_page": {"title": "Other"}},
        ], "has_more": True, "next_cursor": "cur1"},
        {"results": [
            {"type": "paragraph", "id": "p"},
            {"type": "child_page", "id": "match",
             "child_page": {"title": "Wanted"}},
        ], "has_more": False},
    ]
    found = mod.find_subpage_id(client, "parent-id", "Wanted")
    assert found == "match"
    assert client.get.call_count == 2


# ---------------------------------------------------------------------------
# main() — dry-run end-to-end
# ---------------------------------------------------------------------------

def test_main_dry_run_does_not_call_notion(
    state_db: Path, cron_log: Path, monkeypatch, capsys
) -> None:
    # Ensure NOTION_API_KEY irrelevant in dry-run.
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    rc = mod.main([
        "--dry-run",
        "--state-db", str(state_db),
        "--cron-log", str(cron_log),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Pipeline Editorial" in out
    assert "## status" in out
