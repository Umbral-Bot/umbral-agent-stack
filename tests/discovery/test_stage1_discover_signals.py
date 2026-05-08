"""Tests for stage1_discover_signals — RSS/Web fetch+parse, dedup, robots, rate-limit."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

from scripts.discovery.stage0_load_referentes import open_sqlite
from scripts.discovery.stage1_discover_signals import (
    DEFAULT_MIN_INTERVAL_S,
    RateLimiter,
    RobotsCache,
    canonicalize_url,
    dedup_hash,
    parse_rss,
    parse_web_page,
    run,
)


RSS_BODY = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Demo</title>
<item><title>Post A</title><link>https://example.com/a</link><pubDate>Mon, 01 Jan 2026 12:00:00 +0000</pubDate><description>Hola mundo</description></item>
<item><title>Post B</title><link>https://example.com/b?utm_source=newsletter</link><pubDate>Tue, 02 Jan 2026 12:00:00 +0000</pubDate></item>
<item><title>Post C</title><link>https://example.com/c</link><pubDate>Wed, 03 Jan 2026 12:00:00 +0000</pubDate></item>
</channel></rss>"""

ROBOTS_DISALLOW = "User-agent: *\nDisallow: /\n"
ROBOTS_ALLOW = "User-agent: *\nDisallow:\n"


def _seed_snapshot(conn: sqlite3.Connection, *rows: tuple[str, str, str]) -> None:
    for referente_id, canal_tipo, canal_url in rows:
        conn.execute(
            "INSERT INTO referentes_snapshot(referente_id, nombre, canal_tipo, canal_url, snapshot_at) VALUES (?,?,?,?,?)",
            (referente_id, referente_id, canal_tipo, canal_url, "2026-01-01T00:00:00+00:00"),
        )
    conn.commit()


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_rss_parses_n_signals_and_idempotent_rerun(tmp_path: Path):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    _seed_snapshot(conn, ("r1", "rss", "https://example.com/feed"))
    conn.close()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=RSS_BODY)

    sleeper_calls: list[float] = []
    out1 = run(
        sqlite_path=db,
        canal="rss",
        client=_client(handler),
        robots=RobotsCache(fetcher=lambda u: ROBOTS_ALLOW),
        limiter=RateLimiter(0.0, sleeper=lambda s: sleeper_calls.append(s)),
    )
    assert out1["signals_unique"] == 3
    assert out1["signals_duplicate"] == 0

    out2 = run(
        sqlite_path=db,
        canal="rss",
        client=_client(handler),
        robots=RobotsCache(fetcher=lambda u: ROBOTS_ALLOW),
        limiter=RateLimiter(0.0, sleeper=lambda s: sleeper_calls.append(s)),
    )
    assert out2["signals_unique"] == 0
    assert out2["signals_duplicate"] == 3


def test_rate_limit_sleeps_at_least_min_interval(tmp_path: Path):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    _seed_snapshot(
        conn,
        ("r1", "rss", "https://same.example.com/a"),
        ("r2", "rss", "https://same.example.com/b"),
    )
    conn.close()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=RSS_BODY)

    slept: list[float] = []
    clock_v = [0.0]

    def clk() -> float:
        return clock_v[0]

    def slp(s: float) -> None:
        slept.append(s)
        clock_v[0] += s

    out = run(
        sqlite_path=db,
        canal="rss",
        client=_client(handler),
        robots=RobotsCache(fetcher=lambda u: ROBOTS_ALLOW),
        limiter=RateLimiter(2.0, clock=clk, sleeper=slp),
    )
    assert any(s >= 2.0 for s in slept)
    assert out["rate_limit_hits"] >= 1


def test_robots_disallow_blocks_fetch(tmp_path: Path):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    _seed_snapshot(conn, ("r1", "rss", "https://blocked.example.com/feed"))
    conn.close()

    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        return httpx.Response(200, text=RSS_BODY)

    out = run(
        sqlite_path=db,
        canal="rss",
        client=_client(handler),
        robots=RobotsCache(fetcher=lambda u: ROBOTS_DISALLOW),
        limiter=RateLimiter(0.0, sleeper=lambda s: None),
    )
    assert out["robots_disallow"] == 1
    assert calls == []


def test_404_500_timeout_each_recorded(tmp_path: Path):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    _seed_snapshot(
        conn,
        ("r1", "rss", "https://a.example.com/feed"),
        ("r2", "rss", "https://b.example.com/feed"),
        ("r3", "rss", "https://c.example.com/feed"),
    )
    conn.close()

    def handler(req: httpx.Request) -> httpx.Response:
        host = req.url.host
        if host == "a.example.com":
            return httpx.Response(404)
        if host == "b.example.com":
            return httpx.Response(500)
        raise httpx.TimeoutException("simulated timeout")

    out = run(
        sqlite_path=db,
        canal="rss",
        client=_client(handler),
        robots=RobotsCache(fetcher=lambda u: ROBOTS_ALLOW),
        limiter=RateLimiter(0.0, sleeper=lambda s: None),
    )
    assert out["errors_by_status"].get("http_404") == 1
    assert out["errors_by_status"].get("http_5xx") == 1
    assert out["errors_by_status"].get("timeout") == 1


def test_web_html_extracts_title_and_excerpt(tmp_path: Path):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    _seed_snapshot(conn, ("r1", "web", "https://web.example.com/page"))
    conn.close()

    html = (
        "<html><head><title>Mi Titulo</title>"
        "<meta name=\"description\" content=\"Un excerpt corto.\">"
        "</head><body>x</body></html>"
    )

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    out = run(
        sqlite_path=db,
        canal="web",
        client=_client(handler),
        robots=RobotsCache(fetcher=lambda u: ROBOTS_ALLOW),
        limiter=RateLimiter(0.0, sleeper=lambda s: None),
    )
    assert out["signals_unique"] == 1
    conn2 = sqlite3.connect(str(db))
    row = conn2.execute(
        "SELECT title, excerpt, source_status FROM signals_raw"
    ).fetchone()
    assert row[0] == "Mi Titulo"
    assert "excerpt" in (row[1] or "").lower()
    assert row[2] == "ok"
    conn2.close()


def test_canonicalize_strips_utm_and_trailing_slash():
    assert canonicalize_url("HTTPS://Example.com/Path/?utm_source=x&q=1") == \
        "https://example.com/Path?q=1"
    assert canonicalize_url("https://x.com/a/") == "https://x.com/a"
    assert canonicalize_url("https://x.com/?fbclid=1") == "https://x.com/"


def test_dedup_hash_deterministic_and_distinct():
    a = dedup_hash("https://a.com/x", "2026-01-01T00:00:00+00:00")
    b = dedup_hash("https://a.com/x", "2026-01-01T00:00:00+00:00")
    c = dedup_hash("https://a.com/x", None)
    d = dedup_hash("https://a.com/y", "2026-01-01T00:00:00+00:00")
    assert a == b
    assert a != c
    assert a != d
