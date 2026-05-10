"""Tests for stage0_load_referentes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts.discovery.lib.notion_read import ReferenteRow, fan_out_channels
from scripts.discovery.stage0_load_referentes import (
    apply_migrations,
    filter_referentes,
    open_sqlite,
    upsert_snapshot,
)


def _ref(rid: str, **kw) -> ReferenteRow:
    base = dict(
        referente_id=rid,
        nombre=f"Ref {rid}",
        rss_url=None,
        web_url=None,
        youtube_url=None,
        linkedin_feed_url=None,
        linkedin_url=None,
        confianza=None,
        flags=(),
    )
    base.update(kw)
    return ReferenteRow(**base)


def test_filter_excludes_duplicado_and_dup_flag():
    refs = [
        _ref("a", confianza="DUPLICADO"),
        _ref("b", flags=("DUP",)),
        _ref("c", flags=("REQUIERE_VERIFICACION_MANUAL",)),
        _ref("d"),
    ]
    kept, excl, paus, total = filter_referentes(refs)
    assert total == 4
    assert excl == 2
    assert paus == 1
    assert [r.referente_id for r in kept] == ["d"]


def test_filter_limit_respected():
    refs = [_ref(f"r{i}") for i in range(5)]
    kept, *_ = filter_referentes(refs, limit=2)
    assert len(kept) == 2


def test_filter_referente_id_match():
    refs = [_ref("a"), _ref("b"), _ref("c")]
    kept, *_ = filter_referentes(refs, referente_id="b")
    assert [r.referente_id for r in kept] == ["b"]


def test_dry_run_no_sqlite(tmp_path: Path):
    # filter_referentes does not touch sqlite; covers dry-run path indirectly.
    refs = [_ref("a", rss_url="https://example.com/feed")]
    kept, *_ = filter_referentes(refs)
    assert kept[0].rss_url == "https://example.com/feed"


def test_persistence_and_fan_out_5_channels(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    conn = open_sqlite(db)
    ref = _ref(
        "x",
        rss_url="https://example.com/feed",
        web_url="https://example.com",
        youtube_url="https://youtube.com/@x",
        linkedin_feed_url="https://linkedin.com/in/x/recent-activity/",
        linkedin_url="https://linkedin.com/in/x",
    )
    out = upsert_snapshot(conn, referentes=[ref], snapshot_at="2026-01-01T00:00:00+00:00")
    rows = list(conn.execute("SELECT canal_tipo, canal_url FROM referentes_snapshot"))
    assert len(rows) == 5
    canales = sorted(r[0] for r in rows)
    assert canales == ["linkedin", "linkedin", "rss", "web", "youtube"]
    assert out["by_canal"] == {"rss": 1, "web": 1, "youtube": 1, "linkedin": 2}
    conn.close()


def test_idempotent_double_insert(tmp_path: Path):
    db = tmp_path / "state.sqlite"
    conn = open_sqlite(db)
    ref = _ref("y", rss_url="https://example.org/feed.xml")
    upsert_snapshot(conn, referentes=[ref], snapshot_at="2026-01-01T00:00:00+00:00")
    upsert_snapshot(conn, referentes=[ref], snapshot_at="2026-01-02T00:00:00+00:00")
    rows = list(conn.execute("SELECT snapshot_at FROM referentes_snapshot"))
    assert len(rows) == 1
    assert rows[0][0] == "2026-01-02T00:00:00+00:00"
    conn.close()
