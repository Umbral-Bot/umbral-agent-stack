---
id: 2026-05-08-O7b-gitignore-reports-json
title: O7b — decide policy for reports/*.json untracked accumulation
status: open
verdict: pending
owner: copilot-chat
reviewer: david
phase: O7-followup
depends_on:
  - o7-smoke-tournament-as-rick-2026-05-08 (PR #378, merged)
created: 2026-05-08
priority: low
---

# O7b — `reports/*.json` policy

## Why

At the start of the O7 smoke, Copilot-VPS found 16 untracked `reports/*.json`
files in the worktree (not produced by the smoke — pre-existing). They are
artefacts from prior runs accumulating in the working dir.

Two failure modes this risks:

1. **Noisy `git status`** masks real diffs and slows reviews.
2. **Accidental commit** of a payload-bearing JSON during a hurried
   `git add reports/`.

## Decision needed

Pick ONE:

### Option A — gitignore the pattern

```
# .gitignore additions
reports/*.json
!reports/**/manifest.json
!reports/copilot-cli/*.metrics.json
!reports/tournaments/*.metrics.json
```

Pro: zero friction.
Con: easy to lose evidence by mistake; allow-list is fragile.

### Option B — move ephemera to `reports/_scratch/` (gitignored)

Refactor the writers (worker, tournament orchestrator, etc.) so that
**transient** JSON outputs land in `reports/_scratch/<date>/` and only
**curated** evidence lands directly under `reports/<lane>/`.

Pro: clean separation, intent-driven.
Con: requires writer code changes (worker + future wrapper).

### Option C — leave as-is + periodic cleanup

Document a quarterly cleanup task; no code or gitignore change.

Pro: zero work now.
Con: kicks the can; smoke-noise reproduces every quarter.

## Acceptance

- [ ] Decision recorded in this task file (which option, why).
- [ ] If A: PR with `.gitignore` change + audit that no in-flight evidence
      gets ignored retroactively.
- [ ] If B: design note in `docs/adr/` then implementation task spawned.
- [ ] If C: quarterly cleanup task scheduled (Notion or `.agents/tasks/`).
- [ ] Update this task: `status: done`, `verdict: verde`.

## Recommendation (initial)

**Option B**, scoped narrowly: only the tournament orchestrator and
copilot_cli writers route to `reports/_scratch/`. Existing `reports/<lane>/`
paths remain stable (no breaking change for downstream consumers).

## Notes

Out of scope: deleting the existing 16 JSON files. They were pre-existing
before O7 smoke and Copilot-VPS left them untouched — handle separately if
needed.
