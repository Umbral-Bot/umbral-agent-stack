---
id: f8a-run6-after-token-refresh-2026-05-07
title: "F8A run-6 after Copilot token refresh"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-07
---

# F8A run-6 after Copilot token refresh

## Bootstrap

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Context

Run-5 (`mission_run_id=8dad30fe39f94c3781ee481d4d7d4349`) proved the
runtime path is clean except for two final blockers:

- Code blocker: Copilot CLI needs writable `$HOME/.copilot` in the
  read-only sandbox. Fixed on `main` by adding
  `--tmpfs /home/runner/.copilot:size=32m,mode=1777`.
- Human blocker: the live `COPILOT_GITHUB_TOKEN` returned HTTP 401 from
  GitHub API. It must be refreshed before this task opens L3/L4.

This task is the first retry after both conditions should be true.

## Hard approval gate

David's invocation must include exactly:

```text
APPROVE_F8A_RUN6_AFTER_TOKEN_REFRESH=YES
```

If absent, stop with verdict `rojo` and do not touch runtime gates.

## Hard stop conditions

Stop before opening L3/L4 if any of these happen:

- `COPILOT_GITHUB_TOKEN` is absent in the worker process env.
- GitHub API `/user` check with the token returns anything except HTTP 200.
- Source checks do not show `-i`, prompt quoting fix, scoped egress, and
  `/home/runner/.copilot` tmpfs.
- Egress resolver returns zero IPv4 and zero IPv6 addresses.
- Existing Docker network `copilot-egress` is present but does not use bridge
  `br-copilot`.
- Contract verifier fails.

Never print token values. Only print `present_by_name`.

## Rules

- Execute exactly one real `copilot_cli.run`.
- Open L3/L4 only inside the run window.
- Keep `COPILOT_CLI_DIAGNOSTIC_MODE=true`.
- Use `COPILOT_CLI_DOCKER_NETWORK=copilot-egress`.
- Use scoped nft `forward` profile only. No host-wide `output policy drop`.
- Always rollback:
  - `RICK_COPILOT_CLI_EXECUTE=false`
  - `egress.activated=false`
  - diagnostic mode removed
  - nft table removed
  - Docker network removed if this task created it
  - worker restarted
  - `/health` 200

## O0 - Token refresh verification

With gates still closed, restart worker once to load the refreshed token:

```bash
OLD_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user restart umbral-worker.service
sleep 5
NEW_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
echo "OLD_PID=$OLD_PID NEW_PID=$NEW_PID"
curl -s -o /dev/null -w "worker_health=%{http_code}\n" http://127.0.0.1:8088/health
```

Verify token presence by name only:

```bash
PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
tr '\0' '\n' < /proc/$PID/environ | awk -F= '
  $1=="COPILOT_GITHUB_TOKEN" {print "COPILOT_GITHUB_TOKEN=present_by_name"}
  $1=="RICK_COPILOT_CLI_EXECUTE" {print "RICK_COPILOT_CLI_EXECUTE="$2}
'
```

Check GitHub API auth without printing the token:

```bash
PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
python3 - "$PID" <<'PY'
import json
import sys
import urllib.error
import urllib.request

pid = sys.argv[1]
env = {}
with open(f"/proc/{pid}/environ", "rb") as fh:
    for item in fh.read().split(b"\0"):
        if b"=" in item:
            k, v = item.split(b"=", 1)
            env[k.decode()] = v.decode()

token = env.get("COPILOT_GITHUB_TOKEN")
if not token:
    print("TOKEN_STATUS=missing")
    sys.exit(2)

req = urllib.request.Request(
    "https://api.github.com/user",
    headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "umbral-f8a-run6-token-check",
    },
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        status = str(resp.status)
        body = resp.read()
except urllib.error.HTTPError as exc:
    status = str(exc.code)
    body = exc.read()
except Exception as exc:
    print(f"TOKEN_STATUS=check_error:{type(exc).__name__}")
    sys.exit(4)

with open("/tmp/f8a-run6-github-user.json", "wb") as fh:
    fh.write(body)
print(f"GITHUB_USER_HTTP={status}")
if status != "200":
    print("TOKEN_STATUS=invalid_or_expired")
    sys.exit(3)
print("TOKEN_STATUS=valid")
PY
```

If the token check is not `TOKEN_STATUS=valid`, stop `amarillo`; do not
open L3/L4.

## O1 - Source and gated checks

Verify the final source contract:

```bash
grep -n '_REAL_EXECUTION_IMPLEMENTED = True' worker/tasks/copilot_cli.py
grep -n '"-i"' worker/tasks/copilot_cli.py
grep -n 'prompt=$(cat "$prompt_file")' worker/tasks/copilot_cli.py
grep -n -- '--prompt "$prompt"' worker/tasks/copilot_cli.py
grep -n '/home/runner/.copilot:size=32m,mode=1777' worker/tasks/copilot_cli.py
grep -n '_DEFAULT_DOCKER_NETWORK = "copilot-egress"' worker/tasks/copilot_cli.py
python3 scripts/verify_copilot_egress_contract.py
```

Probe with L3 still false:

```bash
WTOKEN=$(grep '^WORKER_TOKEN=' /home/rick/.config/openclaw/env | cut -d= -f2-)
curl -s --max-time 30 -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer $WTOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task":"copilot_cli.run","input":{"mission":"research","prompt":"O1 gate probe","requested_operations":["read_repo"],"repo_path":"/home/rick/umbral-agent-stack","dry_run":true,"metadata":{"batch_id":"f8a-run6-o1","agent_id":"copilot-vps-single-006-o1","brief_id":"O1"}}}' \
  | python3 -m json.tool
```

Expected:

- `decision=execute_flag_off_dry_run`
- `would_run=false`
- `execute_enabled=false`
- `real_execution_implemented=true`
- `egress_activated=false`

If not, stop `rojo`.

## O2 - Resolver and scoped network setup

Run resolver before opening gates:

```bash
python3 scripts/copilot_egress_resolver.py --non-strict --format json \
  > /tmp/f8a-run6-egress.json
python3 - <<'PY'
import json
d = json.load(open('/tmp/f8a-run6-egress.json', encoding='utf-8'))
v4 = d.get('ip_sets', {}).get('copilot_v4', [])
v6 = d.get('ip_sets', {}).get('copilot_v6', [])
print(f"copilot_v4_count={len(v4)}")
print(f"copilot_v6_count={len(v6)}")
if not v4 and not v6:
    raise SystemExit("NO_EGRESS_IPS_STOP")
PY
```

Create or verify Docker network:

```bash
if docker network inspect copilot-egress >/dev/null 2>&1; then
  BRIDGE_NAME=$(docker network inspect copilot-egress -f '{{index .Options "com.docker.network.bridge.name"}}')
  test "$BRIDGE_NAME" = "br-copilot" || { echo "BRIDGE_MISMATCH_STOP"; exit 4; }
  echo false > /tmp/f8a-run6-network-created-by-task
else
  docker network create \
    --driver bridge \
    --opt com.docker.network.bridge.name=br-copilot \
    --opt com.docker.network.bridge.enable_icc=false \
    copilot-egress
  echo true > /tmp/f8a-run6-network-created-by-task
fi
docker network inspect copilot-egress -f 'name={{.Name}} bridge={{index .Options "com.docker.network.bridge.name"}} icc={{index .Options "com.docker.network.bridge.enable_icc"}}'
```

## O3 - Open run window

Backup first:

```bash
BACKUP_DIR="/home/rick/.copilot/backups/f8a-run6-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
cp /home/rick/.config/openclaw/copilot-cli.env "$BACKUP_DIR/copilot-cli.env"
cp config/tool_policy.yaml "$BACKUP_DIR/tool_policy.yaml"
sudo nft list ruleset > "$BACKUP_DIR/nft-ruleset-before.nft" 2>/dev/null || true
chmod 0600 "$BACKUP_DIR"/*
echo "$BACKUP_DIR" > /tmp/f8a-run6-backup-dir
echo "BACKUP_DIR=$BACKUP_DIR"
```

Apply scoped nft and populate IP sets:

```bash
sudo nft -c -f infra/networking/copilot-egress.nft.example
sudo nft -f infra/networking/copilot-egress.nft.example
python3 - <<'PY' > /tmp/f8a-run6-sets.nft
import json
d = json.load(open('/tmp/f8a-run6-egress.json', encoding='utf-8'))
v4 = d.get('ip_sets', {}).get('copilot_v4', [])
v6 = d.get('ip_sets', {}).get('copilot_v6', [])
print('flush set inet copilot_egress copilot_v4')
if v4:
    print('add element inet copilot_egress copilot_v4 { ' + ', '.join(v4) + ' }')
print('flush set inet copilot_egress copilot_v6')
if v6:
    print('add element inet copilot_egress copilot_v6 { ' + ', '.join(v6) + ' }')
PY
sudo nft -f /tmp/f8a-run6-sets.nft
sudo nft list table inet copilot_egress | head -60
```

Open L4 in the working tree only:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('config/tool_policy.yaml')
s = p.read_text(encoding='utf-8')
s2 = s.replace(
    '  egress:\n    profile_name: copilot-egress\n    activated: false',
    '  egress:\n    profile_name: copilot-egress\n    activated: true',
)
if s == s2:
    raise SystemExit('L4_REPLACEMENT_FAILED_STOP')
p.write_text(s2, encoding='utf-8')
PY
grep -A4 '^  egress:' config/tool_policy.yaml
```

Set envfile, restart worker, verify process env:

```bash
IMAGE=$(docker image ls --format '{{.Repository}}:{{.Tag}}' | grep '^umbral-sandbox-copilot-cli:' | head -1)
test -n "$IMAGE" || { echo "NO_SANDBOX_IMAGE_STOP"; exit 5; }
ENVFILE=/home/rick/.config/openclaw/copilot-cli.env

sed -i 's/^RICK_COPILOT_CLI_EXECUTE=false$/RICK_COPILOT_CLI_EXECUTE=true/' "$ENVFILE"

if grep -q '^COPILOT_CLI_DIAGNOSTIC_MODE=' "$ENVFILE"; then
  sed -i 's/^COPILOT_CLI_DIAGNOSTIC_MODE=.*$/COPILOT_CLI_DIAGNOSTIC_MODE=true/' "$ENVFILE"
else
  printf '\nCOPILOT_CLI_DIAGNOSTIC_MODE=true\n' >> "$ENVFILE"
fi

if grep -q '^COPILOT_CLI_SANDBOX_IMAGE=' "$ENVFILE"; then
  sed -i "s|^COPILOT_CLI_SANDBOX_IMAGE=.*$|COPILOT_CLI_SANDBOX_IMAGE=$IMAGE|" "$ENVFILE"
else
  printf '\nCOPILOT_CLI_SANDBOX_IMAGE=%s\n' "$IMAGE" >> "$ENVFILE"
fi

if grep -q '^COPILOT_CLI_DOCKER_NETWORK=' "$ENVFILE"; then
  sed -i 's|^COPILOT_CLI_DOCKER_NETWORK=.*$|COPILOT_CLI_DOCKER_NETWORK=copilot-egress|' "$ENVFILE"
else
  printf '\nCOPILOT_CLI_DOCKER_NETWORK=copilot-egress\n' >> "$ENVFILE"
fi

systemctl --user restart umbral-worker.service
sleep 5
PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
curl -s -o /dev/null -w "worker_health=%{http_code}\n" http://127.0.0.1:8088/health
tr '\0' '\n' < /proc/$PID/environ | awk -F= '
  $1=="RICK_COPILOT_CLI_ENABLED" {print "process RICK_COPILOT_CLI_ENABLED="$2}
  $1=="RICK_COPILOT_CLI_EXECUTE" {print "process RICK_COPILOT_CLI_EXECUTE="$2}
  $1=="COPILOT_CLI_DIAGNOSTIC_MODE" {print "process COPILOT_CLI_DIAGNOSTIC_MODE="$2}
  $1=="COPILOT_CLI_DOCKER_NETWORK" {print "process COPILOT_CLI_DOCKER_NETWORK="$2}
  $1=="COPILOT_CLI_SANDBOX_IMAGE" {print "process COPILOT_CLI_SANDBOX_IMAGE="$2}
  $1=="COPILOT_GITHUB_TOKEN" {print "process COPILOT_GITHUB_TOKEN=present_by_name"}
'
```

Run exactly one task:

```bash
WTOKEN=$(grep '^WORKER_TOKEN=' /home/rick/.config/openclaw/env | cut -d= -f2-)
sudo nft list table inet copilot_egress | grep counter || true
curl -s --max-time 700 -X POST http://127.0.0.1:8088/run \
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
        "batch_id":"f8a-run6-after-token-refresh",
        "agent_id":"copilot-vps-single-006",
        "brief_id":"F8A-run6-after-token-refresh"
      }
    }
  }' | tee /tmp/f8a-run6-response.json | python3 -m json.tool
sudo nft list table inet copilot_egress | grep counter || true
```

## O4 - Evidence capture

Capture:

- `mission_run_id`
- `decision`
- `phase`
- `exit_code`
- `duration_sec`
- stdout/stderr byte counts and short previews with secret scan first
- manifest path
- audit JSONL path
- token/cost source
- nft counters
- worker journal around the run
- secret scans on audit/artifacts/report

If `exit_code != 0`, capture stderr/stdout and diagnose, but do not run a
second `copilot_cli.run`.

## O5 - Rollback

Rollback immediately after evidence capture:

```bash
BACKUP_DIR=$(cat /tmp/f8a-run6-backup-dir)
cp "$BACKUP_DIR/copilot-cli.env" /home/rick/.config/openclaw/copilot-cli.env
cp "$BACKUP_DIR/tool_policy.yaml" config/tool_policy.yaml
sudo nft delete table inet copilot_egress 2>/dev/null || true
if [ "$(cat /tmp/f8a-run6-network-created-by-task 2>/dev/null)" = "true" ]; then
  docker network rm copilot-egress 2>/dev/null || true
fi
systemctl --user restart umbral-worker.service
sleep 5
```

Final state must show:

- `RICK_COPILOT_CLI_EXECUTE=false`
- `egress.activated=false`
- diagnostic mode absent
- no `inet copilot_egress`
- no `copilot-egress` network if this task created it
- `/health=200`

## Report

Write:

```text
reports/copilot-cli/f8a-run6-after-token-refresh-2026-05-07.md
```

Required verdict:

- `verde`: exit_code=0, artifact/audit clean, rollback clean.
- `amarillo`: infra path works but Copilot CLI exits non-zero or provider/auth limitation.
- `rojo`: rollback failed, token leak, host egress regression, or more than one run executed.

## Branch / PR

Branch:

```text
rick/f8a-run6-after-token-refresh-2026-05-07
```

Open PR to `main` with Codex as reviewer. If `gh` is not authenticated, push
the branch and return compare URL.
