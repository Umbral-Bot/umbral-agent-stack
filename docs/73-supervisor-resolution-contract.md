# Supervisor Resolution Contract

> Defines how the `supervisor` string in `config/teams.yaml` should be mapped to an invocable destination (agent, workflow, or manual owner) when supervisor routing is eventually implemented. This is a **design document** — no runtime, dispatcher, config, or worker changes are included. No registry file is created.

## 1. Purpose

The [supervisor routing contract](71-supervisor-routing-contract.md) lists "supervisor resolution" as implementation gate #1: a mechanism to map the `supervisor` string to an invocable agent ID or workflow. Today that string is a human label with no resolution path. This document defines:

- What "resolving a supervisor" means.
- What types of targets a supervisor can resolve to.
- A conceptual registry shape for future implementation.
- Safety rules that prevent premature or unsafe activation.
- A decision table with resolution scenarios.

## 2. Current state (2026-04-19)

| Component | Status |
|-----------|--------|
| `config/teams.yaml` | `supervisor: "Mejora Continua Supervisor"` for `improvement`. Human label, no ID. |
| `dispatcher/team_config.py` | Loads `supervisor` as a string. Returns it in `get_team_capabilities()`. |
| `dispatcher/router.py` | `dispatch()` never reads the `supervisor` field. `list_teams()` returns it as metadata. |
| `dispatcher/service.py` | Worker loop never reads `supervisor`. |
| Supervisor registry | Does not exist. No file, no function, no mapping. |
| String→agent mapping | Does not exist. No way to go from `"Mejora Continua Supervisor"` to `improvement-supervisor`. |
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

## 4. Proposed registry shape

This is a **conceptual structure** for future implementation. It is NOT implemented, NOT a file in the repo, and NOT loaded by any code.

```yaml
# Conceptual only — not a real file
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

### Where this registry could live

Options for future implementation (not decided now):
- `config/supervisors.yaml` — standalone file, loaded by `team_config.py`.
- Inline in `config/teams.yaml` — extend the existing team entry with `supervisor_type`, `supervisor_target`, `supervisor_status`.
- In `openclaw.json` — as part of agent configuration.

The decision depends on whether supervisor resolution is a dispatcher concern or an OpenClaw concern. This is left for the implementation slice.

## 5. Resolution flow (conceptual)

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

All of these must be met before any resolution code is written:

1. **Registry file exists.** A `config/supervisors.yaml` (or equivalent) with the schema from section 4, loaded by `team_config.py` or a new resolver module.
2. **Resolver function exists.** A pure function: `resolve_supervisor(team: str, registry: dict) -> ResolverResult` that returns target + type + fallback. No side effects.
3. **Fallback tested.** Every failure path in the decision table (cases #2, #5, #9, #12) must be covered by tests that verify dispatch continues.
4. **No regression.** All existing dispatcher tests pass without modification. Resolution is additive — it does not change any existing code path.
5. **Observability.** Resolution attempts are logged: `task_id`, `team`, `resolution_result`, `target`, `fallback_used`. This enables monitoring before full rollout.
6. **David approval.** The first `status: "active"` entry requires explicit David go-ahead.

## 10. Non-goals

- **No code changes.** This document does not modify any Python file.
- **No registry file creation.** The conceptual YAML in section 4 is not a real file.
- **No changes to `config/teams.yaml`.** The existing schema is unchanged.
- **No changes to `dispatcher/` or `worker/`.** No resolver function, no resolution logic.
- **No runtime supervisor activation.** All supervisors remain `design_only` or `disabled`.
- **No new OpenClaw agent.** `improvement-supervisor` remains design-only.
- **No decision on registry location.** Whether resolution lives in `config/supervisors.yaml`, `teams.yaml`, or `openclaw.json` is left for the implementation slice.

## 11. Relationship to previous docs

| Document | Relationship |
|----------|-------------|
| [`docs/71-supervisor-routing-contract.md`](71-supervisor-routing-contract.md) | Defines the overall routing contract. This doc satisfies its implementation gate #1: "A mechanism to map the supervisor string to an invocable agent ID or workflow." |
| [`docs/72-ambiguous-improvement-task-detection.md`](72-ambiguous-improvement-task-detection.md) | Defines when `supervisor_hint` should be set. This doc defines what happens after the hint is set: how the supervisor target is resolved. |
| [`improvement-supervisor ROLE.md`](../openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md) | Defines the supervisor's identity and scope. This doc defines how the system finds and invokes that supervisor. Safety rule #2 explicitly states that ROLE.md existence does not equal activation. |
| [`docs/70-agent-governance.md`](70-agent-governance.md) | Governance observes the agent ecosystem. Supervisor resolution is a dispatcher concern, not a governance concern. Governance may observe resolution failures as a friction signal. |
