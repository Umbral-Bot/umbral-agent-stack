"""Stage 9b: LinkedIn OAuth helper for Rick's editorial pipeline.

Subcommands:
    auth-url        Print the LinkedIn authorization URL (3-legged OAuth).
    exchange-code   Exchange an authorization ?code= for access+refresh tokens.
    refresh         Refresh the access_token using the stored refresh_token.
    whoami          GET /v2/me, persist member URN, print URN.
    check-expiry    Exit 1 if refresh_token expires in < 30 days, else 0.

Tokens are persisted to ``~/.config/rick-discovery/linkedin-tokens.json`` with
mode 0600. The file holds:

    {
      "access_token":  "...",
      "refresh_token": "...",
      "access_token_expires_at":  "<UTC ISO>",
      "refresh_token_expires_at": "<UTC ISO>",
      "member_urn": "urn:li:person:<id>",   # set by `whoami`
      "obtained_at": "<UTC ISO>"
    }

Cero secrets en logs: tokens are NEVER printed (not even prefixes/lengths).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_ME_PATH = "/v2/me"

DEFAULT_REDIRECT_URI = "http://localhost:8765/callback"
DEFAULT_SCOPES = "w_member_social r_liteprofile r_basicprofile openid profile email"

DEFAULT_TOKENS_PATH = Path.home() / ".config" / "rick-discovery" / "linkedin-tokens.json"

# Refresh token lifetime: 365 days (LinkedIn does not rotate refresh tokens).
REFRESH_TOKEN_TTL_DAYS = 365
# Alert threshold: warn / fail check-expiry when < this many days remain.
EXPIRY_WARN_DAYS = 30


# ---------- Token store ----------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_tokens(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"No LinkedIn tokens at {path}. Run `exchange-code` first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_tokens(path: Path, tokens: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _safe_print_status(tokens: dict[str, Any]) -> None:
    """Print non-secret fields only."""
    print(json.dumps({
        "access_token_expires_at": tokens.get("access_token_expires_at"),
        "refresh_token_expires_at": tokens.get("refresh_token_expires_at"),
        "member_urn": tokens.get("member_urn"),
        "obtained_at": tokens.get("obtained_at"),
        "has_access_token": bool(tokens.get("access_token")),
        "has_refresh_token": bool(tokens.get("refresh_token")),
    }, indent=2))


# ---------- Subcommands ----------

def cmd_auth_url(args: argparse.Namespace) -> int:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: LINKEDIN_CLIENT_ID not set in env", file=sys.stderr)
        return 2
    redirect_uri = (
        os.environ.get("LINKEDIN_REDIRECT_URI", "").strip() or DEFAULT_REDIRECT_URI
    )
    state = os.environ.get("LINKEDIN_OAUTH_STATE", "").strip() or "rick-stage9b"
    scope = os.environ.get("LINKEDIN_SCOPES", "").strip() or DEFAULT_SCOPES

    qs = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope,
    })
    print(f"{LINKEDIN_AUTH_URL}?{qs}")
    return 0


def _exchange(
    *, grant_type: str, client_id: str, client_secret: str,
    redirect_uri: str | None = None, code: str | None = None,
    refresh_token: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    data: dict[str, str] = {
        "grant_type": grant_type,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if grant_type == "authorization_code":
        if not code or not redirect_uri:
            raise ValueError("authorization_code requires code + redirect_uri")
        data["code"] = code
        data["redirect_uri"] = redirect_uri
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise ValueError("refresh_token grant requires refresh_token")
        data["refresh_token"] = refresh_token
    else:
        raise ValueError(f"unsupported grant_type {grant_type!r}")

    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=30.0)
    try:
        r = client.post(
            LINKEDIN_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code != 200:
            raise RuntimeError(
                f"token endpoint HTTP {r.status_code}: "
                f"{r.text[:200]!r}"
            )
        return r.json()
    finally:
        if owns_client:
            client.close()


def _build_token_record(
    *, resp: dict[str, Any], previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _utcnow()
    expires_in = int(resp.get("expires_in") or 0)
    access_expires_at = (now + timedelta(seconds=expires_in)).isoformat()

    # LinkedIn returns refresh_token_expires_in only on the initial exchange.
    refresh_expires_in = resp.get("refresh_token_expires_in")
    if refresh_expires_in is not None:
        refresh_expires_at = (
            now + timedelta(seconds=int(refresh_expires_in))
        ).isoformat()
    elif previous and previous.get("refresh_token_expires_at"):
        refresh_expires_at = previous["refresh_token_expires_at"]
    else:
        # Conservative default: 365d from now.
        refresh_expires_at = (
            now + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
        ).isoformat()

    new_refresh = resp.get("refresh_token") or (
        previous.get("refresh_token") if previous else ""
    )

    rec: dict[str, Any] = {
        "access_token": resp.get("access_token") or "",
        "refresh_token": new_refresh or "",
        "access_token_expires_at": access_expires_at,
        "refresh_token_expires_at": refresh_expires_at,
        "obtained_at": now.isoformat(),
    }
    if previous and previous.get("member_urn"):
        rec["member_urn"] = previous["member_urn"]
    return rec


def cmd_exchange_code(args: argparse.Namespace) -> int:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("ERROR: LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not set",
              file=sys.stderr)
        return 2
    redirect_uri = (
        os.environ.get("LINKEDIN_REDIRECT_URI", "").strip() or DEFAULT_REDIRECT_URI
    )
    if not args.code:
        print("ERROR: --code required", file=sys.stderr)
        return 2

    resp = _exchange(
        grant_type="authorization_code", client_id=client_id,
        client_secret=client_secret, redirect_uri=redirect_uri, code=args.code,
    )
    rec = _build_token_record(resp=resp)
    save_tokens(args.tokens_path, rec)
    print(f"OK: tokens saved to {args.tokens_path}")
    _safe_print_status(rec)
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("ERROR: LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not set",
              file=sys.stderr)
        return 2
    prev = load_tokens(args.tokens_path)
    refresh_token = prev.get("refresh_token") or ""
    if not refresh_token:
        print("ERROR: no refresh_token in stored tokens", file=sys.stderr)
        return 2

    resp = _exchange(
        grant_type="refresh_token", client_id=client_id,
        client_secret=client_secret, refresh_token=refresh_token,
    )
    rec = _build_token_record(resp=resp, previous=prev)
    save_tokens(args.tokens_path, rec)
    print(f"OK: access_token refreshed; saved to {args.tokens_path}")
    _safe_print_status(rec)
    return 0


def cmd_whoami(args: argparse.Namespace) -> int:
    tokens = load_tokens(args.tokens_path)
    access = tokens.get("access_token") or ""
    if not access:
        print("ERROR: no access_token", file=sys.stderr)
        return 2
    with httpx.Client(timeout=30.0) as c:
        r = c.get(
            f"{LINKEDIN_API_BASE}{LINKEDIN_ME_PATH}",
            headers={
                "Authorization": f"Bearer {access}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
    if r.status_code != 200:
        print(f"ERROR: /v2/me HTTP {r.status_code}: {r.text[:200]!r}",
              file=sys.stderr)
        return 1
    body = r.json()
    member_id = body.get("id") or ""
    if not member_id:
        print(f"ERROR: no 'id' in /v2/me response: {body!r}", file=sys.stderr)
        return 1
    urn = f"urn:li:person:{member_id}"
    tokens["member_urn"] = urn
    save_tokens(args.tokens_path, tokens)
    print(urn)
    return 0


def cmd_check_expiry(args: argparse.Namespace) -> int:
    tokens = load_tokens(args.tokens_path)
    raw = tokens.get("refresh_token_expires_at") or ""
    if not raw:
        print("ERROR: no refresh_token_expires_at", file=sys.stderr)
        return 2
    try:
        expires_at = datetime.fromisoformat(raw)
    except ValueError:
        print(f"ERROR: bad refresh_token_expires_at {raw!r}", file=sys.stderr)
        return 2
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    days_left = (expires_at - _utcnow()).total_seconds() / 86400.0
    print(f"refresh_token_days_left={days_left:.2f}")
    if days_left < EXPIRY_WARN_DAYS:
        print(f"WARN: refresh_token expires in <{EXPIRY_WARN_DAYS}d",
              file=sys.stderr)
        return 1
    return 0


# ---------- Programmatic helpers (used by stage 9c) ----------

def get_valid_access_token(
    tokens_path: Path = DEFAULT_TOKENS_PATH,
    *,
    skew_seconds: int = 300,
) -> str:
    """Return a valid access_token, refreshing in-place if needed.

    Refreshes when the stored access_token expires in less than
    ``skew_seconds`` (default 5 min). Raises RuntimeError on failure.
    """
    tokens = load_tokens(tokens_path)
    raw = tokens.get("access_token_expires_at") or ""
    needs_refresh = True
    if raw:
        try:
            exp = datetime.fromisoformat(raw)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            needs_refresh = (exp - _utcnow()).total_seconds() < skew_seconds
        except ValueError:
            needs_refresh = True

    if needs_refresh:
        client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
        client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise RuntimeError(
                "Cannot refresh: LINKEDIN_CLIENT_ID/SECRET not in env"
            )
        refresh_token = tokens.get("refresh_token") or ""
        if not refresh_token:
            raise RuntimeError("No refresh_token stored; re-run exchange-code")
        resp = _exchange(
            grant_type="refresh_token", client_id=client_id,
            client_secret=client_secret, refresh_token=refresh_token,
        )
        tokens = _build_token_record(resp=resp, previous=tokens)
        save_tokens(tokens_path, tokens)

    access = tokens.get("access_token") or ""
    if not access:
        raise RuntimeError("No access_token after refresh")
    return access


def get_member_urn(tokens_path: Path = DEFAULT_TOKENS_PATH) -> str:
    tokens = load_tokens(tokens_path)
    return tokens.get("member_urn") or ""


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 9b: LinkedIn OAuth helper.")
    p.add_argument(
        "--tokens-path", type=Path, default=DEFAULT_TOKENS_PATH,
        help=f"Default: {DEFAULT_TOKENS_PATH}",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth-url", help="Print the LinkedIn authorization URL.")

    p_ex = sub.add_parser("exchange-code",
                          help="Exchange ?code= for tokens.")
    p_ex.add_argument("--code", required=True)

    sub.add_parser("refresh", help="Refresh the access_token.")
    sub.add_parser("whoami", help="GET /v2/me + persist member URN.")
    sub.add_parser("check-expiry",
                   help="Exit 1 if refresh_token expires in <30d.")

    args = p.parse_args(argv)

    if args.cmd == "auth-url":
        return cmd_auth_url(args)
    if args.cmd == "exchange-code":
        return cmd_exchange_code(args)
    if args.cmd == "refresh":
        return cmd_refresh(args)
    if args.cmd == "whoami":
        return cmd_whoami(args)
    if args.cmd == "check-expiry":
        return cmd_check_expiry(args)
    p.error(f"unknown cmd {args.cmd!r}")
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
