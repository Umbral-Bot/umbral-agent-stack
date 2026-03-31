"""
Granola VM raw intake runner.

Runs on the Windows VM where Granola is installed and executes the safe
`Granola -> raw Notion` intake path through the local Worker `/run` API.

This wrapper is intentionally strict:
- it reuses the existing gap audit and raw ingest batch selection logic
- it prefers the Worker path over local direct calls
- it fails execution when the Worker preflight is unhealthy
- it writes machine-readable JSON reports for later audit of Rick's capacity
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.vm.granola_watcher_env_loader import load_env

DEFAULT_ENV_FILE = r"C:\Granola\.env"
DEFAULT_REPORT_DIR = r"C:\Granola\reports"

load_env(os.environ.get("GRANOLA_ENV_FILE", DEFAULT_ENV_FILE))

from scripts.run_granola_raw_ingest_batch import (  # noqa: E402
    _execute_prepared,
    _prepare_batch_inputs,
    _select_candidates,
    build_report,
)


def _env(key: str, *fallback_keys: str, default: str = "") -> str:
    value = os.environ.get(key, "")
    if value:
        return value
    for fallback in fallback_keys:
        value = os.environ.get(fallback, "")
        if value:
            return value
    return default


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _default_cache_path() -> str:
    return _env(
        "GRANOLA_CACHE_PATH",
        default=str(Path(os.environ.get("APPDATA", "")) / "Granola" / "cache-v6.json"),
    )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _check_worker_preflight(
    worker_url: str,
    worker_token: str,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    worker_url = worker_url.rstrip("/")
    health_url = f"{worker_url}/health"
    run_url = f"{worker_url}/run"

    preflight: dict[str, Any] = {
        "ok": False,
        "worker_url": worker_url,
        "health_ok": False,
        "ping_ok": False,
        "health_status_code": None,
        "ping_status_code": None,
        "failure": "",
    }

    try:
        health_resp = requests.get(health_url, timeout=timeout)
        preflight["health_status_code"] = health_resp.status_code
        preflight["health_ok"] = health_resp.status_code == 200
    except requests.RequestException as exc:
        preflight["failure"] = f"health_check_failed: {exc}"
        return preflight

    headers = {
        "Authorization": f"Bearer {worker_token}",
        "Content-Type": "application/json",
    }
    payload = {"task": "ping", "input": {"source": "granola_vm_raw_intake"}}
    try:
        ping_resp = requests.post(run_url, headers=headers, json=payload, timeout=timeout)
        preflight["ping_status_code"] = ping_resp.status_code
        preflight["ping_ok"] = ping_resp.status_code == 200
        if preflight["ping_ok"]:
            preflight["ok"] = True
        else:
            preflight["failure"] = f"ping_failed_status={ping_resp.status_code}"
    except requests.RequestException as exc:
        preflight["failure"] = f"ping_failed: {exc}"

    return preflight


def _write_report(report_dir: Path, summary: dict[str, Any]) -> str:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"granola-vm-raw-intake-{stamp}.json"
    latest_path = report_dir / "granola-vm-raw-intake-latest.json"
    report_body = json.dumps(summary, ensure_ascii=False, indent=2)
    report_path.write_text(report_body, encoding="utf-8")
    latest_path.write_text(report_body, encoding="utf-8")
    return str(report_path)


def run_vm_raw_intake(
    *,
    cache_path: Path,
    bucket: str,
    limit: int | None,
    execute: bool,
    allow_ambiguous: bool,
    notify_enlace: bool,
    max_raw_items: int,
    recent_days: int,
    batch_dir: Path | None,
    worker_url: str,
    worker_token: str,
    enable_private_api_hydration: bool,
    write_report: bool,
    report_dir: Path,
) -> dict[str, Any]:
    report = build_report(
        cache_path=cache_path,
        max_items=max_raw_items,
        recent_days=recent_days,
        enable_private_api_hydration=enable_private_api_hydration,
    )
    selected_candidates = _select_candidates(
        report,
        bucket=bucket,
        document_ids=None,
        limit=limit,
        allow_ambiguous=allow_ambiguous,
    )

    effective_batch_dir = batch_dir or (
        REPO_ROOT
        / ".tmp"
        / "granola_vm_raw_intake"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    if selected_candidates:
        prepared_batch = _prepare_batch_inputs(
            cache_path=cache_path,
            selected_candidates=selected_candidates,
            batch_dir=effective_batch_dir,
            notify_enlace=notify_enlace,
            enable_private_api_hydration=enable_private_api_hydration,
        )
    else:
        prepared_batch = {
            "prepared": [],
            "batch_dir": str(effective_batch_dir),
            "export_dir": str(effective_batch_dir / "exports"),
            "processed_dir": str(effective_batch_dir / "processed"),
            "manifest_path": str(effective_batch_dir / "manifest.json"),
            "missing_document_ids": [],
        }

    preflight = _check_worker_preflight(worker_url, worker_token)
    if execute and not preflight["ok"]:
        raise RuntimeError(
            f"Worker preflight failed for {worker_url}: {preflight['failure'] or 'unknown'}"
        )

    results: list[dict[str, Any]] = []
    if execute and prepared_batch["prepared"]:
        results = _execute_prepared(
            prepared_batch["prepared"],
            mode="worker",
            worker_url=worker_url,
            worker_token=worker_token,
        )

    summary = {
        "generated_at": _iso_now(),
        "execute": bool(execute),
        "bucket": bucket,
        "selected_count": len(selected_candidates),
        "selected_items": [
            {
                "document_id": str(item.get("document_id") or ""),
                "title": str(item.get("title") or ""),
                "meeting_date": str(item.get("meeting_date") or ""),
                "classification": str(item.get("classification") or ""),
            }
            for item in selected_candidates
        ],
        "prepared_count": len(prepared_batch["prepared"]),
        "missing_document_ids": prepared_batch["missing_document_ids"],
        "notify_enlace": bool(notify_enlace),
        "execution_mode": "worker",
        "worker_preflight": preflight,
        "batch_dir": prepared_batch["batch_dir"],
        "export_dir": prepared_batch["export_dir"],
        "processed_dir": prepared_batch["processed_dir"],
        "manifest_path": prepared_batch["manifest_path"],
        "results": results,
        "report_path": "",
    }

    if write_report:
        summary["report_path"] = _write_report(report_dir, summary)

    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the safe Granola VM raw intake path through the local Worker"
    )
    parser.add_argument(
        "--bucket",
        default=_env("GRANOLA_VM_BATCH_BUCKET", default="batch1_recent_unique"),
        help="Gap report bucket to ingest (default: GRANOLA_VM_BATCH_BUCKET or batch1_recent_unique)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=_env_int("GRANOLA_VM_MAX_ITEMS_PER_RUN", 5),
        help="Maximum number of items to process per run",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the raw writes through Worker /run. Default is preview-only.",
    )
    parser.add_argument(
        "--allow-ambiguous",
        action="store_true",
        help="Allow ambiguous buckets. Default remains blocked.",
    )
    parser.add_argument(
        "--notify-enlace",
        action="store_true",
        help="Notify Enlace during ingest. Default is off.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    parser.add_argument(
        "--cache-path",
        default=_default_cache_path(),
        help="Path to Granola cache-v6.json",
    )
    parser.add_argument(
        "--max-raw-items",
        type=int,
        default=_env_int("GRANOLA_VM_MAX_RAW_ITEMS", 200),
        help="Maximum raw Notion rows to inspect in the gap report",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=_env_int("GRANOLA_VM_RECENT_DAYS", 7),
        help="How many trailing days count as recent in the gap report",
    )
    parser.add_argument(
        "--batch-dir",
        help="Explicit directory for temporary exported markdown batch files",
    )
    parser.add_argument(
        "--worker-url",
        default=_env("GRANOLA_WORKER_URL", "WORKER_URL", default="http://127.0.0.1:8088"),
        help="Worker base URL. Defaults to GRANOLA_WORKER_URL / WORKER_URL / localhost:8088",
    )
    parser.add_argument(
        "--worker-token",
        default=_env("GRANOLA_WORKER_TOKEN", "WORKER_TOKEN"),
        help="Worker token. Defaults to GRANOLA_WORKER_TOKEN / WORKER_TOKEN",
    )
    parser.add_argument(
        "--report-dir",
        default=_env("GRANOLA_VM_REPORT_DIR", default=DEFAULT_REPORT_DIR),
        help="Directory where JSON audit reports are stored",
    )
    parser.add_argument(
        "--no-write-report",
        action="store_true",
        help="Do not persist the JSON report to disk",
    )
    parser.add_argument(
        "--no-private-api-hydration",
        action="store_true",
        help="Disable Granola private API hydration and rely on cache-v6.json only",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    cache_path = Path(args.cache_path)
    if not cache_path.is_file():
        raise RuntimeError(f"Granola cache not found: {cache_path}")

    worker_url = (args.worker_url or "").rstrip("/")
    worker_token = (args.worker_token or "").strip()
    if not worker_url:
        raise RuntimeError("Worker URL is required")
    if not worker_token:
        raise RuntimeError("Worker token is required")

    summary = run_vm_raw_intake(
        cache_path=cache_path,
        bucket=args.bucket,
        limit=args.limit,
        execute=args.execute,
        allow_ambiguous=args.allow_ambiguous,
        notify_enlace=args.notify_enlace,
        max_raw_items=max(1, int(args.max_raw_items)),
        recent_days=max(1, int(args.recent_days)),
        batch_dir=Path(args.batch_dir) if args.batch_dir else None,
        worker_url=worker_url,
        worker_token=worker_token,
        enable_private_api_hydration=not args.no_private_api_hydration,
        write_report=not args.no_write_report,
        report_dir=Path(args.report_dir),
    )

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"bucket={summary['bucket']} execute={summary['execute']} "
            f"selected={summary['selected_count']} prepared={summary['prepared_count']}"
        )
        print(
            f"worker_preflight_ok={summary['worker_preflight']['ok']} "
            f"worker_url={summary['worker_preflight']['worker_url']}"
        )
        if summary["missing_document_ids"]:
            print(
                "missing_document_ids="
                + ",".join(summary["missing_document_ids"])
            )
        if summary["report_path"]:
            print(f"report_path={summary['report_path']}")

    if args.execute:
        failed = sum(1 for item in summary["results"] if not item.get("ok"))
        return 0 if failed == 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
