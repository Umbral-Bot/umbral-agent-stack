#!/usr/bin/env python3
"""CLI wrapper for the HITL-2 -> publish bridge (P2.6).

This script does NOT talk to Notion or Azure directly — it only calls the
Worker over HTTP (`web.publish_editorial_post`), same pattern as
`scripts/editorial/magnific_generate_variants.py`. It never asserts the
Telegram confirmation itself: that decision is the operator's (or an n8n
workflow's, once one exists) to make *before* running this script with
`--telegram-confirmed --live`.

Defaults to `--dry-run` behavior even without the flag: a real (non-dry-run)
call additionally requires **both** `--live` and `--telegram-confirmed`
explicitly, so an accidental bare invocation can never publish for real (see
docs/ops/editorial-hitl2-publish-bridge-p26-2026-07-23.md).

Usage:
    export WORKER_URL=http://127.0.0.1:8088 WORKER_TOKEN=xxx

    # Readiness check (always safe — never live, never asserts Telegram):
    python scripts/editorial/trigger_hitl2_publish.py --notion-page-id <id>

    # Real publish (requires an operator who has verified "ok publica"):
    python scripts/editorial/trigger_hitl2_publish.py --notion-page-id <id> \\
        --telegram-confirmed --live
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from client.worker_client import WorkerClient  # noqa: E402

_DEFAULT_TIMEOUT_SEC = 30.0


def _load_env_vars(env_path: str | None = None) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    path = env_path or os.path.expanduser("~/.config/openclaw/env")
    if not os.path.isfile(path):
        return env_vars
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def _resolve_worker_client() -> WorkerClient:
    url = os.environ.get("WORKER_URL", "").strip()
    token = os.environ.get("WORKER_TOKEN", "").strip()
    if not url or not token:
        env_vars = _load_env_vars()
        url = url or env_vars.get("WORKER_URL", "")
        token = token or env_vars.get("WORKER_TOKEN", "")
    if not url or not token:
        print("ERROR: WORKER_URL and WORKER_TOKEN required (env or ~/.config/openclaw/env)", file=sys.stderr)
        sys.exit(2)
    return WorkerClient(base_url=url, token=token, caller_id="script.trigger_hitl2_publish")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HITL-2 -> web.publish_editorial_post bridge (P2.6, D3 triple gate)"
    )
    parser.add_argument("--notion-page-id", required=True, help="Publicaciones page id or URL")
    parser.add_argument(
        "--telegram-confirmed",
        action="store_true",
        help='Assert that a Telegram "ok publica" reply was verified for this page (D3 — you, the operator, are asserting this; the script never checks it)',
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually attempt to publish (requires --telegram-confirmed too). Without this flag, always dry_run=True regardless of --telegram-confirmed.",
    )
    parser.add_argument("--timeout", type=float, default=_DEFAULT_TIMEOUT_SEC)
    args = parser.parse_args()

    dry_run = not args.live
    if args.live and not args.telegram_confirmed:
        print(
            "ERROR: --live requires --telegram-confirmed (D3: Telegram \"ok publica\" is a hard, "
            "non-optional condition — confirm it was actually verified before re-running with both flags)",
            file=sys.stderr,
        )
        return 3

    input_data = {
        "notion_page_id": args.notion_page_id,
        "dry_run": dry_run,
        "telegram_confirmed": args.telegram_confirmed,
    }

    wc = _resolve_worker_client()
    try:
        response = wc.run("web.publish_editorial_post", input_data, timeout=args.timeout)
    except Exception as e:
        print(f"ERROR: Worker call failed: {e}", file=sys.stderr)
        return 4

    result = response.get("result", response) if isinstance(response, dict) else response
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not isinstance(result, dict):
        print("HITL2_ERROR unexpected_response_shape", file=sys.stderr)
        return 5

    if not result.get("ok"):
        error = str(result.get("error") or "")
        if error == "telegram_confirmation_missing":
            print(f"HITL2_NOT_READY reason=telegram_confirmation_missing page_id={args.notion_page_id}")
            return 0
        print(f"HITL2_BLOCKED error={error} page_id={args.notion_page_id}")
        return 1

    if result.get("dry_run"):
        print(f"HITL2_DRY_RUN_OK page_id={args.notion_page_id} would_publish={result.get('would_publish')}")
        return 0

    print(f"HITL2_PUBLISHED_OK page_id={args.notion_page_id} published_url={result.get('published_url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
