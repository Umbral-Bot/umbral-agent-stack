# Supervisor Observability Monitoring

> Runbook for the Phase 5/6A supervisor observability monitoring tool. Use during the 24h monitoring window (per `docs/75`) and for ongoing health checks of the supervisor observability wiring.

## 1. Purpose

After PR #241 merged the first runtime wiring slice (`_emit_supervisor_observability()` in `dispatcher/router.py`), a 24h monitoring window is required before proceeding. PR #242 delivered the monitoring tool; Phase 6A closes the formatter gap by persisting structured supervisor events to `ops_log.jsonl` directly.

This tool provides a reusable, local-only, non-blocking way to:

- Count supervisor observability log lines from journald.
- Analyze dispatch health from `ops_log.jsonl` (task completed/failed/blocked).
- Read **structured supervisor events** persisted to `ops_log.jsonl` by `OpsLogger.supervisor_event()` (Phase 6A).
- Run local simulation against the pure building blocks to verify event correctness.
- Detect critical conditions: `should_block=True`, non-improvement events, raw text leakage.
- Produce a structured go/no-go recommendation.

## 2. How to Run

### Basic monitoring (last 24 hours)

```bash
python scripts/monitor_supervisor_observability.py --since-minutes 1440
```

### With simulation checks

```bash
WORKER_TOKEN=test python scripts/monitor_supervisor_observability.py --simulate --since-minutes 60
```

### Save reports

```bash
python scripts/monitor_supervisor_observability.py --simulate \
  --output-json /tmp/supervisor-monitor.json \
  --output-md /tmp/supervisor-monitor.md
```

### CI/gate mode (exit 1 on critical)

```bash
python scripts/monitor_supervisor_observability.py --simulate --fail-on-critical
```

### With specific journald unit

```bash
python scripts/monitor_supervisor_observability.py --journal-unit openclaw-dispatcher.service
```

## 3. Recommendation Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **PASS_MONITORING** | All sources healthy, simulation clean. | Safe to continue. No action needed. |
| **WATCH** | No events found or some sources unavailable. | Expected during low/no traffic. Re-check later. Not a failure. |
| **INVESTIGATE** | Supervisor failure lines, high task failure rate, or simulation check failed. | Review manually. Check dispatcher logs and recent changes. |
| **ROLLBACK_RECOMMENDED** | Critical condition detected. | Do NOT proceed with further activation. Evaluate rollback per `docs/75` section 9. Do NOT auto-rollback — human decision required. |

## 4. Critical Triggers (aligned with docs/75)

These conditions produce **ROLLBACK_RECOMMENDED**:

| Condition | Source | What it means |
|-----------|--------|---------------|
| `should_block=True` in resolution event | Simulation | The supervisor resolver is returning block signals — this must never affect dispatch. |
| Non-improvement team event | Simulation | Supervisor observability is firing for teams other than `improvement` — gate violation. |
| Raw text leakage suspected | Simulation | User/task text found in event records — privacy violation. |

## 5. Example Output

```
# Supervisor Observability Monitoring Report

**Recommendation: PASS_MONITORING**

- Generated: 2026-04-20T17:00:00+00:00
- Window: 60 minutes

## Sources

### Journal
- Available: True
- Lines scanned: 842
- `supervisor_observability`: 3
- `supervisor_observability_failed`: 0

### Ops Log
- Available: True
- Events in window: 150
- Completed: 145, Failed: 3, Blocked: 2
- Improvement team events: 4

### Structured Supervisor Events (Phase 6A)
- Available: True
- Events in window: 3
- By event_type: supervisor.ambiguity_signal=2, supervisor.resolution=1
- By outcome: ambiguous=2, unresolved=1
- By severity: info=3
- By team: improvement=3
- Latest event: 2026-04-20T16:58:11+00:00

### Simulation
- Available: True
- [PASS] ambiguity_detection_ambiguous: is_ambiguous=True
- [PASS] ambiguity_detection_concrete: is_ambiguous=False
- [PASS] build_ambiguity_event: event_type=supervisor.ambiguity_signal, outcome=ambiguous
- [PASS] build_resolution_event: outcome=unresolved, severity=info
- [PASS] build_noop_event: outcome=noop
- [PASS] sentinel_text_leakage: no leakage

## Safety Flags

- [ok] supervisor_failure_lines: 0
- [ok] should_block_true_count: 0
- [ok] non_improvement_event_count: 0
- [ok] raw_text_leakage_suspected_count: 0
- [ok] malformed_event_count: 0
- [ok] error_event_count: 0

## Structured Telemetry Status

Structured supervisor observability events are persisted to `ops_log.jsonl`
by `OpsLogger.supervisor_event()` (Phase 6A). The monitoring script reads
them directly; the dispatcher logging formatter gap noted in PR #242 no
longer blocks production visibility of event_type, outcome, team, or
severity. The journald presence signal remains consumed as a secondary
source for continuity.
```

## 6. Structured Supervisor Telemetry (Phase 6A — closed gap)

Phase 6A resolves the previous formatter-gap limitation operationally. The dispatcher logging format (`dispatcher/service.py:38`) still does not serialize `extra` fields — that is unchanged by design to avoid touching the worker loop logging. Instead, `_log_supervisor_event()` now performs dual-channel delivery:

1. **Presence signal (unchanged)**: `logger.info("supervisor_observability", extra={"supervisor_event": record})`. Journald keeps counting the bare string marker for continuity with PR #242.
2. **Structured persistence (Phase 6A)**: `OpsLogger.supervisor_event(record)` writes a JSONL line to `~/.config/umbral/ops_log.jsonl` with:

```json
{
  "ts": "2026-04-20T17:00:00Z",
  "event": "supervisor.ambiguity_signal",
  "event_type": "supervisor.ambiguity_signal",
  "team": "improvement",
  "task_id": "...",
  "task_type": "general",
  "outcome": "ambiguous",
  "severity": "info",
  "fields": { "is_ambiguous": true, "reason": "positive_keyword_match", ... }
}
```

### Safety properties (preserved end to end)

- Only keys from `_SAFE_SUPERVISOR_FIELD_KEYS` in `infra/ops_logger.py` are persisted under `fields`. Free-text keys (`text`, `prompt`, `original_request`, `query`, `question`) are **dropped**, not sanitized, so they can never reach disk.
- `event_type` must start with `supervisor.`; any other record sent to the sink is silently rejected. This keeps the sink scoped and prevents accidental misuse.
- The sink call is wrapped in a defensive `try/except` inside `_log_supervisor_event()`. OpsLogger failure never blocks dispatch.
- `should_block=True` is **persisted** so it is auditable but **never enforced**: routing remains unchanged.
- Improvement-only and ambiguous-only gates from PR #241 are upstream of the sink call; non-improvement and concrete tasks never reach it.

### What the monitor reads

`parse_supervisor_events()` scans `ops_log.jsonl` for records whose `event` starts with `supervisor.`, filters by `since`, and aggregates counts by `event_type`, `outcome`, `severity`, and `team`. It applies the same safety checks as simulation (`should_block=True`, non-improvement team, raw text / sentinel leakage) and feeds them into the recommendation engine. The recommendation can now reach **PASS_MONITORING** on the strength of structured events alone, without relying on simulation.

### Limitation downgrade

The "Known Limitation" block formerly documented here is resolved at the monitoring layer. A future refactor of `dispatcher/service.py` may still switch to a JSON formatter for extra fields, but it is no longer a prerequisite for production observability of supervisor events.

## 7. Data Sources

| Source | What it provides | Status |
|--------|-----------------|--------|
| **journald** | Presence of `supervisor_observability` lines, failure lines | Secondary signal (formatter-agnostic presence) |
| **ops_log.jsonl — task lifecycle** | Task lifecycle (completed/failed/blocked), team breakdown | Primary dispatch health |
| **ops_log.jsonl — structured supervisor events** (Phase 6A) | `event_type`, `outcome`, `team`, `severity`, sanitized `fields` | Primary supervisor observability source |
| **Simulation** (`--simulate`) | Full structured event verification against building blocks | Local sanity check, not production traffic |

## 8. Relationship to Previous Documents

| Document | Relationship |
|----------|-------------|
| `docs/71` (Supervisor Routing Contract) | Defines what supervisor routing means. This tool monitors the first wiring slice. |
| `docs/73` (Supervisor Resolution Contract) | Defines safety rules. This tool checks them via simulation and via structured events. |
| `docs/75` (Activation Playbook) | Defines 24h monitoring window, rollback triggers, and metrics. This tool implements that monitoring with structured telemetry from Phase 6A. |
| `dispatcher/router.py` | Contains `_emit_supervisor_observability()` and `_log_supervisor_event()`. This tool reads `ops_log.jsonl` written by the sink; it does NOT modify the router. |
| `infra/ops_logger.py` | Hosts `OpsLogger.supervisor_event()` — the Phase 6A structured sink with whitelist enforcement. |
