# Supervisor Routing Contract

> Defines what it means for a team in `config/teams.yaml` to have a `supervisor` field, when supervisor routing should apply, and the conditions required before implementation. This is a **design document** — no runtime behavior changes are included.

## 1. Purpose

The `supervisor` field exists in `config/teams.yaml` for every team. Today it is dead metadata: `dispatcher/team_config.py` loads it, `TeamRouter.dispatch()` ignores it, and `dispatcher/service.py` never reads it. This document defines the intended semantics so the field can be activated safely in a future slice.

## 2. Current state (2026-04-19)

### What exists

| Component | File | Status |
|-----------|------|--------|
| `supervisor` field per team | `config/teams.yaml` | Loaded as string, never used in routing |
| `TeamRouter.dispatch()` | `dispatcher/router.py:43-88` | Routes by team + VM check only. No supervisor logic. |
| `route_to_team()` | `dispatcher/intent_classifier.py:240-266` | Keyword-based team selection. No supervisor awareness. |
| `build_envelope()` | `dispatcher/intent_classifier.py:269-330` | Builds envelope with `team` field. No `supervisor` field. |
| Worker loop | `dispatcher/service.py:617-704` | Dequeues, selects model, calls `wc.run()`. No supervisor step. |
| `list_teams()` | `dispatcher/router.py:103-113` | Returns supervisor in team info — the only place it surfaces. |
| `improvement-supervisor` ROLE.md | `openclaw/workspace-agent-overrides/improvement-supervisor/` | Design-only contract. No runtime agent. |

### Current routing flow

```
Notion comment
  → intent_classifier.classify_intent(text) → IntentResult
  → intent_classifier.route_to_team(text) → team string
  → intent_classifier.build_envelope(text, comment_id, intent, team) → TaskEnvelope
  → TeamRouter.dispatch(envelope) → enqueue or block (VM check)
  → worker loop dequeues → model selection → wc.run(task, input_data)
```

No step in this flow reads the `supervisor` field.

## 3. Supervisor field semantics

### Definition

`supervisor` is the **coordination owner** for a team. It is:

- **An optional logical role** — not every team needs one. `lab` and `system` have `supervisor: null` and that is correct.
- **A pointer to a resolvable agent or workflow** — when activated, the supervisor string must resolve to something invocable (an OpenClaw agent, a handler, or a defined workflow). Today it resolves to nothing.
- **A coordination layer, not an execution layer** — the supervisor prioritizes, delegates, and tracks. It does not execute the work itself.
- **Not a routing gate** — the supervisor must never block or intercept tasks that already have a clear handler. It operates alongside the existing routing, not in front of it.

### When `supervisor` is null

The team has no coordinator. All tasks route directly to handlers via the existing flow. This is the current behavior for all teams and must remain the default.

### When `supervisor` is a non-null string

The team has a declared coordinator. The string identifies who/what coordinates the team's work. Until the supervisor resolves to an invocable entity, the field remains informational.

## 4. When supervisor routing applies

Supervisor routing should activate **only** for tasks that meet these criteria:

| Criterion | Example |
|-----------|---------|
| **Ambiguous scope** | The intent classifier assigns the team but the task doesn't map to a specific handler or role. |
| **Cross-role within team** | The task touches multiple roles in the same team (e.g., both `sota_research` and `implementation` in `improvement`). |
| **Team backlog prioritization** | The task is about reviewing, prioritizing, or triaging the team's pending work. |
| **Periodic signal review** | Scheduled review of team health signals (e.g., OODA report + self-eval for `improvement`). |
| **Escalation from a team role** | A role within the team escalates to the supervisor for coordination or decision preparation. |

## 5. When supervisor routing must NOT apply

| Situation | Why |
|-----------|-----|
| **Task has a clear, specific handler** | Direct routing is faster and the supervisor adds no value. A `system.ooda_report` call goes straight to its handler. |
| **Task belongs to a different team** | The supervisor only coordinates its own team. Cross-team work is `rick-orchestrator`'s job. |
| **Operational/infrastructure work** | VPS, VM, cron, deploy — these go to `rick-ops`, not to a team supervisor. |
| **Agent ecosystem governance** | Structural observation of the agent ecosystem is `agent-governance`, not a team supervisor. A team supervisor observes its own team's health, not the system's. |
| **Simple direct tasks** | "Run self-eval" or "Create a Linear issue" — concrete tasks that the worker can execute directly. |

**Core principle:** The supervisor is opt-in enrichment, not a mandatory gate. If removing the supervisor from the flow would produce the same result, the supervisor should not be involved.

## 6. Conceptual routing flow (proposed)

```
Notion comment
  → classify_intent(text) → IntentResult
  → route_to_team(text) → team
  → build_envelope(text, comment_id, intent, team) → TaskEnvelope
  → TeamRouter.dispatch(envelope):
      1. Existing logic: validate team, check VM → enqueue or block
      2. NEW (future): if team has supervisor AND task is ambiguous/strategic:
         - Add `supervisor_hint: true` to envelope metadata
         - The worker or a post-routing step can check this hint
         - Supervisor agent receives the task for triage/delegation
      3. If task is concrete → route as today (no supervisor involvement)
```

### Key design decisions

- **Hint, not intercept.** The supervisor is signaled via envelope metadata, not by replacing the routing target. The existing flow continues to work even if the supervisor is unreachable.
- **Fallback to direct routing.** If the supervisor agent doesn't exist, isn't responding, or the hint is ignored, the task routes normally. Zero regression.
- **No new queue.** Supervisor tasks go through the same queue. The `supervisor_hint` is metadata, not a separate dispatch path.
- **Ambiguity detection is the hard part.** The classifier must determine whether a task is "ambiguous/strategic" vs "concrete." This is the primary implementation challenge and should be addressed in a future slice.

## 7. First application: `improvement` team

| Field | Value |
|-------|-------|
| Team | `improvement` |
| Supervisor string | `"Mejora Continua Supervisor"` |
| Target agent | `improvement-supervisor` (design-only, PR #229) |
| Signals | `system.ooda_report`, `system.self_eval`, Linear `Mejora Continua Agent Stack` |
| Roles in team | `supervisor`, `sota_research`, `self_evaluation`, `implementation` |

### How it would work (once implemented)

1. David says "Revisa el estado de mejora continua" → classified as `improvement` team, ambiguous scope.
2. Envelope gets `supervisor_hint: true`.
3. `improvement-supervisor` agent receives the task, runs `ooda_report` + `self_eval`, reviews Linear issues.
4. Supervisor produces a prioritized recommendation and hands off to `rick-delivery` (for scoped fixes) or `rick-orchestrator` (for multi-front improvements).
5. David reviews the recommendation.

### What's missing before this works

1. `improvement-supervisor` registered as an OpenClaw agent (workspace + `openclaw.json` entry).
2. Ambiguity detection logic in the classifier or router.
3. Supervisor resolution: mapping the `supervisor` string to an invocable agent ID.
4. At least one team role (`sota_research`, `self_evaluation`, or `implementation`) being invocable, not just a label.

## 8. Boundaries with existing roles

| Role | Supervisor's relationship |
|------|--------------------------|
| `rick-orchestrator` | Orchestrator manages **all fronts** across all teams. A team supervisor manages **one team's** internal work. The supervisor prepares recommendations; orchestrator decides cross-team priority. No overlap: the supervisor hands off to orchestrator when the scope exceeds its team. |
| `agent-governance` | Governance is a **systemic function** that observes the entire agent ecosystem (roles, skills, routing, boundaries). A team supervisor observes **its own team's operational health** (task quality, failure rates, backlog). Different scope, different signals, different output. |
| `rick-delivery` | Delivery **executes** work. The supervisor **coordinates** what work to execute and in what order. The supervisor never implements — it delegates to delivery. |
| `rick-qa` | QA **validates** deliveries against criteria. The supervisor **identifies** what needs improvement. QA may validate that an improvement worked, but the supervisor does not validate deliveries itself. |

### Anti-pattern: supervisor-orchestrator loop

The biggest risk is creating a loop: supervisor recommends → orchestrator delegates back to supervisor's team → supervisor re-recommends. Prevention:

- The supervisor produces **concrete, scoped handoffs** — not abstract "something should improve."
- Once the supervisor hands off to orchestrator or delivery, it does not re-enter the loop until the handoff is resolved.
- The supervisor does not re-triage work that orchestrator has already prioritized.

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Bureaucratic overhead** | Medium | Supervisor is opt-in, not mandatory. Concrete tasks bypass it entirely. |
| **Duplicating orchestrator** | High | Strict scope: supervisor coordinates one team only. Cross-team = orchestrator. |
| **Blocking simple tasks** | High | Supervisor is a hint, not a gate. Fallback to direct routing always works. |
| **Supervisor→orchestrator→supervisor loop** | Medium | Supervisor produces concrete handoffs. Once handed off, it waits for resolution. |
| **Metadata confused with runtime** | Medium | ROLE.md and this doc explicitly mark design-only status. No runtime changes without meeting implementation gates. |
| **Activating non-existent agents** | High | Supervisor must resolve to an invocable entity. If resolution fails, fall back to direct routing. |
| **Ambiguity detection is unreliable** | Medium | Start conservative: only trigger supervisor for explicitly marked tasks or scheduled reviews, not for classifier-inferred ambiguity. |

## 10. Implementation gates

All of these must be met before any runtime behavior changes:

1. **Supervisor resolution.** A mechanism to map the `supervisor` string in `teams.yaml` to an invocable agent ID or workflow. Today there is no such mapping.
2. **At least one team with a working supervisor agent.** The `improvement-supervisor` must exist as an OpenClaw agent (workspace, `openclaw.json` entry, model assigned) — not just a ROLE.md.
3. **Ambiguity signal.** A defined, testable way to determine whether a task is "ambiguous/strategic" (routes to supervisor) or "concrete" (routes directly). This can start as a simple flag in the envelope, not a classifier change.
4. **Fallback guarantee.** If the supervisor agent is unreachable or undefined, the task must route as it does today. Zero regression. This must be covered by a test.
5. **No regression test.** All existing dispatcher tests (`tests/test_intent_classifier.py`, `tests/test_worker.py`, etc.) must pass without modification. New behavior must be additive.
6. **Observability.** When supervisor routing activates, it must be logged (at minimum: task_id, team, supervisor_hint, resolution result). This enables monitoring before full rollout.
7. **David approval.** The first activation of supervisor routing requires explicit David go-ahead, not just code merge.

## 11. Explicit non-goals

- **This document does not change dispatcher behavior.** No code, no config, no runtime.
- **This document does not define a new handler or cron.** Supervisor routing is a future enhancement to the existing router.
- **This document does not activate `improvement-supervisor`.** The ROLE.md (PR #229) remains design-only.
- **This document does not propose changes to `config/teams.yaml`.** The existing schema is sufficient; the `supervisor` field just needs to be read.
- **This document does not define per-team queues or priority systems.** Supervisor routing uses the existing single queue with metadata hints.
- **This document does not define how roles become invocable.** That is a separate slice (making `sota_research`, `self_evaluation`, `implementation` into something the system can actually delegate to).
