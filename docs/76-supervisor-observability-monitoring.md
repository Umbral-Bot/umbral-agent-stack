# Supervisor Observability Monitoring

> Runbook for the Phase 5 supervisor observability monitoring tool. Use during the 24h monitoring window (per `docs/75`) and for ongoing health checks of the supervisor observability wiring.

## 1. Purpose

After PR #241 merged the first runtime wiring slice (`_emit_supervisor_observability()` in `dispatcher/router.py`), a 24h monitoring window is required before proceeding. This tool provides a reusable, local-only, non-blocking way to:

- Count supervisor observability log lines from journald.
- Analyze dispatch health from `ops_log.jsonl` (task completed/failed/blocked).
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

**Recommendation: WATCH**

- Generated: 2026-04-20T17:00:00+00:00
- Window: 60 minutes

## Reasons

- [WATCH] No supervisor_observability lines in journal (no traffic or formatter gap)

## Sources

### Journal
- Available: True
- Lines scanned: 0
- `supervisor_observability`: 0

### Ops Log
- Available: True
- Events in window: 150
- Completed: 145, Failed: 3, Blocked: 2
- Improvement team events: 0

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

## Known Limitation

The dispatcher logging format (`%(asctime)s [%(levelname)s] %(name)s: %(message)s`)
does NOT serialize `extra` fields. `supervisor_event` dicts emitted by
`_log_supervisor_event()` do not appear in stdout/journald output.
Structured event data is only available via `--simulate`.
Next improvement: configure JSON logging sink or OpsLogger integration.
```

## 6. Known Limitation: Logging Format Gap

The dispatcher (`dispatcher/service.py:38`) uses:

```python
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
```

This format does **not** serialize `extra` fields. The `_log_supervisor_event()` method (`dispatcher/router.py:219-235`) passes the event dict via:

```python
logger.info("supervisor_observability", extra={"supervisor_event": record})
```

In journald/stdout, this produces only the bare string `"supervisor_observability"` — the structured `supervisor_event` dict is lost. The monitoring script can count these lines as a presence signal but cannot extract event_type, outcome, team, or severity from production logs.

**Structured event data is only available via `--simulate`**, which exercises the pure building blocks locally.

### Next Improvement

A future slice should add one of:

1. **JSON logging sink** — configure a `logging.Handler` that serializes `extra` fields to a JSON file.
2. **OpsLogger integration** — emit supervisor events via `infra/ops_logger.py` alongside existing task lifecycle events.

Either approach would make structured supervisor event data available for production monitoring without changing the event emission code in `router.py`.

## 7. Data Sources

| Source | What it provides | Limitation |
|--------|-----------------|------------|
| **journald** | Presence of `supervisor_observability` lines, failure lines | No structured event data (formatter gap) |
| **ops_log.jsonl** | Task lifecycle (completed/failed/blocked), team breakdown | Does not contain supervisor observability events |
| **Simulation** (`--simulate`) | Full structured event verification against building blocks | Local-only, does not reflect production traffic |

## 8. Relationship to Previous Documents

| Document | Relationship |
|----------|-------------|
| `docs/71` (Supervisor Routing Contract) | Defines what supervisor routing means. This tool monitors the first wiring slice. |
| `docs/73` (Supervisor Resolution Contract) | Defines safety rules. This tool checks them via simulation. |
| `docs/75` (Activation Playbook) | Defines 24h monitoring window, rollback triggers, and metrics. This tool implements that monitoring. |
| `dispatcher/router.py` | Contains `_emit_supervisor_observability()`. This tool reads its output but does NOT modify it. |
| `infra/ops_logger.py` | Existing structured log system. Future integration target. |
