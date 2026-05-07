"""Setup Rick's Notion integration identity.

Validates the integration token from `~/.config/umbral/notion/.env`, lists
workspace users, locates `rick.asistente@gmail.com`, and writes back
`NOTION_RICK_USER_ID` + `NOTION_WORKSPACE_ID` for the channel adapter.

Per ADR D2 (autoría real OAuth) — this token must NOT be reused across
identities and MUST NOT be logged. We only print fingerprints.

Security:
- Token never echoed; only fingerprint (first4…last4) on success.
- `secret-output-guard` regla #8 vigente.

Usage:
    python scripts/notion/setup_rick_integration.py [--env PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import urllib.error
import urllib.request

logger = logging.getLogger("setup_rick_integration")

DEFAULT_ENV_PATH = Path.home() / ".config" / "umbral" / "notion" / ".env"
RICK_EMAIL = "rick.asistente@gmail.com"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


def _fingerprint(token: str) -> str:
    """Return safe-to-log fingerprint of a secret."""
    if not token or len(token) < 10:
        return "<too-short>"
    return f"{token[:4]}…{token[-4:]} (len={len(token)})"


def _read_env(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE env file. Lines starting with # are comments."""
    if not path.exists():
        raise FileNotFoundError(
            f"Env file not found at {path}. Copy .env.template first and paste the integration token."
        )
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def _write_env(path: Path, updates: dict[str, str]) -> None:
    """Update env file in place, preserving comments and unrelated keys."""
    if not path.exists():
        path.write_text("", encoding="utf-8")
    lines = path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                out_lines.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        out_lines.append(line)
    for k, v in updates.items():
        if k not in seen:
            out_lines.append(f"{k}={v}")
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def _api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{NOTION_API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_API_VERSION,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(
            f"Notion API HTTP {exc.code} on GET {path}: {body}"
        ) from None


def find_rick_user(token: str) -> Tuple[Optional[str], Optional[str]]:
    """Page through /users and return (rick_user_id, workspace_id) or (None, None)."""
    rick_id: Optional[str] = None
    workspace_id: Optional[str] = None
    cursor: Optional[str] = None
    page = 0
    while True:
        page += 1
        suffix = f"?start_cursor={cursor}" if cursor else ""
        data = _api_get(f"/users{suffix}", token)
        for user in data.get("results", []):
            if user.get("type") == "bot":
                bot_owner = (user.get("bot") or {}).get("workspace_name")
                if bot_owner and not workspace_id:
                    workspace_id = (user.get("bot") or {}).get("workspace_id") or workspace_id
                continue
            person = user.get("person") or {}
            email = person.get("email")
            if email and email.lower() == RICK_EMAIL:
                rick_id = user.get("id")
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if page > 20:
            logger.warning("Stopped paging after %d pages (safety cap).", page)
            break
    return rick_id, workspace_id


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=str(DEFAULT_ENV_PATH), help="Path to env file.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write back IDs.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    env_path = Path(args.env).expanduser()
    env = _read_env(env_path)
    token = env.get("NOTION_RICK_INTEGRATION_TOKEN", "")
    if not token:
        logger.error(
            "NOTION_RICK_INTEGRATION_TOKEN missing in %s. "
            "Paste integration secret first (see template comments).",
            env_path,
        )
        return 2

    logger.info("Using integration token fingerprint: %s", _fingerprint(token))

    try:
        me = _api_get("/users/me", token)
    except RuntimeError as exc:
        logger.error("Token validation failed: %s", exc)
        return 3
    bot_name = (me.get("bot") or {}).get("owner", {}).get("workspace") or me.get("name")
    logger.info("Token valid. Bot/integration name: %s", bot_name)
    bot_workspace_id = (me.get("bot") or {}).get("workspace_id") or ""

    rick_id, workspace_id = find_rick_user(token)
    workspace_id = workspace_id or bot_workspace_id

    if not rick_id:
        logger.error(
            "User %s not found in workspace. Ensure David invited Rick as guest "
            "and shared at least one page with the integration.",
            RICK_EMAIL,
        )
        return 4

    logger.info("Found rick user_id=%s workspace_id=%s", rick_id, workspace_id or "<unknown>")

    if args.dry_run:
        logger.info("--dry-run: not writing env. Run without --dry-run to persist.")
        return 0

    updates = {
        "NOTION_RICK_USER_ID": rick_id,
        "NOTION_WORKSPACE_ID": workspace_id or "",
    }
    _write_env(env_path, updates)
    logger.info("Wrote NOTION_RICK_USER_ID + NOTION_WORKSPACE_ID to %s", env_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
