#!/usr/bin/env python3
"""
auth_lifecycle_check.py — Evaluate credential lifecycle from YAML config.

Reads a YAML config file declaring credentials with optional expiry dates,
classifies each credential's lifecycle status, and optionally writes events
to OpsLogger.

Default mode is dry-run (stdout JSON, no log writes).

Usage:
  python scripts/auth_lifecycle_check.py --config config/auth_lifecycle.example.yaml
  python scripts/auth_lifecycle_check.py --config config/auth_lifecycle.yaml --write-ops-log

Environment:
  UMBRAL_OPS_LOG_DIR  Override OpsLogger directory (default: ~/.config/umbral)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from infra.auth_lifecycle import (
    build_auth_lifecycle_record,
    parse_expiry,
)
from infra.ops_logger import OpsLogger


def load_config(config_path: Path) -> list[dict[str, Any]]:
    """Load credentials list from YAML config file."""
    if yaml is None:
        print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "credentials" not in data:
        print(f"ERROR: Config file must have a 'credentials' key: {config_path}", file=sys.stderr)
        sys.exit(1)
    creds = data["credentials"]
    if not isinstance(creds, list):
        print(f"ERROR: 'credentials' must be a list: {config_path}", file=sys.stderr)
        sys.exit(1)
    return creds


def evaluate_credentials(
    credentials: list[dict[str, Any]],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Evaluate each credential and return lifecycle records."""
    if now is None:
        now = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    for cred in credentials:
        provider = cred.get("provider", "unknown")
        credential_ref = cred.get("credential_ref", "unnamed")
        expires_at = parse_expiry(cred.get("expires_at"))
        warning_days = int(cred.get("warning_days", 14))
        critical_days = int(cred.get("critical_days", 3))
        notes = cred.get("notes", "")

        record = build_auth_lifecycle_record(
            provider=provider,
            credential_ref=credential_ref,
            expires_at=expires_at,
            now=now,
            warning_days=warning_days,
            critical_days=critical_days,
            source="auth_lifecycle_check_script",
            details=notes[:300] if notes else None,
        )
        results.append(record)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate credential lifecycle status from YAML config.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to YAML config file with credentials metadata.",
    )
    parser.add_argument(
        "--write-ops-log",
        action="store_true",
        default=False,
        help="Write auth_lifecycle_check events to OpsLogger (default: dry-run).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON array.",
    )
    args = parser.parse_args(argv)

    if not args.config.exists():
        print(f"ERROR: Config file not found: {args.config}", file=sys.stderr)
        return 1

    credentials = load_config(args.config)
    results = evaluate_credentials(credentials)

    if args.write_ops_log:
        ops = OpsLogger()
        for record in results:
            ops.auth_lifecycle_check(**record)
        print(f"Wrote {len(results)} auth_lifecycle_check events to {ops.path}")
    else:
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            for r in results:
                status = r["status"]
                marker = {"ok": ".", "warning": "!", "critical": "!!", "expired": "X", "unknown": "?"}
                icon = marker.get(status, "?")
                days = r.get("days_until_expiry")
                days_str = f"{days}d" if days is not None else "n/a"
                print(f"  [{icon}] {r['provider']}/{r['credential_ref']}: {status} ({days_str})")
            print(f"\n{len(results)} credentials evaluated (dry-run, no log written).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
