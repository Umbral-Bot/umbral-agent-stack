#!/usr/bin/env python3
"""Compare worker handler inventories and smoke critical handlers."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import httpx


DEFAULT_REQUIRED_TASKS = (
    "notion.upsert_deliverable",
    "notion.upsert_bridge_item",
)

DEFAULT_SMOKE_PAYLOADS: dict[str, dict[str, Any]] = {
    "notion.upsert_deliverable": {"name": "Smoke deliverable"},
    "notion.upsert_bridge_item": {"name": "Smoke bridge item"},
}


@dataclass(frozen=True)
class TargetSpec:
    name: str
    base_url: str


@dataclass(frozen=True)
class InventorySnapshot:
    target: TargetSpec
    version: str
    tasks: frozenset[str]

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)


@dataclass(frozen=True)
class SmokeResult:
    target_name: str
    task_name: str
    status_code: int
    handled: bool
    message: str


def parse_target(value: str) -> TargetSpec:
    name, separator, raw_url = value.partition("=")
    if separator != "=":
        raise argparse.ArgumentTypeError("Targets must use NAME=URL format.")
    name = name.strip()
    base_url = raw_url.strip().rstrip("/")
    if not name or not base_url:
        raise argparse.ArgumentTypeError("Targets must include both name and URL.")
    return TargetSpec(name=name, base_url=base_url)


def load_inventory(
    target: TargetSpec,
    timeout: float = 10.0,
    client_factory: Callable[..., Any] = httpx.Client,
) -> InventorySnapshot:
    with client_factory(timeout=timeout) as client:
        response = client.get(f"{target.base_url}/health")
        response.raise_for_status()
        payload = response.json()

    tasks = payload.get("tasks_registered") or []
    if not isinstance(tasks, list):
        raise ValueError(f"{target.name} returned invalid tasks_registered payload")

    return InventorySnapshot(
        target=target,
        version=str(payload.get("version") or "unknown"),
        tasks=frozenset(str(task) for task in tasks),
    )


def compare_inventory(
    reference: InventorySnapshot,
    candidate: InventorySnapshot,
    required_tasks: Iterable[str],
) -> tuple[list[str], list[str], list[str]]:
    required = set(required_tasks)
    missing_required = sorted(required - set(candidate.tasks))
    missing_vs_reference = sorted(set(reference.tasks) - set(candidate.tasks))
    extra_vs_reference = sorted(set(candidate.tasks) - set(reference.tasks))
    return missing_required, missing_vs_reference, extra_vs_reference


def smoke_task(
    target: TargetSpec,
    token: str,
    task_name: str,
    timeout: float = 20.0,
    client_factory: Callable[..., Any] = httpx.Client,
) -> SmokeResult:
    payload = DEFAULT_SMOKE_PAYLOADS.get(task_name, {})
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with client_factory(timeout=timeout) as client:
        response = client.post(
            f"{target.base_url}/run",
            headers=headers,
            json={"task": task_name, "input": payload},
        )

    handled = response.status_code == 200
    message = response.text.strip()

    try:
        body = response.json()
    except json.JSONDecodeError:
        body = None

    if isinstance(body, dict):
        if handled:
            result = body.get("result")
            if isinstance(result, dict) and result.get("error"):
                message = str(result["error"])
            else:
                message = "handler reached"
        else:
            detail = body.get("detail")
            if detail:
                message = str(detail)

    return SmokeResult(
        target_name=target.name,
        task_name=task_name,
        status_code=response.status_code,
        handled=handled,
        message=message,
    )


def print_inventory_summary(
    reference: InventorySnapshot,
    snapshots: list[InventorySnapshot],
    required_tasks: list[str],
) -> bool:
    print("Worker inventory summary")
    print(
        f"- reference: {reference.target.name} {reference.target.base_url} "
        f"({reference.total_tasks} handlers, v{reference.version})"
    )

    drift_detected = False
    for snapshot in snapshots:
        missing_required, missing_vs_reference, extra_vs_reference = compare_inventory(
            reference,
            snapshot,
            required_tasks,
        )
        print(
            f"- {snapshot.target.name}: {snapshot.target.base_url} "
            f"({snapshot.total_tasks} handlers, v{snapshot.version})"
        )
        if missing_required:
            drift_detected = True
            print(f"  missing required: {', '.join(missing_required)}")
        if missing_vs_reference:
            drift_detected = True
            print(f"  missing vs {reference.target.name}: {', '.join(missing_vs_reference)}")
        if extra_vs_reference:
            drift_detected = True
            print(f"  extra vs {reference.target.name}: {', '.join(extra_vs_reference)}")
        if not missing_required and not missing_vs_reference and not extra_vs_reference:
            print("  inventory matches reference")

    return not drift_detected


def print_smoke_summary(results: list[SmokeResult]) -> bool:
    print("Active smoke")
    all_ok = True
    for result in results:
        status = "OK" if result.handled else "FAIL"
        print(
            f"- {result.target_name} -> {result.task_name}: "
            f"{status} (HTTP {result.status_code}) {result.message}"
        )
        all_ok = all_ok and result.handled
    return all_ok


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare worker handler inventories and smoke critical handlers.",
    )
    parser.add_argument(
        "--target",
        action="append",
        type=parse_target,
        required=True,
        help="Comparison target in NAME=URL format. First target is the reference.",
    )
    parser.add_argument(
        "--required",
        action="append",
        default=[],
        help="Critical handler that must exist on every target. Repeat as needed.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("WORKER_TOKEN", ""),
        help="Bearer token for active smoke on /run. Defaults to WORKER_TOKEN.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Execute required handlers on every target after comparing inventories.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout for inventory reads.")
    parser.add_argument("--smoke-timeout", type=float, default=20.0, help="HTTP timeout for active smoke.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if len(args.target) < 2:
        parser.error("Provide at least two --target entries.")

    required_tasks = args.required or list(DEFAULT_REQUIRED_TASKS)

    try:
        snapshots = [load_inventory(target, timeout=args.timeout) for target in args.target]
    except Exception as exc:
        print(f"Inventory check failed: {exc}", file=sys.stderr)
        return 1

    reference = snapshots[0]
    inventory_ok = print_inventory_summary(reference, snapshots, required_tasks)

    smoke_ok = True
    if args.smoke:
        if not args.token:
            print("Active smoke requested but no WORKER_TOKEN/token was provided.", file=sys.stderr)
            return 2
        results = [
            smoke_task(target, args.token, task_name, timeout=args.smoke_timeout)
            for target in args.target
            for task_name in required_tasks
        ]
        smoke_ok = print_smoke_summary(results)

    return 0 if inventory_ok and smoke_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
