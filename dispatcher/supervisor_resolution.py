"""
Pure supervisor resolution helpers.

This module implements the first Phase 5 runtime-safe building block: mapping a
team key to an explicit supervisor registry entry without changing dispatcher
routing. Nothing here enqueues, invokes agents, or blocks dispatch.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger("dispatcher.supervisor_resolution")

VALID_TARGET_TYPES = {
    "openclaw_agent",
    "worker_task",
    "external_workflow",
    "manual_owner",
    "none",
}
VALID_STATUSES = {"design_only", "active", "disabled"}
VALID_FALLBACKS = {"direct", "manual", "disabled"}


@dataclass(frozen=True)
class SupervisorResolution:
    """Resolution result prepared for future observability/logging."""

    team: str | None
    supervisor_label: str | None
    resolution_status: str
    target_type: str | None = None
    target: str | None = None
    fallback: str = "direct"
    fallback_used: bool = True
    should_block: bool = False
    reason: str = ""

    def to_log_fields(self) -> dict[str, Any]:
        """Return stable fields for logs/telemetry without side effects."""

        return {
            "team": self.team,
            "supervisor_label": self.supervisor_label,
            "resolution_status": self.resolution_status,
            "target_type": self.target_type,
            "target": self.target,
            "fallback": self.fallback,
            "fallback_used": self.fallback_used,
            "should_block": self.should_block,
            "reason": self.reason,
        }


def default_supervisors_path() -> Path:
    """Return repo default config/supervisors.yaml path."""

    return Path(__file__).resolve().parent.parent / "config" / "supervisors.yaml"


def load_supervisor_registry(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """
    Load supervisor registry YAML safely.

    Missing, malformed, or invalid files return an empty registry. This preserves
    the fallback-direct invariant and keeps resolution non-blocking.
    """

    registry_path = Path(
        path or os.environ.get("SUPERVISORS_CONFIG_PATH") or default_supervisors_path()
    )
    if not registry_path.is_file():
        logger.warning("Supervisor registry not found at %s; using empty registry", registry_path)
        return {}

    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed; using empty supervisor registry")
        return {}

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        logger.warning("Failed to load supervisor registry %s: %s", registry_path, exc)
        return {}

    if not isinstance(data, dict):
        logger.warning("Supervisor registry %s is not a mapping; using empty registry", registry_path)
        return {}
    supervisors = data.get("supervisors")
    if supervisors is not None and not isinstance(supervisors, dict):
        logger.warning("Supervisor registry %s has non-mapping supervisors; using empty registry", registry_path)
        return {}
    return data


def resolve_supervisor(
    team: str | None,
    *,
    teams_config: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
    target_available: bool | None = None,
) -> SupervisorResolution:
    """
    Resolve a team supervisor to an explicit registry target.

    This is deliberately conservative:
    - resolution matches by team key only, never by human-readable label;
    - design_only/disabled entries never activate;
    - active entries require an explicit target availability signal;
    - every failure path returns should_block=False with fallback direct/manual.
    """

    team_key = team or None
    team_info = _team_info(team_key, teams_config)
    supervisor_label = _as_optional_str(team_info.get("supervisor")) if team_info else None

    if not team_key:
        return _result(None, supervisor_label, "none", reason="missing_team")

    if not supervisor_label:
        return _result(team_key, None, "none", target_type="none", reason="team_has_no_supervisor")

    supervisors = _supervisors_mapping(registry)
    entry = supervisors.get(team_key)
    if not isinstance(entry, Mapping):
        return _result(
            team_key,
            supervisor_label,
            "unresolved",
            reason="registry_entry_missing",
        )

    normalized = _normalize_entry(entry)
    if normalized["error"]:
        return _result(
            team_key,
            supervisor_label,
            "unresolved",
            target_type=normalized["target_type"],
            target=normalized["target"],
            fallback=normalized["fallback"],
            reason=normalized["error"],
        )

    status = normalized["status"]
    target_type = normalized["target_type"]
    target = normalized["target"]
    fallback = normalized["fallback"]

    if status == "design_only":
        return _result(
            team_key,
            supervisor_label,
            "unresolved",
            target_type=target_type,
            target=target,
            fallback=fallback,
            reason="status_design_only",
        )

    if status == "disabled":
        return _result(
            team_key,
            supervisor_label,
            "unresolved",
            target_type=target_type,
            target=target,
            fallback=fallback,
            reason="status_disabled",
        )

    if target_type == "none":
        return _result(
            team_key,
            supervisor_label,
            "none",
            target_type=target_type,
            target=target,
            fallback=fallback,
            reason="target_type_none",
        )

    if target_available is True:
        return SupervisorResolution(
            team=team_key,
            supervisor_label=supervisor_label,
            resolution_status="resolved",
            target_type=target_type,
            target=target,
            fallback=fallback,
            fallback_used=False,
            should_block=False,
            reason="target_available",
        )

    if target_available is False:
        return _result(
            team_key,
            supervisor_label,
            "unresolved",
            target_type=target_type,
            target=target,
            fallback=fallback,
            reason="target_unavailable",
        )

    return _result(
        team_key,
        supervisor_label,
        "not_ready",
        target_type=target_type,
        target=target,
        fallback=fallback,
        reason="target_availability_unknown",
    )


def _result(
    team: str | None,
    supervisor_label: str | None,
    resolution_status: str,
    *,
    target_type: str | None = None,
    target: str | None = None,
    fallback: str = "direct",
    reason: str,
) -> SupervisorResolution:
    fallback = fallback if fallback in VALID_FALLBACKS else "direct"
    return SupervisorResolution(
        team=team,
        supervisor_label=supervisor_label,
        resolution_status=resolution_status,
        target_type=target_type,
        target=target,
        fallback=fallback,
        fallback_used=True,
        should_block=False,
        reason=reason,
    )


def _team_info(team: str | None, teams_config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not team or not isinstance(teams_config, Mapping):
        return {}
    teams = teams_config.get("teams") if isinstance(teams_config.get("teams"), Mapping) else teams_config
    info = teams.get(team) if isinstance(teams, Mapping) else None
    return info if isinstance(info, Mapping) else {}


def _supervisors_mapping(registry: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(registry, Mapping):
        return {}
    supervisors = registry.get("supervisors")
    if isinstance(supervisors, Mapping):
        return supervisors
    return registry


def _normalize_entry(entry: Mapping[str, Any]) -> dict[str, str | None]:
    target_type = _as_optional_str(entry.get("type")) or "none"
    target = _as_optional_str(entry.get("target"))
    status = _as_optional_str(entry.get("status")) or "disabled"
    fallback = _as_optional_str(entry.get("fallback")) or "direct"

    if target_type not in VALID_TARGET_TYPES:
        return {
            "target_type": target_type,
            "target": target,
            "status": status,
            "fallback": fallback,
            "error": "invalid_target_type",
        }
    if status not in VALID_STATUSES:
        return {
            "target_type": target_type,
            "target": target,
            "status": status,
            "fallback": fallback,
            "error": "invalid_status",
        }
    if fallback not in VALID_FALLBACKS:
        return {
            "target_type": target_type,
            "target": target,
            "status": status,
            "fallback": "direct",
            "error": "invalid_fallback",
        }
    if status == "active" and target_type != "none" and not target:
        return {
            "target_type": target_type,
            "target": target,
            "status": status,
            "fallback": fallback,
            "error": "active_target_missing",
        }
    return {
        "target_type": target_type,
        "target": target,
        "status": status,
        "fallback": fallback,
        "error": None,
    }


def _as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


# ── Config consistency validation ────────────────────────────────


@dataclass(frozen=True)
class SupervisorConfigIssue:
    """A single consistency issue between teams.yaml and supervisors.yaml."""

    team: str
    severity: str  # "error" | "warning"
    code: str
    message: str


def validate_supervisor_config_consistency(
    teams_config: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> tuple[SupervisorConfigIssue, ...]:
    """
    Validate consistency between teams config and supervisor registry.

    Pure function: takes already-loaded dicts, returns tuple of issues.
    No file I/O, no logging, no side effects.
    """
    issues: list[SupervisorConfigIssue] = []

    # Extract teams mapping
    teams_raw = teams_config.get("teams") if isinstance(teams_config, Mapping) else None
    teams: Mapping[str, Any] = teams_raw if isinstance(teams_raw, Mapping) else {}

    # Extract supervisors mapping
    supervisors = _supervisors_mapping(registry)

    # Rule 1: every registry team must exist in teams config
    for team_key in supervisors:
        if not isinstance(team_key, str):
            continue
        if team_key not in teams:
            issues.append(SupervisorConfigIssue(
                team=team_key,
                severity="error",
                code="registry_team_missing_from_teams_config",
                message=f"Registry defines '{team_key}' but it does not exist in teams config",
            ))

    # Rules 2-8: validate each registry entry and check label consistency
    for team_key, entry in supervisors.items():
        if not isinstance(team_key, str) or not isinstance(entry, Mapping):
            continue
        if team_key not in teams:
            continue  # already reported in rule 1

        # Rule 2: label consistency
        team_info = teams.get(team_key)
        if isinstance(team_info, Mapping):
            teams_label = _as_optional_str(team_info.get("supervisor"))
            registry_label = _as_optional_str(entry.get("label"))
            if teams_label and registry_label and teams_label != registry_label:
                issues.append(SupervisorConfigIssue(
                    team=team_key,
                    severity="error",
                    code="supervisor_label_mismatch",
                    message=(
                        f"teams.yaml supervisor '{teams_label}' != "
                        f"registry label '{registry_label}'"
                    ),
                ))

        # Rule 4: valid status
        status = _as_optional_str(entry.get("status")) or "disabled"
        if status not in VALID_STATUSES:
            issues.append(SupervisorConfigIssue(
                team=team_key,
                severity="error",
                code="invalid_supervisor_status",
                message=f"Invalid status '{status}'; allowed: {sorted(VALID_STATUSES)}",
            ))

        # Rule 5: valid type
        target_type = _as_optional_str(entry.get("type")) or "none"
        if target_type not in VALID_TARGET_TYPES:
            issues.append(SupervisorConfigIssue(
                team=team_key,
                severity="error",
                code="invalid_supervisor_type",
                message=f"Invalid type '{target_type}'; allowed: {sorted(VALID_TARGET_TYPES)}",
            ))

        # Rule 6: valid fallback
        fallback = _as_optional_str(entry.get("fallback")) or "direct"
        if fallback not in VALID_FALLBACKS:
            issues.append(SupervisorConfigIssue(
                team=team_key,
                severity="error",
                code="invalid_supervisor_fallback",
                message=f"Invalid fallback '{fallback}'; allowed: {sorted(VALID_FALLBACKS)}",
            ))

        # Rule 7: active requires target
        target = _as_optional_str(entry.get("target"))
        if status == "active" and target_type != "none" and not target:
            issues.append(SupervisorConfigIssue(
                team=team_key,
                severity="error",
                code="active_supervisor_missing_target",
                message="status is 'active' but target is missing",
            ))

    # Rule 3: teams with supervisor should have registry entry (warning)
    for team_key, team_info in teams.items():
        if not isinstance(team_key, str) or not isinstance(team_info, Mapping):
            continue
        supervisor_label = _as_optional_str(team_info.get("supervisor"))
        if supervisor_label and team_key not in supervisors:
            issues.append(SupervisorConfigIssue(
                team=team_key,
                severity="warning",
                code="team_supervisor_missing_registry_entry",
                message=(
                    f"Team '{team_key}' has supervisor '{supervisor_label}' "
                    f"but no registry entry in supervisors.yaml"
                ),
            ))

    return tuple(issues)
