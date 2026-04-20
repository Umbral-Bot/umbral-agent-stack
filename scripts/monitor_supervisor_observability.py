#!/usr/bin/env python3
"""
Supervisor Observability Monitoring — Phase 5 24h window tool.

Parses available log sources (journald, ops_log.jsonl) and optionally runs
local simulation against the passive building blocks to produce a structured
monitoring report with safety flags and a go/no-go recommendation.

Data sources (graceful degradation):
  1. journald (via ``journalctl``): counts ``supervisor_observability`` and
     failure-related lines.  Falls back silently if journald unavailable.
  2. ops_log.jsonl: structured JSONL with task lifecycle events.  Provides
     dispatch health (completed/failed/blocked counts by team).
  3. Local simulation (``--simulate``): exercises the pure building blocks
     from ``dispatcher/`` to verify event correctness without touching
     runtime.

Known limitation:
  The dispatcher logging format (``service.py:38``) uses
  ``%(asctime)s [%(levelname)s] %(name)s: %(message)s`` which does NOT
  serialize ``extra`` fields.  ``_log_supervisor_event()`` passes the event
  dict via ``extra={"supervisor_event": record}`` but it never appears in
  stdout/journald output.  Production log lines only show the bare string
  ``"supervisor_observability"``.  Structured event data is available only
  via local simulation (``--simulate``) until a JSON logging sink or
  OpsLogger integration is added in a future slice.

Usage:
  python scripts/monitor_supervisor_observability.py --since-minutes 60
  python scripts/monitor_supervisor_observability.py --simulate
  python scripts/monitor_supervisor_observability.py --simulate --output-json /tmp/report.json
  python scripts/monitor_supervisor_observability.py --fail-on-critical
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# ── Constants ───────────────────────────────────────────────────────

_DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"

_SUPERVISOR_LOG_MARKERS = (
    "supervisor_observability",
    "supervisor_observability_failed",
    "supervisor_ambiguity_detection_failed",
    "supervisor_resolution_event_failed",
)

_SUSPICIOUS_TEXT_KEYS = frozenset({
    "text", "prompt", "query", "question",
    "original_request", "payload", "input",
})

_SENTINEL_PATTERNS = (
    "TEXTO_SENSIBLE",
    "NO_DEBE_APARECER",
)

# Recommendation levels (ordered by severity).
PASS_MONITORING = "PASS_MONITORING"
WATCH = "WATCH"
INVESTIGATE = "INVESTIGATE"
ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"


# ── Journal parsing ─────────────────────────────────────────────────

def parse_journal(
    *,
    since_minutes: int,
    unit: Optional[str] = None,
) -> Dict[str, Any]:
    """Read journald lines and count supervisor markers.

    Returns a dict with counts and raw_lines_scanned.  Never raises;
    returns ``{"available": False}`` if journalctl is missing or fails.
    """
    result: Dict[str, Any] = {
        "available": False,
        "raw_lines_scanned": 0,
        "marker_counts": {m: 0 for m in _SUPERVISOR_LOG_MARKERS},
    }

    since_str = f"{since_minutes} minutes ago"
    cmd = ["journalctl", "--no-pager", "-o", "cat", "--since", since_str]
    if unit:
        cmd.extend(["-u", unit])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return result
    except Exception:
        return result

    if proc.returncode != 0:
        return result

    result["available"] = True
    for line in proc.stdout.splitlines():
        result["raw_lines_scanned"] += 1
        for marker in _SUPERVISOR_LOG_MARKERS:
            if marker in line:
                result["marker_counts"][marker] += 1

    return result


# ── Ops log parsing ─────────────────────────────────────────────────

def parse_ops_log(
    path: Path,
    *,
    since: datetime,
) -> Dict[str, Any]:
    """Read ops_log.jsonl and compute dispatch health metrics.

    Returns counts of task events by type and team within the time window.
    Never raises; returns ``{"available": False}`` on error.
    """
    result: Dict[str, Any] = {
        "available": False,
        "events_in_window": 0,
        "by_event": {},
        "by_team": {},
        "task_completed": 0,
        "task_failed": 0,
        "task_blocked": 0,
        "improvement_events": 0,
        "non_improvement_task_events": 0,
    }

    if not path.exists():
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            result["available"] = True
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    ev = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                ts_str = ev.get("ts", "")
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

                if ts < since:
                    continue

                result["events_in_window"] += 1
                event_type = ev.get("event", "unknown")
                result["by_event"][event_type] = result["by_event"].get(event_type, 0) + 1

                team = ev.get("team")
                if team:
                    result["by_team"][team] = result["by_team"].get(team, 0) + 1

                if event_type == "task_completed":
                    result["task_completed"] += 1
                elif event_type == "task_failed":
                    result["task_failed"] += 1
                elif event_type == "task_blocked":
                    result["task_blocked"] += 1

                if team == "improvement":
                    result["improvement_events"] += 1

    except Exception:
        result["available"] = False

    return result


# ── Simulation ──────────────────────────────────────────────────────

def run_simulation() -> Dict[str, Any]:
    """Exercise passive building blocks locally and check safety.

    Returns structured results with per-check pass/fail and any safety
    flags triggered.
    """
    result: Dict[str, Any] = {
        "available": False,
        "checks": [],
        "should_block_true_count": 0,
        "non_improvement_event_count": 0,
        "raw_text_leakage_suspected_count": 0,
        "malformed_event_count": 0,
        "error_event_count": 0,
    }

    try:
        from dispatcher.ambiguity_signal import detect_ambiguity_signal
        from dispatcher.supervisor_observability import (
            build_ambiguity_signal_event,
            build_supervisor_resolution_event,
            build_supervisor_noop_event,
        )
        from dispatcher.supervisor_resolution import (
            load_supervisor_registry,
            resolve_supervisor,
        )
    except ImportError as exc:
        result["checks"].append({
            "name": "import_building_blocks",
            "passed": False,
            "detail": f"Import failed: {exc}",
        })
        return result

    result["available"] = True

    # Check 1: Ambiguity detection on known ambiguous text
    try:
        signal = detect_ambiguity_signal(
            "revisa la salud del sistema y dime que deberiamos mejorar",
            team="improvement",
            task="notion.add_comment",
            task_type="general",
        )
        passed = getattr(signal, "is_ambiguous", False) is True
        result["checks"].append({
            "name": "ambiguity_detection_ambiguous",
            "passed": passed,
            "detail": f"is_ambiguous={getattr(signal, 'is_ambiguous', 'N/A')}",
        })
    except Exception as exc:
        result["checks"].append({
            "name": "ambiguity_detection_ambiguous",
            "passed": False,
            "detail": str(exc)[:200],
        })

    # Check 2: Ambiguity detection on concrete text (should NOT be ambiguous)
    try:
        signal_concrete = detect_ambiguity_signal(
            "corre el ooda report",
            team="improvement",
            task="system.ooda_report",
            task_type="observability",
        )
        passed = getattr(signal_concrete, "is_ambiguous", True) is False
        result["checks"].append({
            "name": "ambiguity_detection_concrete",
            "passed": passed,
            "detail": f"is_ambiguous={getattr(signal_concrete, 'is_ambiguous', 'N/A')}",
        })
    except Exception as exc:
        result["checks"].append({
            "name": "ambiguity_detection_concrete",
            "passed": False,
            "detail": str(exc)[:200],
        })

    # Check 3: Build ambiguity event from ambiguous signal
    try:
        signal = detect_ambiguity_signal(
            "revisa la salud del sistema y dime que deberiamos mejorar",
            team="improvement",
            task="notion.add_comment",
            task_type="general",
        )
        amb_event = build_ambiguity_signal_event(
            signal, task_id="sim-1", task_type="general",
        )
        record = amb_event.to_log_record()
        passed = (
            record.get("event_type") == "supervisor.ambiguity_signal"
            and record.get("outcome") == "ambiguous"
            and record.get("team") == "improvement"
        )
        result["checks"].append({
            "name": "build_ambiguity_event",
            "passed": passed,
            "detail": f"event_type={record.get('event_type')}, outcome={record.get('outcome')}",
        })
        _check_event_safety(record, result)
    except Exception as exc:
        result["checks"].append({
            "name": "build_ambiguity_event",
            "passed": False,
            "detail": str(exc)[:200],
        })

    # Check 4: Resolution (should be unresolved/design_only)
    try:
        registry = load_supervisor_registry()
        resolution = resolve_supervisor(
            team="improvement",
            registry=registry,
        )
        res_event = build_supervisor_resolution_event(
            resolution, task_id="sim-1", task_type="general",
        )
        record = res_event.to_log_record()
        passed = (
            record.get("event_type") == "supervisor.resolution"
            and record.get("outcome") == "unresolved"
        )
        result["checks"].append({
            "name": "build_resolution_event",
            "passed": passed,
            "detail": f"outcome={record.get('outcome')}, severity={record.get('severity')}",
        })
        # Check should_block
        fields = record.get("fields", {})
        if fields.get("should_block") is True:
            result["should_block_true_count"] += 1
        _check_event_safety(record, result)
    except Exception as exc:
        result["checks"].append({
            "name": "build_resolution_event",
            "passed": False,
            "detail": str(exc)[:200],
        })

    # Check 5: Noop event
    try:
        noop_event = build_supervisor_noop_event(
            team="improvement",
            reason="monitoring_simulation",
            task_id="sim-noop",
        )
        record = noop_event.to_log_record()
        passed = (
            record.get("event_type") == "supervisor.noop"
            and record.get("outcome") == "noop"
        )
        result["checks"].append({
            "name": "build_noop_event",
            "passed": passed,
            "detail": f"outcome={record.get('outcome')}",
        })
        _check_event_safety(record, result)
    except Exception as exc:
        result["checks"].append({
            "name": "build_noop_event",
            "passed": False,
            "detail": str(exc)[:200],
        })

    # Check 6: Sentinel text leakage test
    try:
        sentinel = "TEXTO_SENSIBLE_MONITOR_SENTINEL_2026"
        signal_sent = detect_ambiguity_signal(
            f"{sentinel} revisa la salud del sistema y dime que deberiamos mejorar",
            team="improvement",
            task="notion.add_comment",
            task_type="general",
        )
        if getattr(signal_sent, "is_ambiguous", False):
            evt = build_ambiguity_signal_event(
                signal_sent, task_id="sim-sentinel", task_type="general",
            )
            record = evt.to_log_record()
            blob = json.dumps(record, default=str)
            leaked = sentinel in blob
            if leaked:
                result["raw_text_leakage_suspected_count"] += 1
            result["checks"].append({
                "name": "sentinel_text_leakage",
                "passed": not leaked,
                "detail": "sentinel found in event" if leaked else "no leakage",
            })
        else:
            result["checks"].append({
                "name": "sentinel_text_leakage",
                "passed": True,
                "detail": "signal not ambiguous with sentinel — no event produced",
            })
    except Exception as exc:
        result["checks"].append({
            "name": "sentinel_text_leakage",
            "passed": False,
            "detail": str(exc)[:200],
        })

    return result


def _check_event_safety(record: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Check a single event record for safety flags."""
    team = record.get("team")
    if team is not None and team != "improvement":
        result["non_improvement_event_count"] += 1

    severity = record.get("severity", "")
    if severity in ("error", "warning"):
        result["error_event_count"] += 1

    # Check for raw text leakage in fields
    fields = record.get("fields", {})
    _check_fields_for_text(fields, result)


def _check_fields_for_text(
    fields: Dict[str, Any],
    result: Dict[str, Any],
) -> None:
    """Flag suspicious free-text keys in event fields."""
    for key, value in fields.items():
        if key in _SUSPICIOUS_TEXT_KEYS and isinstance(value, str) and len(value) > 50:
            result["raw_text_leakage_suspected_count"] += 1
            return
        if isinstance(value, str):
            for sentinel in _SENTINEL_PATTERNS:
                if sentinel in value:
                    result["raw_text_leakage_suspected_count"] += 1
                    return
    # Check nested dicts
    for value in fields.values():
        if isinstance(value, dict):
            _check_fields_for_text(value, result)


# ── Recommendation engine ───────────────────────────────────────────

def compute_recommendation(
    *,
    journal: Dict[str, Any],
    ops_log: Dict[str, Any],
    simulation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Produce a recommendation from all data sources."""
    reasons: List[str] = []
    level = PASS_MONITORING

    def escalate(new_level: str, reason: str) -> None:
        nonlocal level
        severity_order = [PASS_MONITORING, WATCH, INVESTIGATE, ROLLBACK_RECOMMENDED]
        if severity_order.index(new_level) > severity_order.index(level):
            level = new_level
        reasons.append(f"[{new_level}] {reason}")

    # Journal checks
    if journal.get("available"):
        markers = journal.get("marker_counts", {})
        failed_count = (
            markers.get("supervisor_observability_failed", 0)
            + markers.get("supervisor_ambiguity_detection_failed", 0)
            + markers.get("supervisor_resolution_event_failed", 0)
        )
        if failed_count > 0:
            escalate(INVESTIGATE, f"{failed_count} supervisor failure lines in journal")

        obs_count = markers.get("supervisor_observability", 0)
        if obs_count == 0:
            escalate(WATCH, "No supervisor_observability lines in journal (no traffic or formatter gap)")
    else:
        escalate(WATCH, "journald not available — cannot verify supervisor log presence")

    # Ops log checks
    if ops_log.get("available"):
        task_failed = ops_log.get("task_failed", 0)
        task_completed = ops_log.get("task_completed", 0)
        if task_completed > 0 and task_failed > 0:
            fail_rate = task_failed / (task_completed + task_failed)
            if fail_rate > 0.2:
                escalate(INVESTIGATE, f"High task failure rate: {fail_rate:.1%} ({task_failed}/{task_completed + task_failed})")
    else:
        escalate(WATCH, "ops_log not available — cannot verify dispatch health")

    # Simulation checks
    if simulation and simulation.get("available"):
        if simulation.get("should_block_true_count", 0) > 0:
            escalate(ROLLBACK_RECOMMENDED, f"should_block=True detected in {simulation['should_block_true_count']} event(s)")

        if simulation.get("non_improvement_event_count", 0) > 0:
            escalate(ROLLBACK_RECOMMENDED, f"Non-improvement team event detected in {simulation['non_improvement_event_count']} event(s)")

        if simulation.get("raw_text_leakage_suspected_count", 0) > 0:
            escalate(ROLLBACK_RECOMMENDED, f"Raw text leakage suspected in {simulation['raw_text_leakage_suspected_count']} event(s)")

        if simulation.get("malformed_event_count", 0) > 0:
            escalate(INVESTIGATE, f"{simulation['malformed_event_count']} malformed event(s)")

        failed_checks = [c for c in simulation.get("checks", []) if not c.get("passed")]
        if failed_checks:
            names = ", ".join(c["name"] for c in failed_checks)
            escalate(INVESTIGATE, f"Simulation checks failed: {names}")

    return {"level": level, "reasons": reasons}


# ── Report generation ───────────────────────────────────────────────

def build_report(
    *,
    since_minutes: int,
    journal: Dict[str, Any],
    ops_log: Dict[str, Any],
    simulation: Optional[Dict[str, Any]],
    recommendation: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the full structured report."""
    now = datetime.now(timezone.utc)
    return {
        "report_type": "supervisor_observability_monitoring",
        "generated_at": now.isoformat(),
        "time_window_minutes": since_minutes,
        "window_start": (now - timedelta(minutes=since_minutes)).isoformat(),
        "window_end": now.isoformat(),
        "sources": {
            "journal": {
                "available": journal.get("available", False),
                "raw_lines_scanned": journal.get("raw_lines_scanned", 0),
                "marker_counts": journal.get("marker_counts", {}),
            },
            "ops_log": {
                "available": ops_log.get("available", False),
                "events_in_window": ops_log.get("events_in_window", 0),
                "by_event": ops_log.get("by_event", {}),
                "by_team": ops_log.get("by_team", {}),
                "task_completed": ops_log.get("task_completed", 0),
                "task_failed": ops_log.get("task_failed", 0),
                "task_blocked": ops_log.get("task_blocked", 0),
                "improvement_events": ops_log.get("improvement_events", 0),
            },
            "simulation": _sanitize_simulation(simulation) if simulation else None,
        },
        "safety_flags": _compute_safety_flags(journal, ops_log, simulation),
        "recommendation": recommendation,
    }


def _sanitize_simulation(sim: Dict[str, Any]) -> Dict[str, Any]:
    """Return simulation results without any raw text content."""
    return {
        "available": sim.get("available", False),
        "checks": sim.get("checks", []),
        "should_block_true_count": sim.get("should_block_true_count", 0),
        "non_improvement_event_count": sim.get("non_improvement_event_count", 0),
        "raw_text_leakage_suspected_count": sim.get("raw_text_leakage_suspected_count", 0),
        "malformed_event_count": sim.get("malformed_event_count", 0),
        "error_event_count": sim.get("error_event_count", 0),
    }


def _compute_safety_flags(
    journal: Dict[str, Any],
    ops_log: Dict[str, Any],
    simulation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate safety flags from all sources."""
    flags: Dict[str, int] = {
        "supervisor_failure_lines": 0,
        "should_block_true_count": 0,
        "non_improvement_event_count": 0,
        "raw_text_leakage_suspected_count": 0,
        "malformed_event_count": 0,
        "error_event_count": 0,
    }

    if journal.get("available"):
        markers = journal.get("marker_counts", {})
        flags["supervisor_failure_lines"] = (
            markers.get("supervisor_observability_failed", 0)
            + markers.get("supervisor_ambiguity_detection_failed", 0)
            + markers.get("supervisor_resolution_event_failed", 0)
        )

    if simulation and simulation.get("available"):
        flags["should_block_true_count"] = simulation.get("should_block_true_count", 0)
        flags["non_improvement_event_count"] = simulation.get("non_improvement_event_count", 0)
        flags["raw_text_leakage_suspected_count"] = simulation.get("raw_text_leakage_suspected_count", 0)
        flags["malformed_event_count"] = simulation.get("malformed_event_count", 0)
        flags["error_event_count"] = simulation.get("error_event_count", 0)

    return flags


# ── Markdown output ─────────────────────────────────────────────────

def format_markdown(report: Dict[str, Any]) -> str:
    """Format report as readable Markdown."""
    lines: List[str] = []
    rec = report["recommendation"]

    lines.append(f"# Supervisor Observability Monitoring Report")
    lines.append("")
    lines.append(f"**Recommendation: {rec['level']}**")
    lines.append("")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Window: {report['time_window_minutes']} minutes")
    lines.append("")

    if rec["reasons"]:
        lines.append("## Reasons")
        lines.append("")
        for r in rec["reasons"]:
            lines.append(f"- {r}")
        lines.append("")

    # Sources
    src = report["sources"]
    lines.append("## Sources")
    lines.append("")

    j = src["journal"]
    lines.append(f"### Journal")
    lines.append(f"- Available: {j['available']}")
    lines.append(f"- Lines scanned: {j['raw_lines_scanned']}")
    if j["available"]:
        for marker, count in j["marker_counts"].items():
            lines.append(f"- `{marker}`: {count}")
    lines.append("")

    o = src["ops_log"]
    lines.append("### Ops Log")
    lines.append(f"- Available: {o['available']}")
    lines.append(f"- Events in window: {o['events_in_window']}")
    if o["available"] and o["by_event"]:
        lines.append(f"- Completed: {o['task_completed']}, Failed: {o['task_failed']}, Blocked: {o['task_blocked']}")
        lines.append(f"- Improvement team events: {o['improvement_events']}")
        if o["by_team"]:
            teams_str = ", ".join(f"{k}={v}" for k, v in sorted(o["by_team"].items()))
            lines.append(f"- By team: {teams_str}")
    lines.append("")

    sim = src.get("simulation")
    if sim:
        lines.append("### Simulation")
        lines.append(f"- Available: {sim['available']}")
        if sim["available"]:
            for check in sim.get("checks", []):
                status = "PASS" if check["passed"] else "FAIL"
                lines.append(f"- [{status}] {check['name']}: {check.get('detail', '')}")
        lines.append("")

    # Safety flags
    flags = report["safety_flags"]
    lines.append("## Safety Flags")
    lines.append("")
    for key, value in flags.items():
        marker = "!!" if value > 0 else "ok"
        lines.append(f"- [{marker}] {key}: {value}")
    lines.append("")

    # Known limitation
    lines.append("## Known Limitation")
    lines.append("")
    lines.append("The dispatcher logging format (`%(asctime)s [%(levelname)s] %(name)s: %(message)s`)")
    lines.append("does NOT serialize `extra` fields. `supervisor_event` dicts emitted by")
    lines.append("`_log_supervisor_event()` do not appear in stdout/journald output.")
    lines.append("Structured event data is only available via `--simulate`.")
    lines.append("Next improvement: configure JSON logging sink or OpsLogger integration.")
    lines.append("")

    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────────

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Monitor supervisor observability events from Phase 5 runtime wiring.",
    )
    p.add_argument(
        "--since-minutes",
        type=int,
        default=1440,
        help="Time window in minutes (default: 1440 = 24h)",
    )
    p.add_argument(
        "--journal-unit",
        type=str,
        default=None,
        help="systemd unit for journalctl filtering (e.g. openclaw-dispatcher.service)",
    )
    p.add_argument(
        "--ops-log",
        type=str,
        default=str(_DEFAULT_OPS_LOG),
        help=f"Path to ops_log.jsonl (default: {_DEFAULT_OPS_LOG})",
    )
    p.add_argument(
        "--simulate",
        action="store_true",
        help="Run local building-block simulation checks",
    )
    p.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Write JSON report to file",
    )
    p.add_argument(
        "--output-md",
        type=str,
        default=None,
        help="Write Markdown report to file",
    )
    p.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with code 1 if recommendation is ROLLBACK_RECOMMENDED",
    )
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    since = datetime.now(timezone.utc) - timedelta(minutes=args.since_minutes)

    # Gather data
    journal = parse_journal(
        since_minutes=args.since_minutes,
        unit=args.journal_unit,
    )

    ops = parse_ops_log(Path(args.ops_log), since=since)

    simulation = run_simulation() if args.simulate else None

    # Compute recommendation
    recommendation = compute_recommendation(
        journal=journal,
        ops_log=ops,
        simulation=simulation,
    )

    # Build report
    report = build_report(
        since_minutes=args.since_minutes,
        journal=journal,
        ops_log=ops,
        simulation=simulation,
        recommendation=recommendation,
    )

    # Output
    md = format_markdown(report)
    print(md)

    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"JSON report written to: {path}")

    if args.output_md:
        path = Path(args.output_md)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
        print(f"Markdown report written to: {path}")

    if args.fail_on_critical and recommendation["level"] == ROLLBACK_RECOMMENDED:
        print(f"\nCRITICAL: Recommendation is {ROLLBACK_RECOMMENDED}. Exiting with code 1.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
