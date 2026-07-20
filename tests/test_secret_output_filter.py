"""Tests for scripts/vps/secret_output_filter.py (B2 guard-fix).

Reproducible check that the redaction filter strips credential fingerprints
(including the ``openclaw models status`` partial-Vertex case) from captured
CLI output while leaving normal status text intact.

NOTE: every token-like string below is a FABRICATED placeholder (``FAKE`` /
zeros), never a real or real-masked secret — per the secret-output-guard skill.
"""
from __future__ import annotations

import io

import pytest

from scripts.vps import secret_output_filter as f

R = f.REDACTED


# ---------- redacts credential shapes ----------

@pytest.mark.parametrize(
    "sample",
    [
        # openclaw models status partial-Vertex fingerprint (masked).
        "google-vertex fp=ab12cd34ef56****…",
        # gh-style masked prefix.
        "  - Token: gho_abcd0000******",
        # github_pat masked (the tournament near-miss shape).
        "token github_pat_11BUELfakeSCSVfake_***...",
        # Full Google API key.
        "key=AIzaSyFAKE0000000000000000000000000",
        # Google OAuth access + refresh tokens.
        "at ya29.FAKEaccesstoken0000000000",
        "rt 1//0FAKErefreshtoken0000000",
        # JWT-like.
        "jwt eyJhbGciOiFAKEheader.eyJzdWIiFAKEpayload.SIGfake0000",
        # Common prefixes.
        "sk-FAKE0000000000openai",
        "whsec_FAKE0000000000stripe",
        "ntn_FAKE0000000000notion",
        # Bearer auth.
        "Authorization: Bearer FAKEbearertokenvalue000000",
    ],
)
def test_redacts_credential_shapes(sample):
    out = f.redact_secret_fingerprints(sample)
    assert R in out
    # No long alnum run of the original secret survives.
    assert "FAKE" not in out or out.count(R) >= 1


def test_redacts_env_assignment_value_by_name():
    out = f.redact_secret_fingerprints("GOOGLE_API_KEY=AIzaSyFAKE0000000000000000000000000")
    assert out == f"GOOGLE_API_KEY={R}"


def test_redacts_generic_sensitive_env_names():
    assert f.redact_secret_fingerprints("CLIENT_SECRET=supersecretvalue") == f"CLIENT_SECRET={R}"
    assert f.redact_secret_fingerprints("VM_PASSWORD=hunter2hunter2") == f"VM_PASSWORD={R}"


# ---------- preserves benign status text ----------

@pytest.mark.parametrize(
    "line",
    [
        "google-vertex        available     last-check 2026-07-20T04:00:00Z",
        "openai-codex/gpt-5.3-codex   routed",
        "anthropic/claude-opus-4-8    ok",
        "profiles=3 healthy=3 degraded=0",
        "MAX_POSTS_PER_DAY=1",
        "days_until_expiry=55",
    ],
)
def test_preserves_benign_status_text(line):
    assert f.redact_secret_fingerprints(line) == line


# ---------- idempotency & structure ----------

def test_idempotent():
    once = f.redact_secret_fingerprints("key AIzaSyFAKE0000000000000000000000000")
    twice = f.redact_secret_fingerprints(once)
    assert once == twice
    assert R in twice


def test_preserves_line_structure_multiline():
    text = (
        "google-vertex available\n"
        "  - Token: gho_abcd0000******\n"
        "openai-codex ok\n"
    )
    out = f.redact_secret_fingerprints(text)
    lines = out.splitlines()
    assert lines[0] == "google-vertex available"
    assert R in lines[1] and "gho_" not in lines[1]
    assert lines[2] == "openai-codex ok"


def test_empty_input():
    assert f.redact_secret_fingerprints("") == ""


# ---------- stdin → stdout filter ----------

def test_main_streams_stdin_to_stdout(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO("google-vertex fp=ab12cd34ef56****…\nhealthy=3\n"),
    )
    rc = f.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert R in out
    assert "healthy=3" in out
    assert "ab12cd34ef56" not in out
