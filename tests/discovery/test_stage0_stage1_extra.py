"""Extra coverage for stage0/stage1 — edge cases, pagination, atom, retries, CLI."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from scripts.discovery.lib import notion_read as nr
from scripts.discovery.stage0_load_referentes import (
    main as stage0_main,
    open_sqlite,
)
from scripts.discovery import stage1_discover_signals as s1


# ---------- notion_read ----------

def _page(rid: str, props: dict[str, Any]) -> dict[str, Any]:
    return {"id": rid, "properties": props}


def test_normalize_referente_full():
    p = _page("p1", {
        nr.NAME_PROP: {"type": "title", "title": [{"plain_text": "X"}]},
        nr.RSS_PROP: {"url": "https://a.example.com/feed"},
        nr.WEB_PROP: {"url": "https://a.example.com"},
        nr.YOUTUBE_PROP: {"url": "https://youtube.com/@a"},
        nr.LINKEDIN_FEED_PROP: {"url": "https://linkedin.com/in/a/feed"},
        nr.LINKEDIN_PROP: {"url": "https://linkedin.com/in/a"},
        nr.CONFIANZA_PROP: {"select": {"name": "ALTA"}},
        nr.FLAGS_PROP: {"multi_select": [{"name": "OTHER"}]},
    })
    r = nr.normalize_referente(p)
    assert r.nombre == "X"
    assert r.rss_url == "https://a.example.com/feed"
    assert r.is_activo
    assert not r.is_excluded
    assert not r.is_pausado


def test_normalize_referente_empty_props():
    r = nr.normalize_referente(_page("p2", {}))
    assert r.nombre == ""
    assert r.rss_url is None
    assert r.flags == ()


def test_fan_out_dedupes_linkedin_when_same_url():
    r = nr.ReferenteRow(
        referente_id="x", nombre="x",
        rss_url=None, web_url=None, youtube_url=None,
        linkedin_feed_url="https://linkedin.com/in/x",
        linkedin_url="https://linkedin.com/in/x",
        confianza=None, flags=(),
    )
    assert nr.fan_out_channels(r) == [("linkedin", "https://linkedin.com/in/x")]


def test_query_data_source_paginates_then_stops():
    pages_returned = []

    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = json.loads(req.content.decode("utf-8"))
        if calls["n"] == 1:
            assert "start_cursor" not in body
            return httpx.Response(200, json={
                "results": [_page("p1", {})],
                "has_more": True,
                "next_cursor": "cursor-A",
            })
        assert body.get("start_cursor") == "cursor-A"
        return httpx.Response(200, json={
            "results": [_page("p2", {})],
            "has_more": False,
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = list(nr.query_data_source(
        data_source_id="ds-X", api_key="k", client=client
    ))
    client.close()
    assert [p["id"] for p in out] == ["p1", "p2"]
    assert calls["n"] == 2


def test_query_data_source_raises_on_401():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        list(nr.query_data_source(
            data_source_id="ds-X", api_key="bad", client=client
        ))
    client.close()


# ---------- _to_iso ----------

def test_to_iso_variants():
    assert s1._to_iso("2026-01-01T00:00:00Z").startswith("2026-01-01T00:00:00")
    iso = s1._to_iso("Mon, 01 Jan 2026 12:00:00 +0000")
    assert iso and iso.startswith("2026-01-01T12:00:00")
    assert s1._to_iso(None) is None
    assert s1._to_iso("") is None
    assert s1._to_iso("not a date") is None


# ---------- atom feed ----------

ATOM_BODY = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>x</title>
<entry><title>One</title><link href="https://atom.example.com/1"/><updated>2026-01-01T00:00:00Z</updated><summary>S1</summary></entry>
<entry><title>Two</title><link href="https://atom.example.com/2"/><published>2026-01-02T00:00:00Z</published></entry>
</feed>"""


def test_parse_atom_entries():
    items = s1.parse_rss(ATOM_BODY)
    assert len(items) == 2
    assert items[0]["url"] == "https://atom.example.com/1"
    assert items[0]["title"] == "One"
    assert items[0]["published_at"].startswith("2026-01-01T00:00:00")


def test_parse_rss_invalid_raises():
    with pytest.raises(ValueError):
        s1.parse_rss("<<<not xml>>>")


# ---------- 5xx retries ----------

def test_5xx_retries_three_total_calls(tmp_path: Path):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    conn.execute(
        "INSERT INTO referentes_snapshot(referente_id, nombre, canal_tipo, canal_url, snapshot_at) VALUES (?,?,?,?,?)",
        ("r", "r", "rss", "https://flap.example.com/feed", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    out = s1.run(
        sqlite_path=db,
        canal="rss",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        robots=s1.RobotsCache(fetcher=lambda u: "User-agent: *\nDisallow:\n"),
        limiter=s1.RateLimiter(0.0, sleeper=lambda s: None),
    )
    assert calls["n"] == 3  # 1 initial + 2 retries
    assert out["errors_by_status"].get("http_5xx") == 1


# ---------- youtube out_of_scope ----------

def test_youtube_recorded_as_out_of_scope_stage1(tmp_path: Path):
    db = tmp_path / "s.sqlite"
    conn = open_sqlite(db)
    conn.execute(
        "INSERT INTO referentes_snapshot(referente_id, nombre, canal_tipo, canal_url, snapshot_at) VALUES (?,?,?,?,?)",
        ("r", "r", "youtube", "https://youtube.com/@x", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    requests: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(str(req.url))
        return httpx.Response(200)

    out = s1.run(
        sqlite_path=db,
        canal="all",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        robots=s1.RobotsCache(fetcher=lambda u: "User-agent: *\nDisallow:\n"),
        limiter=s1.RateLimiter(0.0, sleeper=lambda s: None),
    )
    assert requests == []
    conn2 = sqlite3.connect(str(db))
    rows = list(conn2.execute(
        "SELECT source_status FROM signals_raw WHERE canal_tipo='youtube'"
    ))
    conn2.close()
    assert len(rows) == 1
    assert rows[0][0] == "out_of_scope_stage1"


# ---------- CLI smoke ----------

def test_stage0_main_missing_env_returns_2(monkeypatch, capsys):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    rc = stage0_main(["--sqlite", "/tmp/_nope.sqlite"])
    assert rc == 2


def test_stage0_main_missing_ds_returns_2(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.delenv("UMBRAL_DISCOVERY_REFERENTES_DS_ID", raising=False)
    rc = stage0_main(["--sqlite", "/tmp/_nope.sqlite"])
    assert rc == 2


def test_stage1_main_runs_against_empty_db(tmp_path: Path, capsys):
    db = tmp_path / "s.sqlite"
    open_sqlite(db).close()
    rc = s1.main(["--sqlite", str(db), "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"snapshot_rows": 0' in out


# ---------- canonicalize port + LinkedIn host check ----------

def test_canonicalize_keeps_nondefault_port():
    assert s1.canonicalize_url("https://x.com:8443/a") == "https://x.com:8443/a"


def test_is_linkedin_subdomain():
    assert s1.is_linkedin("https://m.linkedin.com/in/x")
    assert s1.is_linkedin("https://www.linkedin.com/in/x")
    assert not s1.is_linkedin("https://example.com/linkedin")
    assert not s1.is_linkedin("not-a-url")


# ---------- robots cache hit ----------

def test_robots_cache_called_once_per_host():
    calls: list[str] = []

    def fetcher(url: str) -> str:
        calls.append(url)
        return "User-agent: *\nDisallow:\n"

    rc = s1.RobotsCache(fetcher=fetcher)
    assert rc.can_fetch("https://h.example.com/a")
    assert rc.can_fetch("https://h.example.com/b")
    assert len(calls) == 1
