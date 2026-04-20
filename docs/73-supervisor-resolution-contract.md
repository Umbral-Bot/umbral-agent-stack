# Supervisor Resolution Contract

> Defines how the `supervisor` string in `config/teams.yaml` should be mapped to an invocable destination (agent, workflow, or manual owner) when supervisor routing is eventually implemented. Since PR #234, a passive registry (`config/supervisors.yaml`) and pure resolver (`dispatcher/supervisor_resolution.py`) exist, but they are **not connected to runtime routing**. No dispatcher behavior changes, no runtime activation, no OpenClaw agent, no `supervisor_hint` in envelope.

## 1. Purpose

The [supervisor routing contract](71-supervisor-routing-contract.md) lists "supervisor resolution" as implementation gate #1: a mechanism to map the `supervisor` string to an invocable agent ID or workflow. Today that string is a human label with no resolution path. This document defines:

- What "resolving a supervisor" means.
- What types of targets a supervisor can resolve to.
- The registry shape (now implemented as a passive file).
- A pure resolver function (now implemented, not connected to runtime).
- Safety rules that prevent premature or unsafe activation.
- A decision table with resolution scenarios.

## 2. Current state (2026-04-20)

| Component | Status |
|-----------|--------|
| `config/teams.yaml` | `supervisor: "Mejora Continua Supervisor"` for `improvement`. Human label, no ID. Unchanged. |
| `dispatcher/team_config.py` | Loads `supervisor` as a string. Returns it in `get_team_capabilities()`. Unchanged. |
| `dispatcher/router.py` | `dispatch()` never reads the `supervisor` field or the resolver. `list_teams()` returns supervisor as metadata. Unchanged. |
| `dispatcher/service.py` | Worker loop never reads `supervisor` or the resolver. Unchanged. |
| `config/supervisors.yaml` | **Exists (PR #234).** Passive registry with `improvement` entry at `status: "design_only"`. Not loaded by any runtime path. |
| `dispatcher/supervisor_resolution.py` | **Exists (PR #234).** Pure resolver: `resolve_supervisor()` maps team key → registry entry. Not imported by router, service, or classifier. |
| `tests/test_supervisor_resolution.py` | **Exists (PR #234).** 15 tests covering resolution, fallback, safety rules, registry loading, and performance. |
| String→agent mapping | Implemented as pure lookup by team key in `dispatcher/supervisor_resolution.py`. Not consumed by runtime. |
| `improvement-supervisor` in `openclaw.json` | Does not exist. No agent entry, no workspace. |
| `improvement-supervisor` ROLE.md | Exists as design-only contract (PR #229). |

## 3. Resolution target types

When a supervisor string is resolved, it must map to one of these target types:

| Type | Description | Example |
|------|-------------|---------|
| `openclaw_agent` | An OpenClaw runtime agent with workspace and model. The supervisor string maps to an agent ID that can receive tasks via `openclaw agent --agent <id>`. | `improvement-supervisor` (future) |
| `worker_task` | A Worker task that can be dispatched via `umbral_worker_run`. The supervisor string maps to a task name. | `improvement.supervise` (hypothetical) |
| `external_workflow` | An external automation (n8n, Make, Linear automation) that can be triggered via webhook or API. | n8n workflow for improvement triage (hypothetical) |
| `manual_owner` | A human (David) who receives the task for manual coordination. No automated agent. | David reviews improvement backlog manually. |
| `none` | No resolvable supervisor. The team has no coordinator. Direct routing applies. | `lab` team (`supervisor: null`). |

## 4. Registry shape

The registry file exists at `config/supervisors.yaml` since PR #234. It is **passive**: no runtime path loads it for dispatch. The current file contains only the `improvement` team entry. The full conceptual shape for all teams is shown below for reference.

```yaml
# config/supervisors.yaml (improvement entry is real; others are conceptual for future use)
supervisors:
  improvement:
    label: "Mejora Continua Supervisor"
    type: "openclaw_agent"
    target: "improvement-supervisor"
    status: "design_only"       # design_only | active | disabled
    fallback: "direct"          # direct | manual | disabled
  marketing:
    label: "Marketing Supervisor"
    type: "none"
    target: null
    status: "design_only"
    fallback: "direct"
  advisory:
    label: "Asesoría Personal Supervisor"
    type: "none"
    target: null
    status: "design_only"
    fallback: "direct"
  lab:
    label: null
    type: "none"
    target: null
    status: "disabled"
    fallback: "direct"
  system:
    label: null
    type: "none"
    target: null
    status: "disabled"
    fallback: "direct"
```

### Field semantics

| Field | Meaning |
|-------|---------|
| `label` | Human-readable name from `teams.yaml`. Informational only — never used for resolution matching. |
| `type` | Resolution target type (see section 3). |
| `target` | The invocable destination: agent ID, task name, webhook URL, or `null`. |
| `status` | Lifecycle state: `design_only` (contract exists, no runtime), `active` (resolvable and invocable), `disabled` (explicitly turned off). |
| `fallback` | What happens when resolution fails: `direct` (route as today), `manual` (escalate to David), `disabled` (supervisor feature off for this team). |

### Where this registry lives

The passive implementation uses `config/supervisors.yaml` as a standalone file. The pure resolver in `dispatcher/supervisor_resolution.py` loads it via `load_supervisor_registry()`. Future runtime activation may revisit whether resolution belongs inline in `teams.yaml` or in `openclaw.json`, but for the passive phase `config/supervisors.yaml` is the canonical location.

## 5. Resolution flow

### Current (passive, PR #234)

A pure resolver function exists at `dispatcher/supervisor_resolution.py`:

```
resolve_supervisor(team, teams_config=..., registry=..., target_available=None)
  → Reads registry for team key (never matches on human label)
  → Check status:
      - "disabled" or "design_only" → return unresolved, fallback direct
      - "active" → check target_available signal
  → If target_available is True → return resolved, should_block=False
  → If target_available is False or None → return unresolved/not_ready, fallback direct
  → Every path returns should_block=False
```

This function is **not called by any runtime code**. It is only used by `tests/test_supervisor_resolution.py`. No dispatcher, router, or service imports it.

### Future (runtime integration, not yet implemented)

```
Task arrives with team="improvement", supervisor_hint=true
  → Resolver reads registry for team "improvement"
  → Check status:
      - "disabled" or "design_only" → skip, route direct
      - "active" → proceed to resolution
  → Check type:
      - "openclaw_agent" → verify agent exists and is reachable
      - "worker_task" → verify task is registered
      - "external_workflow" → verify endpoint is configured
      - "manual_owner" → create notification for David
      - "none" → route direct
  → If target is reachable → deliver task to supervisor
  → If target is NOT reachable → apply fallback:
      - "direct" → route as today (zero regression)
      - "manual" → notify David
      - "disabled" → drop supervisor hint, route direct
```

Runtime integration requires `supervisor_hint` in the envelope, resolver wired into dispatch, and David approval. None of these exist today.

### Key properties

- **Resolution is a lookup, not inference.** The registry maps team→target explicitly. No string matching against human labels.
- **Resolution failure is not a dispatch failure.** If the supervisor can't be resolved, the task routes directly. Dispatch never blocks.
- **Resolution is checked once per task.** No retries, no polling, no async resolution.

## 6. Safety rules

These rules are **non-negotiable constraints** for any future implementation of supervisor resolution:

1. **No string matching against human labels.** The `label` field ("Mejora Continua Supervisor") is informational only. Resolution must use the explicit `target` field. Never attempt to fuzzy-match, normalize, or infer an agent ID from a human-readable label.

2. **No activation by presence of ROLE.md.** A ROLE.md file existing in `openclaw/workspace-agent-overrides/` does NOT mean the supervisor is active. Only the registry `status: "active"` field determines activation. ROLE.md is a design contract, not an activation signal.

3. **No activation by presence of supervisor in teams.yaml.** The `supervisor` field in `teams.yaml` being non-null does NOT trigger supervisor routing. The registry `status` must be explicitly `"active"`. Today all supervisors are `"design_only"` or `"disabled"`.

4. **No automatic fallback to orchestrator.** If a supervisor cannot be resolved, the task routes **directly** (as today) or to **manual** (David). It NEVER falls back to `rick-orchestrator`. The orchestrator manages cross-team work — it is not a catch-all for unresolved supervisors.

5. **No supervisor↔orchestrator loops.** A supervisor hands off to orchestrator when scope exceeds its team. Orchestrator does NOT hand back to the same supervisor for the same task. If orchestrator receives a task that originated from a supervisor escalation, it must not re-route it to that supervisor.

6. **Never block dispatch on failed resolution.** If the registry is missing, corrupted, unreachable, or the target agent is down, the task MUST still be dispatched via direct routing. Resolution failure is logged and monitored, but never causes a task to be rejected or blocked.

## 7. First application: `improvement` team

| Field | Value |
|-------|-------|
| Team | `improvement` |
| Label | `"Mejora Continua Supervisor"` |
| Type | `openclaw_agent` |
| Target | `improvement-supervisor` |
| Status | `design_only` (no runtime agent exists) |
| Fallback | `direct` |

### What must happen before `status` can become `active`

1. `improvement-supervisor` registered as an OpenClaw agent (workspace + `openclaw.json` entry + model assigned).
2. Agent is reachable via `openclaw agent --agent improvement-supervisor`.
3. Registry file created with `status: "active"`.
4. Fallback tested: if agent is unreachable, task routes direct.
5. David approves activation.

## 8. Decision table

| # | Input state | Resolution result | Fallback | Should block dispatch? |
|---|-------------|-------------------|----------|----------------------|
| 1 | Team `improvement`, registry has `status: active`, target `improvement-supervisor` reachable | Resolved to `improvement-supervisor` | N/A (success) | **No** |
| 2 | Team `improvement`, registry has `status: active`, target `improvement-supervisor` unreachable | Resolution failed | `direct` — route as today | **No** |
| 3 | Team `improvement`, registry has `status: design_only` | Skip resolution | `direct` — route as today | **No** |
| 4 | Team `improvement`, registry has `status: disabled` | Skip resolution | `direct` — route as today | **No** |
| 5 | Team `improvement`, registry file missing entirely | No registry to read | `direct` — route as today | **No** |
| 6 | Team `lab`, `supervisor: null` in teams.yaml | Type `none`, no target | `direct` — route as today | **No** |
| 7 | Team `marketing`, registry has `status: design_only`, type `none` | Skip resolution | `direct` — route as today | **No** |
| 8 | Team `improvement`, registry has `type: worker_task`, target `improvement.supervise`, task registered | Resolved to `improvement.supervise` | N/A (success) | **No** |
| 9 | Team `improvement`, registry has `type: external_workflow`, webhook URL invalid | Resolution failed (endpoint unreachable) | `direct` — route as today | **No** |
| 10 | Team `improvement`, registry has `type: manual_owner`, target `david` | Resolved to manual notification | N/A (success, David notified) | **No** |
| 11 | Team `improvement`, registry has `status: active`, target `improvement-supervisor` reachable, but `supervisor_hint: false` on envelope | No resolution attempted (hint not set) | Direct routing | **No** |
| 12 | Registry file corrupted (invalid YAML / missing fields) | Parse error caught | `direct` — route as today, log error | **No** |

**Pattern:** The answer to "Should block dispatch?" is always **No**. Resolution failure never blocks dispatch. This is the single most important safety property.

## 9. Implementation gates

Status after PR #234:

1. **Registry file exists.** Done (PR #234). `config/supervisors.yaml` with `improvement` entry at `status: "design_only"`. Loaded by `load_supervisor_registry()` in `dispatcher/supervisor_resolution.py`.
2. **Resolver function exists.** Done (PR #234). Pure function `resolve_supervisor()` returns `SupervisorResolution` with target + type + fallback + should_block. No side effects. Not connected to runtime.
3. **Fallback tested.** Done for resolver (PR #234). Tests cover cases #2, #5, #9, #12 from the decision table. Dispatcher-level fallback tests (proving dispatch is unchanged with registry present) are still pending before runtime wiring.
4. **No regression.** Done for focused suites (PR #234). 162 tests pass. Full runtime wiring regression (proving `TeamRouter.dispatch()` is unchanged) is still pending.
5. **Observability.** Partial (PR #234). `SupervisorResolution.to_log_fields()` provides stable fields for future logging. No runtime consumer emits these fields yet.
6. **David approval.** Pending. The first `status: "active"` entry requires explicit David go-ahead.

## 10. Non-goals

- **No runtime integration.** The resolver exists but is not called by `dispatcher/router.py`, `dispatcher/service.py`, or any runtime path.
- **No dispatcher routing changes.** `TeamRouter.dispatch()` is unchanged. No supervisor logic in the dispatch path.
- **No `supervisor_hint` in envelope.** The `TaskEnvelope` schema is unchanged. No ambiguity detection in the classifier.
- **No runtime supervisor activation.** All supervisors remain `design_only` or `disabled`. No `status: "active"` entry.
- **No new OpenClaw agent.** `improvement-supervisor` remains design-only. No workspace, no `openclaw.json` entry.
- **No healthcheck implementation.** The resolver accepts `target_available` as a parameter but does not perform real health checks.
- **No automatic invocation.** The resolver does not invoke agents, enqueue tasks, or call external workflows.
- **No changes to `config/teams.yaml`.** The existing schema is unchanged.
- **No changes to `dispatcher/intent_classifier.py` or `dispatcher/service.py`.** These files are untouched.

## 11. Relationship to previous docs

| Document | Relationship |
|----------|-------------|
| [`docs/71-supervisor-routing-contract.md`](71-supervisor-routing-contract.md) | Defines the overall routing contract. This doc satisfies its implementation gate #1: "A mechanism to map the supervisor string to an invocable agent ID or workflow." |
| [`docs/72-ambiguous-improvement-task-detection.md`](72-ambiguous-improvement-task-detection.md) | Defines when `supervisor_hint` should be set. This doc defines what happens after the hint is set: how the supervisor target is resolved. |
| [`improvement-supervisor ROLE.md`](../openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md) | Defines the supervisor's identity and scope. This doc defines how the system finds and invokes that supervisor. Safety rule #2 explicitly states that ROLE.md existence does not equal activation. |
| [`docs/70-agent-governance.md`](70-agent-governance.md) | Governance observes the agent ecosystem. Supervisor resolution is a dispatcher concern, not a governance concern. Governance may observe resolution failures as a friction signal. |
