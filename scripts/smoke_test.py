#!/usr/bin/env python3
"""
Umbral Smoke Test — quick post-deploy health check (< 5 seconds).

Verifies only the essentials:
  1. Worker /health endpoint
  2. Ping round-trip
  3. Redis connectivity
  4. Quota status (if endpoint available)

Usage:
    PYTHONPATH=. python3 scripts/smoke_test.py
    PYTHONPATH=. python3 scripts/smoke_test.py --quiet

Exit code 0 = all OK, 1 = failure.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def smoke_worker_health(base_url: str) -> tuple[bool, str]:
    """Check Worker /health endpoint."""
    try:
        with httpx.Client(timeout=5.0) as c:
            resp = c.get(f"{base_url}/health")
            resp.raise_for_status()
            data = resp.json()
            v = data.get("version", "?")
            return True, f"v{v} OK"
    except Exception as e:
        return False, f"FAIL: {e}"


def smoke_ping(base_url: str, token: str) -> tuple[bool, str]:
    """Check ping round-trip."""
    try:
        with httpx.Client(timeout=5.0) as c:
            resp = c.post(
                f"{base_url}/run",
                headers=_headers(token),
                json={"task": "ping", "input": {}},
            )
            resp.raise_for_status()
            echo = resp.json().get("result", {}).get("echo", "?")
            return True, f"echo={echo}"
    except Exception as e:
        return False, f"FAIL: {e}"


def smoke_redis(redis_url: str) -> tuple[bool, str]:
    """Check Redis connectivity."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(redis_url, decode_responses=True)
        r.ping()
        pending = r.llen("umbral:tasks:pending")
        return True, f"connected, pending={pending}"
    except Exception as e:
        return False, f"FAIL: {e}"


def smoke_quota(base_url: str, token: str) -> tuple[bool, str]:
    """Check GET /quota/status (optional — may not exist yet)."""
    try:
        with httpx.Client(timeout=5.0) as c:
            resp = c.get(f"{base_url}/quota/status", headers=_headers(token))
            if resp.status_code == 404:
                return True, "SKIP (endpoint not deployed)"
            resp.raise_for_status()
            return True, "OK"
    except Exception as e:
        return False, f"FAIL: {e}"


def main():
    quiet = "--quiet" in sys.argv

    base_url = os.environ.get("WORKER_URL", "").rstrip("/")
    token = os.environ.get("WORKER_TOKEN", "")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    if not base_url or not token:
        print("ERROR: WORKER_URL and WORKER_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    checks = [
        ("Worker health", lambda: smoke_worker_health(base_url)),
        ("Ping", lambda: smoke_ping(base_url, token)),
        ("Redis", lambda: smoke_redis(redis_url)),
        ("Quota status", lambda: smoke_quota(base_url, token)),
    ]

    start = time.monotonic()
    failures = 0

    if not quiet:
        print(f"Smoke test → {base_url}")
        print()

    for name, fn in checks:
        ok, detail = fn()
        status = "OK" if ok else "FAIL"
        if not ok:
            failures += 1
        if not quiet:
            print(f"  [{status:4s}] {name:<20s} {detail}")

    elapsed = time.monotonic() - start

    if not quiet:
        print()
        print(f"  {'PASS' if failures == 0 else 'FAIL'} — {elapsed:.1f}s")

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
