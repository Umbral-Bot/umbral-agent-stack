"""Compat tests guarding the legacy ``source_verifier.py`` public surface.

Stage 2 (Hilo 3) introduces a *new* contract via ``stage2_verify_sources``
+ ``lib/dedup`` while leaving ``source_verifier.py`` untouched, since it is
still consumed by ``stage7_5_copy_writer``. These tests fail loudly if a
future refactor accidentally breaks that surface.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import httpx
import pytest

from scripts.discovery import source_verifier as sv


def test_verify_source_signature_unchanged():
    sig = inspect.signature(sv.verify_source)
    expected = {"config", "cache_db", "use_cache", "ops_log", "client"}
    params = set(sig.parameters.keys())
    assert "url" in params
    assert expected <= params, f"missing kwargs: {expected - params}"


def test_verifier_config_dataclass_fields_unchanged():
    expected = {
        "blocklist_domains",
        "blocklist_tlds",
        "allowlist_high_trust",
        "warning_new_domain_days",
        "arxiv_min_year",
        "arxiv_max_year_offset",
        "short_body_min_chars",
        "allowed_content_types",
        "http_timeout_s",
        "http_retries",
    }
    fields = set(sv.VerifierConfig.__dataclass_fields__.keys())
    assert expected <= fields, f"missing fields: {expected - fields}"


def test_public_callables_present():
    for name in ("verify_source", "load_config", "cache_get", "cache_put", "VerifierConfig"):
        assert hasattr(sv, name), f"legacy public symbol missing: {name}"


def test_verify_source_does_not_import_lib_dedup():
    """Hard isolation: the legacy module must not pull in the new lib."""
    src = Path(sv.__file__).read_text(encoding="utf-8")
    assert "lib.dedup" not in src
    assert "from scripts.discovery.lib" not in src


def test_verdict_shape_smoke(tmp_path):
    """End-to-end smoke: make sure the verdict dict still has its top-level keys."""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><head><title>Demo Paper</title></head><body>"
                 + ("x " * 4000) + "</body></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        verdict = sv.verify_source(
            "https://arxiv.org/abs/2401.12345",
            config=sv.load_config(),
            cache_db=tmp_path / "c.sqlite",
            use_cache=False,
            ops_log=None,
            client=client,
        )
    finally:
        client.close()
    assert {"ok", "url", "reason", "warnings", "details"} <= set(verdict.keys())
    assert {
        "host",
        "status_code",
        "content_type",
        "final_url",
        "title",
        "body_chars",
        "from_cache",
        "cache_age_s",
    } <= set(verdict["details"].keys())
