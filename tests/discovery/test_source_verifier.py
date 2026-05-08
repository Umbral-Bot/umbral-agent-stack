"""Unit tests for scripts/discovery/source_verifier.py.

All HTTP traffic is mocked via ``httpx.MockTransport`` — these tests do NOT
hit the network. Cache lives under ``tmp_path`` so the user's real cache
(``~/.cache/rick-discovery/source_verification.sqlite``) is never touched.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import httpx
import pytest

from scripts.discovery import source_verifier as sv


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _mk_client(handler) -> httpx.Client:
    transport = httpx.MockTransport(handler)
    return httpx.Client(
        transport=transport,
        follow_redirects=True,
        headers={"User-Agent": "test"},
        timeout=5.0,
    )


def _ok_html(title: str = "Mocked title", body_chars: int = 1500) -> bytes:
    body = "x" * body_chars
    return (
        f"<html><head><title>{title}</title></head>"
        f"<body>{body}</body></html>"
    ).encode("utf-8")


@pytest.fixture
def cfg() -> sv.VerifierConfig:
    return sv.VerifierConfig.default()


@pytest.fixture
def cache(tmp_path: Path) -> Path:
    return tmp_path / "cache.sqlite"


@pytest.fixture
def ops_log(tmp_path: Path) -> Path:
    return tmp_path / "ops.jsonl"


# --------------------------------------------------------------------------- #
# 1. Blocklist hard-blocks (TLD + domain)
# --------------------------------------------------------------------------- #


def test_blocklist_tld_dot_test_blocks(cfg, cache, ops_log):
    # No client should be called — fail fast on blocklist.
    def handler(request):
        pytest.fail(f"unexpected http call: {request.url}")

    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://this-domain-does-not-exist-zzz.test",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is False
    assert v["reason"] == "blocklist_tld"


def test_blocklist_domain_example_com_blocks(cfg, cache, ops_log):
    def handler(request):
        pytest.fail("should not call HTTP for blocklisted domain")

    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://example.com/article",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is False
    assert v["reason"] == "blocklist_domain"


def test_blocklist_localhost_blocks(cfg, cache, ops_log):
    v = sv.verify_source(
        "http://localhost:8080/page",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    assert v["ok"] is False
    assert v["reason"] == "blocklist_domain"


# --------------------------------------------------------------------------- #
# 2. arXiv format (hard)
# --------------------------------------------------------------------------- #


def test_arxiv_valid_passes(cfg, cache, ops_log):
    def handler(request):
        return httpx.Response(
            200, headers={"content-type": "text/html; charset=utf-8"},
            content=_ok_html("arXiv paper"),
        )
    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is True, v
    assert v["reason"] == ""
    assert v["details"]["host"] == "arxiv.org"


def test_arxiv_malformed_path_blocks(cfg, cache, ops_log):
    v = sv.verify_source(
        "https://arxiv.org/something-else/123",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    assert v["ok"] is False
    assert v["reason"] == "arxiv_malformed"


def test_arxiv_year_too_old_blocks(cfg, cache, ops_log):
    # arxiv_min_year default = 2020. YY=19 → year 2019, MM=01 valid.
    v = sv.verify_source(
        "https://arxiv.org/abs/1901.12345",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    assert v["ok"] is False
    assert v["reason"] == "arxiv_year_out_of_range"


def test_arxiv_year_too_far_future_blocks(cfg, cache, ops_log):
    # YY=29 → year 2029, MM=01 valid. current_year=2026 + offset 1 = 2027 max.
    v = sv.verify_source(
        "https://arxiv.org/abs/2901.12345",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    assert v["ok"] is False
    assert v["reason"] == "arxiv_year_out_of_range"


# --------------------------------------------------------------------------- #
# 3. HTTP probe results
# --------------------------------------------------------------------------- #


def test_http_404_blocks(cfg, cache, ops_log):
    def handler(request):
        return httpx.Response(404, headers={"content-type": "text/html"})
    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://buildingsmart.org/missing",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is False
    assert v["reason"] == "http_404"
    assert v["details"]["status_code"] == 404


def test_http_500_blocks(cfg, cache, ops_log):
    def handler(request):
        return httpx.Response(500, headers={"content-type": "text/html"})
    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://acm.org/journal/x",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is False
    assert v["reason"] == "http_500"


def test_transport_error_blocks_after_retry(cfg, cache, ops_log):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        raise httpx.ConnectError("boom")

    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://ieee.org/article",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is False
    assert v["reason"] == "http_unreachable"
    # 1 retry by default ⇒ at least 2 attempts.
    assert calls["n"] >= 2


def test_redirect_to_different_domain_blocks(cfg, cache, ops_log):
    def handler(request):
        if request.url.host == "buildingsmart.org":
            return httpx.Response(
                302,
                headers={
                    "location": "https://malicious.example.org/sneaky",
                    "content-type": "text/html",
                },
            )
        # If something follows the redirect onward, return a 200 anyway —
        # but blocklist on example.org should fire first via final-host check.
        return httpx.Response(200, headers={"content-type": "text/html"})

    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://buildingsmart.org/foo",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is False
    assert v["reason"] in ("redirect_domain_change", "redirect_to_blocklist_domain")


def test_redirect_same_domain_passes(cfg, cache, ops_log):
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(
                301,
                headers={
                    "location": "https://buildingsmart.org/end",
                    "content-type": "text/html",
                },
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=_ok_html("Same-domain redirect"),
        )

    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://buildingsmart.org/start",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is True, v


def test_content_type_image_blocks(cfg, cache, ops_log):
    def handler(request):
        return httpx.Response(
            200, headers={"content-type": "image/png"}, content=b"\x89PNG..."
        )
    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://github.com/foo.png",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is False
    assert v["reason"] == "content_type_rejected"


def test_content_type_pdf_passes(cfg, cache, ops_log):
    def handler(request):
        return httpx.Response(
            200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.4..."
        )
    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://buildingsmart.org/spec.pdf",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is True, v


# --------------------------------------------------------------------------- #
# 4. Soft warnings
# --------------------------------------------------------------------------- #


def test_warning_missing_title(cfg, cache, ops_log):
    def handler(request):
        # No <title>.
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html><body>" + b"x" * 1500 + b"</body></html>",
        )
    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://github.com/somerepo",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is True, v
    assert "missing_title" in v["warnings"]


def test_warning_short_body(cfg, cache, ops_log):
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html><head><title>t</title></head><body>tiny</body></html>",
        )
    client = _mk_client(handler)
    try:
        v = sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=client,
        )
    finally:
        client.close()
    assert v["ok"] is True, v
    assert "short_body" in v["warnings"]


# --------------------------------------------------------------------------- #
# 5. Malformed URLs (hard)
# --------------------------------------------------------------------------- #


def test_empty_url_blocks(cfg, cache, ops_log):
    v = sv.verify_source(
        "", config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    assert v["ok"] is False
    assert v["reason"] == "empty_url"


def test_no_scheme_blocks(cfg, cache, ops_log):
    v = sv.verify_source(
        "arxiv.org/abs/2401.12345",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    assert v["ok"] is False
    assert v["reason"] == "malformed_url"


def test_ftp_scheme_blocks(cfg, cache, ops_log):
    v = sv.verify_source(
        "ftp://example.com/file",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    assert v["ok"] is False
    assert v["reason"] == "malformed_url"


# --------------------------------------------------------------------------- #
# 6. Cache semantics
# --------------------------------------------------------------------------- #


def test_cache_hit_short_circuits_http(cfg, cache, ops_log):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=_ok_html(),
        )

    # First call populates cache.
    c1 = _mk_client(handler)
    try:
        v1 = sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=c1,
        )
    finally:
        c1.close()
    assert v1["ok"] is True
    assert v1["details"]["from_cache"] is False
    n_after_first = calls["n"]
    assert n_after_first >= 1

    # Second call: cache hit, no HTTP traffic.
    c2 = _mk_client(handler)
    try:
        v2 = sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=c2,
        )
    finally:
        c2.close()
    assert v2["ok"] is True
    assert v2["details"]["from_cache"] is True
    assert calls["n"] == n_after_first  # no new HTTP call


def test_cache_disabled_always_probes(cfg, cache, ops_log):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=_ok_html(),
        )
    c = _mk_client(handler)
    try:
        sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=c, use_cache=False,
        )
        sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=c, use_cache=False,
        )
    finally:
        c.close()
    assert calls["n"] >= 2


def test_cache_ttl_expiry(cfg, cache, ops_log, monkeypatch):
    def handler(request):
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=_ok_html(),
        )
    c = _mk_client(handler)
    try:
        sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=c,
        )
    finally:
        c.close()

    # Force the cached row to look 8 days old (TTL is 7 days).
    conn = sqlite3.connect(cache)
    conn.execute(
        "UPDATE source_verification_cache SET cached_at=?",
        (int(time.time()) - 8 * 24 * 3600,),
    )
    conn.commit()
    conn.close()

    cached = sv.cache_get(cache, "https://arxiv.org/abs/2401.12345")
    assert cached is None  # expired


def test_cache_blocked_verdict_persists(cfg, cache, ops_log):
    # When a URL is blocklisted, verifier still caches the negative verdict
    # so subsequent calls don't re-evaluate.
    sv.verify_source(
        "https://example.com/x",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    cached = sv.cache_get(cache, "https://example.com/x")
    assert cached is not None
    assert cached["ok"] is False
    assert cached["reason"] == "blocklist_domain"


# --------------------------------------------------------------------------- #
# 7. Config loading
# --------------------------------------------------------------------------- #


def test_config_loads_default_when_path_missing(tmp_path):
    cfg = sv.load_config(tmp_path / "missing.yaml")
    assert cfg.blocklist_tlds == sv.DEFAULT_BLOCKLIST_TLDS


def test_config_loads_from_yaml(tmp_path):
    p = tmp_path / "verifier.yaml"
    p.write_text(
        "blocklist_domains: [bad.example]\n"
        "blocklist_tlds: ['.evil']\n"
        "arxiv_min_year: 2010\n",
        encoding="utf-8",
    )
    cfg = sv.load_config(p)
    assert "bad.example" in cfg.blocklist_domains
    assert ".evil" in cfg.blocklist_tlds
    assert cfg.arxiv_min_year == 2010


# --------------------------------------------------------------------------- #
# 8. Ops log integration
# --------------------------------------------------------------------------- #


def test_ops_log_written_on_block(cfg, cache, ops_log):
    sv.verify_source(
        "https://example.com/x",
        config=cfg, cache_db=cache, ops_log=ops_log,
        client=_mk_client(lambda r: pytest.fail("no http")),
    )
    lines = [
        json.loads(line) for line in ops_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    blocked = [r for r in lines if r["event"] == "stage7_5.source_blocked"]
    assert blocked, lines
    assert blocked[0]["reason"] == "blocklist_domain"


def test_ops_log_written_on_verified(cfg, cache, ops_log):
    def handler(request):
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=_ok_html(),
        )
    c = _mk_client(handler)
    try:
        sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=cfg, cache_db=cache, ops_log=ops_log, client=c,
        )
    finally:
        c.close()
    lines = [
        json.loads(line) for line in ops_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    verified = [r for r in lines if r["event"] == "stage7_5.source.verified"]
    assert verified, lines
