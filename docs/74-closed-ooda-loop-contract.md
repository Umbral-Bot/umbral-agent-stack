# Closed OODA Loop Contract

> Defines the minimum closed-loop circuit for continuous improvement in the Umbral Agent Stack: signal → prioritization → delegation → execution → QA validation → closure. This is a **design document** — no runtime, dispatcher, config, worker, handler, or cron changes are included. No automation is created.

## 1. Purpose

The Phase 5 diagnostic established that no runtime supervisor should be activated until at least one closed-loop circuit works. Today the signals exist (`system.ooda_report`, `system.self_eval`, Linear backlog) but nobody consumes them automatically, and there is no defined path from signal detection to verified closure.

This document defines:

- What a closed OODA loop means in this stack.
- The minimum viable loop that must work before supervisor activation.
- Ownership rules at each stage.
- Failure modes to avoid.
- Testable acceptance criteria for future implementation.

OODA here means: **Observe → Orient → Decide → Act → Verify → Close**. The classic OODA (Boyd) has four stages; we add Verify (QA validation) and Close (trazabilidad) because this stack requires evidence-based closure.

## 2. Current state (2026-04-19)

| Component | Status |
|-----------|--------|
| `system.ooda_report` | Exists. Produces task volume, failure rates, provider distribution from Redis. Handler in `worker/tasks/observability.py`. |
| `system.self_eval` | Exists. Produces quality scores for completed tasks. Handler in `worker/tasks/observability.py`. |
| Linear `Mejora Continua Agent Stack` | Active project. Tracks improvement issues, follow-ups, and debt. |
| Notion page | Active. Used for David-facing summaries and governance notes. |
| `improvement-supervisor` | Design-only ROLE.md (PR #229). No runtime agent. |
| Supervisor routing | Design-only contracts (PRs #230-#232). No runtime behavior. |
| Closed loop | **Does not exist.** Signals are produced but not consumed systematically. No defined path from signal to verified closure. |
| Automatic issue creation from signals | Does not exist. |
| Handoff telemetry | Does not exist. No structured tracking of signal→action→closure. |

## 3. Loop stages

### Observe

Collect signals that indicate something needs improvement.

| Source | What it produces | How it's accessed today |
|--------|-----------------|------------------------|
| `system.ooda_report` | Task volume, failure rates, provider distribution | Worker task, manual invocation |
| `system.self_eval` | Quality scores per task, average score | Worker task, manual invocation |
| Linear `Mejora Continua Agent Stack` | Blocked issues, stale follow-ups, enhancement requests | `linear.list_agent_stack_issues` |
| Manual David request | "Something feels broken", "review system health" | Telegram/Notion comment |
| Failed task patterns | Recurring failures with same fingerprint | `dispatcher/service.py` dedup logic, ops_log |
| Agent governance report | Role drift, skill gaps, saturation signals | `docs/70-agent-governance.md`, manual invocation |

### Orient

Classify the signal: severity, probable cause, impact area, and suggested owner.

| Dimension | Values |
|-----------|--------|
| Severity | `critical` (blocking David's work), `high` (degraded quality), `medium` (technical debt), `low` (cosmetic/minor) |
| Cause category | `task_failure`, `quality_degradation`, `process_gap`, `capability_gap`, `drift`, `stale_backlog` |
| Impact area | dispatcher, worker, routing, observability, skills, agents, infrastructure, docs |
| Suggested owner | `rick-delivery` (scoped fix), `rick-orchestrator` (multi-front), `rick-qa` (validation), David (decision) |

### Decide

Choose action or explicit no-action, set priority, define acceptance criteria.

| Decision | Meaning |
|----------|---------|
| **Act** | Create or update Linear issue with owner, acceptance criteria, and priority. |
| **Defer** | Signal is real but not urgent. Create issue with `low` priority and reason for deferral. |
| **No-action** | Signal is noise, already addressed, or below threshold. Record decision with reason. Do not create issue. |

Every decision must be recorded — "no-action" is a valid outcome, but it must have a reason.

### Act

Delegate execution to the appropriate agent.

| Destination | When |
|-------------|------|
| `rick-delivery` | Scoped fix: code change, doc update, config fix, artifact production. |
| `rick-orchestrator` | Multi-front improvement that needs planning and sequencing across teams. |
| `rick-qa` | Validation of a previous improvement or cross-system consistency check. |
| David | Irreversible action, budget, strategic direction, or runtime activation decision. |

The handoff must include: scope, acceptance criteria, evidence from the signal, and link to the Linear issue.

### Verify

QA validates the result with observable evidence.

| Verification type | When |
|-------------------|------|
| **Full QA** | Code change, config change, or runtime behavior change. QA checks against acceptance criteria with evidence. |
| **Spot check** | Doc-only change or trivial fix. QA confirms the change exists and is correct. |
| **Explicit skip** | No-action decision or deferred item. QA is skipped but the reason is recorded. |

QA must never be silently skipped. If QA doesn't apply, the reason must be in the closure artifact.

### Close

Register the outcome in Linear and Notion with trazabilidad.

| Closure artifact | Where |
|------------------|-------|
| Linear issue status update | `Mejora Continua Agent Stack` — mark done, cancelled, or deferred with reason. |
| Notion summary (if significant) | Page `3455f443fb5c810593f3d930426e61b0` — brief note linking signal to outcome. |
| PR link (if code change) | Referenced in Linear issue. |

**Never close only in chat.** Every loop must leave a trace in Linear at minimum.

## 4. Minimum viable loop

The smallest loop that satisfies the "closed circuit" requirement before supervisor activation:

1. **One concrete signal enters.** Example: `system.self_eval` shows average score < 3.0.
2. **Signal is classified.** Severity, cause, impact area, suggested owner documented.
3. **Linear issue created or updated.** With owner, acceptance criteria, and link to signal evidence.
4. **Owner executes or records no-action.** Delivery produces fix, or decision-maker records why no action.
5. **QA validates or explicit skip recorded.** Evidence checked, or reason for skipping documented.
6. **Linear issue closed with link.** Status updated, closure note includes what was done and evidence.
7. **Notion note if significant.** Optional but recommended for high-severity signals.

This loop can be executed **manually today** by David and Rick without any automation. The point is to prove the circuit works before automating it.

## 5. Inputs and outputs

### Inputs (what triggers the loop)

| Input | Source | Frequency |
|-------|--------|-----------|
| OODA report with elevated failures | `system.ooda_report` | On-demand |
| Self-eval with low scores | `system.self_eval` | On-demand |
| Manual David request | Telegram / Notion | Anytime |
| Linear issue accumulation | `Mejora Continua Agent Stack` | Continuous |
| Failed task pattern | Dispatcher dedup / ops_log | Reactive |
| Governance report | `agent-governance` function | At phase/milestone close |

### Outputs (what the loop produces)

| Output | Destination |
|--------|-------------|
| Linear issue created/updated | `Mejora Continua Agent Stack` |
| Notion summary | Page `3455f443...` (if significant) |
| Handoff to delivery/orchestrator/qa | Via existing delegation mechanisms |
| Explicit no-action decision with reason | Linear comment or issue update |
| PR (if code change) | GitHub, linked from Linear |

## 6. Ownership rules

| Role | Responsibility in the loop |
|------|---------------------------|
| `improvement-supervisor` (future) | Coordinates: observe, orient, decide, delegate. Does NOT execute fixes. |
| `rick-delivery` | Executes: code, docs, config, artifacts. Reports back with evidence. |
| `rick-qa` | Validates: checks acceptance criteria with observable evidence. |
| `rick-orchestrator` | Plans: handles multi-front improvements that exceed one team's scope. |
| David | Approves: irreversible actions, budget, strategy, runtime activation. |

**Key constraint:** Until `improvement-supervisor` is a runtime agent, the coordination role (observe, orient, decide) is performed by `rick-orchestrator` or David directly. The loop works without a dedicated supervisor — the supervisor makes it more structured, not possible.

## 7. Decision table

| # | Signal | Orient result | Owner | Action | Verification | Closure artifact |
|---|--------|---------------|-------|--------|-------------|-----------------|
| 1 | `ooda_report` shows failure rate > 15% | `high` / `task_failure` / dispatcher | `rick-delivery` | Fix dispatcher error handling | QA validates failure rate drops | Linear issue closed with PR link |
| 2 | `self_eval` average score < 3.0 | `medium` / `quality_degradation` / worker | `rick-delivery` | Improve prompt or task logic | QA validates score improves | Linear issue closed with evidence |
| 3 | Recurring dispatcher timeout (same fingerprint 3x) | `high` / `task_failure` / dispatcher | `rick-delivery` | Fix timeout or increase limit | QA validates no recurrence | Linear issue closed with PR link |
| 4 | 10+ stale issues in `Mejora Continua Agent Stack` | `medium` / `stale_backlog` / process | `improvement-supervisor` (future) or David | Triage, close irrelevant, prioritize rest | Spot check: backlog reduced | Linear issues updated |
| 5 | One-off task failure, no pattern | `low` / `task_failure` / worker | No-action | Record as noise, monitor for recurrence | Explicit skip: one-off | Linear comment: "one-off, monitoring" |
| 6 | David asks "qué sigue en mejora" | `medium` / `process_gap` / all | `improvement-supervisor` (future) or orchestrator | Run ooda_report + self_eval, produce summary | Spot check: summary delivered | Notion note with recommendations |
| 7 | Governance report finds ROLE.md drift | `medium` / `drift` / agents | `rick-delivery` | Update ROLE.md to match runtime | QA validates alignment | Linear issue closed with PR link |
| 8 | Delivery fix completed for #1 | N/A (continuation) | `rick-qa` | Validate fix against acceptance criteria | Full QA with evidence | Linear issue closed by QA |
| 9 | QA rejects fix for #2 | `high` / `quality_degradation` / worker | `rick-delivery` | Rework based on QA feedback | QA re-validates | Linear issue reopened then closed |
| 10 | Signal below threshold, no user impact | `low` / `cosmetic` / docs | No-action | Explicit decision: not worth fixing now | Explicit skip with reason | Linear comment: "below threshold, deferred" |

## 8. Failure modes

| Failure mode | Why it's bad | Prevention |
|-------------|-------------|------------|
| Loop closes without owner | Nobody is accountable. Work drifts. | Every Linear issue must have an assignee before the Act stage. |
| Loop closes without evidence | "Done" without proof. Quality unknown. | Closure requires link to PR, test result, or explicit skip reason. |
| QA skipped without reason | Validation gap. Regression risk. | QA skip must have documented reason in Linear. |
| Supervisor implements instead of delegating | Role boundary violation. Supervisor becomes bottleneck. | Supervisor ROLE.md boundary: "Does not implement code." Enforced by review. |
| Endless diagnosis, no action | Analysis paralysis. Backlog grows. | Decide stage has a maximum: classify → decide within same session. If undecidable, escalate to David. |
| Duplicate issues for same signal | Noise, confusion, wasted work. | Check Linear for existing issue with same signal before creating new one. |
| Stale Notion/Linear mismatch | David sees outdated info. Trust erodes. | Close stage updates both, or explicitly notes Notion skip for low-severity items. |
| External work mixed into improvement loop | Improvement backlog polluted with client work. | Improvement loop only covers internal stack improvement. External work goes through orchestrator's normal flow. |

## 9. Acceptance criteria for future implementation

These must be met by any automation of the OODA loop:

1. **Every loop has an owner.** No Linear issue is created or updated without an assignee. Tested by checking issue fields.
2. **Every loop has acceptance criteria.** The Act stage includes what "done" looks like. Tested by checking issue description.
3. **Every loop has a closure artifact.** Linear issue status + link to evidence (PR, test result, or skip reason). Tested by checking closed issues.
4. **No chat-only closure.** The loop must leave a trace in Linear at minimum. Tested by verifying no loop completes without a Linear update.
5. **QA validation required or explicit exception.** Every closure has QA sign-off or documented reason for skip. Tested by checking closure comments.
6. **Delivery handoff includes scope and evidence.** Handoff to delivery contains: what to fix, acceptance criteria, and link to signal. Tested by checking issue body at Act stage.
7. **No duplicate active issue for same signal.** Before creating a new issue, check for existing open issue with overlapping scope. Tested by searching before creation.
8. **No runtime activation without David approval.** Any step that would activate a supervisor agent, create a workspace, or modify `openclaw.json` requires explicit David go-ahead. Tested by requiring approval flag.
9. **Loop can run manually.** The entire loop must be executable by David + Rick without any new handler, cron, or automation. Automation is an optimization, not a requirement.

## 10. Non-goals

- **No code changes.** This document does not modify any Python file.
- **No config changes.** No `teams.yaml`, `openclaw.json`, or `quota_policy.yaml` modifications.
- **No new handler.** No `improvement.supervise` or `system.improvement_loop` task.
- **No new cron.** No scheduled signal collection or automatic triage.
- **No runtime supervisor.** `improvement-supervisor` remains design-only.
- **No automatic issue creation.** Issues are created manually or by existing tools (Rick, David).
- **No Notion automation.** Notion updates are manual or via existing `notion.add_comment`.
- **No enforcement.** This is declarative design. Compliance is by practice, not by code.
- **No dispatcher routing changes.** The loop operates on top of existing routing, not inside it.

## 11. Relationship to previous docs

| Document | Relationship |
|----------|-------------|
| [`docs/71-supervisor-routing-contract.md`](71-supervisor-routing-contract.md) | Defines supervisor routing. This doc defines the loop that the supervisor would coordinate once activated. Satisfies the "closed loop before runtime supervisor" condition from the Phase 5 diagnostic. |
| [`docs/72-ambiguous-improvement-task-detection.md`](72-ambiguous-improvement-task-detection.md) | Defines when a task is ambiguous. This doc defines what happens after ambiguity is detected: the signal enters the OODA loop. |
| [`docs/73-supervisor-resolution-contract.md`](73-supervisor-resolution-contract.md) | Defines how to resolve a supervisor target. This doc defines what the resolved supervisor would actually do: coordinate the loop stages. |
| [`improvement-supervisor ROLE.md`](../openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md) | Defines the supervisor's identity and boundaries. This doc defines the operational loop the supervisor coordinates. The ROLE.md says "observe ooda_report, self_eval, prioritize, prepare handoffs" — this doc formalizes that as a closed circuit. |
| [`docs/70-agent-governance.md`](70-agent-governance.md) | Governance observes the agent ecosystem. Governance reports can be an **input** to the OODA loop (signal source), but the loop itself is not governance — it is operational improvement execution. |
