from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

LOG_DIR_ENV = "UMBRAL_REGISTRY_BACKUP_LOG_DIR"
FALLBACK_LOG_DIR_ENV = "REGISTRY_BACKUP_LOG_DIR"
DEFAULT_LOG_DIR_NAME = "umbral-registry-backup"
SUPPORTED_LOG_SUFFIXES = {".log", ".txt"}

_FAIL_MARKER_RE = re.compile(
    r"(?:\bFAIL(?:ED|URE)?\b|\bSTATUS\s*[:=]\s*FAIL\b|\bRESULT\s*[:=]\s*FAIL\b|\bbackup failed\b)",
    re.IGNORECASE,
)
_SUCCESS_MARKER_RE = re.compile(
    r"(?:\bSUCCESS\b|\bSUCCEEDED\b|\bSTATUS\s*[:=]\s*(?:SUCCESS|OK)\b|\bRESULT\s*[:=]\s*SUCCESS\b|\bcompleted successfully\b|\bbackup ok\b)",
    re.IGNORECASE,
)
_EXIT_CODE_RE = re.compile(
    r"\b(?:process\s+)?(?:exit(?:ed)?(?:\s+with)?(?:\s+code)?|exitcode|return\s+code|rc)\s*[:=]?\s*(-?\d+)\b",
    re.IGNORECASE,
)
_DATE_PATTERNS = (
    re.compile(
        r"(?P<year>20\d{2})-(?P<month>\d{2})-(?P<day>\d{2})(?:[T._-]?(?P<hour>\d{2})[-:]?(?P<minute>\d{2})[-:]?(?P<second>\d{2}))?"
    ),
    re.compile(
        r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})(?:[T._-]?(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2}))?"
    ),
)


@dataclass(frozen=True)
class BackupRun:
    path: Path
    run_at: datetime
    day: date
    status: str
    reason: str
    modified_at: float


@dataclass(frozen=True)
class AlertEvaluation:
    alert: bool
    summary: str
    log_dir: Path
    daily_runs: tuple[BackupRun, ...]
    alert_pair: tuple[BackupRun, BackupRun] | None = None


def resolve_log_dir(log_dir: str | os.PathLike[str] | None = None) -> Path:
    if log_dir:
        return Path(log_dir).expanduser()

    env_override = (os.environ.get(LOG_DIR_ENV) or os.environ.get(FALLBACK_LOG_DIR_ENV) or "").strip()
    if env_override:
        return Path(env_override).expanduser()

    local_app_data = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local_app_data:
        return Path(local_app_data) / DEFAULT_LOG_DIR_NAME

    return Path.home() / "AppData" / "Local" / DEFAULT_LOG_DIR_NAME


def _safe_dir_label(log_dir: Path) -> str:
    return log_dir.name or DEFAULT_LOG_DIR_NAME


def _parse_timestamp_from_name(path: Path) -> datetime | None:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(path.name)
        if not match:
            continue
        parts = match.groupdict(default="00")
        try:
            return datetime(
                int(parts["year"]),
                int(parts["month"]),
                int(parts["day"]),
                int(parts["hour"]),
                int(parts["minute"]),
                int(parts["second"]),
            )
        except ValueError:
            continue
    return None


def _infer_run_at(path: Path) -> datetime:
    return _parse_timestamp_from_name(path) or datetime.fromtimestamp(path.stat().st_mtime)


def classify_log_text(text: str) -> tuple[str, str]:
    last_status: str | None = None
    last_reason: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        exit_code_match = _EXIT_CODE_RE.search(line)
        if exit_code_match:
            exit_code = int(exit_code_match.group(1))
            if exit_code == 0:
                last_status = "success"
                last_reason = "exit-code-0"
            else:
                last_status = "failure"
                last_reason = f"exit-code-{exit_code}"
            continue

        if _FAIL_MARKER_RE.search(line):
            last_status = "failure"
            last_reason = "fail-marker"
            continue

        if _SUCCESS_MARKER_RE.search(line):
            last_status = "success"
            last_reason = "success-marker"
            continue

    return last_status or "unknown", last_reason or "no-status-marker"


def _iter_log_files(log_dir: Path) -> Iterable[Path]:
    if not log_dir.exists() or not log_dir.is_dir():
        return ()

    files = [
        path
        for path in log_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_LOG_SUFFIXES
    ]
    return sorted(
        files,
        key=lambda path: (_infer_run_at(path), path.stat().st_mtime, path.name),
        reverse=True,
    )


def collect_daily_runs(log_dir: Path, *, max_files: int = 60) -> tuple[BackupRun, ...]:
    latest_per_day: dict[date, BackupRun] = {}

    for path in list(_iter_log_files(log_dir))[:max_files]:
        text = path.read_text(encoding="utf-8", errors="replace")
        status, reason = classify_log_text(text)
        run_at = _infer_run_at(path)
        stat = path.stat()
        run = BackupRun(
            path=path,
            run_at=run_at,
            day=run_at.date(),
            status=status,
            reason=reason,
            modified_at=stat.st_mtime,
        )
        current = latest_per_day.get(run.day)
        if current is None or (run.run_at, run.modified_at, run.path.name) > (
            current.run_at,
            current.modified_at,
            current.path.name,
        ):
            latest_per_day[run.day] = run

    return tuple(sorted(latest_per_day.values(), key=lambda run: run.day))


def find_consecutive_failures(daily_runs: Iterable[BackupRun]) -> tuple[BackupRun, BackupRun] | None:
    ordered_runs = list(daily_runs)
    if len(ordered_runs) < 2:
        return None

    streak: list[BackupRun] = []
    expected_previous_day: date | None = None
    for run in reversed(ordered_runs):
        if not streak:
            if run.status != "failure":
                return None
            streak.append(run)
            expected_previous_day = run.day - timedelta(days=1)
            continue

        if run.status != "failure" or run.day != expected_previous_day:
            break

        streak.append(run)
        expected_previous_day = run.day - timedelta(days=1)
        if len(streak) >= 2:
            pair = tuple(reversed(streak[:2]))
            return pair[0], pair[1]

    return None


def evaluate_backup_alert(
    *,
    log_dir: str | os.PathLike[str] | None = None,
    max_files: int = 60,
) -> AlertEvaluation:
    resolved_log_dir = resolve_log_dir(log_dir)
    daily_runs = collect_daily_runs(resolved_log_dir, max_files=max_files)
    alert_pair = find_consecutive_failures(daily_runs)
    summary = build_summary(
        log_dir=resolved_log_dir,
        daily_runs=daily_runs,
        alert_pair=alert_pair,
    )
    return AlertEvaluation(
        alert=alert_pair is not None,
        summary=summary,
        log_dir=resolved_log_dir,
        daily_runs=daily_runs,
        alert_pair=alert_pair,
    )


def build_summary(
    *,
    log_dir: Path,
    daily_runs: Iterable[BackupRun],
    alert_pair: tuple[BackupRun, BackupRun] | None,
) -> str:
    label = _safe_dir_label(log_dir)
    daily_runs = tuple(daily_runs)

    if alert_pair is not None:
        first, second = alert_pair
        return (
            "ALERT registry backup failed on "
            f"{first.day.isoformat()} and {second.day.isoformat()} "
            f"(2 consecutive daily failures detected in {label})"
        )

    if not log_dir.exists():
        return f"OK registry backup alert clear: no log directory found for {label}"

    if not daily_runs:
        return f"OK registry backup alert clear: no log files found in {label}"

    return (
        "OK registry backup alert clear: no 2-day failure streak detected in "
        f"{label} ({len(daily_runs)} daily logs checked)"
    )
