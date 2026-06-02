---
name: multi-agent-tournament-orchestrator
description: >-
  Thin OpenClaw-native wrapper for Mega 1 tournaments: pre-flight, N parallel
  lanes via sessions_spawn, PR collection, winner rubric, merge + metrics.
  Runs only from agent main in standalone session (G-D1b). NOT the ideational
  tournament.run skill — see docs/79-tournament-protocol-openclaw-native.md.
metadata:
  openclaw:
    emoji: "🏁"
    requires:
      env: []
---

# Multi-agent tournament orchestrator (OpenClaw-native)

Wrapper skill implementing [`docs/79-tournament-protocol-openclaw-native.md`](../../../../docs/79-tournament-protocol-openclaw-native.md) and launch rules in [`docs/architecture/tournament-protocol.md`](../../../../docs/architecture/tournament-protocol.md).

**Status:** v1 procedure (D2.1) — executable steps below. Real spawn requires D2.2 dry-run pass + David gate on merge.

## When to use

- David requests a **real** implementation tournament (Git branches + PRs + winner merge).
- Signals: "torneo real", "torneo de implementación", "competir en ramas", benchmark on an issue.
- **Do not use** for ideational debate — use skill `tournament` + `tournament.run` instead.

## When to abort (hard stops)

| Condition | Action |
|---|---|
| Current session is nested (no `sessions_spawn` in tool list) | STOP — ISSUE-001 / G-D1b |
| `agents.defaults.subagents.maxSpawnDepth < 2` | STOP — run G-D1a + restart |
| `git status` not clean in tournament repo | STOP — ask David to stash/commit |
| `git fetch origin main` not fast-forward | STOP — rebase/merge main first |
| Lane count ∉ [2, 5] or duplicate `agent_id` | STOP — fix spec |
| Lane `agent_id` not in parent `allowAgents` | STOP — fix openclaw.json |
| `gh auth status` not green | STOP — fix gh auth on VPS |
| David has not approved this tournament run | STOP — publication-gatekeeper |

## Launch constraints (G-D1b — mandatory)

1. **Agent:** invoke from **`main`**, not from nested `rick-orchestrator`.
2. **Session:** standalone entry only — `sessions_spawn` must appear in the active tool set ([ISSUE-001](../../../../docs/external-context/openclaw-known-issues.md)).
3. If `sessions_spawn` is missing → **STOP** and report ISSUE-001 / wrong entry surface.

**Allowed surfaces:** OpenClaw Control UI chat with `main`; CLI `openclaw agent --agent main` in a **new** session; `/skills run multi-agent-tournament-orchestrator …` on `main`.

**Forbidden:** Telegram → nested `rick-orchestrator`; any nested subagent as spawn parent.

---

## Input — tournament spec

YAML or JSON path passed as first argument. Contract: `docs/79` §2–§3.

```yaml
tournament_id: umbral-agent-stack-321-7752e42   # or omit → auto from issue + short sha
issue_id: Umbral-Bot/umbral-agent-stack#321
issue_url: https://github.com/Umbral-Bot/umbral-agent-stack/issues/321
issue_title: "Fix typo in tournament docs"
repo_path: ~/umbral-agent-stack                 # default on VPS
usd_budget_cap: 0.50                          # optional
cleanup_policy: keep-losers                     # keep-losers | soft-close
winner_rubric: |
  Pick the PR that best satisfies the issue with the smallest correct diff.
  Tie-break: fewer lines changed, then green checks first.
lanes:
  - specialty: backend-typescript
    agent_id: rick-delivery
    task_template: |
      # Tarea: {{issue_title}}
      Issue: {{issue_url}}
      Branch: tournament/{{tournament_id}}/lane-backend-typescript
      ...
  - specialty: lane-python
    agent_id: rick-delivery
    task_template: |
      ...
```

**Invariants:** 2–5 lanes; distinct `agent_id` per lane; branch `tournament/<tournament_id>/lane-<specialty>`; PR title `[tournament:<tournament_id>:<specialty>] <issue_title>`. A lane is complete only after branch push + verified PR URL; subagent `finalStatus=success` without PR is `lane_incomplete`.

Example smoke spec: `examples/smoke-tournament-spec.yaml` in this skill folder.

---

## Phase 0 — Parse spec

1. Load YAML/JSON; validate required fields: `issue_id`, `lanes`, `winner_rubric`.
2. If `tournament_id` missing: `<repo-slug>-<issue_num>-<git rev-parse --short=8 HEAD>`.
3. Render each lane `task_template` with `{{tournament_id}}`, `{{issue_url}}`, `{{issue_title}}`, `{{specialty}}`.
4. Compute `runTimeoutSeconds` per lane if `usd_budget_cap` set (ADR §5 — use lane model cost table; cap per lane = budget / N).

---

## Phase 1 — Pre-flight (wrapper aborts if any fails)

Execute in order; emit a checklist table to David before spawn.

| # | Check | How |
|---|---|---|
| 1 | G-D1b standalone | Confirm `sessions_spawn` in **current** tool whitelist. If absent → abort ISSUE-001. |
| 2 | maxSpawnDepth | `jq '.agents.defaults.subagents.maxSpawnDepth // 1' ~/.openclaw/openclaw.json` ≥ 2 |
| 3 | Git clean | `cd <repo_path> && git status --porcelain` empty |
| 4 | Main ff-only | `git fetch origin main && git merge-base --is-ancestor HEAD origin/main` (on main) |
| 5 | allowAgents | Each lane `agent_id` allowed for `main` subagents |
| 6 | Lane agents coding profile | Each lane agent has `tools.profile: coding` (git/gh) |
| 7 | gh auth | `gh auth status` in repo_path |
| 8 | N lanes | 2 ≤ N ≤ 5, unique `agent_id` |
| 9 | Budget | If `usd_budget_cap`, each lane gets finite `runTimeoutSeconds` |

**Dry-run without spawn:** run `scripts/openclaw/tournament-preflight-dry-run.sh <spec.yaml>` on VPS (D2.2).

---

## Phase 2 — Spawn lanes (parallel)

For each lane `L` in `lanes[]`:

```text
sessions_spawn({
  "runtime": "subagent",
  "agentId": "<L.agent_id>",
  "label": "tournament-<tournament_id>-<L.specialty>",
  "timeoutSeconds": <L.runTimeoutSeconds or 1800>,
  "model": "<L.model if set>",
  "task": "<rendered task_template>"
})
```

**Task body must include (append if missing):**

```markdown
## Tournament lane contract (read-only)
- Branch: `tournament/<tournament_id>/lane-<specialty>` from updated `main`.
- Do NOT merge your own PR.
- Push the branch and create PR with title `[tournament:<tournament_id>:<specialty>] <issue_title>`.
- Announce back to parent with JSON:
  {"pr_url":"...","diff_stats":"...","checks_status":"...","specialty":"<specialty>"}
```

**Orchestrator rules:**

- Fire all N spawns in one turn (parallel fan-out).
- Record `label`, `runId`, `childSessionKey` per lane ([subagent-result-integration](../subagent-result-integration/SKILL.md)).
- Treat `status: accepted` as started only — wait for push-completion announces.

---

## Phase 3 — Collect PRs

1. Wait until N announce-backs received or all lanes timeout.
2. For each lane, require `branch_pushed && pr_url_present && gh_pr_view_ok`.
3. For each announce, parse `pr_url`; verify title matches `[tournament:<tournament_id>:<specialty>]`.
4. Enrich with `gh pr view <url> --json url,headRefName,title,mergeable,statusCheckRollup,additions,deletions`.
5. Verify `headRefName == tournament/<tournament_id>/lane-<specialty>`.
6. If the subagent reports `finalStatus=success` but no verified PR exists, mark the lane `lane_incomplete`; do not count it in `lanes_completed`.
7. Continue only if ≥2 verified PRs are present; otherwise abort tournament before judge.

Record `time_to_first_pr_seconds` from spawn start to first valid PR.

---

## Phase 4 — Judge (orchestrator turn on `main`)

1. Load `winner_rubric` + verified PR metadata into one message. Exclude `lane_incomplete` lanes from winner consideration.
2. Decide `winner_specialty` explicitly (name the lane, cite PR URL).
3. **David gate:** if tournament is not smoke and David has not said "ok, merge winner" → stop after recommendation, do not merge.

Smoke rubric default: "PR with fewer total line changes wins; tie → first green checks."

---

## Phase 5 — Merge winner + close losers

Only after explicit David approval for non-smoke runs.

```bash
gh pr merge <winner_pr_number> --squash --delete-branch=false
```

For each loser PR per `cleanup_policy`:

| Policy | Action |
|---|---|
| `keep-losers` (default) | `gh pr close <n> --comment "Tournament loser — branch kept for forensics (tournament_id=<id>)"` |
| `soft-close` | Same + label `tournament-loser` if available |

Do **not** delete loser branches in v1.

Record `time_to_winner_seconds`.

---

## Phase 6 — Cleanup

```text
/subagents kill all
```

Verify no live tournament lane children. Rely on OpenClaw auto-archive (~60 min) for transcripts.

---

## Phase 7 — Metrics (post-merge)

Emit JSON (stdout + optional Notion/Linear when wired):

```json
{
  "tournament_id": "<id>",
  "issue_id": "<owner/repo>#<n>",
  "lanes_total": 3,
  "lanes_completed": 3,
  "lane_incomplete": 0,
  "lanes_pr_mergeable": 2,
  "winner_specialty": "backend-typescript",
  "winner_pr_url": "https://github.com/.../pull/...",
  "time_to_first_pr_seconds": 412,
  "time_to_winner_seconds": 1840,
  "tokens_total": null,
  "usd_estimated": null
}
```

Fill `tokens_total` / `usd_estimated` from `openclaw tasks list --runtime subagent --json` when available.

Post to Notion Mission Control + Linear comment — **when D4 wired**; until then, paste JSON to tournament task log.

---

## Smoke (mandatory before first real tournament)

Per `docs/79` §7:

- Trivial doc typo issue; N=2 lanes; trivial rubric.
- Run full flow once; David verifies merge + loser close + metrics shape.
- **No production issue** until smoke passes.

Checklist reference: `docs/ops/tournament-d2.2-dry-run-checklist.md`.

---

## Deploy path (repo → VPS)

1. Skill in `openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/`.
2. Cursor **push `main`** before Copilot-VPS handoff.
3. VPS: workspace sync per OpenClaw runbook → verify skill listed for `main`.
4. Run D2.2 dry-run script; then smoke with David present.

---

## References

- Architecture (launch): `docs/architecture/tournament-protocol.md`
- Contract: `docs/79-tournament-protocol-openclaw-native.md`
- ADR: `docs/adr/tournament-on-openclaw-primitives.md`
- Dry-run: `docs/ops/tournament-d2.2-dry-run-checklist.md`
- Task: `.agents/tasks/2026-06-01-003-d2.1-multi-agent-tournament-orchestrator-skill.md`
