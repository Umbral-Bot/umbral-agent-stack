---
id: f8a-retry-after-docker-stdin-fix-2026-05-06
title: "F8A retry after docker -i stdin fix"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-06
---

# F8A retry after docker stdin fix

## Bootstrap

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Context

Diagnostic evidence `5d270087a2944283957bc3d21e4059e7` located the silent
exit root cause: `docker run` missed `-i`, so the prompt sent by
`subprocess.run(input=prompt)` never reached container stdin.

This retry verifies the fix.

## Rules

- `APPROVE_F8A_STDIN_FIX_RETRY=YES` must be present in David's invocation.
- Open L3/L4 temporarily only inside the retry window.
- Run exactly one `copilot_cli.run`.
- Always rollback L3=false, `egress.activated=false`, nft table removed.
- Never print token values.

## Required preflight

```bash
grep -n '"docker", "run", "--rm"' worker/tasks/copilot_cli.py
grep -n '"-i"' worker/tasks/copilot_cli.py
grep -n 'COPILOT_CLI_DIAGNOSTIC_MODE' worker/tasks/copilot_cli.py
```

Expected:

- `"-i"` present in docker argv.
- diagnostic mode present.

## Runbook

Reuse the same guarded one-shot protocol from
`.agents/tasks/f8a-diagnose-silent-exit-2026-05-06.md`, with these changes:

1. Keep `COPILOT_CLI_DIAGNOSTIC_MODE=true` for this retry.
2. Use:

```text
batch_id=f8a-retry-stdin-fix
agent_id=copilot-vps-single-003
```

3. Write report:

```text
reports/copilot-cli/f8a-retry-after-docker-stdin-fix-2026-05-06.md
```

Required report fields:

- verdict: verde / amarillo / rojo
- reference diagnostic run: `5d270087a2944283957bc3d21e4059e7`
- new `mission_run_id`
- confirm docker argv contains `-i`
- confirm prompt reaches container (stdout/stderr no longer "No prompt provided")
- exit_code
- duration_sec
- stdout/stderr summary
- artifact manifest path
- audit JSONL path
- token/cost source
- nft state before/during/after
- rollback evidence
- secret scan result

Branch:

```text
rick/f8a-retry-after-docker-stdin-fix-2026-05-06
```

Open PR to `main` with Codex as reviewer. If `gh` is not authenticated, push the
branch and return compare URL.

