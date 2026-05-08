---
id: o7-smoke-tournament-as-rick-2026-05-08
title: O7 smoke — simulated tournament from rick (manual, no wrapper yet)
status: done
verdict: verde
owner: copilot-vps
reviewer: copilot-chat
phase: O7-smoke
depends_on:
  - docs/79-tournament-protocol-openclaw-native.md (v1 contract)
  - docs/adr/tournament-on-openclaw-primitives.md (Decision A — Wrapper-only)
created: 2026-05-08
closed: 2026-05-08
notes: |
  tournament_id: umbral-agent-stack-375-fa19920
  issue: https://github.com/Umbral-Bot/umbral-agent-stack/issues/375
  winner PR (merged): https://github.com/Umbral-Bot/umbral-agent-stack/pull/376 (lane docs-concise, +1/-1)
  loser PR (closed, branch preserved): https://github.com/Umbral-Bot/umbral-agent-stack/pull/377 (lane docs-explanatory, +2/-2)
  report: reports/tournaments/umbral-agent-stack-375-fa19920.md
  metrics: reports/tournaments/umbral-agent-stack-375-fa19920.metrics.json
  divergences: PAT lacks issues:write (no contract comment on issue); pre-existing untracked reports/*.json in worktree
---

# O7 smoke — manual tournament simulation as if launched from rick

## Why

The wrapper skill `multi-agent-tournament-orchestrator` is not yet built (~12-15h
pending). The protocol §7 mandates an end-to-end smoke before the first real
tournament. We want a **manual simulation** of the protocol on a trivial issue,
driven by Copilot-VPS playing the role rick would play — to validate that the
contract works end-to-end on the current OpenClaw + `gh` + `git` primitives,
WITHOUT needing the wrapper or `maxSpawnDepth >= 2`.

This is a **simulation/smoke**, not the first real tournament. No production
code is changed; the issue must be trivial.

## Hard constraints

- Apply skill `secret-output-guard` to every output (report, PR body, mailbox
  reply). Any leak aborts the smoke.
- `cleanup_policy: keep-losers` (per protocol v1 default).
- Lanes: **N=2**. Single repo: `umbral-agent-stack`. Branch base: `main`
  (must be fast-forward clean).
- Issue: trivial doc/typo fix. **Do NOT** touch runtime code (worker/, dispatcher/,
  openclaw/, identity/, config/, pyproject.toml). If no suitable issue exists,
  open a tiny one (e.g. "fix typo in README §X").
- No `vps-deploy-after-edit` triggered (smoke only touches docs).
- Total wall-clock budget: 60 min. If exceeded, abort, kill any orphan subagents,
  report partial state.
- USD budget cap: 0.50 (sum of both lanes).

## Pre-flight (mandatory)

```bash
cd ~/umbral-agent-stack && git checkout main && git pull --ff-only origin main
git status --porcelain     # must be empty
gh auth status             # must be green
openclaw status --all      # gateway up
```

Pick or open the trivial issue. Capture `<issue_url>` + `<issue_number>`.

Compute `tournament_id` per protocol §2:
`tournament_id="umbral-agent-stack-${issue_number}-$(git rev-parse --short=7 main)"`

## Simulation flow (manual, single-operator playing rick)

### Step 1 — Lane A (specialty: docs-concise)

```bash
git checkout -b "tournament/${tournament_id}/lane-docs-concise"
# Apply the trivial fix in the most concise way (smallest diff).
git add -A && git commit -m "docs: <fix> [tournament:${tournament_id}:docs-concise]"
git push -u origin "tournament/${tournament_id}/lane-docs-concise"
gh pr create \
  --base main \
  --title "[tournament:${tournament_id}:docs-concise] <issue title>" \
  --body "Lane: docs-concise. Approach: minimal diff. Issue: <issue_url>."
```

Capture: PR URL, diff stats (`gh pr diff <pr> --stat`), checks status.

### Step 2 — Lane B (specialty: docs-explanatory)

```bash
git checkout main && git pull --ff-only origin main
git checkout -b "tournament/${tournament_id}/lane-docs-explanatory"
# Apply the same trivial fix but with an extra clarifying sentence / context line.
git add -A && git commit -m "docs: <fix> + clarification [tournament:${tournament_id}:docs-explanatory]"
git push -u origin "tournament/${tournament_id}/lane-docs-explanatory"
gh pr create \
  --base main \
  --title "[tournament:${tournament_id}:docs-explanatory] <issue title>" \
  --body "Lane: docs-explanatory. Approach: fix + 1 clarifying sentence. Issue: <issue_url>."
```

Capture: PR URL, diff stats, checks status.

### Step 3 — Winner selection (rubric)

**Rubric for this smoke (per protocol §7 default):** PR with the smallest line
delta that still passes CI wins.

Apply the rubric. Document the decision in the report (which lane won + line
counts). Tie-break: prefer `docs-concise`.

### Step 4 — Merge winner, close loser

```bash
gh pr merge <winner_pr> --squash --delete-branch
gh pr close  <loser_pr> --comment "tournament loser, kept for forensic per cleanup_policy=keep-losers"
# Loser branch is preserved (no --delete-branch on close).
```

### Step 5 — Cleanup verification

```bash
openclaw tasks list --runtime subagent --json | jq '. | length'   # expect 0 orphans
gh pr list --search "[tournament:${tournament_id}:" --state all  # 1 merged + 1 closed
git fetch --prune origin                                          # winner branch gone, loser preserved
```

### Step 6 — Metrics

Emit `reports/tournaments/${tournament_id}.metrics.json` per protocol §6 schema:

```json
{
  "tournament_id": "<id>",
  "issue_id": "Umbral-Bot/umbral-agent-stack#<n>",
  "lanes_total": 2,
  "lanes_completed": 2,
  "lanes_pr_mergeable": 2,
  "winner_specialty": "docs-concise",
  "time_to_first_pr_seconds": <n>,
  "time_to_winner_seconds": <n>,
  "tokens_total": null,
  "usd_estimated": <n>,
  "mode": "manual-simulation"
}
```

Fields `tokens_total: null` is acceptable in manual mode.

## Acceptance gates

- [ ] `tournament_id` consistent in 2 branch names + 2 PR titles + metrics file.
- [ ] Both lanes produced a PR. Both PRs CI green or trivially-no-CI (docs).
- [ ] Winner picked by rubric, merged via `--squash --delete-branch`.
- [ ] Loser closed with comment, branch preserved.
- [ ] No orphan subagents (`openclaw tasks list --runtime subagent --json` returns `[]`).
- [ ] No secrets in any output (report, PR bodies, mailbox reply). `secret-output-guard` applied.
- [ ] `/health` of worker still `{"ok":true}` (smoke must not affect worker).

## Deliverables

1. Report `reports/tournaments/${tournament_id}.md` — pre-flight evidence,
   step-by-step log, rubric decision, cleanup verification, verdict.
2. Metrics JSON `reports/tournaments/${tournament_id}.metrics.json` (schema above).
3. Branch `copilot-vps/o7-smoke-tournament-${tournament_id}` with the report
   + metrics committed → PR to `main`.
4. Update this task: `status: done`, `verdict: <color>`, link to report PR + the
   merged tournament-winner PR + the closed loser PR.

## Out of scope (do NOT do in this smoke)

- Real `sessions_spawn` of subagents — this is a manual simulation; the
  operator plays both lanes sequentially. The wrapper smoke (with real
  spawning) comes later, after `multi-agent-tournament-orchestrator` exists
  AND `maxSpawnDepth >= 2` is flipped.
- Touching the wrapper skill code or `openclaw.json`.
- More than 2 lanes.
- Tournament on non-trivial issues.

## Rollback

If anything goes sideways:

```bash
# Kill any orphan subagents
openclaw tasks list --runtime subagent --json | jq -r '.[].id' | xargs -r -n1 openclaw subagents kill
# Close all open tournament PRs without merging
gh pr list --search "[tournament:${tournament_id}:" --state open --json number -q '.[].number' \
  | xargs -r -n1 -I{} gh pr close {} --comment "smoke aborted"
# Delete remote branches
git push origin --delete "tournament/${tournament_id}/lane-docs-concise" || true
git push origin --delete "tournament/${tournament_id}/lane-docs-explanatory" || true
# Verify worker untouched
curl -fsS http://127.0.0.1:8088/health
```

Then file the divergence as the finding in the report. Do NOT retry without
sign-off from David.
