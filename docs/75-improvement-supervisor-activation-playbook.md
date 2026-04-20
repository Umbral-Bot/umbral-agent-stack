# Improvement Supervisor Activation Playbook

> **Status: Design/ops document only.** This playbook does not change runtime behavior, does not activate any agent, and does not modify dispatcher routing. No code, config, or OpenClaw changes are included. David approval is required before any runtime activation.

## 1. Purpose

This document is an operational playbook for the future activation of `improvement-supervisor` runtime wiring. It converts the passive Phase 5 foundation (PRs #229–#239) into an executable, auditable plan for the Cursor Opus 4.7 architecture slice.

It answers:

- What conditions must be met before activating.
- What exact changes the runtime slice would make.
- What smoke tests to run before, during, and after.
- What metrics to monitor.
- What signals force rollback.
- How to revert without breaking dispatch.
- What is explicitly out of scope.

**This document does not activate anything.** It prepares the path so activation can be safe, observable, and reversible.

## 2. Current State

| Component | File | Status |
|---|---|---|
| Supervisor registry | `config/supervisors.yaml` | Exists. `improvement.status = "design_only"`. Passive. |
| Pure resolver | `dispatcher/supervisor_resolution.py` | Exists. `resolve_supervisor()` + `validate_supervisor_config_consistency()`. Not imported by runtime. |
| Ambiguity detector | `dispatcher/ambiguity_signal.py` | Exists. `detect_ambiguity_signal()`. 7 keyword families. Not imported by runtime. |
| Observability builders | `dispatcher/supervisor_observability.py` | Exists. 4 event types. JSON-serializable. Not imported by runtime. |
| Phase 5 tests | `tests/test_supervisor_*.py` (5 files) | 100 tests, all passing. |
| Regression tests | `tests/test_dispatcher.py`, `test_task_routing.py`, `test_intent_classifier.py` | 72 tests, all passing. |
| ROLE.md | `openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md` | Design-only contract. No runtime agent. |
| OpenClaw registration | `~/.openclaw/openclaw.json` | `improvement-supervisor` NOT present. |
| `TeamRouter` wiring | `dispatcher/router.py` | No supervisor imports, no supervisor logic. |
| `supervisor_hint` | Envelope schema | Does NOT exist. Only referenced in docs and invariance tests asserting absence. |
| Runtime telemetry | Structured logs | No supervisor events emitted. Event builders exist but have no consumer. |

## 3. Activation Goal

The minimum first activation is a **non-blocking observability-only path** for the `improvement` team:

- Call `detect_ambiguity_signal()` for `team=improvement` tasks after team classification.
- Call `resolve_supervisor()` only for ambiguous improvement tasks.
- Build observability events using existing event builders.
- Emit structured log records via existing safe logger.
- **Do not change the routing result.** Direct dispatch remains default for all tasks.
- **Do not enqueue supervisor tasks.** No delegation, no automatic execution.
- **Do not call OpenClaw agents.** No supervisor invocation.
- All failures fall back silently to current behavior.

### First activation must NOT

- Execute code via supervisor.
- Create Linear issues automatically.
- Create or update Notion pages automatically.
- Call OpenClaw `improvement-supervisor` automatically.
- Change task owner or routing target.
- Intercept or delay task dispatch.
- Block any dispatch path.
- Affect non-improvement teams.

## 4. Preconditions / Gates

All gates must be satisfied before any runtime activation PR is merged.

| # | Gate | Required Evidence | Owner | Status |
|---|---|---|---|---|
| 1 | David explicit approval | Written approval (Notion, Telegram, or Linear comment) | David | Pending |
| 2 | Phase 5 passive tests green | `100/100` on `tests/test_supervisor_*.py` | Copilot/Rick | Verified post-#239 |
| 3 | Regression tests green | `72/72` on dispatcher + routing + classifier tests | Copilot/Rick | Verified post-#239 |
| 4 | Config validation 0 errors | `validate_supervisor_config_consistency()` returns 0 errors | Copilot/Rick | Verified post-#239 |
| 5 | `improvement` remains `design_only` | `config/supervisors.yaml` status unchanged until activation PR | Copilot/Rick | Current |
| 6 | OpenClaw agent exists only if required | `improvement-supervisor` in `openclaw.json` only if activation slice needs it | Cursor Opus 4.7 | Not needed for observability-only |
| 7 | Rollback commit identified | Pre-merge SHA documented; revert command prepared | Copilot/Rick | At PR time |
| 8 | Observability event schema reviewed | 7-key schema stable; no raw text leakage confirmed | Copilot/Rick | Verified post-#239 |
| 9 | No raw task text in events | `TestNoTextLeakage` tests passing | Copilot/Rick | Verified post-#239 |
| 10 | Smoke tests defined before merge | Smoke test matrix from section 8 reviewed and runnable | Copilot/Rick | This document |

## 5. Proposed Runtime Slice Scope

This section describes the **future** Cursor Opus 4.7 runtime slice. It is a proposal, not a commitment. Multiple implementation approaches are valid.

### Potential files touched

| File | Potential change | Notes |
|---|---|---|
| `dispatcher/router.py` | Add non-blocking observability call after `dispatch()` | Call ambiguity signal + resolver, emit event, do not change routing result |
| `dispatcher/intent_classifier.py` | Possibly add `supervisor_hint` to envelope metadata | Only if envelope metadata is the chosen signaling mechanism |
| `config/supervisors.yaml` | Change `improvement.status` from `design_only` to `active` | Only after observability-only wiring is proven safe |
| `tests/` | New tests for runtime wiring | Verify dispatch unchanged, events emitted, no blocking |

### Minimum scope (observability-only)

```
TaskEnvelope arrives at TeamRouter.dispatch()
  → Existing logic runs (validate team, check VM, enqueue/block)
  → AFTER dispatch result is determined (not before):
      1. If team == "improvement":
         a. Call detect_ambiguity_signal(text, team=team, task=task, task_type=task_type)
         b. If ambiguous: call resolve_supervisor("improvement", teams_config, registry)
         c. Build observability event(s)
         d. Emit to structured logger
      2. Return original dispatch result unchanged
```

### What this does NOT do

- Does not change the `dispatch()` return value.
- Does not add `supervisor_hint` to envelope (unless chosen as the signaling mechanism).
- Does not enqueue supervisor tasks.
- Does not call OpenClaw agents.
- Does not block or delay dispatch.

## 6. Non-Goals for First Activation

These are explicitly **out of scope** for the first runtime activation:

1. **No automatic delegation.** Supervisor does not hand off tasks to agents.
2. **No automatic Linear issue creation.** No `linear.create_issue` from supervisor path.
3. **No automatic Notion updates.** No `notion.add_comment` from supervisor path.
4. **No closed OODA automation.** The loop from `docs/74` remains manual.
5. **No supervisor-to-delivery execution.** No automatic handoffs to `rick-delivery`.
6. **No agent governance replacement.** `agent-governance` remains a separate function.
7. **No support for marketing/advisory supervisors.** First activation is `improvement`-only.
8. **No blocking dispatch.** `should_block` must always be `False`.
9. **No raw user text in observability.** Events use structured fields only.
10. **No external network calls from routing path.** No HTTP, no webhooks, no OpenClaw calls.
11. **No `openclaw.json` changes.** No agent registration for observability-only.
12. **No VM dependency.** Supervisor observability runs on VPS only.

## 7. Rollout Plan

### Phase A: Pre-merge validation

Before merging the runtime wiring PR:

```bash
# 1. Phase 5 passive tests
WORKER_TOKEN=test .venv/bin/python -m pytest \
  tests/test_supervisor_resolution.py \
  tests/test_supervisor_invariance.py \
  tests/test_ambiguity_signal.py \
  tests/test_supervisor_config_consistency.py \
  tests/test_supervisor_observability.py -v

# 2. Regression tests
WORKER_TOKEN=test .venv/bin/python -m pytest \
  tests/test_intent_classifier.py \
  tests/test_dispatcher.py \
  tests/test_task_routing.py -v

# 3. Config validation
WORKER_TOKEN=test .venv/bin/python -c "
from dispatcher.supervisor_resolution import load_supervisor_registry, validate_supervisor_config_consistency
from dispatcher.team_config import get_team_capabilities
issues = validate_supervisor_config_consistency({'teams': get_team_capabilities()}, load_supervisor_registry())
errors = [i for i in issues if i.severity == 'error']
assert len(errors) == 0, f'Config errors: {errors}'
print(f'Config valid: {len(errors)} errors, {len(issues) - len(errors)} warnings')
"

# 4. OpenClaw agent state
python3 -c "
import json
data = json.load(open('$HOME/.openclaw/openclaw.json'))
assert 'improvement-supervisor' not in json.dumps(data), 'improvement-supervisor found in openclaw.json!'
print('OpenClaw: improvement-supervisor NOT registered (expected)')
"

# 5. Runtime log baseline
journalctl --user -u openclaw-dispatcher.service --since "1 hour ago" --no-pager | tail -20
```

### Phase B: Merge runtime wiring

- Merge the runtime PR with observability-only behavior.
- `config/supervisors.yaml` should remain `design_only` initially if possible.
- If `status: "active"` is required for event emission, change it only after observability-only wiring is proven.
- Restart dispatcher if runtime code path changed:

```bash
systemctl --user restart openclaw-dispatcher.service
systemctl --user status openclaw-dispatcher.service --no-pager
```

### Phase C: Post-merge smoke tests

Run the smoke test matrix from section 8 against the live system.

```bash
# Verify dispatcher health
curl -s "http://127.0.0.1:8088/health" -H "Authorization: Bearer $WORKER_TOKEN" | python3 -m json.tool

# Run Phase 5 + regression tests on deployed code
WORKER_TOKEN=test .venv/bin/python -m pytest \
  tests/test_supervisor_resolution.py \
  tests/test_supervisor_invariance.py \
  tests/test_ambiguity_signal.py \
  tests/test_supervisor_config_consistency.py \
  tests/test_supervisor_observability.py \
  tests/test_dispatcher.py \
  tests/test_task_routing.py -v

# Check logs for unexpected supervisor events
journalctl --user -u openclaw-dispatcher.service --since "10 minutes ago" --no-pager | grep -i supervisor || echo "No supervisor log entries (expected for observability-only)"
```

### Phase D: Monitoring window (24 hours)

- Collect dispatch success/failure rates.
- Check no increase in blocked tasks.
- Check no unexpected supervisor events for non-improvement teams.
- Check no raw text in structured logs.
- Check dispatcher memory/CPU are stable.

```bash
# Periodic checks during monitoring window
redis-cli llen umbral:tasks:pending 2>/dev/null
redis-cli llen umbral:tasks:blocked 2>/dev/null
journalctl --user -u openclaw-dispatcher.service --since "1 hour ago" --no-pager | grep -c "supervisor" || echo "0"
systemctl --user status openclaw-dispatcher.service --no-pager | head -10
```

### Phase E: Decision

After the 24h monitoring window, decide:

| Outcome | Action |
|---|---|
| **Keep** | No anomalies. Supervisor events emitted correctly. Dispatch unchanged. Proceed to next activation stage. |
| **Rollback** | Any rollback trigger from section 9 fired. Execute rollback plan. |
| **Investigate** | Ambiguous signals. Extend monitoring window. Do not proceed until resolved. |

## 8. Smoke Test Matrix

| # | Case | Input | Expected routing | Expected supervisor behavior | Expected event |
|---|---|---|---|---|---|
| 1 | Non-improvement task | Delivery task to `marketing` | Unchanged | None | `supervisor.noop` or none |
| 2 | Concrete improvement task | `system.ooda_report` | Unchanged | None — explicit handler | `supervisor.ambiguity_signal` with `outcome=not_ambiguous` |
| 3 | Ambiguous improvement task | "revisa la salud del sistema" | Unchanged | Non-blocking signal detected | `supervisor.ambiguity_signal` with `outcome=ambiguous` + `supervisor.resolution` with `outcome=unresolved` |
| 4 | Resolver `design_only` | Current `config/supervisors.yaml` | Unchanged | Unresolved, fallback direct | `supervisor.resolution` with `reason=status_design_only` |
| 5 | Registry missing | Synthetic: remove registry | Unchanged | Fallback direct | `supervisor.resolution` with `reason=registry_entry_missing` |
| 6 | OpenClaw unavailable | Future: agent registered but down | Unchanged | Fallback direct | `supervisor.resolution` with `reason=target_unavailable` |
| 7 | Invalid registry YAML | Synthetic: corrupt file | Unchanged | Fallback direct, log warning | `supervisor.resolution` with warning severity |
| 8 | Non-improvement ambiguous text | "revisa la salud" to `marketing` | Unchanged | None — wrong team | `supervisor.noop` or none |
| 9 | Empty/whitespace input | "" or "   " | Unchanged | None — safety gate | None or `supervisor.noop` |
| 10 | Resolver exception | Synthetic: force error in resolver | Unchanged — exception caught | Fallback direct | Error-level event or none |

**Pattern:** The "Expected routing" column is always "Unchanged." Supervisor observability never alters dispatch.

## 9. Rollback Plan

### Immediate rollback triggers

Any of these signals require immediate rollback:

| # | Trigger | Severity |
|---|---|---|
| 1 | Dispatch blocked unexpectedly (`should_block=True` observed) | Critical |
| 2 | Increase in task failures correlated with merge | Critical |
| 3 | Supervisor event emitted for non-improvement teams | High |
| 4 | Raw task text appears in structured logs | High |
| 5 | Resolver exception reaches dispatch path (uncaught) | High |
| 6 | Routing latency increase > 100ms p95 vs baseline | Medium |
| 7 | Any OpenClaw supervisor call happens unintentionally | Critical |
| 8 | Dispatcher crash or restart loop after merge | Critical |
| 9 | `should_block > 0` in any code path | Critical |
| 10 | Blocked task count increases without VM being down | High |

### Rollback steps

```bash
# 1. Identify the runtime merge commit
RUNTIME_MERGE_SHA="<runtime-merge-sha>"

# 2. Revert the merge commit
git revert $RUNTIME_MERGE_SHA
git push origin main

# 3. Restore config/supervisors.yaml to design_only if changed
# (should already be design_only after revert)
grep "status:" config/supervisors.yaml

# 4. Verify no supervisor imports in runtime files
grep -R "supervisor_observability\|ambiguity_signal\|resolve_supervisor" \
  dispatcher/router.py dispatcher/service.py dispatcher/intent_classifier.py \
  || echo "CLEAN: no runtime wiring"

# 5. Run regression tests
WORKER_TOKEN=test .venv/bin/python -m pytest \
  tests/test_dispatcher.py \
  tests/test_task_routing.py \
  tests/test_supervisor_invariance.py -v

# 6. Restart dispatcher
systemctl --user restart openclaw-dispatcher.service
systemctl --user status openclaw-dispatcher.service --no-pager

# 7. Verify health
curl -s "http://127.0.0.1:8088/health" -H "Authorization: Bearer $WORKER_TOKEN" | python3 -m json.tool
redis-cli ping

# 8. Post rollback note
# Update Linear UMB-173 with rollback reason and evidence
# Update Notion Phase 5 page with rollback note
```

### Post-rollback verification

- All existing tests pass.
- Dispatcher health endpoint returns `ok: true`.
- Redis responds to `ping`.
- No supervisor-related log entries in dispatcher journal.
- `config/supervisors.yaml` shows `status: "design_only"`.
- `improvement-supervisor` not in `openclaw.json`.

## 10. Monitoring Metrics

### Metrics to collect

| Metric | Source | Baseline |
|---|---|---|
| Dispatch count (total) | Redis queue stats | Current rate |
| Dispatch failure rate | Dispatcher logs | Current rate |
| Blocked tasks count | Redis `umbral:tasks:blocked` | Current count |
| Supervisor event count by type | Structured logs | 0 (new metric) |
| Supervisor events by team | Structured logs | 0 (new metric) |
| Ambiguity true/false ratio | Structured logs | 0 (new metric) |
| Resolution outcomes | Structured logs | 0 (new metric) |
| `fallback_used` count | Structured logs | 0 (new metric) |
| `should_block` count | Structured logs | Must be 0 |
| Routing latency (p50, p95) | Dispatcher timing | Current baseline |
| Raw text leakage | Log audit | Must be 0 |

### Thresholds

| Condition | Action |
|---|---|
| `should_block > 0` in any event | **Immediate rollback** |
| Supervisor events for non-improvement teams | **Rollback or hotfix** |
| Raw task text in structured logs | **Immediate rollback** |
| Dispatch failure rate +5pp vs baseline | **Investigate, rollback if correlated** |
| Routing latency p95 increase > 100ms | **Investigate** |
| Blocked task count increase (VM is up) | **Investigate, rollback if correlated** |
| Ambiguity true ratio > 80% | **Investigate** (detector may be too aggressive) |
| Ambiguity true ratio < 5% | **Investigate** (detector may be too conservative) |

## 11. Ownership and Handoff

| Role | Responsibility |
|---|---|
| **David** | Approves activation. Decides rollback if business risk. Final go/no-go authority. |
| **Cursor Opus 4.7** | Owns runtime architecture and wiring implementation. Designs the dispatch integration, writes the runtime PR. |
| **Copilot / Rick** | Owns tests, smoke validation, config verification, Linear/Notion reporting. Executes pre-merge and post-merge validation. Monitors during 24h window. |
| **Rick QA** | Validates no-regression. Audits structured logs for text leakage. Confirms rollback works. |

### Handoff sequence

1. David approves activation (gate #1).
2. Copilot/Rick verifies all pre-merge gates (section 4).
3. Cursor Opus 4.7 implements runtime wiring PR.
4. Copilot/Rick reviews PR against this playbook.
5. Copilot/Rick runs pre-merge validation (Phase A).
6. PR is merged.
7. Copilot/Rick runs post-merge smoke (Phase C).
8. Copilot/Rick monitors during 24h window (Phase D).
9. David + Copilot/Rick decide: keep, rollback, or investigate (Phase E).
10. Copilot/Rick updates Linear and Notion with outcome.

## 12. Decision Record

| Date | Decision | Owner | Context |
|---|---|---|---|
| 2026-04-20 | Phase 5 passive foundation complete. Runtime activation: NO. | Rick | Readiness report post-PR #239. 100 Phase 5 tests + 72 regression tests green. |
| 2026-04-20 | Approved next action: docs-only activation playbook. | David | This document. No runtime changes. |
| Pending | Runtime wiring activation. | David | Requires explicit David approval. Cursor Opus 4.7 implements. |
| Pending | `improvement-supervisor` OpenClaw registration. | David | Only after non-blocking wiring is proven safe. |

## 13. Final Recommendation

1. **Ready for architecture slice, not runtime activation.** The passive foundation is complete and tested. The next step is runtime wiring design by Cursor Opus 4.7.

2. **First runtime activation must be observability-only.** Non-blocking, improvement-team-only, no delegation, no automatic execution. Emit events to structured logs; do not change dispatch behavior.

3. **Do not register `improvement-supervisor` in OpenClaw until non-blocking wiring is proven.** The observability-only slice does not need a registered agent. Registration should happen in a subsequent slice after observability proves safe.

4. **Do not change `config/supervisors.yaml` status to `active` until observability-only wiring passes the 24h monitoring window.** Keep `design_only` during initial wiring. Change status only when the resolver is proven non-blocking in production.

5. **Next runtime work should go to Cursor Opus 4.7.** The proposed scope is: `supervisor_hint` envelope field + `TeamRouter` non-blocking observability-only wiring. But only after explicit David approval.

6. **Alternative safer slice before Cursor:** A docs-only activation sequence document (step-by-step commands for the day of activation) can be prepared by Copilot without any runtime risk.

## 14. Relationship to Previous Docs

| Document | Relationship |
|---|---|
| [`docs/71`](71-supervisor-routing-contract.md) | Defines supervisor routing contract and implementation gates. This playbook operationalizes gates #1–#7. |
| [`docs/72`](72-ambiguous-improvement-task-detection.md) | Defines ambiguity detection rules. This playbook assumes `detect_ambiguity_signal()` (PR #237) implements them. |
| [`docs/73`](73-supervisor-resolution-contract.md) | Defines resolution contract and safety rules. This playbook's rollback triggers enforce those safety rules at runtime. |
| [`docs/74`](74-closed-ooda-loop-contract.md) | Defines closed OODA loop. This playbook explicitly defers loop automation as a non-goal for first activation. |
| [`ROLE.md`](../openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md) | Defines supervisor identity and activation conditions. This playbook is the operational counterpart. |

## 15. Explicit Scope Boundary

If implementing any part of this playbook requires changes to:

- `dispatcher/router.py`, `dispatcher/service.py`, `dispatcher/intent_classifier.py`
- `worker/` directory
- `config/teams.yaml`, `config/supervisors.yaml`, `openclaw.json`
- OpenClaw agent registration

**Stop.** Those changes belong to the Cursor Opus 4.7 runtime wiring slice, not to this playbook. This document is design/ops documentation only.
