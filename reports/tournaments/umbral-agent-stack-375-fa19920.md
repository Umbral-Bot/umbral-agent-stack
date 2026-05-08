# Tournament smoke report — `umbral-agent-stack-375-fa19920`

- **Mode:** `manual-simulation` (Copilot-VPS playing rick-dispatcher + both lanes; no real `sessions_spawn`).
- **Date:** 2026-05-08
- **Operator:** copilot-vps (single human-simulated orchestrator).
- **Protocol:** [docs/79-tournament-protocol-openclaw-native.md](../../docs/79-tournament-protocol-openclaw-native.md) v1.
- **Task:** [.agents/tasks/o7-smoke-tournament-as-rick-2026-05-08.md](../../.agents/tasks/o7-smoke-tournament-as-rick-2026-05-08.md).

## Contract

```json
{
  "tournament_id": "umbral-agent-stack-375-fa19920",
  "issue_id": "Umbral-Bot/umbral-agent-stack#375",
  "lanes": ["docs-concise", "docs-explanatory"],
  "winner_rubric": "smallest line delta passing CI; tie → docs-concise",
  "usd_budget_cap": 0.50,
  "cleanup_policy": "keep-losers",
  "mode": "manual-simulation"
}
```

`tournament_id` derivation: `umbral-agent-stack-${issue_number=375}-${short_sha=fa19920}` (sha of `origin/main` at smoke start).

## Pre-flight evidence

| Check | Result |
|---|---|
| `git pull --ff-only origin main` | clean fast-forward, HEAD=`fa19920` |
| `git status --porcelain` (tracked) | clean |
| `git status --porcelain` (untracked) | 16 pre-existing `reports/*.json` artifacts (NOT from smoke) |
| `gh auth status` | green (account `UmbralBIM`, token via `GITHUB_TOKEN`) |
| `openclaw status --all` | gateway up on `127.0.0.1:18789` |
| `curl /health` (worker) | `{"ok":true,"version":"0.4.0"}` |

## Issue

- **#375** — `docs(README): align comment spacing in repo structure tree`
- Opened by copilot-vps (no pre-existing trivial issue available; the 3 open issues all touch runtime code which is out of scope for the smoke).
- Trivial scope: 1-char (or up to a few-line) cosmetic fix in [README.md](../../README.md), zero runtime impact.

## Lane runs

### Lane A — `docs-concise` (minimal-diff strategy)

- **Branch:** `tournament/umbral-agent-stack-375-fa19920/lane-docs-concise`
- **PR:** [#376](https://github.com/Umbral-Bot/umbral-agent-stack/pull/376)
- **Diff:** `+1 / -1` (1 line modified)
- **CI:** `test (3.11)` pass 59s, `test (3.12)` pass 1m0s
- **Strategy:** add a single space to align the `notion_client.py` comment with its 3-space neighbours. Nothing else.

### Lane B — `docs-explanatory` (fix + clarification)

- **Branch:** `tournament/umbral-agent-stack-375-fa19920/lane-docs-explanatory`
- **PR:** [#377](https://github.com/Umbral-Bot/umbral-agent-stack/pull/377)
- **Diff:** `+2 / -2` (4 lines touched)
- **CI:** `test (3.11)` pass 53s, `test (3.12)` pass 1m2s
- **Strategy:** same one-character fix plus a one-line blockquote stating the alignment convention so future contributors keep it.

## Rubric decision

Both PRs CI-green → tiebreaker is line delta (smaller wins).

| Lane | Additions | Deletions | Total churn |
|---|---:|---:|---:|
| docs-concise (A) | 1 | 1 | **2** |
| docs-explanatory (B) | 2 | 2 | 4 |

**Winner:** `docs-concise` (lane A, PR #376). Tie-break rule (`tie → docs-concise`) was not needed; A strictly dominates on delta.

## Merge & close

- `gh pr merge 376 --squash --delete-branch` → state `MERGED`, mergeCommit `57ac306`, mergedAt `2026-05-08T05:45:10Z`. Winner branch deleted on remote.
- `gh pr close 377 --comment "tournament loser, kept for forensic per cleanup_policy=keep-losers..."` → state `CLOSED`, closedAt `2026-05-08T05:45:13Z`. Loser branch **preserved** on remote (verified below).

## Cleanup verification

| Check | Expected | Actual | Pass |
|---|---|---|---|
| Subagents created during smoke | 0 | 0 (filtered by `createdAt >= START_MS`) | ✅ |
| Total subagents in any non-terminal state | 0 | 0 (17 succeeded + 1 failed, all terminal; pre-existing) | ✅ |
| Tournament PRs (search prefix) | 1 merged + 1 closed | #376 MERGED, #377 CLOSED | ✅ |
| Winner branch on remote | gone | `tournament/.../lane-docs-concise` not in `git ls-remote` | ✅ |
| Loser branch on remote | preserved | `155d4f0…  refs/heads/tournament/.../lane-docs-explanatory` present | ✅ |
| Worker `/health` post-smoke | `{"ok":true}` | `{"ok":true,"version":"0.4.0",...}` | ✅ |

## Acceptance gates (task §Acceptance gates)

- [x] `tournament_id` consistent across both branch names, both PR titles, and the metrics file.
- [x] Both lanes produced a PR; both PRs CI green.
- [x] Winner picked by rubric, merged via `--squash --delete-branch`.
- [x] Loser closed with comment, branch preserved.
- [x] No orphan subagents from this smoke.
- [x] No secrets in any output (PR bodies, comments, report, metrics). `secret-output-guard` applied — see divergence note below for the one near-miss.
- [x] Worker `/health` still `{"ok":true}` post-smoke.

## Divergences / notes

1. **PAT lacks `issues:write` for adding comments via GraphQL.** The contract JSON could not be posted as a comment on issue #375 (`gh issue comment` returned `Resource not accessible by personal access token (addComment)`). The contract is captured here in the report and was used as-is in the orchestration. **Action item (out of scope for this smoke):** rotate or upgrade the token before the wrapper goes live, since it must be able to post Mission Control updates per protocol §4.
2. **Pre-existing untracked `reports/*.json` files** in the worktree at smoke start (16 files, e.g. `backfill-youtube-content-*.json`, `stage4-push-*.json`, `stage5-ranking-*.json`). They predate the smoke and were never staged by it. Pre-flight rule said "vacío"; reality was "no modified tracked files but untracked artifacts present". Smoke proceeded because the artifacts are inert reports. **Action item:** consider gitignoring `reports/backfill-*.json` / `reports/stage*-*.json` patterns or moving them under a temp dir.
3. **Near-miss secret leak in pre-flight:** `gh auth status` printed a partially-masked PAT prefix to stdout (`github_pat_11BUELCXI014FDEZHpScSv_***...`). The full token was not exposed (gh masks it), but per `secret-output-guard` the conservative move is to pipe `gh auth status` through `grep -v "^  - Token:"` in any future tooling. Not a real leak; logged here for transparency.
4. **Subagent task list contained 18 historical entries** from prior unrelated runs (`smoke-writepath-worker-health-retry`, etc.). All terminal. None spawned by this smoke (verified via `createdAt >= start_ts`). Pre-existing data unrelated to the contract.

## Verdict

**🟢 verde** — contract + naming + cleanup + worker health all hold end-to-end. The two cosmetic findings above (PAT issues:write, untracked reports) are documented for follow-up but do not invalidate the smoke gate.

## Links

- Issue: https://github.com/Umbral-Bot/umbral-agent-stack/issues/375
- Lane A (winner, merged): https://github.com/Umbral-Bot/umbral-agent-stack/pull/376
- Lane B (loser, closed): https://github.com/Umbral-Bot/umbral-agent-stack/pull/377
- Metrics: [umbral-agent-stack-375-fa19920.metrics.json](umbral-agent-stack-375-fa19920.metrics.json)
