---
id: f8a-diagnose-silent-exit-2026-05-06
title: "F8A diagnose silent Copilot CLI exit 1"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-06
---

# F8A — diagnose silent Copilot CLI exit 1

## Bootstrap

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Context

Two F8A real-run attempts reached the sandbox:

1. `49a1496515c84826b215ae9d8ec400e9` failed with obsolete `--no-banner`.
2. `ee5aa7b921d44fdcb435d1c0803656d2` failed silently: stdout=stderr=0, exit 1.

This task enables diagnostic mode (`COPILOT_CLI_DIAGNOSTIC_MODE=true`) so the
wrapper removes `--output-format=json --stream=off` and adds
`--log-level=debug`.

## Rules

- `APPROVE_F8A_DIAGNOSTIC_RUN=YES` must be present in David's invocation.
- Open L3/L4 temporarily only inside the diagnostic run window.
- Run exactly one request.
- Always rollback L3=false, `egress.activated=false`, nft table removed, and
  remove `COPILOT_CLI_DIAGNOSTIC_MODE` from envfile after the run.
- Never print token values.

## Runbook

Reuse `.agents/tasks/f8a-retry-after-no-banner-fix-2026-05-06.md`, with these
changes:

1. Before opening L3, set:

```bash
COPILOT_CLI_DIAGNOSTIC_MODE=true
```

in `/home/rick/.config/openclaw/copilot-cli.env`.

2. Use:

```text
batch_id=f8a-diagnose-silent-exit
agent_id=copilot-vps-diagnostic-001
```

3. After rollback, verify:

```bash
grep -q '^COPILOT_CLI_DIAGNOSTIC_MODE=' /home/rick/.config/openclaw/copilot-cli.env \
  && echo "DIAGNOSTIC_MODE_STILL_SET_BAD" \
  || echo "diagnostic mode removed"
```

4. Write report:

```text
reports/copilot-cli/f8a-diagnose-silent-exit-2026-05-06.md
```

Required report fields:

- verdict: verde / amarillo / rojo
- reference runs: `49a1496515c84826b215ae9d8ec400e9`,
  `ee5aa7b921d44fdcb435d1c0803656d2`
- new `mission_run_id`
- docker argv redacted (verify no `--output-format=json`, no `--stream=off`)
- stdout/stderr summary
- copied `/scratch/copilot-logs` if available in artifact manifest, otherwise
  explicit "not available"
- exit_code
- duration_sec
- audit JSONL path
- nft state before/during/after
- rollback evidence
- secret scan result

Branch:

```text
rick/f8a-diagnose-silent-exit-2026-05-06
```

Open PR to `main` with Codex as reviewer. If `gh` is not authenticated, push the
branch and return compare URL.

