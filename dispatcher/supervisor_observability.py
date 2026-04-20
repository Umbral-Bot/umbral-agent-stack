"""
Pure passive supervisor observability event builders.

Defines structured event records for future telemetry/logging of supervisor
resolution, ambiguity signal, config validation, and no-op paths. These
builders are deliberately passive: no logging emission, no file I/O, no
network calls, no runtime imports. They produce JSON-serializable dicts
that a future runtime consumer can emit to structured logs, Langfuse, or
other observability backends.

Safety invariants:
- No logging, no I/O, no network, no env vars.
- No raw user/task text in event records.
- Deterministic: same inputs produce same output.
- Not imported by any runtime dispatcher path.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence


# ── Severity / outcome constants ─────────────────────────────────

VALID_SEVERITIES = {"debug", "info", "warning", "error"}

VALID_OUTCOMES = {
    "resolved", "unresolved", "ambiguous", "not_ambiguous",
    "valid", "warning", "error", "noop",
}


# ── Event dataclass ──────────────────────────────────────────────

@dataclass(frozen=True)
class SupervisorObservabilityEvent:
    """A structured observability event for supervisor-related operations."""

    event_type: str
    team: str | None
    task_id: str | None
    task_type: str | None
    outcome: str
    severity: str
    fields: Mapping[str, Any]

    def to_log_record(self) -> dict[str, Any]:
        """Return stable JSON-serializable dict with fixed top-level keys."""
        return {
            "event_type": self.event_type,
            "team": self.team,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "outcome": self.outcome,
            "severity": self.severity,
            "fields": dict(self.fields) if self.fields else {},
        }


# ── Resolution event ─────────────────────────────────────────────

# Reasons that map to info severity (expected passive states).
_RESOLUTION_INFO_REASONS = {
    "status_design_only",
    "status_disabled",
    "registry_entry_missing",
    "team_has_no_supervisor",
    "missing_team",
    "target_type_none",
}


def build_supervisor_resolution_event(
    resolution: Any,
    *,
    task_id: str | None = None,
    task_type: str | None = None,
) -> SupervisorObservabilityEvent:
    """
    Build an observability event from a SupervisorResolution result.

    Accepts any object with to_log_fields() or known attributes.
    """
    fields = _extract_fields(resolution)
    resolution_status = fields.get("resolution_status", "")
    reason = fields.get("reason", "")

    if resolution_status == "resolved":
        outcome = "resolved"
        severity = "info"
    else:
        outcome = "unresolved"
        severity = (
            "info" if reason in _RESOLUTION_INFO_REASONS else "warning"
        )

    return SupervisorObservabilityEvent(
        event_type="supervisor.resolution",
        team=fields.get("team"),
        task_id=task_id,
        task_type=task_type,
        outcome=outcome,
        severity=severity,
        fields=fields,
    )


# ── Ambiguity signal event ───────────────────────────────────────

def build_ambiguity_signal_event(
    signal: Any,
    *,
    task_id: str | None = None,
    task_type: str | None = None,
) -> SupervisorObservabilityEvent:
    """
    Build an observability event from an AmbiguitySignal result.

    Accepts any object with to_log_fields() or known attributes.
    """
    fields = _extract_fields(signal)
    is_ambiguous = fields.get("is_ambiguous", False)

    return SupervisorObservabilityEvent(
        event_type="supervisor.ambiguity_signal",
        team=fields.get("team"),
        task_id=task_id,
        task_type=task_type,
        outcome="ambiguous" if is_ambiguous else "not_ambiguous",
        severity="info" if is_ambiguous else "debug",
        fields=fields,
    )


# ── Config validation event ──────────────────────────────────────

def build_config_validation_event(
    issues: Sequence[Any],
    *,
    task_id: str | None = None,
    task_type: str | None = None,
) -> SupervisorObservabilityEvent:
    """
    Build an observability event from config validation issues.

    Accepts a sequence of SupervisorConfigIssue or any objects with
    team/severity/code/message attributes.
    """
    issue_dicts = []
    error_count = 0
    warning_count = 0

    for issue in issues:
        d = _issue_to_dict(issue)
        issue_dicts.append(d)
        sev = d.get("severity", "")
        if sev == "error":
            error_count += 1
        elif sev == "warning":
            warning_count += 1

    if error_count > 0:
        outcome = "error"
        severity = "error"
    elif warning_count > 0:
        outcome = "warning"
        severity = "warning"
    else:
        outcome = "valid"
        severity = "info"

    fields: dict[str, Any] = {
        "issue_count": len(issue_dicts),
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issue_dicts,
    }

    return SupervisorObservabilityEvent(
        event_type="supervisor.config_validation",
        team=None,
        task_id=task_id,
        task_type=task_type,
        outcome=outcome,
        severity=severity,
        fields=fields,
    )


# ── Noop event ───────────────────────────────────────────────────

def build_supervisor_noop_event(
    *,
    team: str | None = None,
    reason: str,
    task_id: str | None = None,
    task_type: str | None = None,
) -> SupervisorObservabilityEvent:
    """
    Build a no-op event for when no supervisor path is used.

    Documents "supervisor routing was not applicable" for future
    observability without changing dispatch behavior.
    """
    return SupervisorObservabilityEvent(
        event_type="supervisor.noop",
        team=team,
        task_id=task_id,
        task_type=task_type,
        outcome="noop",
        severity="debug",
        fields={"reason": reason},
    )


# ── Internal helpers ─────────────────────────────────────────────

def _extract_fields(obj: Any) -> dict[str, Any]:
    """Extract fields from an object safely, preferring to_log_fields()."""
    if hasattr(obj, "to_log_fields") and callable(obj.to_log_fields):
        result = obj.to_log_fields()
        if isinstance(result, Mapping):
            return dict(result)

    # Fallback: read known dataclass fields
    if hasattr(obj, "__dataclass_fields__"):
        return {
            k: getattr(obj, k) for k in obj.__dataclass_fields__
            if not k.startswith("_")
        }

    if isinstance(obj, Mapping):
        return dict(obj)

    return {}


def _issue_to_dict(issue: Any) -> dict[str, Any]:
    """Convert a config issue to a stable dict."""
    if hasattr(issue, "__dataclass_fields__"):
        return {
            k: getattr(issue, k) for k in issue.__dataclass_fields__
            if not k.startswith("_")
        }
    if isinstance(issue, Mapping):
        return dict(issue)
    return {}
