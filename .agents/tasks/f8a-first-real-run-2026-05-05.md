---
id: f8a-first-real-run-2026-05-05
title: "F8A first controlled real Docker execution"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-05
---

# F8A — first controlled `copilot_cli.run` real-execution probe

## Bootstrap obligatorio

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Hard rules

- Secret-output-guard: never print token values. Names only are allowed.
- VPS Reality Check: report repo state and live process state separately.
- Do not commit runtime backups, envfiles, nft dumps, or JSONL audit logs.
- Do not leave L3 or L4 open after the task.
- Do not write to Notion, Slack, Telegram, LinkedIn, Gmail, GitHub comments, or gates publish.
- Do not run more than one `copilot_cli.run`.

## O1 — Deploy verification with L3 still closed

1. Verify main contains F8A code:

```bash
grep -n 'F8A.real_execution' worker/tasks/copilot_cli.py
grep -n '^_REAL_EXECUTION_IMPLEMENTED' worker/tasks/copilot_cli.py
```

Expected:

```text
_REAL_EXECUTION_IMPLEMENTED = True
```

2. Restart worker once to ensure F8A code is loaded:

```bash
OLD_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user restart umbral-worker.service
sleep 4
NEW_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user show umbral-worker.service -p ActiveState -p SubState
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
```

3. Verify gates from repo + process:

```bash
PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
tr '\0' '\n' < /proc/$PID/environ \
  | awk -F= '
      $1=="RICK_COPILOT_CLI_ENABLED" {print "process RICK_COPILOT_CLI_ENABLED="$2}
      $1=="RICK_COPILOT_CLI_EXECUTE" {print "process RICK_COPILOT_CLI_EXECUTE="$2}
      $1=="COPILOT_GITHUB_TOKEN" {print "process COPILOT_GITHUB_TOKEN=present_by_name"}
      $1=="WORKER_TOKEN" {print "process WORKER_TOKEN=present_by_name"}
    '
grep -E '^RICK_COPILOT_CLI_(ENABLED|EXECUTE)=' /home/rick/.config/openclaw/copilot-cli.env
grep -A8 '^copilot_cli:' config/tool_policy.yaml | head -10
grep -n '^_REAL_EXECUTION_IMPLEMENTED' worker/tasks/copilot_cli.py
```

4. Probe while L3 is closed:

```bash
WTOKEN=$(grep '^WORKER_TOKEN=' /home/rick/.config/openclaw/env | cut -d= -f2-)
curl -s -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer $WTOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task":"copilot_cli.run",
    "input":{
      "mission":"research",
      "prompt":"F8A deploy verification probe",
      "requested_operations":["read_repo"],
      "repo_path":"/home/rick/umbral-agent-stack",
      "dry_run":false,
      "metadata":{"batch_id":"f8a-deploy-check","agent_id":"copilot-vps"}
    }
  }' | tee /tmp/f8a-l3-closed-probe.json | python3 -m json.tool
```

Expected:

```text
decision = execute_flag_off_dry_run
real_execution_implemented = true
execute_enabled = false
would_run = false
```

If this fails, stop and report **rojo**.

## O2 — One-shot real run window

Only continue if David's invocation prompt includes this exact line:

```text
APPROVE_F8A_ONE_SHOT_RUN=YES
```

If the approval line is missing, stop after O1 and report **amarillo**:
F8A deployed, but no real run authorized.

### O2.1 Backup

```bash
RUN_ID="f8a-$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/home/rick/.copilot/backups/$RUN_ID"
mkdir -p "$BACKUP_DIR"
cp /home/rick/.config/openclaw/copilot-cli.env "$BACKUP_DIR/copilot-cli.env"
cp config/tool_policy.yaml "$BACKUP_DIR/tool_policy.yaml"
sudo nft list ruleset > "$BACKUP_DIR/nft-ruleset-before.nft"
chmod 0600 "$BACKUP_DIR"/*
```

### O2.2 Apply L4 egress temporarily

```bash
sudo nft -f infra/networking/copilot-egress.nft.example
python3 scripts/copilot_egress_resolver.py --non-strict --format json > /tmp/f8a-egress-resolver.json
python3 - <<'PY' > /tmp/f8a-egress-sets.nft
import json
d = json.load(open('/tmp/f8a-egress-resolver.json', encoding='utf-8'))
v4 = d.get('ip_sets', {}).get('copilot_v4', [])
v6 = d.get('ip_sets', {}).get('copilot_v6', [])
print('flush set inet copilot_egress copilot_v4')
if v4:
    print('add element inet copilot_egress copilot_v4 { ' + ', '.join(v4) + ' }')
print('flush set inet copilot_egress copilot_v6')
if v6:
    print('add element inet copilot_egress copilot_v6 { ' + ', '.join(v6) + ' }')
PY
sudo nft -f /tmp/f8a-egress-sets.nft
python3 - <<'PY'
from pathlib import Path
p = Path('config/tool_policy.yaml')
s = p.read_text(encoding='utf-8')
s = s.replace('  egress:\n    profile_name: copilot-egress\n    activated: false',
              '  egress:\n    profile_name: copilot-egress\n    activated: true')
p.write_text(s, encoding='utf-8')
PY
```

Verify:

```bash
sudo nft list table inet copilot_egress
grep -A4 '^  egress:' config/tool_policy.yaml
```

### O2.3 Open L3 temporarily

```bash
IMAGE=$(docker image ls --format '{{.Repository}}:{{.Tag}}' \
  | grep '^umbral-sandbox-copilot-cli:' \
  | head -1)
if [ -z "$IMAGE" ]; then
  echo "NO_SANDBOX_IMAGE_FOUND_STOP"
  exit 2
fi
if grep -q '^COPILOT_CLI_SANDBOX_IMAGE=' /home/rick/.config/openclaw/copilot-cli.env; then
  sed -i "s|^COPILOT_CLI_SANDBOX_IMAGE=.*$|COPILOT_CLI_SANDBOX_IMAGE=$IMAGE|" \
    /home/rick/.config/openclaw/copilot-cli.env
else
  printf '\nCOPILOT_CLI_SANDBOX_IMAGE=%s\n' "$IMAGE" >> /home/rick/.config/openclaw/copilot-cli.env
fi
if grep -q '^COPILOT_CLI_DOCKER_NETWORK=' /home/rick/.config/openclaw/copilot-cli.env; then
  sed -i 's|^COPILOT_CLI_DOCKER_NETWORK=.*$|COPILOT_CLI_DOCKER_NETWORK=bridge|' \
    /home/rick/.config/openclaw/copilot-cli.env
else
  printf 'COPILOT_CLI_DOCKER_NETWORK=bridge\n' >> /home/rick/.config/openclaw/copilot-cli.env
fi
sed -i 's/^RICK_COPILOT_CLI_EXECUTE=false$/RICK_COPILOT_CLI_EXECUTE=true/' \
  /home/rick/.config/openclaw/copilot-cli.env
OLD_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user restart umbral-worker.service
sleep 4
NEW_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
```

Verify process L3 true and token name present, value not printed:

```bash
PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
tr '\0' '\n' < /proc/$PID/environ \
  | awk -F= '
      $1=="RICK_COPILOT_CLI_EXECUTE" {print "process RICK_COPILOT_CLI_EXECUTE="$2}
      $1=="COPILOT_GITHUB_TOKEN" {print "process COPILOT_GITHUB_TOKEN=present_by_name"}
    '
```

### O2.4 Execute exactly one run

```bash
WTOKEN=$(grep '^WORKER_TOKEN=' /home/rick/.config/openclaw/env | cut -d= -f2-)
curl -s -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer $WTOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task":"copilot_cli.run",
    "input":{
      "mission":"research",
      "prompt":"Read this repository and produce a short markdown risk note: top 3 risks before letting Copilot CLI write files. Do not write files. Return only the markdown note.",
      "requested_operations":["read_repo"],
      "repo_path":"/home/rick/umbral-agent-stack",
      "dry_run":false,
      "max_wall_sec":600,
      "metadata":{
        "batch_id":"f8a-first-real-run",
        "agent_id":"copilot-vps-single-001",
        "brief_id":"F8-B1"
      }
    }
  }' | tee /tmp/f8a-first-real-run-response.json | python3 -m json.tool
```

Capture:

- `mission_run_id`
- `batch_id`
- `agent_id`
- `decision`
- `exit_code`
- `duration_sec`
- `artifact_manifest`
- `tokens`
- `cost_usd`
- `audit_log`

## O3 — Mandatory rollback

Run rollback even if O2.4 fails.

```bash
cp "$BACKUP_DIR/copilot-cli.env" /home/rick/.config/openclaw/copilot-cli.env
cp "$BACKUP_DIR/tool_policy.yaml" config/tool_policy.yaml
sudo nft delete table inet copilot_egress 2>/dev/null || true
OLD_PID_ROLLBACK=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user restart umbral-worker.service
sleep 4
NEW_PID_ROLLBACK=$(systemctl --user show umbral-worker.service -p MainPID --value)
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
```

Verify final state:

```bash
grep -E '^RICK_COPILOT_CLI_(ENABLED|EXECUTE)=' /home/rick/.config/openclaw/copilot-cli.env
grep -A4 '^  egress:' config/tool_policy.yaml
grep -n '^_REAL_EXECUTION_IMPLEMENTED' worker/tasks/copilot_cli.py
sudo nft list table inet copilot_egress 2>/dev/null && echo "TABLE_PRESENT_BAD" || echo "no copilot nft table"
docker network ls 2>/dev/null | grep -i copilot || echo "no copilot docker network"
```

Expected final state:

```text
RICK_COPILOT_CLI_EXECUTE=false
egress.activated=false
_REAL_EXECUTION_IMPLEMENTED = True
no copilot nft table
```

## O4 — Report and PR

Create:

```text
reports/copilot-cli/f8a-first-real-run-2026-05-05.md
```

Required report fields:

- verdict: verde / amarillo / rojo
- whether O1 deploy check passed
- whether one-shot approval line was present
- gate matrix before run, during run, after rollback
- batch_id
- agent_id
- mission_run_id
- tokens + source
- cost_usd + source
- exit_code
- duration_sec
- artifact_manifest path
- generated artifact paths + sha256
- audit JSONL path
- journalctl window
- nft table/set snapshot before/during/after
- Docker image and network used
- secret scan result
- rollback evidence

Branch:

```text
rick/f8a-first-real-run-2026-05-05
```

Commit + push + open PR to `main` with Codex as reviewer. If `gh` is not
authenticated, push the branch and report the compare URL.
