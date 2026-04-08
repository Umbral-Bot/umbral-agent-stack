#!/usr/bin/env python3
"""Execute explicit Granola operational promotion plans against the Worker.

By default this script runs in dry-run mode. Use --execute to allow writes.
Plans must remain explicit: this runner does not infer classification.
Legacy note: this helper still models the V1 curated-session bridge.
It is preserved only for explicit historical or repair runs, not for the normal V2 direct flow.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from client.worker_client import WorkerClient
from scripts import env_loader

env_loader.load()


def _load_plan_file(plan_path: str) -> list[dict[str, Any]]:
    raw = Path(plan_path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if isinstance(data, list):
        plans = data
    elif isinstance(data, dict) and isinstance(data.get("plans"), list):
        plans = data["plans"]
    else:
        raise ValueError("Plan file must be a JSON array or an object with a 'plans' array")
    if not all(isinstance(item, dict) for item in plans):
        raise ValueError("Every plan entry must be a JSON object")
    return plans


def _normalize_plan(plan: dict[str, Any], default_dry_run: bool) -> dict[str, Any]:
    transcript_page_id = str(
        plan.get("transcript_page_id")
        or plan.get("page_id")
        or plan.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("Each plan requires 'transcript_page_id'")

    curated_payload = plan.get("curated_payload")
    if not isinstance(curated_payload, dict) or not curated_payload:
        raise ValueError("Each plan requires a non-empty 'curated_payload' object")

    human_task_payload = plan.get("human_task_payload")
    if human_task_payload is not None and not isinstance(human_task_payload, dict):
        raise ValueError("'human_task_payload' must be an object when provided")

    commercial_project_payload = plan.get("commercial_project_payload")
    if commercial_project_payload is not None and not isinstance(commercial_project_payload, dict):
        raise ValueError("'commercial_project_payload' must be an object when provided")

    if not human_task_payload and not commercial_project_payload:
        raise ValueError(
            "Each plan requires at least one destination payload: 'human_task_payload' or 'commercial_project_payload'"
        )

    normalized: dict[str, Any] = {
        "transcript_page_id": transcript_page_id,
        "curated_payload": dict(curated_payload),
    }
    if human_task_payload:
        normalized["human_task_payload"] = dict(human_task_payload)
    if commercial_project_payload:
        normalized["commercial_project_payload"] = dict(commercial_project_payload)

    if "label" in plan:
        normalized["label"] = str(plan["label"])

    normalized["dry_run"] = bool(plan.get("dry_run", default_dry_run))
    return normalized


def _select_plans(
    plans: list[dict[str, Any]],
    *,
    only_label: str | None = None,
    only_transcript_page_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selected = plans
    if only_label:
        selected = [plan for plan in selected if str(plan.get("label") or "") == only_label]
    if only_transcript_page_id:
        selected = [
            plan
            for plan in selected
            if str(plan.get("transcript_page_id") or "") == only_transcript_page_id
        ]
    if limit is not None:
        selected = selected[: max(0, limit)]
    return selected


def _build_summary(results: list[dict[str, Any]], *, dry_run: bool) -> dict[str, Any]:
    ok = sum(1 for item in results if item.get("ok"))
    failed = len(results) - ok
    return {
        "dry_run_default": dry_run,
        "count": len(results),
        "ok": ok,
        "failed": failed,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run explicit Granola operational promotion plans")
    parser.add_argument("plan_file", help="Path to a JSON plan file")
    parser.add_argument("--execute", action="store_true", help="Perform real writes instead of dry-run")
    parser.add_argument("--only-label", help="Run only the plan with this exact label")
    parser.add_argument("--only-transcript-page-id", help="Run only the plan for this raw transcript page id")
    parser.add_argument("--limit", type=int, help="Maximum number of plans to run")
    parser.add_argument("--worker-url", help="Override WORKER_URL")
    parser.add_argument("--worker-token", help="Override WORKER_TOKEN")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON summary")
    args = parser.parse_args()

    worker_url = (args.worker_url or "").strip()
    worker_token = (args.worker_token or "").strip()
    if not worker_url:
        worker_url = (os.environ.get("WORKER_URL") or "").rstrip("/")
    if not worker_token:
        worker_token = os.environ.get("WORKER_TOKEN", "")
    if not worker_url or not worker_token:
        raise RuntimeError("WORKER_URL and WORKER_TOKEN are required")

    default_dry_run = not args.execute
    raw_plans = _load_plan_file(args.plan_file)
    normalized = [_normalize_plan(plan, default_dry_run) for plan in raw_plans]
    selected = _select_plans(
        normalized,
        only_label=args.only_label,
        only_transcript_page_id=args.only_transcript_page_id,
        limit=args.limit,
    )

    wc = WorkerClient(
        base_url=worker_url,
        token=worker_token,
        timeout=60.0,
        caller_id="script.run_granola_operational_batch",
    )

    results: list[dict[str, Any]] = []
    for index, plan in enumerate(selected, start=1):
        label = str(plan.get("label") or f"plan-{index}")
        try:
            payload = {k: v for k, v in plan.items() if k != "label"}
            response = wc.run("granola.promote_operational_slice", payload)
            results.append(
                {
                    "label": label,
                    "transcript_page_id": plan["transcript_page_id"],
                    "dry_run": plan["dry_run"],
                    "ok": True,
                    "response": response,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "label": label,
                    "transcript_page_id": plan["transcript_page_id"],
                    "dry_run": plan["dry_run"],
                    "ok": False,
                    "error": str(exc),
                }
            )

    summary = _build_summary(results, dry_run=default_dry_run)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Plans run: {summary['count']} | ok={summary['ok']} | failed={summary['failed']}")
        for item in summary["results"]:
            status = "OK" if item["ok"] else "FAILED"
            print(f"- [{status}] {item['label']} :: {item['transcript_page_id']} :: dry_run={item['dry_run']}")
            if not item["ok"]:
                print(f"  error: {item['error']}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
