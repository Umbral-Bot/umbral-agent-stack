# ADR — Tournament format on OpenClaw native primitives

- **Date:** 2026-05-06
- **Status:** Accepted
- **Owner:** copilot-vps (spike) — confirmed by David before first tournament
- **Closes:** O7.0 (Plan Q2-2026 → roadmap line 467)
- **Unblocks:** O7 (formato tournament estándar), pre-requisito de S2 first real tournament
- **Related:** [.agents/tasks/2026-05-06-014-copilot-vps-spike-openclaw-subagents-tournament.md](../../.agents/tasks/2026-05-06-014-copilot-vps-spike-openclaw-subagents-tournament.md)

---

## Decision

**A — Wrapper-only.**

The OpenClaw native primitives `sessions_spawn` / `/subagents` (plus the `parallel-specialist-lanes` design pattern) cover **≥ 80 %** of the tournament flow. We will write a thin OpenClaw skill `multi-agent-tournament-orchestrator` that orchestrates over native primitives. **Do not** reimplement spawn / isolation / concurrency / cleanup / kill / nesting in Python.

Estimated implementation: **~12–15 h** (see §6).

---

## 1. OpenClaw version evaluated

```
$ openclaw --version
OpenClaw 2026.5.3-1 (2eae30e)
```

Installed at `/home/rick/.npm-global/bin/openclaw` (npm global). Bundled docs at `/home/rick/.npm-global/lib/node_modules/openclaw/docs/`.

## 2. Native primitives — verified

### 2.1 `subagents` is a real primitive

Source: `docs/tools/subagents.md` (557 lines, summary "Spawn isolated background agent runs that announce results back to the requester chat").

- **Tool:** `sessions_spawn` (exposed under `coding` and `full` tool profiles).
- **Slash command:** `/subagents {list, kill, log, info, send, steer, spawn}`.
- **Session key shape:** `agent:<agentId>:subagent:<uuid>` (depth 1) and `…:subagent:<uuid>:subagent:<uuid>` (depth 2).

Capabilities verified in source + config:

| Capability | Native? | Evidence |
|---|---|---|
| Parallel isolated child runs | Yes | `sessions_spawn` with `context: "isolated"` (default). Each child gets its own transcript + token budget. |
| Per-spawn model / thinking / timeout | Yes | `sessions_spawn` params: `model`, `thinking`, `runTimeoutSeconds`. |
| Push-based completion | Yes | "Completion is push-based. Once spawned, do **not** poll." Child announces back to parent on finish. |
| Auto-archive losers | Yes | `archiveAfterMinutes` (default 60). `cleanup: "delete"` archives immediately after announce. |
| Concurrency caps | Yes | `maxChildrenPerAgent` (default 5), `maxConcurrent` (default 8 — confirmed via `openclaw config get agents.defaults.subagents` → `{"maxConcurrent": 8}`). |
| Kill switch | Yes | `/subagents kill <id\|#\|all>`. |
| Per-target allowlist | Yes | `agents.list[].subagents.allowAgents` — already configured in this VPS (`rick-orchestrator` allowed to target `rick-{communication-director, delivery, ops, qa, tracker, linkedin-writer}`). |
| Nesting depth 2 (orchestrator pattern) | Yes | `maxSpawnDepth: 2` → main → orchestrator (depth 1) → workers (depth 2). Depth-2 leaves cannot spawn further. |
| Sandbox enforcement | Yes | `sandbox: "require"` rejects spawn unless child runtime is sandboxed. |
| Tracked as background tasks | Yes | `openclaw tasks list --runtime subagent` (CLI). Evidence: 3 historical runs already in store: `9604ea0a` (rick-ops), `717373ba` + `3ef5c451` (rick-tracker). JSON output via `--json`. |

### 2.2 `parallel-specialist-lanes` is a **pattern**, not a config block

Source: `docs/concepts/parallel-specialist-lanes.md` (127 lines).

A "lane" = an isolated agent with a **written contract** (Owns / Does not own / Chat budget / Handoff / Tool posture). It is the design pattern that tells you **which** agents to wire as subagent targets, not a separate runtime. Phase 2 of the rollout uses concrete config knobs that are already real: `agents.defaults.maxConcurrent`, `agents.defaults.subagents.maxConcurrent`, `messages.queue.{mode,debounceMs,cap,drop}`.

**Implication:** the Plan Q2-2026 phrasing "primitivas `subagents` + `parallel-specialist-lanes`" maps to **one** native primitive (`subagents`) plus **one** design pattern that we already largely follow (the 7 `rick-*` agents in `~/.openclaw/agents/` are exactly such lanes).

## 3. Spike status

A **live `sessions_spawn` smoke** was deliberately **not** executed in this spike. Rationale:

- The 3 historical subagent runs in `openclaw tasks list --runtime subagent` already prove the primitive works end-to-end (spawn → run → archive) on this VPS.
- A live spawn would consume tokens against an active production agent (`rick-orchestrator` or one of the lane agents) and risk disrupting in-flight ops with announce noise.
- The first end-to-end tournament smoke belongs in the wrapper's own delivery, on a synthetic agent or a sandboxed run, not in the discovery spike.

Confidence is sufficient from: bundled docs + 3 historical successful spawn entries + live `subagents` config blocks in `~/.openclaw/openclaw.json`.

## 4. Gap analysis (tournament requirements)

| Tournament requirement | Cubierto nativo | Gap (qué cubre el wrapper) |
|---|---|---|
| 1 issue → N branches paralelos | **Spawn part: yes** (N `sessions_spawn` calls from a depth-1 orchestrator, each with a different specialty `task`, all auto-respect `maxConcurrent`). | Branch creation per lane (`tournament/<issue>/lane-<specialty>`) is git work, not OpenClaw. The lane's task body does it. |
| Métricas: PRs creados, % mergeable, tiempo revisión | **Per-task primitives: yes** (`status`, timestamps, run/token stats, delivery state, transcript path). | Aggregation: count PRs, mergeable %, time-to-review. Wrapper reads `openclaw tasks list --runtime subagent --json` + `gh pr list` and renders. |
| Cap tokens / kill switch | **Yes**: `runTimeoutSeconds` + `/subagents kill`. Cheaper-model-for-children via `agents.defaults.subagents.model`. | Hard USD-budget cap is not native. Wrapper can pre-set a `runTimeoutSeconds` derived from `<budget> / <token_cost_per_sec>` and call `/subagents kill` if exceeded. |
| Selección de winner | **Pattern-only**: announce-chain delivers all child summaries to the depth-1 orchestrator. The orchestrator prompt decides. | Winner rubric = wrapper concern (skill prompt content). No infra build. |
| Cleanup branches losers | **Sessions: auto-archive native**. **Git branches: app-side**. | Wrapper runs `gh pr close <loser>` + `git push origin :tournament/<issue>/lane-<loser>` after winner is picked. |
| Integración con Mission Control (O13.4 dispatcher) | **Hook native**: `openclaw tasks list --runtime subagent --json`. | Wrapper polls (or subscribes to gateway events) and pushes a Notion/Linear update with tournament state. |

**Coverage estimate: 5/6 requirements have ≥ 80 % native coverage. 1/6 (winner selection) is pattern-only by design** — that is correct, because winner rubric must live with the team that owns the issue, not in the runtime.

## 5. What the wrapper skill `multi-agent-tournament-orchestrator` must contain

**Pure orchestration, no runtime reimplementation.** Boundaries:

1. **Inputs:** `issue_id`, `lanes: [{specialty, task_template, model?, runTimeoutSeconds?}]`, `winner_rubric` (text), `usd_budget_cap` (optional).
2. **Pre-flight:**
   - Verify the calling agent is allowed to target each lane agent via `subagents.allowAgents`.
   - Verify `agents.defaults.subagents.maxSpawnDepth >= 2` (orchestrator pattern requires depth 2).
   - Translate `usd_budget_cap` → `runTimeoutSeconds` per lane using the lane's model cost.
3. **Spawn (uses native):** N `sessions_spawn` calls, each with `agentId=<lane-agent>`, `task=<rendered template + branch convention>`, `model`, `runTimeoutSeconds`, `cleanup: "keep"` (we want to inspect losers before delete).
4. **Lane task body** (handed to each child as the `task` prompt):
   - Create branch `tournament/<issue>/lane-<specialty>`.
   - Implement.
   - `gh pr create` with title `[tournament:<issue>:<specialty>]`.
   - Announce back: PR URL + diff stats + checks status.
5. **Winner pick** (orchestrator turn after all announces):
   - Apply `winner_rubric`.
   - Call `gh pr merge <winner> --squash`.
   - For each loser: `gh pr close --comment "tournament loser, kept for forensic"` + leave branch (we do NOT auto-delete loser branches in v1; soft-delete via `gh` only).
6. **Cleanup:** `/subagents kill all` for the orchestrator's children that didn't finish. Native auto-archive handles the rest (60-min default).
7. **Metrics:** read `openclaw tasks list --runtime subagent --json` + `gh pr view --json` for each PR. Emit one Notion update + one Linear comment per tournament.

**Components NOT to build** (covered by native):

- ❌ Spawn/fork/process management.
- ❌ Concurrency / lane queueing.
- ❌ Per-child sandbox.
- ❌ Auto-archive of sessions.
- ❌ Push-completion event bus.
- ❌ Per-task token/timing tracking.
- ❌ Kill switch.
- ❌ Per-agent allowlists.

## 6. Implementation estimate (Decision A)

| Component | Estimate |
|---|---|
| Skill `multi-agent-tournament-orchestrator/SKILL.md` (lane contract + winner rubric + handoff format) | 4–6 h |
| Per-lane task body template (branch convention + `gh pr create` + announce) | 3–4 h |
| Mission Control glue (read native task JSON + post to Notion/Linear) | 2–3 h |
| Smoke on a trivial real issue (NOT O1 hardening — that's the first real tournament) + retro | 2 h |
| **Total** | **~12–15 h** |

## 7. Pre-conditions before first tournament

These are checks the wrapper must run before spawn:

1. `~/.openclaw/openclaw.json` has `agents.defaults.subagents.maxSpawnDepth: 2`. **Currently the effective config returns only `{"maxConcurrent": 8}` for `agents.defaults.subagents` — `maxSpawnDepth` defaults to 1.** This must be flipped to 2 (or set per-agent on `rick-orchestrator`) before the first tournament. Documented as a config patch the wrapper installs (or as a one-line PR to add it to `openclaw.json` reviewed separately).
2. Each lane agent in `subagents.allowAgents` has the `coding` tool profile (so the lane agent itself can create branches and PRs). Today: `rick-orchestrator` allows the 6 `rick-*` agents; verify each has `tools.profile: "coding"`.
3. `gh auth status` green inside each lane agent's workspace. Today: `gh` works on the VPS as user `rick` via `GITHUB_TOKEN` (account `UmbralBIM`).

## 8. Why not B or C

- **B (Primitives insufficient):** rejected. Every claimed gap is either app-glue (git/PR/metrics) or pattern (winner rubric). None is a runtime gap. Implementing parallel-spawn / isolation / concurrency / kill in Python over OpenClaw would duplicate `sessions_spawn` and lose the push-completion + archive lifecycle that OpenClaw already wires correctly.
- **C (Hybrid):** rejected for v1. The natural "boundary" candidates are metrics aggregation and winner selection. Metrics are a thin read of `openclaw tasks list --json` — not enough surface to justify a Python service. Winner selection should live in the orchestrator agent's prompt, not in code, so that the team can edit the rubric without a deploy. Revisit C if the wrapper grows beyond 1 skill + 1 task template (re-eval after first 3 real tournaments).

## 9. Caveats / out-of-scope for this ADR

- **No live `sessions_spawn` smoke ran in this spike** (see §3). The first wrapper PR must include an end-to-end smoke before the first real tournament on O1 hardening.
- This ADR does **not** define the winner rubric content. That belongs in the skill's SKILL.md and is per-issue-class (typo fix vs. infra refactor have different rubrics).
- This ADR does **not** authorize editing `~/.openclaw/openclaw.json` to flip `maxSpawnDepth` — that change must come as its own PR with explicit David sign-off, since it's a runtime topology change (per skill `openclaw-vps-operator`).
