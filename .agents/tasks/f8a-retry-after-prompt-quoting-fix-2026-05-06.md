---
id: f8a-retry-after-prompt-quoting-fix-2026-05-06
title: "F8A retry after wrapper prompt quoting fix"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-06
---

# F8A retry after wrapper prompt quoting fix

## Bootstrap

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Context

F8A retry `863af7a4e81c452faec1c06f94cf2132` confirmed PR #302 fixed
Docker stdin (`docker run -i` present; prompt file populated in sandbox), but
found a second wrapper bug: `--prompt "$(cat \"$prompt_file\")"` collapses to
an empty prompt under `sh -lc`.

This retry verifies the prompt quoting fix:

```sh
prompt=$(cat "$prompt_file")
exec copilot ... --prompt "$prompt"
```

## Hard approval gate

David's invocation must include exactly:

```text
APPROVE_F8A_PROMPT_QUOTING_RETRY=YES
```

If that line is absent, stop with verdict `rojo` and do not touch runtime gates.

## Rules

- VPS Reality Check applies: verify repo state and process env, not just claims.
- Open L3/L4 temporarily only inside the retry window.
- Keep `COPILOT_CLI_DIAGNOSTIC_MODE=true` for this retry.
- Run exactly one `copilot_cli.run`.
- Always rollback: L3=false, `egress.activated=false`, diagnostic mode removed,
  nft table removed, worker restarted, `/health` 200.
- Never print token values. Only `present_by_name` is allowed.
- If DNS/egress resolver returns empty IP sets, do **not** open L3/L4 and do
  **not** execute Copilot. Report `amarillo` with DNS/egress blocker evidence.

## Required preflight

```bash
grep -n '"docker", "run", "--rm"' worker/tasks/copilot_cli.py
grep -n '"-i"' worker/tasks/copilot_cli.py
grep -n 'prompt=$(cat "$prompt_file")' worker/tasks/copilot_cli.py
grep -n -- '--prompt "$prompt"' worker/tasks/copilot_cli.py
! grep -n 'cat \\"$prompt_file\\"' worker/tasks/copilot_cli.py
grep -n 'COPILOT_CLI_DIAGNOSTIC_MODE' worker/tasks/copilot_cli.py
grep -n '^_REAL_EXECUTION_IMPLEMENTED' worker/tasks/copilot_cli.py
```

Expected:

- `"-i"` present in docker argv.
- `prompt=$(cat "$prompt_file")` present.
- `--prompt "$prompt"` present.
- old nested escaped `$(cat \"$prompt_file\")` pattern absent.
- `_REAL_EXECUTION_IMPLEMENTED = True`.

## O1 — Gated deploy verification

Restart the worker once to load main HEAD, then run a gated probe while L3 is
still closed.

Expected probe:

- `decision=execute_flag_off_dry_run`
- `would_run=false`
- `execute_enabled=false`
- `real_execution_implemented=true`
- `egress_activated=false`

If this fails, stop and report `rojo`.

## O2 — Egress readiness hard stop

Before opening L3/L4, run:

```bash
python3 scripts/copilot_egress_resolver.py --non-strict --format json \
  > /tmp/f8a-prompt-quoting-egress.json
```

Parse the JSON. If both `ip_sets.copilot_v4` and `ip_sets.copilot_v6` are
empty, stop with verdict `amarillo`:

- do not open L3
- do not set `egress.activated=true`
- do not apply nft
- do not run Copilot
- include resolver errors, worker health, and gate state in the report

Reason: previous retry found VPS DNS `gaierror: Temporary failure in name
resolution`; empty nft sets would block egress even if the prompt bug is fixed.

## O3 — One-shot retry window

If and only if O1 passes and O2 returns at least one IP:

1. Backup:
   - `/home/rick/.config/openclaw/copilot-cli.env`
   - `config/tool_policy.yaml`
   - `sudo nft list ruleset`
2. Apply `infra/networking/copilot-egress.nft.example`.
3. Populate nft sets from the resolver JSON.
4. Set `egress.activated: true` in the working tree only.
5. Set envfile:
   - `RICK_COPILOT_CLI_EXECUTE=true`
   - `COPILOT_CLI_DIAGNOSTIC_MODE=true`
   - `COPILOT_CLI_SANDBOX_IMAGE=<existing umbral-sandbox-copilot-cli tag>`
   - `COPILOT_CLI_DOCKER_NETWORK=bridge`
6. Restart worker and verify booleans from `/proc/$PID/environ`.
7. Execute exactly one run:

```text
batch_id=f8a-retry-prompt-quoting
agent_id=copilot-vps-single-004
brief_id=F8A-prompt-quoting
prompt=Read this repository and produce a short markdown risk note: top 3 risks before letting Copilot CLI write files. Do not write files. Return only the markdown note.
requested_operations=["read_repo"]
repo_path=/home/rick/umbral-agent-stack
dry_run=false
max_wall_sec=600
```

8. Rollback immediately.

## Required report

Write:

```text
reports/copilot-cli/f8a-retry-after-prompt-quoting-fix-2026-05-06.md
```

Required fields:

- verdict: verde / amarillo / rojo
- references:
  - stdin retry `863af7a4e81c452faec1c06f94cf2132`
  - diagnostic retry `5d270087a2944283957bc3d21e4059e7`
- new `mission_run_id` (or `n/a` if O2 DNS hard stop)
- confirm docker argv contains `-i`
- confirm prompt quoting fix is present and old nested cat quoting absent
- egress resolver result (`copilot_v4`/`copilot_v6` counts and errors)
- exit_code, duration_sec, stdout/stderr summary if run executed
- artifact manifest path if run executed
- audit JSONL path if run executed
- token/cost source
- nft state before/during/after
- rollback evidence
- secret scan result

## Branch and PR

Branch:

```text
rick/f8a-retry-after-prompt-quoting-fix-2026-05-06
```

Open PR to `main` with Codex as reviewer. If `gh` is not authenticated, push
the branch and return compare URL.
