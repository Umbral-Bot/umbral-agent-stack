# Ambiguous Improvement Task Detection

> Defines when a task routed to the `improvement` team should be conceptually tagged as `supervisor_hint: true` (candidate for supervisor coordination) versus routed directly to its handler. This is a **design document** — no runtime, dispatcher, config, or worker changes are included.

## 1. Purpose

The [supervisor routing contract](71-supervisor-routing-contract.md) established that supervisor routing is a hint, not a gate, and identified ambiguity detection as the primary implementation challenge. This document satisfies that gate by defining:

- What makes an `improvement` task "ambiguous" (candidate for supervisor coordination).
- What makes an `improvement` task "concrete" (routes directly to handler).
- Testable signals for both categories.
- A decision table with concrete examples.

The `supervisor_hint` concept does NOT exist at runtime today. This document defines the detection logic so it can be implemented and tested in a future slice.

## 2. Current state (2026-04-19)

| Component | Status |
|-----------|--------|
| `intent_classifier.route_to_team()` | Matches `improvement` team via keywords: `improvement`, `mejora`, `ooda`, `sota`, `self-eval`, `evaluación`, `benchmark`, `research`, `implementación`, `upgrade`, `optimizar`, `optimización`, `refactor`, `ciclo`, `análisis`. |
| `intent_classifier.classify_intent()` | Classifies intent as `question`, `task`, `instruction`, `scheduled_task`, or `echo`. No ambiguity flag. |
| `intent_classifier.build_envelope()` | Creates envelope with `team`, `task_type`, `task`, `input`. No `supervisor_hint` field. |
| `TeamRouter.dispatch()` | Routes by team + VM check. No supervisor logic. |
| `system.ooda_report` | Concrete handler in `worker/tasks/observability.py`. Always routes directly. |
| `system.self_eval` | Concrete handler in `worker/tasks/observability.py`. Always routes directly. |
| `supervisor_hint` | Does not exist. Not in envelope schema, not in dispatcher, not in worker. |

## 3. Definition: ambiguous improvement task

An improvement task is **ambiguous** when it requires coordination, prioritization, or diagnosis before a concrete handler can be identified. Specifically, a task is ambiguous when it meets **one or more** of these criteria:

1. **No specific handler.** The request asks to improve the system but doesn't name a concrete task like `system.ooda_report` or `system.self_eval`.
2. **Multi-area scope.** The request touches multiple areas of the stack (e.g., "review overall system health" spans observability, task quality, backlog, and process).
3. **Prioritization required.** The request asks what to improve next, what's most urgent, or how to sequence improvement work.
4. **Diagnostic before action.** The request requires gathering signals (OODA, self-eval, Linear backlog) and synthesizing them before deciding what to do.
5. **No clear owner.** The request could generate work for `rick-delivery`, `rick-qa`, or `rick-orchestrator`, but the assignment isn't obvious yet.

## 4. Direct-routing cases (no supervisor hint)

These cases MUST NOT trigger `supervisor_hint`, even when the team is `improvement`:

| Case | Reason |
|------|--------|
| Explicit `system.ooda_report` request | Concrete handler exists. Direct execution. |
| Explicit `system.self_eval` request | Concrete handler exists. Direct execution. |
| `ping` or health check | System team task, not improvement coordination. |
| Task with an exact handler name in input | The user specified what to run. No ambiguity. |
| Task routed to a different team | Supervisor only coordinates its own team. |
| Fix with specific file or module identified | Concrete scope → direct to `rick-delivery`. |
| Agent ecosystem governance | Covered by `agent-governance` function, not improvement supervisor. |
| External client deliverable | Not internal improvement. Different team or orchestrator scope. |
| Scheduled task with explicit handler | Temporal features don't make a concrete task ambiguous. |

## 5. Candidate signals

### Positive signals (suggest `supervisor_hint: true`)

**Keyword families:**

| Family | Keywords |
|--------|----------|
| General improvement | `mejora continua`, `mejora del sistema`, `mejorar el stack`, `improvement cycle` |
| Health review | `salud del sistema`, `system health`, `cómo estamos`, `estado general`, `health check interno` |
| Backlog/prioritization | `backlog`, `qué sigue`, `priorizar mejoras`, `next improvement`, `pendientes de mejora` |
| Friction/drift | `fricción`, `drift`, `friction`, `sistema roto`, `something broken`, `qué falla` |
| OODA cycle (non-specific) | `ciclo OODA`, `OODA review`, `revisión OODA` (without specifying `system.ooda_report` handler) |
| Self-eval (non-specific) | `evaluar calidad`, `quality review`, `cómo lo estamos haciendo` (without specifying `system.self_eval` handler) |

**Structural signals:**

| Signal | Description |
|--------|-------------|
| No `task` field in envelope | Intent classified as `task` or `question` for improvement team, but no specific handler mapped. |
| `task_type=improvement` without concrete handler | The team is improvement but there's no worker task to call. |
| Multi-step diagnostic implied | The request implies gathering data from multiple sources before acting. |
| Intent confidence is `medium` or `low` | The classifier wasn't strongly confident, suggesting the request is open-ended. |

### Negative signals (suggest direct routing)

| Signal | Description |
|--------|-------------|
| Explicit handler named | `system.ooda_report`, `system.self_eval`, or any specific worker task. |
| Explicit file/module target | "Fix dispatcher/router.py" → concrete delivery task. |
| Explicit owner named | "Rick delivery should..." → direct to delivery. |
| External deliverable | "Prepare report for client" → not internal improvement. |
| `intent=echo` | No actionable content. |

## 6. Decision table

| # | Request | Team | Direct handler? | supervisor_hint | Reason |
|---|---------|------|-----------------|-----------------|--------|
| 1 | "Revisa el estado de mejora continua" | improvement | No | **Yes** | Open-ended health review, no specific handler. |
| 2 | "¿Qué deberíamos mejorar next?" | improvement | No | **Yes** | Prioritization request, requires diagnosis. |
| 3 | "Hay drift entre lo documentado y lo desplegado" | improvement | No | **Yes** | Diagnostic needed, multi-area, no clear handler. |
| 4 | "Revisa el backlog de Mejora Continua Agent Stack" | improvement | No | **Yes** | Backlog review, supervisor coordination scope. |
| 5 | "El sistema tiene fricción, revisa qué falla" | improvement | No | **Yes** | Friction signal, diagnostic before action. |
| 6 | "Corre el OODA report" | improvement | `system.ooda_report` | **No** | Explicit handler. Direct execution. |
| 7 | "Ejecuta self-eval" | improvement | `system.self_eval` | **No** | Explicit handler. Direct execution. |
| 8 | "Refactoriza dispatcher/router.py" | improvement | Delivery task | **No** | Specific file, concrete scope → delivery. |
| 9 | "Crea un issue en Linear para el fix del quota tracker" | system | `linear.create_issue` | **No** | Different team, explicit handler. |
| 10 | "Ping" | system | `ping` | **No** | System team, concrete handler. |
| 11 | "Revisa si los agentes runtime están bien configurados" | improvement | No | **Borderline → No** | Sounds like agent-governance, not improvement supervisor. Conservative: route to governance or direct. |
| 12 | "Mejora el flujo de OODA para que sea más rápido" | improvement | No | **Borderline → Yes** | "Mejora" keyword + no concrete handler. The request is about process improvement, not running a report. Conservative: supervisor hint, since it requires prioritization. |

## 7. Acceptance criteria for future implementation

These criteria must be met by any implementation of `supervisor_hint` detection:

1. **Concrete handlers still route direct.** If `system.ooda_report` or `system.self_eval` is the resolved task, no `supervisor_hint` is added. Tested with explicit handler inputs.
2. **Ambiguous improvement requests can be tagged without blocking.** Adding `supervisor_hint: true` to envelope metadata does not change the routing path. The task still enqueues normally. Tested by verifying `dispatch()` output is identical with and without the hint.
3. **Fallback direct path remains default.** If no `supervisor_hint` logic exists or the detection function returns `false`, the task routes as today. Zero regression. Tested by running existing test suite without modification.
4. **No supervisor hint for non-improvement teams.** Only `team=improvement` tasks are evaluated. Tested with marketing, advisory, lab, system team inputs.
5. **Logging includes detection metadata.** When `supervisor_hint` is evaluated (whether true or false), the log entry includes: `task_id`, `team`, `task_type`, `supervisor_hint`, `reason`. Tested by checking log output.
6. **Decision table cases pass.** All 12 examples from section 6 are implemented as test cases. Positive cases return `supervisor_hint: true`, negative cases return `false`, borderline cases match the documented conservative decision.
7. **Detection is a pure function.** The `supervisor_hint` decision depends only on envelope contents (team, task, task_type, input text). No side effects, no external calls, no state mutation.

## 8. Non-goals

- **No code changes.** This document does not modify any Python file.
- **No dispatcher/router/service changes.** The `supervisor_hint` field does not exist yet.
- **No changes to `config/teams.yaml`.** The schema is unchanged.
- **No runtime supervisor activation.** `improvement-supervisor` remains design-only.
- **No new handler or cron.** Detection is a future addition to the classifier or router.
- **No new OpenClaw agent.** No workspace, no `openclaw.json` entry.
- **No enforcement.** This is declarative design.
- **No ambiguity detection for other teams.** This document scopes to `improvement` only. Other teams can follow the same pattern later if needed.

## 9. Relationship to previous docs

| Document | Relationship |
|----------|-------------|
| [`docs/71-supervisor-routing-contract.md`](71-supervisor-routing-contract.md) | Defines the overall supervisor routing contract. This doc satisfies its implementation gate #3: "A defined, testable way to determine whether a task is ambiguous/strategic or concrete." |
| [`improvement-supervisor ROLE.md`](../openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md) | Defines the supervisor's identity, scope, and boundaries. This doc defines which tasks would reach that supervisor. |
| [`docs/70-agent-governance.md`](70-agent-governance.md) | Governance observes the agent ecosystem. This doc explicitly excludes governance-scope tasks from supervisor hint (decision table #11). |
