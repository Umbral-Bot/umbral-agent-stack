# Improvement Supervisor — Phase 6B Activation Readiness Plan

> **DO NOT APPLY ANYTHING FROM THIS DOCUMENT IN THIS PR.** This is a docs/readiness hardening document only. It does not activate the supervisor, does not register an OpenClaw agent, does not flip any config, and does not wire any runtime path. Every instruction that would affect runtime behavior, configuration, or OpenClaw state is labeled future/manual and requires explicit David approval before execution.
>
> **Scope of this PR:** documentation + ROLE.md hardening. Nothing else.

## 1. Status

| Area | State |
|------|-------|
| Phase 5 (passive foundation) | Closed. Final merge at `0a94d8d`. |
| Phase 6A (structured supervisor telemetry sink in `ops_log.jsonl`) | Closed. Merged via PR #243 at `070edc7` or later. |
| `config/supervisors.yaml` `improvement.status` | `design_only`. Unchanged by this PR. |
| OpenClaw registration of `improvement-supervisor` | Not present. Unchanged by this PR. |
| Supervisor routing in `TeamRouter.dispatch()` | Non-blocking observability-only wiring (from PR #241). Does not change dispatch result. |
| Structured Supervisor Events source (`ops_log.jsonl` via `OpsLogger.supervisor_event()`) | Available. Monitor reads directly (Phase 6A). |
| Observation window | **WATCH** — the monitoring script reached `WATCH` for the 60m, 24h, and 48h windows because no ambiguous improvement traffic has entered the system yet. Zero structured supervisor events observed. |
| Safety flags (raw text leakage, non-improvement events, `should_block=True`, malformed events) | All clean. |
| Activation performed? | No. No activation. No runtime config change. No OpenClaw registration. |

This document does **not** activate anything. It prepares the readiness materials so a future activation — if and when David approves — has a complete, auditable, reversible path. Until David gives explicit approval, Phase 6B remains planned but not executed.

## 2. Scope

Phase 6B activation readiness is scoped deliberately narrowly:

- **First activation candidate:** `improvement-supervisor` only. No other team supervisor is in scope.
- **Improvement-only:** the runtime path that reads supervisor observability must reject non-`improvement` teams upstream of any sink call. This invariant is already enforced by the wiring from PR #241 and must be preserved.
- **Ambiguous-task-only:** only tasks that `detect_ambiguity_signal()` classifies as ambiguous may reach the resolver/sink path. Concrete improvement tasks (e.g., `system.ooda_report`, `system.self_eval`) must route directly and must not reach the supervisor path.
- **Non-blocking:** the first activation must remain non-blocking. `should_block` stays `False` on every code path. Dispatch is never rejected, delayed, or rerouted because of supervisor logic. David may later approve a stricter mode, but not as part of the first activation.
- **Direct fallback remains mandatory:** if resolver, registry, sink, or OpenClaw target is unavailable, the task routes via direct dispatch. Fallback is the default behavior, not a failure case.
- **Readiness, not execution:** this plan is for readiness and future approval. Nothing in it is applied until David explicitly approves a subsequent activation PR.

## 3. Preconditions

All of the following must be satisfied before any activation PR is merged. Missing any one of these is a hard stop.

| # | Precondition | Evidence required |
|---|--------------|-------------------|
| 1 | David explicit approval | Written approval (Notion comment on Control Room, Telegram message, or Linear comment). No inferred approval. |
| 2 | Phase 6A observation window completed | `docs/75` section 7 window + `scripts/monitor_supervisor_observability.py` reports archived for 60m / 24h / 48h windows. |
| 3 | Structured Supervisor Events source `Available=True` | Monitor report shows `Structured Supervisor Events — Available: True`. Sink is writing to `ops_log.jsonl`. |
| 4 | Either `PASS_OBSERVATION` with real structured events, **or** explicit David waiver if no organic traffic appears during the window | Monitor report, or David-signed note in the activation PR that acknowledges zero-traffic waiver. The waiver must reference `docs/76` section 3 meaning of `WATCH`. |
| 5 | 0 rollback triggers | Monitor report shows `should_block_true_count=0`, `non_improvement_event_count=0`, `raw_text_leakage_suspected_count=0`, `malformed_event_count=0`, `error_event_count=0`, `supervisor_observability_failed=0`. |
| 6 | Config validation 0 errors | `validate_supervisor_config_consistency()` returns 0 errors. Warnings permitted only if documented. |
| 7 | OpenClaw registration plan reviewed | This doc's section 7 plan reviewed by David; no registration performed yet. |
| 8 | Rollback commit identified | Pre-merge SHA of `main` recorded in the activation PR body and in Linear UMB-173. |
| 9 | Smoke test owner assigned | Copilot or Rick owner declared in the activation PR. |
| 10 | Linear / Notion evidence updated | UMB-173 and Notion Phase 5 page updated with the readiness state and approval record. |

## 4. Activation options

These options are evaluated in order of safety. Each one is a distinct, independently-mergeable step. Activation must not combine options in a single PR.

### Option A — Register OpenClaw agent only; keep `supervisors.yaml` `design_only`

| Aspect | Detail |
|--------|--------|
| What changes | `improvement-supervisor` workspace is registered in OpenClaw (either via `openclaw/workspace-agent-overrides/improvement-supervisor/` binding or an entry in `openclaw.json`). `config/supervisors.yaml` still reports `status: design_only`. Resolver returns unresolved; fallback remains `direct`. |
| Risk | Low. The registry keeps the resolver in `design_only`, so even if wiring inadvertently calls the resolver, the task still routes direct. Only risk: the agent exists but has no traffic; it must not be invoked by other paths. |
| Benefit | Validates OpenClaw registration mechanics and ROLE.md loading without changing dispatch semantics. Allows observing agent boot, model assignment, and tooling availability under zero-traffic conditions. |
| Rollback | Remove OpenClaw registration (delete workspace entry, remove binding). No config revert required. |
| Go / No-Go | Go only if preconditions 1, 3, 7, 8 from section 3 are satisfied. |
| Recommendation | **Recommended as step 1.** Smallest reversible change. Isolates OpenClaw mechanics from routing semantics. |

### Option B — Flip improvement supervisor to `active` but observability-only, no delegation

| Aspect | Detail |
|--------|--------|
| What changes | `config/supervisors.yaml` `improvement.status` changes from `design_only` to `active` (still hypothetical — see section 6). Existing non-blocking observability wiring from PR #241 now emits `supervisor.resolution` events with `outcome=resolved` for ambiguous improvement tasks. No delegation, no task enqueue to the supervisor, no agent invocation. `should_block` stays `False`. |
| Risk | Medium. The resolver begins to consider the registry as "active," which is a semantic shift. If target availability checks ever wire in and the target is down, fallback must kick in. The sink will begin to produce `outcome=resolved` rows in `ops_log.jsonl`. |
| Benefit | Proves end-to-end observability with a resolved outcome. Verifies `fallback` semantics under the `active` status. |
| Rollback | Revert `config/supervisors.yaml` change to `design_only`. No code revert needed if wiring remains non-blocking. |
| Go / No-Go | Go only if Option A succeeded and preconditions 1–10 all hold. |
| Recommendation | **Not recommended before Option A.** Depends on Option A to be useful. |

### Option C — Active advisory supervisor output routed to logs only

| Aspect | Detail |
|--------|--------|
| What changes | On top of Option B, the supervisor agent is actually invoked for ambiguous improvement tasks but its output is written **only** to structured logs (`ops_log.jsonl` supervisor sink and/or journald). No Linear / Notion writes, no handoff to delivery, no task rerouting. |
| Risk | Higher. Introduces an OpenClaw round-trip in the dispatch-adjacent path. Requires strict latency budget, timeout, and error handling. Any failure must be swallowed and logged as `supervisor_observability_failed` without affecting dispatch. |
| Benefit | First real supervisor output under observation. Exercises the agent reasoning loop without exposing it to users or to Notion/Linear automation. |
| Rollback | Disable agent invocation (code flag or OpenClaw unregistration). Revert `supervisors.yaml` to `design_only` if Option B was applied. |
| Go / No-Go | Go only if Options A and B succeeded, their monitoring windows closed clean, and David explicitly approves invocation. |
| Recommendation | **Not recommended for Phase 6B.** This option is Phase 6C or later. Listed here only for completeness so reviewers know what the future path looks like. |

## 5. Recommended activation path

The safest path is a strict staircase. No step may be combined with another, and each step requires its own David approval.

1. **Step 1 — Register OpenClaw agent but do not route traffic.** Adopt Option A. Keep `config/supervisors.yaml` at `design_only`. Do not touch dispatch code. Verify the agent appears in OpenClaw's agent list.
2. **Step 2 — Verify OpenClaw status.** Run manual verification commands (see section 7). Confirm workspace loads, ROLE.md is recognized, model is assigned, and no traffic is flowing in or out of the agent.
3. **Step 3 — Run smoke matrix.** Execute the smoke test matrix from section 8 against the live system, with OpenClaw agent registered but `design_only`. All rows must pass. No structured supervisor event should change shape compared to Phase 6A WATCH.
4. **Step 4 — Only later consider config flip.** If Steps 1–3 are clean and David approves, evaluate Option B. This must be a separate PR against `config/supervisors.yaml` only, with its own pre-merge validation window.
5. **Step 5 — Continue monitoring.** After any change, re-run `scripts/monitor_supervisor_observability.py --since-minutes 1440` and archive the report. Maintain the 48h window before declaring the step done.

Each step requires David approval. Each step has an independent rollback. Skipping a step is not permitted.

## 6. Exact proposed future config diff

> **DO NOT APPLY IN THIS PR.** The diff below is hypothetical. It describes what a future Option B PR would propose. Nothing in this section is applied to `config/supervisors.yaml` as part of Phase 6B readiness docs.

Current state (actual, at this PR's base):

```yaml
supervisors:
  improvement:
    label: "Mejora Continua Supervisor"
    type: "openclaw_agent"
    target: "improvement-supervisor"
    status: "design_only"
    fallback: "direct"
```

Hypothetical future state if Option B is approved (**not applied here**):

```yaml
supervisors:
  improvement:
    label: "Mejora Continua Supervisor"
    type: "openclaw_agent"
    target: "improvement-supervisor"
    status: "active"        # <-- only changes if Option B is approved
    fallback: "direct"      # fallback remains direct even when active
```

Conceptual unified diff for reference (again, **not applied**):

```diff
 supervisors:
   improvement:
     label: "Mejora Continua Supervisor"
     type: "openclaw_agent"
     target: "improvement-supervisor"
-    status: "design_only"
+    status: "active"
     fallback: "direct"
```

This is illustrative. The actual future PR must:

- Touch only `config/supervisors.yaml`.
- Include evidence that Options A preconditions are satisfied.
- Include a rollback command (`git revert`) on the merge commit.
- Keep `fallback: "direct"` unchanged.

## 7. OpenClaw registration checklist

> All commands in this section are **future/manual**. They are not executed as part of this readiness PR.

- **Where ROLE.md lives:** `openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md`. This is the canonical role contract. Registration binds this file to an OpenClaw agent workspace.
- **What registration looks like:** either a workspace binding referenced from `~/.openclaw/openclaw.json`, or a declarative block in `openclaw/workspace-agent-overrides/` that the OpenClaw runtime discovers. The exact mechanism must follow the pattern of already-registered Rick agents (`rick-orchestrator`, `rick-delivery`, `rick-qa`). This PR does not prescribe the mechanism; it only documents the checklist.
- **How to verify OpenClaw status (future/manual):**

```bash
# future/manual — do NOT run as part of this readiness PR
openclaw agents list 2>/dev/null | grep -i improvement-supervisor || echo "not registered"
python3 -c "
import json, os
data = json.load(open(os.path.expanduser('~/.openclaw/openclaw.json')))
print('improvement-supervisor present:', 'improvement-supervisor' in json.dumps(data))
"
```

- **How to confirm no extra permissions:** compare the registered workspace's allowed tools / skills against the `Tools and permissions` section in `ROLE.md`. Reject registration if any tool not listed there is present. Specifically reject `github.*` write tools, `client.*`, `windows.*`, `browser.*`, `notion.add_comment`, `linear.create_issue`, or any tool that can write external state. The supervisor is advisory; it must not hold execution capability during first activation.
- **How to remove / rollback registration (future/manual):**

```bash
# future/manual — rollback step, run only if registration needs to be undone
# 1. remove the workspace binding or openclaw.json entry for improvement-supervisor
# 2. restart OpenClaw-adjacent services if required by the registration mechanism
# 3. verify the agent no longer appears in `openclaw agents list`
# 4. re-run scripts/monitor_supervisor_observability.py --since-minutes 60
```

- **Evidence to post to Linear / Notion after registration:**
  - Linear UMB-173 comment with: registration commit or config delta, `openclaw agents list` output redacted, monitor report window, rollback command.
  - Notion Phase 5 page with a short note linking to the Linear update.
- **Evidence to post after rollback:** same format, plus explicit statement that rollback was executed and verified.

## 8. Smoke test matrix

All commands are **future/manual**. The matrix below is the acceptance criteria for any activation step.

| # | Case | Input | Expected dispatch | Expected supervisor event | Notes |
|---|------|-------|-------------------|---------------------------|-------|
| 1 | Non-improvement task unchanged | Task routed to `marketing`, `advisory`, `lab`, or `system` | Unchanged direct dispatch | None, or `supervisor.noop` only if the code path explicitly emits noop. Never a `supervisor.ambiguity_signal` or `supervisor.resolution` for non-improvement team. | Team gate upstream of sink. |
| 2 | Concrete improvement task unchanged | Explicit `system.ooda_report` or `system.self_eval` | Unchanged direct dispatch to the concrete handler | `supervisor.ambiguity_signal` with `outcome=not_ambiguous` at most, or no event. No `supervisor.resolution`. | Concrete handlers must not trigger resolver. |
| 3 | Ambiguous improvement emits structured events | "Revisa el estado de mejora continua" or similar | Unchanged direct dispatch | `supervisor.ambiguity_signal` with `outcome=ambiguous` + `supervisor.resolution` with `outcome=unresolved` while `status=design_only`, or `outcome=resolved` if Option B was ever approved | Dispatch must not change. |
| 4 | Resolver unavailable → fallback direct | Simulate `SUPERVISORS_CONFIG_PATH` pointing at a missing file | Unchanged direct dispatch | `supervisor.resolution` with `reason=registry_entry_missing` or equivalent | Fallback must be silent to the user. |
| 5 | OpenClaw unavailable → fallback direct | Agent registered but unreachable (simulated) | Unchanged direct dispatch | `supervisor.resolution` with `outcome=unresolved` and fallback applied | Only applies after Option A. |
| 6 | Supervisor error → fallback direct | Force exception inside `_emit_supervisor_observability` | Unchanged direct dispatch | `supervisor_observability_failed` logged at warning level | Monitor flags it under safety triggers. |
| 7 | Raw text sentinel — no leakage | Inject sentinel string in task text | Unchanged direct dispatch | No event field contains the sentinel | Whitelist in `infra/ops_logger.py` enforces this. |
| 8 | `should_block` remains false | Any of the above cases | Unchanged direct dispatch | Every event has `fields.should_block` either absent or `false` | Critical rollback trigger if violated. |
| 9 | Monitor decision | Run `python scripts/monitor_supervisor_observability.py --simulate --since-minutes 60` | N/A | `PASS_MONITORING` or `WATCH` | `INVESTIGATE` or `ROLLBACK_RECOMMENDED` stops progress. |
| 10 | OODA / self-eval regression | Run `system.ooda_report` and `system.self_eval` manually | Both complete successfully | N/A | Confirms no regression from supervisor wiring. |
| 11 | Structured telemetry visible in `ops_log.jsonl` | Ambiguous improvement task processed | N/A | JSONL row with `event` starting `supervisor.` and sanitized `fields` | Sink is reachable. |
| 12 | No `supervisor_hint` added | Inspect envelope for any processed task | N/A | Envelope must **not** contain a `supervisor_hint` field | This readiness PR and the current runtime do not introduce `supervisor_hint`. |

Pattern: the "Expected dispatch" column is always "Unchanged." Supervisor observability never changes the dispatch result in Phase 6B.

## 9. Rollback plan

### Rollback actions

1. **Revert config flip** (only if Option B was ever applied): `git revert <commit-that-flipped-supervisors.yaml>`; verify `grep "status:" config/supervisors.yaml` shows `design_only`.
2. **Remove OpenClaw registration** (only if Option A was ever applied): follow section 7 "rollback registration" checklist. Confirm `openclaw agents list` no longer shows `improvement-supervisor`.
3. **Restart / reload services if required:** `systemctl --user restart openclaw-dispatcher.service` and `systemctl --user status openclaw-dispatcher.service --no-pager`. Only if the registration mechanism requires a restart for the change to take effect.
4. **Run monitor after rollback:** `python scripts/monitor_supervisor_observability.py --simulate --since-minutes 60`. Expect `PASS_MONITORING` or `WATCH` with 0 supervisor events.
5. **Update Linear UMB-173 / Notion Phase 5 page** with: rollback trigger, rollback commit/command, post-rollback monitor report, residual risk.
6. **Reconfirm invariants:** `config/supervisors.yaml` shows `status: "design_only"`; `improvement-supervisor` absent from OpenClaw; `dispatcher/router.py` still contains non-blocking observability-only wiring unchanged by rollback (Phase 5 / 6A code stays).

### Rollback triggers (aligned with `docs/75` section 9 and `docs/76` section 4)

Any one of these triggers requires immediate rollback:

- `should_block=True` observed in any event or log line (> 0 occurrences).
- Supervisor event emitted for a non-improvement team.
- Raw task text appears in structured logs or `ops_log.jsonl` supervisor fields.
- `supervisor_observability_failed` fires with a pattern (not a one-off), or its count exceeds baseline.
- Dispatch blocking observed (tasks rejected or delayed correlated with supervisor wiring).
- Worker or dispatcher health regression correlated with the activation commit (crash loop, elevated failure rate, latency p95 increase > 100 ms vs baseline).
- OpenClaw unexpected behavior (agent booted but started invoking tools on its own, or responded to traffic it should not have received).
- Config validation errors (`validate_supervisor_config_consistency()` returns errors).

## 10. Observability requirements

### Monitor commands

```bash
# 60-minute window
python scripts/monitor_supervisor_observability.py --simulate --since-minutes 60

# 24-hour window
python scripts/monitor_supervisor_observability.py --simulate --since-minutes 1440

# 48-hour window
python scripts/monitor_supervisor_observability.py --simulate --since-minutes 2880
```

The `--simulate` flag runs the local simulation against the pure building blocks from `dispatcher/supervisor_observability.py`. It is a sanity check that is independent of live traffic and must always pass. See `docs/76` for the full runbook.

### Expected structured supervisor event shape

From `infra/ops_logger.py` sink (Phase 6A):

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
  "fields": { "is_ambiguous": true, "reason": "positive_keyword_match" }
}
```

Fields under `fields` are whitelisted by `_SAFE_SUPERVISOR_FIELD_KEYS`. Free-text keys (`text`, `prompt`, `original_request`, `query`, `question`) are dropped and must never appear.

### Safety flags (monitor must report all 0)

- `supervisor_observability_failed` lines count.
- `should_block_true_count`.
- `non_improvement_event_count`.
- `raw_text_leakage_suspected_count`.
- `malformed_event_count`.
- `error_event_count`.

### Recommendation levels (from `docs/76`)

| Level | Meaning | Expected in Phase 6B readiness |
|-------|---------|-------------------------------|
| `PASS_MONITORING` | All sources healthy, simulation clean, structured events present. | Target state after activation, once organic ambiguous traffic has been observed. |
| `WATCH` | No events found or some sources unavailable. Not a failure. | Current state (48h WATCH with 0 events). |
| `INVESTIGATE` | Simulation failure, elevated failure rate, unexpected supervisor failure lines. | Must not appear. Requires manual review if it does. |
| `ROLLBACK_RECOMMENDED` | Critical condition detected. | Must not appear. Triggers section 9 rollback. |

### Expected behavior when there is no organic traffic

Phase 6B activation readiness accepts `WATCH` as healthy when no ambiguous improvement traffic has entered the system. `WATCH` with 0 events and 0 safety flags is not a failure and not a gate against progressing the readiness doc. It **is** a gate against claiming `PASS_MONITORING` without evidence; a `PASS_MONITORING` claim requires at least one real structured event or an explicit David waiver (precondition #4).

## 11. Go / No-Go table

| Decision | Condition | Required evidence |
|----------|-----------|-------------------|
| GO to register agent (Option A) | David approval + preconditions 1, 2, 3, 5, 6, 7, 8, 9, 10 | Written approval, monitor report with 0 safety flags, rollback commit SHA, smoke owner, Linear/Notion updated. |
| GO to flip config `active` (Option B) | Option A completed clean for ≥ 48 h + David approval | Option A monitor reports, no rollback triggers fired, Linear/Notion comment recording the Option A result. |
| NO-GO | Any precondition missing, any monitor safety flag non-zero, or no David approval | Monitor report showing the failure, or absence of approval message. Do not proceed. |
| ROLLBACK | Any rollback trigger from section 9 fires | Monitor report or log excerpt showing the trigger, updated UMB-173/Notion, post-rollback monitor report. |

## 12. Ownership

| Role | Responsibility |
|------|----------------|
| **David** | Final activation approval. Final rollback authority. Only David can authorize any step in section 5 or any option in section 4. |
| **Copilot** | Reviews and merges this docs PR. Reviews and merges future smoke reports and activation evidence. Does not perform runtime activation. |
| **Opus / Cursor** | Implements runtime wiring changes only after David approval. Produces activation PRs per the staircase in section 5. |
| **Rick / AI Orchestrator** | Coordinates the sequence. Persists evidence to Linear (UMB-173) and Notion. Re-runs monitor between steps. Escalates to David if any safety flag lights up. |

## 13. Explicit non-goals

This PR and this document are explicitly **not**:

- **Not an activation.** No step in section 4 or 5 is executed by this PR.
- **Not a config change.** `config/supervisors.yaml` and `config/teams.yaml` are untouched.
- **Not an OpenClaw registration.** `~/.openclaw/openclaw.json` and OpenClaw workspace bindings are untouched.
- **Not introducing `supervisor_hint`.** The envelope schema is unchanged. `supervisor_hint` does not exist at runtime today and is not added. Mentions of `supervisor_hint` in this document and in the ROLE.md are design references carried forward from `docs/71` / `docs/72` and are explicitly marked as not active and not to be added in this PR.
- **Not enabling automatic delegation.** The supervisor does not delegate tasks, does not enqueue work, does not call `rick-delivery` or `rick-orchestrator` automatically.
- **Not enabling Linear / Notion runtime calls.** No `linear.*` or `notion.*` calls from the supervisor path. Linear UMB-173 and Notion Phase 5 page updates for this PR are performed manually by the agent owner via existing CLI/API, not via runtime wiring.
- **Not persisting raw task text.** The `OpsLogger.supervisor_event()` whitelist in `infra/ops_logger.py` continues to drop free-text keys. This PR adds no new sink path.
- **Not blocking dispatch.** `should_block` remains `False` on every path. No dispatch is rejected or delayed.

## 14. Relationship to previous documents

| Document | Relationship |
|----------|--------------|
| [`docs/71-supervisor-routing-contract.md`](71-supervisor-routing-contract.md) | Overall supervisor routing contract. This plan operationalizes readiness for its implementation gate #7 (David approval). |
| [`docs/72-ambiguous-improvement-task-detection.md`](72-ambiguous-improvement-task-detection.md) | Ambiguity detection rules used by `detect_ambiguity_signal()`. Phase 6B assumes this detector's semantics unchanged. |
| [`docs/73-supervisor-resolution-contract.md`](73-supervisor-resolution-contract.md) | Resolution contract and safety rules. Rollback triggers in section 9 preserve those safety rules. |
| [`docs/74-closed-ooda-loop-contract.md`](74-closed-ooda-loop-contract.md) | Closed loop contract. Phase 6B explicitly does not automate the loop. |
| [`docs/75-improvement-supervisor-activation-playbook.md`](75-improvement-supervisor-activation-playbook.md) | Activation playbook. This plan extends the playbook with Phase 6B-specific options (A/B/C), recommended staircase, and explicit hypothetical config diff. |
| [`docs/76-supervisor-observability-monitoring.md`](76-supervisor-observability-monitoring.md) | Monitoring runbook. This plan references its PASS / WATCH / INVESTIGATE / ROLLBACK_RECOMMENDED semantics for the Go/No-Go table. |
| [`openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md`](../openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md) | Hardened in the same PR. Defines identity, boundaries, safety rules, and activation preconditions the supervisor must follow once it ever becomes a runtime agent. |
