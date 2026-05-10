"""LinkedIn double-guard tests — must NOT make any HTTP request to LinkedIn."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import httpx
import pytest

from scripts.discovery.stage0_load_referentes import open_sqlite
from scripts.discovery.stage1_discover_signals import (
    RateLimiter,
    RobotsCache,
    run,
)


def _seed(conn: sqlite3.Connection, *rows: tuple[str, str, str]) -> None:
    for rid, ct, url in rows:
        conn.execute(
            "INSERT INTO referentes_snapshot(referente_id, nombre, canal_tipo, canal_url, snapshot_at) VALUES (?,?,?,?,?)",
            (rid, rid, ct, url, "2026-01-01T00:00:00+00:00"),
        )
    conn.commit()


def test_linkedin_canal_skipped_zero_requests_two_skip_rows(tmp_path: Path, caplog):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    _seed(
        conn,
        ("r1", "linkedin", "https://linkedin.com/in/x"),
        ("r1", "linkedin", "https://www.linkedin.com/in/x/recent-activity/"),
    )
    conn.close()

    requests: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(str(req.url))
        return httpx.Response(200, text="<html/>")

    with caplog.at_level(logging.WARNING):
        out = run(
            sqlite_path=db,
            canal="all",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            robots=RobotsCache(fetcher=lambda u: "User-agent: *\nDisallow:\n"),
            limiter=RateLimiter(0.0, sleeper=lambda s: None),
        )

    assert requests == []
    assert out["linkedin_skips"] == 2
    conn2 = sqlite3.connect(str(db))
    rows = list(conn2.execute(
        "SELECT source_status FROM signals_raw WHERE source_status='linkedin_skip'"
    ))
    assert len(rows) == 2
    conn2.close()
    msgs = [r.getMessage() for r in caplog.records]
    assert any("linkedin canal pendiente" in m for m in msgs)


def test_mistagged_linkedin_url_on_rss_canal_also_blocked(tmp_path: Path):
    """If somehow canal_tipo=rss but URL host is linkedin, still skip."""
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    _seed(conn, ("r1", "rss", "https://linkedin.com/in/x/feed.rss"))
    conn.close()

    requests: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(str(req.url))
        return httpx.Response(200, text="<rss/>")

    out = run(
        sqlite_path=db,
        canal="all",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        robots=RobotsCache(fetcher=lambda u: "User-agent: *\nDisallow:\n"),
        limiter=RateLimiter(0.0, sleeper=lambda s: None),
    )
    assert requests == []
    assert out["linkedin_skips"] == 1
