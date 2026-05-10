# Wave 2.A — autonomous execution status update (2026-05-10)

**Date**: 2026-05-10 (autonomous Wave 2.A coordinator pass)
**Author**: Copilot Chat (cross-repo coordinator role)
**Status**: in progress — 3 of 4 deliverables open as draft PRs.
**Predecessor doc**: `docs/audits/2026-05-10-wave2a-plan.md`
  (lives on `copilot-vps/wave2a-405-stop-button` until #407 merges).

This is a coordination snapshot. The plan itself is unchanged.

## Summary

| # | Issue     | PR    | Branch                                               | Base                                 | Status   |
|---|---|---|---|---|---|
| 1 | #405      | #407  | `copilot-vps/wave2a-405-stop-button`                 | `main`                               | hardened, draft (do-not-merge) |
| 2 | #402      | #410  | `rrss-wave2a/402-publication-content-hash`           | `copilot-vps/wave2a-405-stop-button` | draft (do-not-merge), tests green |
| 3 | #404-lite | #411  | `rrss-wave2a/404-lite-publish-log`                   | `main`                               | draft (do-not-merge), tests green |
| 4 | #406      | —     | not started                                          | —                                    | parallel doc-only, deferred until David authorizes |

Three `do-not-merge` PRs open. Zero real publishes triggered. Zero
runtime-authority changes shipped.

## Stacking decisions

* **#410 stacks on #407** because it consumes `PublishFlags` from the
  hardened guard. When #407 merges to `main`, #410's diff against `main`
  collapses to the #402-only changes.
* **#411 stacks on `main`** intentionally. The contract + writer are
  independent; integration with the guard waits for #407 + #410 to
  merge first, then a follow-up PR wires `publish_log.write_event` into
  `assert_can_publish`.

## Test evidence

| Branch                                       | New tests | Total tests | Failures (unrelated) |
|---|---|---|---|
| `copilot-vps/wave2a-405-stop-button` (#407)  | 94        | 482         | 1 (test_stage9b_linkedin_oauth — pre-existing on main) |
| `rrss-wave2a/402-publication-content-hash` (#410) | 32   | 520         | 1 (same pre-existing) |
| `rrss-wave2a/404-lite-publish-log` (#411)    | 18        | 242         | 1 (same pre-existing) |

The single failing test is `tests/discovery/test_stage9b_linkedin_oauth.py::test_exchange_code_persists_tokens`.
Verified across the three branches with `git log main..HEAD --
tests/discovery/test_stage9b_linkedin_oauth.py
scripts/discovery/lib/stage_9b_*` empty for all three. Pre-existing on
`main`. Not introduced by Wave 2.A.

## Restrictions verification

For each branch, ran:

```bash
git diff origin/main...HEAD -- 'scripts/discovery/stage7_5_*'
git diff origin/main...HEAD -- 'scripts/discovery/lib/variants.py'
git diff --name-only origin/main...HEAD | grep -E "aeco|o16|azure|infra/docker|containerapp"
```

All checks empty for all three branches. No restriction violated.

## Carry-overs

* **Post-#407 + #410 merge**: open follow-up PR
  `rrss-wave2a/404-lite-publish-log-integration` that wires
  `publish_log.write_event` into the three guard outcomes
  (`runtime_block`, `gate_block`, `gate_pass`) per
  `docs/editorial-pipeline/publish-log-contract.md` §
  "Integration with #405 / #402".
* **#406 source-use policy**: pure documentation, can start in parallel,
  but blocking dependency on the merged contracts of #405 / #402 /
  #404-lite for cross-references. Recommend starting after the three PRs
  are reviewed (not necessarily merged).
* **n8n design intent**: 3 "use now" candidates parked for separate
  issues post-Wave 2.A close. See
  `docs/audits/2026-05-10-wave2a-n8n-applicability-scan.md`.

## Decisions required from David

1. Confirm stacking order for review: #407 → #410 → #411-integration
   follow-up.
2. Confirm body-normalization policy in #402 contract (case-preserving
   vs lowercase).
3. Confirm `~/.config/umbral/publish_log.jsonl` as the canonical path
   for #404-lite.
4. Authorize start of #406 (doc-only, no runtime risk).

## References

* `docs/audits/2026-05-10-wave2a-plan.md` (on #407 branch)
* `docs/audits/2026-05-10-wave2a-n8n-applicability-scan.md`
* `docs/audits/2026-05-10-wave2a-402-report.md`
* `docs/audits/2026-05-10-wave2a-404-lite-report.md`
* `docs/audits/2026-05-10-wave2a-vps-prompts.md`
