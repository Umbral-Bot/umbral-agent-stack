#!/usr/bin/env python3
"""Alert when the registry backup fails on two consecutive days.

The Windows runner in `notion-governance/scripts/daily-registry-backup.ps1`
writes transcripts named `run-YYYY-MM-DDTHHmmss.log` under
`%LOCALAPPDATA%\\umbral-registry-backup`. This script reads those logs without
touching the registry or backup destination.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


DEFAULT_LOG_SUBDIR = "umbral-registry-backup"
ENV_LOG_DIR = "UMBRAL_REGISTRY_BACKUP_LOG_DIR"
RUN_LOG_RE = re.compile(r"^run-(?P<stamp>\d{4}-\d{2}-\d{2}T\d{6})\.log$", re.IGNORECASE)
EXIT_CODE_RE = re.compile(
    r"\b(?:exit(?:ed)?(?:\s+code)?|exitcode|last[_\s-]*exit[_\s-]*code)\b\s*[:=]?\s*\(?(-?\d+)\)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BackupRun:
    path: Path
    started_at: datetime
    status: str

    @property
    def day(self) -> date:
        return self.started_at.date()


def default_log_dir(env: dict[str, str] | None = None) -> Path:
    """Return the default Windows log directory, with env override support."""
    env = env or os.environ
    override = (env.get(ENV_LOG_DIR) or "").strip()
    if override:
        return Path(override)

    local_app_data = (env.get("LOCALAPPDATA") or "").strip()
    if local_app_data:
        return Path(local_app_data) / DEFAULT_LOG_SUBDIR

    return Path.home() / "AppData" / "Local" / DEFAULT_LOG_SUBDIR


def _parse_started_at(path: Path) -> datetime | None:
    match = RUN_LOG_RE.match(path.name)
    if not match:
        return None
    return datetime.strptime(match.group("stamp"), "%Y-%m-%dT%H%M%S")


def classify_log(text: str) -> str:
    """Classify transcript text as success, failure, or unknown."""
    lines = [line.strip() for line in text.splitlines()]
    for line in lines:
        if line.startswith("FAIL:") or line == "FAIL":
            return "failure"

    for match in EXIT_CODE_RE.finditer(text):
        try:
            if int(match.group(1)) != 0:
                return "failure"
        except ValueError:  # pragma: no cover - regex only captures ints
            continue

    for line in lines:
        if line == "OK" or line.startswith("OK "):
            return "success"

    for match in EXIT_CODE_RE.finditer(text):
        try:
            if int(match.group(1)) == 0:
                return "success"
        except ValueError:  # pragma: no cover
            continue

    return "unknown"


def load_runs(log_dir: Path) -> list[BackupRun]:
    """Load parseable run logs from a directory."""
    if not log_dir.exists() or not log_dir.is_dir():
        return []

    runs: list[BackupRun] = []
    for path in log_dir.iterdir():
        if not path.is_file():
            continue
        started_at = _parse_started_at(path)
        if started_at is None:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        runs.append(BackupRun(path=path, started_at=started_at, status=classify_log(text)))
    return sorted(runs, key=lambda run: run.started_at, reverse=True)


def latest_run_by_day(runs: Iterable[BackupRun]) -> list[BackupRun]:
    """Return the newest log for each date, newest date first."""
    by_day: dict[date, BackupRun] = {}
    for run in sorted(runs, key=lambda item: item.started_at, reverse=True):
        by_day.setdefault(run.day, run)
    return [by_day[day] for day in sorted(by_day.keys(), reverse=True)]


def evaluate_backup_health(runs: Iterable[BackupRun]) -> dict[str, object]:
    """Evaluate whether the latest two daily runs are consecutive failures."""
    daily_runs = latest_run_by_day(runs)
    if len(daily_runs) < 2:
        return {
            "ok": True,
            "alert": False,
            "reason": "insufficient_daily_logs",
            "daily_runs_checked": len(daily_runs),
        }

    latest, previous = daily_runs[0], daily_runs[1]
    expected_previous_day = latest.day - timedelta(days=1)
    consecutive_days = previous.day == expected_previous_day
    consecutive_failures = consecutive_days and latest.status == "failure" and previous.status == "failure"

    return {
        "ok": not consecutive_failures,
        "alert": consecutive_failures,
        "reason": "two_consecutive_failures" if consecutive_failures else "no_consecutive_failure_pair",
        "daily_runs_checked": len(daily_runs),
        "latest_day": latest.day.isoformat(),
        "latest_status": latest.status,
        "previous_day": previous.day.isoformat(),
        "previous_status": previous.status,
        "consecutive_days": consecutive_days,
    }


def format_summary(result: dict[str, object], log_dir: Path) -> str:
    """Return a single-line status or alert summary."""
    if result.get("alert"):
        return (
            "ALERT registry_backup consecutive_failures=2 "
            f"latest_day={result.get('latest_day')} previous_day={result.get('previous_day')} "
            f"log_dir={log_dir}"
        )

    return (
        "OK registry_backup "
        f"reason={result.get('reason')} daily_runs_checked={result.get('daily_runs_checked')} "
        f"log_dir={log_dir}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check registry backup logs for two consecutive failures.")
    parser.add_argument("--log-dir", type=Path, default=None, help=f"Override log directory (or {ENV_LOG_DIR}).")
    args = parser.parse_args(argv)

    log_dir = args.log_dir or default_log_dir()
    result = evaluate_backup_health(load_runs(log_dir))
    print(format_summary(result, log_dir))
    return 2 if result.get("alert") else 0


if __name__ == "__main__":
    raise SystemExit(main())
