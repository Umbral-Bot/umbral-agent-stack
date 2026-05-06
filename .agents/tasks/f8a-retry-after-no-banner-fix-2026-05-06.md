---
id: f8a-retry-after-no-banner-fix-2026-05-06
title: "F8A retry after dropping obsolete --no-banner flag"
assigned_to: copilot-vps
status: done
verdict: amarillo
priority: high
reviewer: codex
created_at: 2026-05-06
completed_at: 2026-05-06
mission_run_id: ee5aa7b921d44fdcb435d1c0803656d2
report: reports/copilot-cli/f8a-retry-after-no-banner-fix-2026-05-06.md
---

# F8A retry after no-banner bugfix

## Bootstrap

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Objective

Retry exactly one controlled real `copilot_cli.run` after the bugfix that removes
obsolete `--no-banner` from the Copilot CLI wrapper command.

Previous run:

- `mission_run_id=49a1496515c84826b215ae9d8ec400e9`
- reached sandboxed Copilot CLI binary
- failed `exit_code=1`
- stderr: `error: unknown option '--no-banner'`
- rollback restored L3=false, L4=false, nft removed

## Rules

- `APPROVE_F8A_ONE_SHOT_RUN=YES` must be present in David's invocation.
- Open L3/L4 temporarily only inside this run window.
- Run exactly one request.
- Always rollback L3=false, `egress.activated=false`, nft table removed.
- Never print token values.
- Commit report only, not runtime artifacts or backups.

## Runbook

Reuse the same guarded script from `.agents/tasks/f8a-first-real-run-2026-05-05.md`,
with these changes:

1. Confirm `grep -- '--no-banner' worker/tasks/copilot_cli.py` returns no hits.
2. Use `batch_id=f8a-retry-no-banner`.
3. Use `agent_id=copilot-vps-single-002`.
4. Write report:

```text
reports/copilot-cli/f8a-retry-after-no-banner-fix-2026-05-06.md
```

Required report fields:

- verdict: verde / amarillo / rojo
- previous failure reference: `49a1496515c84826b215ae9d8ec400e9`
- new `mission_run_id`
- batch_id
- agent_id
- decision
- exit_code
- duration_sec
- artifact_manifest
- stdout/stderr summary
- tokens/cost source
- audit JSONL path
- nft state before/during/after
- rollback evidence
- secret scan result

Branch:

```text
rick/f8a-retry-after-no-banner-fix-2026-05-06
```

Open PR to `main` with Codex as reviewer. If `gh` is not authenticated, push the
branch and return the compare URL.

