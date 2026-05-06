---
id: f8a-clean-first-real-run-retry-2026-05-07
title: "F8A clean first real Copilot CLI run retry"
assigned_to: copilot-vps
status: done
verdict: amarillo
priority: high
reviewer: codex
created_at: 2026-05-07
---

# F8A clean first real Copilot CLI run retry

## Bootstrap

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Context

This is the first clean retry after all prior blockers were addressed:

- `--no-banner` removed.
- Docker stdin uses `-i`.
- Prompt quoting uses `prompt=$(cat "$prompt_file")` + `--prompt "$prompt"`.
- Scoped egress staging is green: Docker network `copilot-egress`, bridge
  `br-copilot`, nft `forward policy accept`, host egress unaffected.

## Hard approval gate

David's invocation must include exactly:

```text
APPROVE_F8A_CLEAN_REAL_RUN_RETRY=YES
```

If absent, stop with verdict `rojo` and do not touch runtime gates.

## Rules

- Execute exactly one real `copilot_cli.run`.
- Open L3/L4 only inside the run window.
- Keep `COPILOT_CLI_DIAGNOSTIC_MODE=true`.
- Use `COPILOT_CLI_DOCKER_NETWORK=copilot-egress`.
- Never print token values. Only `present_by_name`.
- Always rollback:
  - `RICK_COPILOT_CLI_EXECUTE=false`
  - `egress.activated=false`
  - diagnostic mode removed
  - nft table removed
  - Docker network removed if created by this task
  - worker restarted
  - `/health` 200

## O1 — Source and gated checks

Verify:

```bash
grep -n '_REAL_EXECUTION_IMPLEMENTED = True' worker/tasks/copilot_cli.py
grep -n '"-i"' worker/tasks/copilot_cli.py
grep -n 'prompt=$(cat "$prompt_file")' worker/tasks/copilot_cli.py
grep -n -- '--prompt "$prompt"' worker/tasks/copilot_cli.py
grep -n '_DEFAULT_DOCKER_NETWORK = "copilot-egress"' worker/tasks/copilot_cli.py
python3 scripts/verify_copilot_egress_contract.py
```

Restart worker once, with L3 still false, then probe:

- `decision=execute_flag_off_dry_run`
- `would_run=false`
- `execute_enabled=false`
- `real_execution_implemented=true`
- `egress_activated=false`

If not, stop `rojo`.

## O2 — Resolver and scoped network setup

Run resolver before opening gates:

```bash
python3 scripts/copilot_egress_resolver.py --non-strict --format json \
  > /tmp/f8a-clean-real-run-egress.json
```

If `copilot_v4` and `copilot_v6` are both empty, stop `amarillo` and do not
open gates.

Create or verify Docker network:

```bash
docker network inspect copilot-egress
# If absent:
docker network create \
  --driver bridge \
  --opt com.docker.network.bridge.name=br-copilot \
  --opt com.docker.network.bridge.enable_icc=false \
  copilot-egress
```

If the network exists but its bridge is not `br-copilot`, stop `rojo`.

## O3 — Open run window

Backup first:

```bash
BACKUP_DIR="/home/rick/.copilot/backups/f8a-clean-real-run-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
cp /home/rick/.config/openclaw/copilot-cli.env "$BACKUP_DIR/copilot-cli.env"
cp config/tool_policy.yaml "$BACKUP_DIR/tool_policy.yaml"
sudo nft list ruleset > "$BACKUP_DIR/nft-ruleset-before.nft"
chmod 0600 "$BACKUP_DIR"/*
```

Then:

1. `sudo nft -c -f infra/networking/copilot-egress.nft.example`
2. `sudo nft -f infra/networking/copilot-egress.nft.example`
3. Populate `copilot_v4` / `copilot_v6` from resolver JSON.
4. Set working-tree `config/tool_policy.yaml :: egress.activated=true`.
5. Set envfile:
   - `RICK_COPILOT_CLI_EXECUTE=true`
   - `COPILOT_CLI_DIAGNOSTIC_MODE=true`
   - `COPILOT_CLI_DOCKER_NETWORK=copilot-egress`
   - `COPILOT_CLI_SANDBOX_IMAGE=<existing umbral-sandbox-copilot-cli tag>`
6. Restart worker.
7. Verify process env from `/proc/$PID/environ` with token name only.
8. Run exactly one task:

```text
task=copilot_cli.run
mission=research
batch_id=f8a-clean-real-run
agent_id=copilot-vps-single-005
brief_id=F8A-clean-real-run
requested_operations=["read_repo"]
repo_path=/home/rick/umbral-agent-stack
dry_run=false
max_wall_sec=600
prompt=Read this repository and produce a short markdown risk note: top 3 risks before letting Copilot CLI write files. Do not write files. Return only the markdown note.
```

## O4 — Evidence capture

Capture:

- `mission_run_id`
- `decision`
- `phase`
- `exit_code`
- `duration_sec`
- stdout/stderr byte counts and short previews (no secrets)
- manifest path
- audit JSONL path
- token/cost source
- nft counters and journald `copilot-egress` lines
- worker journal around the run
- secret scans on audit/artifacts/report

## O5 — Rollback

Rollback immediately after evidence capture:

```bash
cp "$BACKUP_DIR/copilot-cli.env" /home/rick/.config/openclaw/copilot-cli.env
cp "$BACKUP_DIR/tool_policy.yaml" config/tool_policy.yaml
sudo nft delete table inet copilot_egress 2>/dev/null || true
docker network rm copilot-egress 2>/dev/null || true   # only if this task created it
systemctl --user restart umbral-worker.service
sleep 4
```

Final state:

- `RICK_COPILOT_CLI_EXECUTE=false`
- `egress.activated=false`
- diagnostic mode absent
- no `inet copilot_egress`
- no `copilot-egress` network if task created it
- `/health=200`

## Report

Write:

```text
reports/copilot-cli/f8a-clean-first-real-run-retry-2026-05-07.md
```

Required verdict:

- `verde`: exit_code=0, artifact/audit clean, rollback clean.
- `amarillo`: infra path works but Copilot CLI exits non-zero or provider/auth limitation.
- `rojo`: rollback failed, token leak, host egress regression, or more than one run executed.

## Branch / PR

Branch:

```text
rick/f8a-clean-first-real-run-retry-2026-05-07
```

Open PR to `main` with Codex as reviewer. If `gh` is not authenticated, push
the branch and return compare URL.
