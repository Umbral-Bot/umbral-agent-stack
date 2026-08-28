#!/usr/bin/env python3
"""CLI wrapper for the `magnific.generate_variants` Worker task (P2.2).

This script does NOT talk to Notion or Magnific directly — it only calls the
Worker over HTTP, same as `scripts/run_worker_task.py`. Notion writes and the
Magnific API key stay inside `worker/tasks/magnific.py` (ADR-011 #1: Notion
writes are Worker/core's exclusive job). Use this for manual dry-runs or
one-off invocations from an operator's terminal; the production trigger is
the dispatcher poller scan (`NOTION_POLLER_ENABLE_MAGNIFIC`, default off —
see docs/ops/editorial-magnific-p22-poller-2026-07-23.md).

Usage:
    export WORKER_URL=http://127.0.0.1:8088 WORKER_TOKEN=xxx
    python scripts/editorial/magnific_generate_variants.py --page-id <id> --dry-run
    python scripts/editorial/magnific_generate_variants.py --page-id <id>
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

_DEFAULT_DRY_RUN_TIMEOUT_SEC = 30.0
# Real generation is up to 5 sequential Magnific submit+poll cycles. Match
# the production poller's margin: the 600s sleep budget excludes HTTP time.
_DEFAULT_GENERATE_TIMEOUT_SEC = 1200.0


def _redact_result_for_output(result: object) -> object:
    """Return a CLI-safe copy without signed URLs or upstream diagnostics."""
    if not isinstance(result, dict):
        return result
    safe = dict(result)
    if "urls" in safe:
        urls = safe["urls"]
        if isinstance(urls, list):
            safe["urls"] = ["[REDACTED_URL]" for _ in urls]
        else:
            safe["urls"] = "[REDACTED_URL]"
    if safe.get("error"):
        safe["error"] = "[REDACTED_DIAGNOSTIC]"
    return safe


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
    return WorkerClient(base_url=url, token=token, caller_id="script.magnific_generate_variants")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Magnific image variants for a Publicaciones row via Worker/core (P2.2)"
    )
    parser.add_argument("--page-id", required=True, help="Publicaciones page id or URL")
    parser.add_argument("--dry-run", action="store_true", help="Verify eligibility + preview prompt only, no writes")
    parser.add_argument("--count", type=int, default=None, help="Variants to generate (1-5, default 5)")
    parser.add_argument(
        "--aspect-ratio", default=None, help="Magnific aspect_ratio enum (default 4:3)"
    )
    parser.add_argument(
        "--resolution", default=None, help="Magnific resolution enum: 1K|2K|4K (default 2K)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Magnific model alias (default nano-banana-pro-flash / Nano Banana 2; "
            "explicit nano-banana-pro or mystic/realism also supported)"
        ),
    )
    parser.add_argument("--prompt", default=None, help="Explicit prompt override")
    parser.add_argument("--timeout", type=float, default=None, help="Override the HTTP timeout in seconds")
    args = parser.parse_args()

    input_data: dict = {"publicacion_page_id": args.page_id, "dry_run": args.dry_run}
    if args.count is not None:
        input_data["count"] = args.count
    if args.aspect_ratio:
        input_data["aspect_ratio"] = args.aspect_ratio
    if args.resolution:
        input_data["resolution"] = args.resolution
    if args.model:
        input_data["model"] = args.model
    if args.prompt:
        input_data["prompt"] = args.prompt

    timeout = args.timeout
    if timeout is None:
        timeout = _DEFAULT_DRY_RUN_TIMEOUT_SEC if args.dry_run else _DEFAULT_GENERATE_TIMEOUT_SEC

    wc = _resolve_worker_client()
    try:
        response = wc.run("magnific.generate_variants", input_data, timeout=timeout)
    except Exception as e:
        print(f"ERROR: Worker call failed ({type(e).__name__})", file=sys.stderr)
        return 4

    result = response.get("result", response) if isinstance(response, dict) else response
    print(json.dumps(_redact_result_for_output(result), indent=2, ensure_ascii=False))

    if not isinstance(result, dict):
        print("MAGNIFIC_ERROR unexpected_response_shape", file=sys.stderr)
        return 5

    if not result.get("ok"):
        error = str(result.get("error") or "")
        if "MAGNIFIC_API_KEY" in error:
            print("MAGNIFIC_BLOCKED missing_credential", file=sys.stderr)
            return 6
        print("MAGNIFIC_ERROR worker_reported_failure", file=sys.stderr)
        return 1

    if result.get("dry_run"):
        print(f"MAGNIFIC_DRY_RUN_OK page_id={args.page_id} count={result.get('count')}")
        return 0

    if result.get("skipped"):
        print(f"MAGNIFIC_SKIPPED page_id={args.page_id} reason={result.get('reason') or 'already_generated'}")
        return 0

    print(
        f"MAGNIFIC_GENERATED_OK page_id={args.page_id} "
        f"generated={result.get('generated')}/{result.get('requested')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
