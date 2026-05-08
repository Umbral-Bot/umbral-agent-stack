"""Tests for scripts/discovery/stage9b_linkedin_oauth.py."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from scripts.discovery import stage9b_linkedin_oauth as mod


# ---------- Fixtures ----------

@pytest.fixture
def tokens_path(tmp_path: Path) -> Path:
    return tmp_path / "linkedin-tokens.json"


@pytest.fixture
def env_creds(monkeypatch):
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "fake-client-secret")
    monkeypatch.setenv("LINKEDIN_REDIRECT_URI", "http://localhost:8765/callback")


# ---------- auth-url ----------

def test_auth_url_prints_url_with_required_params(env_creds, capsys, tokens_path):
    rc = mod.main(["--tokens-path", str(tokens_path), "auth-url"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out.startswith("https://www.linkedin.com/oauth/v2/authorization?")
    for needle in (
        "response_type=code",
        "client_id=fake-client-id",
        "redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback",
        "scope=w_member_social",
    ):
        assert needle in out, f"missing {needle}"


def test_auth_url_missing_client_id_fails(monkeypatch, capsys, tokens_path):
    monkeypatch.delenv("LINKEDIN_CLIENT_ID", raising=False)
    rc = mod.main(["--tokens-path", str(tokens_path), "auth-url"])
    assert rc == 2


# ---------- exchange-code ----------

def _fake_token_response(*, refresh: bool = False) -> dict:
    body = {
        "access_token": "AT-abc",
        "expires_in": 5184000,  # 60 days
        "refresh_token": "RT-xyz",
        "refresh_token_expires_in": 31536000,  # 365 days
    }
    if refresh:
        body["access_token"] = "AT-new"
    return body


def _mock_post(monkeypatch, status_code=200, body=None):
    body = body or _fake_token_response()
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = json.dumps(body)
    resp.json.return_value = body
    client = MagicMock(spec=httpx.Client)
    client.__enter__ = lambda s: s
    client.__exit__ = lambda *a: None
    client.post.return_value = resp
    monkeypatch.setattr(mod.httpx, "Client", lambda *a, **kw: client)
    return client


def test_exchange_code_persists_tokens(env_creds, monkeypatch, tokens_path, capsys):
    client = _mock_post(monkeypatch)
    rc = mod.main([
        "--tokens-path", str(tokens_path),
        "exchange-code", "--code", "AUTHCODE-123",
    ])
    assert rc == 0
    assert tokens_path.exists()
    data = json.loads(tokens_path.read_text())
    assert data["access_token"] == "AT-abc"
    assert data["refresh_token"] == "RT-xyz"
    assert "access_token_expires_at" in data
    assert "refresh_token_expires_at" in data
    # Permissions = 0600
    mode = oct(tokens_path.stat().st_mode & 0o777)
    assert mode == "0o600"
    # And the POST body contains the expected fields.
    sent = client.post.call_args
    assert sent.kwargs["data"]["grant_type"] == "authorization_code"
    assert sent.kwargs["data"]["code"] == "AUTHCODE-123"
    # Secrets are NOT echoed back to stdout.
    out = capsys.readouterr().out
    assert "AT-abc" not in out
    assert "RT-xyz" not in out


def test_exchange_code_http_error_raises(env_creds, monkeypatch, tokens_path):
    _mock_post(monkeypatch, status_code=400, body={"error": "invalid_grant"})
    with pytest.raises(RuntimeError, match="HTTP 400"):
        mod.main([
            "--tokens-path", str(tokens_path),
            "exchange-code", "--code", "BAD",
        ])


# ---------- refresh ----------

def _seed_tokens(path: Path, *, member_urn: str | None = None,
                 access_in_seconds: int = 3600,
                 refresh_in_days: int = 365) -> dict:
    now = datetime.now(timezone.utc)
    rec = {
        "access_token": "AT-old",
        "refresh_token": "RT-old",
        "access_token_expires_at": (
            now + timedelta(seconds=access_in_seconds)
        ).isoformat(),
        "refresh_token_expires_at": (
            now + timedelta(days=refresh_in_days)
        ).isoformat(),
        "obtained_at": now.isoformat(),
    }
    if member_urn:
        rec["member_urn"] = member_urn
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec))
    return rec


def test_refresh_updates_access_token(env_creds, monkeypatch, tokens_path):
    _seed_tokens(tokens_path, member_urn="urn:li:person:rick")
    _mock_post(monkeypatch, body={
        "access_token": "AT-new", "expires_in": 5184000,
        # NOTE: refresh endpoint may omit refresh_token_expires_in
    })
    rc = mod.main(["--tokens-path", str(tokens_path), "refresh"])
    assert rc == 0
    data = json.loads(tokens_path.read_text())
    assert data["access_token"] == "AT-new"
    # refresh_token preserved when not returned
    assert data["refresh_token"] == "RT-old"
    # member_urn preserved
    assert data["member_urn"] == "urn:li:person:rick"


def test_refresh_without_stored_tokens_fails(env_creds, tokens_path):
    with pytest.raises(FileNotFoundError):
        mod.main(["--tokens-path", str(tokens_path), "refresh"])


# ---------- whoami ----------

def _mock_get(monkeypatch, status_code=200, body=None):
    body = body or {"id": "abc123XYZ"}
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = json.dumps(body)
    resp.json.return_value = body
    client = MagicMock()
    client.__enter__ = lambda s: client
    client.__exit__ = lambda *a: None
    client.get.return_value = resp
    monkeypatch.setattr(mod.httpx, "Client", lambda *a, **kw: client)
    return client


def test_whoami_persists_urn(env_creds, monkeypatch, tokens_path, capsys):
    _seed_tokens(tokens_path)
    client = _mock_get(monkeypatch, body={"id": "abc123XYZ"})
    rc = mod.main(["--tokens-path", str(tokens_path), "whoami"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "urn:li:person:abc123XYZ"
    data = json.loads(tokens_path.read_text())
    assert data["member_urn"] == "urn:li:person:abc123XYZ"
    # Authorization header set with bearer.
    sent = client.get.call_args
    assert sent.kwargs["headers"]["Authorization"].startswith("Bearer ")
    assert sent.kwargs["headers"]["X-Restli-Protocol-Version"] == "2.0.0"


def test_whoami_http_error_returns_1(env_creds, monkeypatch, tokens_path):
    _seed_tokens(tokens_path)
    _mock_get(monkeypatch, status_code=401, body={"message": "unauth"})
    rc = mod.main(["--tokens-path", str(tokens_path), "whoami"])
    assert rc == 1


# ---------- check-expiry ----------

def test_check_expiry_ok_when_far(env_creds, tokens_path, capsys):
    _seed_tokens(tokens_path, refresh_in_days=200)
    rc = mod.main(["--tokens-path", str(tokens_path), "check-expiry"])
    assert rc == 0
    assert "refresh_token_days_left=" in capsys.readouterr().out


def test_check_expiry_fails_when_close(env_creds, tokens_path):
    _seed_tokens(tokens_path, refresh_in_days=10)
    rc = mod.main(["--tokens-path", str(tokens_path), "check-expiry"])
    assert rc == 1


# ---------- get_valid_access_token (used by Stage 9c) ----------

def test_get_valid_access_token_no_refresh_when_fresh(env_creds, tokens_path):
    _seed_tokens(tokens_path, access_in_seconds=3600)
    # No mock needed: refresh path must NOT be hit.
    tok = mod.get_valid_access_token(tokens_path)
    assert tok == "AT-old"


def test_get_valid_access_token_refreshes_when_expired(
    env_creds, monkeypatch, tokens_path,
):
    _seed_tokens(tokens_path, access_in_seconds=10)  # < 5min skew
    _mock_post(monkeypatch, body={"access_token": "AT-new", "expires_in": 5184000})
    tok = mod.get_valid_access_token(tokens_path)
    assert tok == "AT-new"
    data = json.loads(tokens_path.read_text())
    assert data["access_token"] == "AT-new"


def test_get_valid_access_token_no_creds_raises(monkeypatch, tokens_path):
    _seed_tokens(tokens_path, access_in_seconds=10)
    monkeypatch.delenv("LINKEDIN_CLIENT_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="LINKEDIN_CLIENT_ID"):
        mod.get_valid_access_token(tokens_path)
