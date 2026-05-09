"""Tests for Stage 2 source verification."""

from __future__ import annotations

import json
import sqlite3
from io import StringIO

import httpx
import pytest

from scripts.discovery import stage2_verify_sources as s2


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _client(handler) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        timeout=5.0,
        follow_redirects=True,
        headers={"User-Agent": "test"},
    )


def _seed(conn: sqlite3.Connection, rows):
    s2.ensure_schema(conn)
    for sid, url, title, excerpt in rows:
        conn.execute(
            "INSERT INTO signals_raw (signal_id, url, title, excerpt) VALUES (?,?,?,?)",
            (sid, url, title, excerpt),
        )
    conn.commit()


def _ok_html(title="Hello", body_chars=4000, canonical=None) -> str:
    body = "x " * (body_chars // 2)
    can_link = (
        f'<link rel="canonical" href="{canonical}"/>' if canonical else ""
    )
    return f"<html><head><title>{title}</title>{can_link}</head><body>{body}</body></html>"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


# --------------------------------------------------------------------------- #
# verify_signal — status classification
# --------------------------------------------------------------------------- #


def test_ok_with_canonical():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "HEAD":
            return httpx.Response(200, headers={"content-type": "text/html"})
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text=_ok_html(canonical="https://example.com/canonical"),
        )

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://example.com/x", "T", "E", client=c)
    assert v.source_status == "ok"
    assert v.canonical_url == "https://example.com/canonical"
    assert v.http_status == 200
    assert v.error == ""


def test_redirect_to_other_host():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "first.example":
            return httpx.Response(301, headers={"location": "https://second.example/p"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_ok_html())

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://first.example/p", "T", "E", client=c)
    assert v.source_status == "redirect"
    assert v.final_url.startswith("https://second.example/")


def test_404():
    def handler(req):
        return httpx.Response(404)

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://x/y", "T", "E", client=c)
    assert v.source_status == "404"
    assert v.http_status == 404


def test_410():
    def handler(req):
        return httpx.Response(410)

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://x/y", "T", "E", client=c)
    assert v.source_status == "410"


def test_paywall_402():
    def handler(req):
        return httpx.Response(402)

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://x/y", "T", "E", client=c)
    assert v.source_status == "paywall"
    assert v.paywall_detected is True


def test_paywall_keyword():
    def handler(req: httpx.Request) -> httpx.Response:
        body = "<html><body>" + ("x " * 4000) + " Subscribe to read more</body></html>"
        return httpx.Response(200, headers={"content-type": "text/html"}, text=body)

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://x/y", "T", "E", client=c)
    assert v.source_status == "paywall"


def test_paywall_thin_body():
    def handler(req):
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html><body>tiny</body></html>")

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://x/y", "T", "E", client=c)
    assert v.source_status == "paywall"


def test_503_blocked():
    def handler(req):
        return httpx.Response(503)

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://x/y", "T", "E", client=c)
    assert v.source_status == "blocked"
    assert v.http_status == 503


def test_head_405_falls_back_to_get():
    seen = []

    def handler(req):
        seen.append(req.method)
        if req.method == "HEAD":
            return httpx.Response(405)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_ok_html())

    with _client(handler) as c:
        v = s2.verify_signal(1, "https://x/y", "T", "E", client=c)
    assert v.source_status == "ok"
    assert "HEAD" in seen and "GET" in seen


def test_malformed_url():
    with _client(lambda r: httpx.Response(200)) as c:
        v = s2.verify_signal(1, "not-a-url", "T", "E", client=c)
    assert v.source_status == "blocked"
    assert v.error == "malformed_url"
    assert v.http_status is None


# --------------------------------------------------------------------------- #
# Retries
# --------------------------------------------------------------------------- #


def test_timeout_with_retries_exhausts_budget():
    attempts = {"n": 0}

    def handler(req):
        attempts["n"] += 1
        raise httpx.ConnectTimeout("boom")

    sleeps: list[float] = []

    with _client(handler) as c:
        probe = s2._http_probe(
            "https://x/y",
            client=c,
            backoffs=(1.0, 3.0),
            sleep=lambda s: sleeps.append(s),
        )
    assert attempts["n"] == 3  # initial + 2 retries
    assert sleeps == [1.0, 3.0]
    assert probe.transport_failed is True
    assert probe.error.startswith("timeout")


def test_timeout_status_via_run(monkeypatch, conn):
    monkeypatch.setattr(s2.time, "sleep", lambda s: None)

    def handler(req):
        raise httpx.ConnectTimeout("boom")

    _seed(conn, [(101, "https://x/timeout", "T", "E")])
    with _client(handler) as c:
        verdicts = s2.run(conn=conn, client=c, batch=10)
    assert len(verdicts) == 1
    assert verdicts[0].source_status == "timeout"


def test_retry_failed_picks_up_timeout(monkeypatch, conn):
    monkeypatch.setattr(s2.time, "sleep", lambda s: None)
    s2.ensure_schema(conn)
    conn.execute(
        "INSERT INTO signals_raw (signal_id, url, title, excerpt) VALUES (?,?,?,?)",
        (1, "https://x/y", "T", "E"),
    )
    # pre-existing timeout verdict
    conn.execute(
        "INSERT INTO signals_verified VALUES (?,?,?,?,?,?,?,?,?,?)",
        (1, "https://x/y", "timeout", "h", "k", 0, "2026-01-01T00:00:00+00:00", None, "https://x/y", "timeout:X"),
    )
    conn.commit()

    def handler(req):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_ok_html())

    with _client(handler) as c:
        verdicts_no_retry = s2.run(conn=conn, client=c, batch=10, retry_failed=False)
        assert verdicts_no_retry == []
        verdicts_retry = s2.run(conn=conn, client=c, batch=10, retry_failed=True)
        assert len(verdicts_retry) == 1
        assert verdicts_retry[0].source_status == "ok"


# --------------------------------------------------------------------------- #
# Persistence + idempotency
# --------------------------------------------------------------------------- #


def test_persistence_writes_row(conn):
    _seed(conn, [(7, "https://x/y", "Title", "Body")])

    def handler(req):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_ok_html())

    with _client(handler) as c:
        s2.run(conn=conn, client=c, batch=10)
    row = conn.execute("SELECT signal_id, source_status FROM signals_verified").fetchone()
    assert row == (7, "ok")


def test_same_signal_twice_idempotent(conn):
    _seed(conn, [(8, "https://x/y", "T", "E")])

    def handler(req):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_ok_html())

    with _client(handler) as c:
        v1 = s2.run(conn=conn, client=c, batch=10)
        # second call with retry_failed picks nothing because v1 was ok
        v2 = s2.run(conn=conn, client=c, batch=10, retry_failed=True)
    assert len(v1) == 1 and v2 == []
    n = conn.execute("SELECT COUNT(*) FROM signals_verified").fetchone()[0]
    assert n == 1


def test_dry_run_no_persist(conn):
    _seed(conn, [(9, "https://x/y", "T", "E")])

    def handler(req):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_ok_html())

    with _client(handler) as c:
        s2.run(conn=conn, client=c, batch=10, dry_run=True)
    n = conn.execute("SELECT COUNT(*) FROM signals_verified").fetchone()[0]
    assert n == 0


def test_fetch_unverified_missing_table():
    c = sqlite3.connect(":memory:")
    try:
        # no schema applied at all
        assert s2.fetch_unverified(c, batch=5, retry_failed=False) == []
    finally:
        c.close()


# --------------------------------------------------------------------------- #
# Helpers — canonical / paywall / json
# --------------------------------------------------------------------------- #


def test_canonical_extracted():
    html = _ok_html(canonical="https://canonical.example/p")
    assert s2._extract_canonical(html, "https://other/p") == "https://canonical.example/p"


def test_canonical_invalid_falls_back():
    html = '<link rel="canonical" href="javascript:void(0)"/>'
    assert s2._extract_canonical(html, "https://fallback/p") == "https://fallback/p"


def test_visible_text_strips_scripts():
    html = "<html><body><script>var x=1;</script><p>Hello world</p><style>a{}</style></body></html>"
    n = s2._visible_text_chars(html)
    assert 5 <= n <= 30


def test_to_json_roundtrip():
    v = s2.Verdict(
        signal_id=1,
        canonical_url="u",
        source_status="ok",
        content_hash="h",
        idempotency_key="k",
        paywall_detected=False,
        verified_at="2026-01-01T00:00:00+00:00",
        http_status=200,
        final_url="u",
        error="",
    )
    parsed = json.loads(v.to_json())
    assert parsed["signal_id"] == 1
    assert parsed["source_status"] == "ok"


def test_main_dry_run(monkeypatch, tmp_path):
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    s2.ensure_schema(conn)
    conn.execute(
        "INSERT INTO signals_raw (signal_id, url, title, excerpt) VALUES (?,?,?,?)",
        (1, "https://x/y", "T", "E"),
    )
    conn.commit()
    conn.close()

    def handler(req):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_ok_html())

    fake = _client(handler)
    monkeypatch.setattr(s2, "_build_client", lambda *a, **k: fake)
    buf = StringIO()
    monkeypatch.setattr(s2.sys, "stdout", buf)
    rc = s2.main(["--db", str(db), "--dry-run", "--batch", "10", "--verbose"])
    out = buf.getvalue()
    assert rc == 0
    assert '"processed": 1' in out
    assert '"ok": 1' in out
