---
id: f8b-diagnose-egress-and-model-power-2026-05-07
title: "F8B diagnose Copilot egress drops and model-power path"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-07
---

# F8B diagnose Copilot egress drops and model-power path

## Objective

Run a direct, bounded diagnostic after F8A run-6 showed the infra path is clean
but scoped nft dropped 36 packets and Copilot CLI exited `1` with zero output.

This task must answer:

- Which destination IPs/hosts are being dropped by the scoped `br-copilot`
  nft profile?
- Does the installed Copilot CLI expose `--model`, and can it select the
  requested high-capability model (`Claude Opus 4.7`) under the refreshed
  token/account?
- What exact allow-list update is required before another canonical
  `copilot_cli.run` retry?

## Hard approval gate

David's invocation must include exactly:

```text
APPROVE_F8B_EGRESS_MODEL_DIAGNOSTIC=YES
```

If absent, stop `rojo` and do not create nft tables, Docker networks, or direct
Copilot runs.

## Rules

- Do **not** call `copilot_cli.run` in this task. F8A already used its one
  canonical run.
- Use direct sandbox diagnostics only.
- Keep token value secret; print `COPILOT_GITHUB_TOKEN=present_by_name` only.
- Do not use `--allow-all-tools`, `--allow-all`, or `--yolo`.
- Do not enable write tools.
- Do not modify repo files from inside the Copilot sandbox.
- Open scoped nft/Docker network only inside the diagnostic window.
- Always rollback nft table and Docker network if this task created it.
- If `Claude Opus 4.7` is unavailable, capture the exact non-secret error and
  continue with the egress diagnosis using the default model only if that does
  not require a second canonical `copilot_cli.run`.

## O0 - Sync and source checks

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
git log --oneline -3

grep -n 'get_copilot_cli_allowed_models' worker/tool_policy.py
grep -n '"model"' worker/tasks/copilot_cli.py
grep -n -- '--model' worker/tasks/copilot_cli.py
grep -n 'Claude Opus 4.7' config/tool_policy.yaml
python3 scripts/verify_copilot_egress_contract.py
```

Stop `rojo` if the model override code or egress contract is missing.

## O1 - Token and CLI capability check

Restart worker once to load current secrets, then validate the token without
printing it:

```bash
OLD_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user restart umbral-worker.service
sleep 5
NEW_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
echo "OLD_PID=$OLD_PID NEW_PID=$NEW_PID"
curl -s -o /dev/null -w "worker_health=%{http_code}\n" http://127.0.0.1:8088/health

PID=$NEW_PID
tr '\0' '\n' < /proc/$PID/environ | awk -F= '
  $1=="COPILOT_GITHUB_TOKEN" {print "COPILOT_GITHUB_TOKEN=present_by_name"}
  $1=="RICK_COPILOT_CLI_EXECUTE" {print "RICK_COPILOT_CLI_EXECUTE="$2}
'
```

Check GitHub API auth:

```bash
PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
python3 - "$PID" <<'PY'
import sys, urllib.error, urllib.request
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
    raise SystemExit(2)
req = urllib.request.Request(
    "https://api.github.com/user",
    headers={"Authorization": f"token {token}", "User-Agent": "umbral-f8b-token-check"},
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        status = resp.status
except urllib.error.HTTPError as exc:
    status = exc.code
print(f"GITHUB_USER_HTTP={status}")
print("TOKEN_STATUS=valid" if status == 200 else "TOKEN_STATUS=invalid")
raise SystemExit(0 if status == 200 else 3)
PY
```

Stop `amarillo` if token is not valid.

Inspect installed CLI support without calling Copilot providers:

```bash
IMAGE=$(docker image ls --format '{{.Repository}}:{{.Tag}}' | grep '^umbral-sandbox-copilot-cli:' | head -1)
test -n "$IMAGE" || { echo "NO_SANDBOX_IMAGE_STOP"; exit 4; }
docker run --rm --entrypoint /bin/sh "$IMAGE" -lc '
  copilot --version
  copilot --help | grep -E -- "--model|--available-tools|--allow-all|--allow-tool|--deny-tool" || true
'
```

## O2 - Scoped network and nft with drop evidence

Resolve current allow-list:

```bash
python3 scripts/copilot_egress_resolver.py --non-strict --format json > /tmp/f8b-egress.json
python3 - <<'PY'
import json
d = json.load(open('/tmp/f8b-egress.json', encoding='utf-8'))
v4 = d.get('ip_sets', {}).get('copilot_v4', [])
v6 = d.get('ip_sets', {}).get('copilot_v6', [])
print(f"copilot_v4_count={len(v4)}")
print(f"copilot_v6_count={len(v6)}")
if not v4 and not v6:
    raise SystemExit("NO_EGRESS_IPS_STOP")
PY
```

Create/verify network:

```bash
if docker network inspect copilot-egress >/dev/null 2>&1; then
  BRIDGE_NAME=$(docker network inspect copilot-egress -f '{{index .Options "com.docker.network.bridge.name"}}')
  test "$BRIDGE_NAME" = "br-copilot" || { echo "BRIDGE_MISMATCH_STOP"; exit 4; }
  echo false > /tmp/f8b-network-created-by-task
else
  docker network create \
    --driver bridge \
    --opt com.docker.network.bridge.name=br-copilot \
    --opt com.docker.network.bridge.enable_icc=false \
    copilot-egress
  echo true > /tmp/f8b-network-created-by-task
fi
```

Apply scoped nft and populate sets:

```bash
BACKUP_DIR="/home/rick/.copilot/backups/f8b-egress-model-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
sudo nft list ruleset > "$BACKUP_DIR/nft-ruleset-before.nft" 2>/dev/null || true
chmod 0600 "$BACKUP_DIR"/*
echo "$BACKUP_DIR" > /tmp/f8b-backup-dir

sudo nft -c -f infra/networking/copilot-egress.nft.example
sudo nft -f infra/networking/copilot-egress.nft.example

python3 - <<'PY' > /tmp/f8b-sets.nft
import json
d = json.load(open('/tmp/f8b-egress.json', encoding='utf-8'))
v4 = d.get('ip_sets', {}).get('copilot_v4', [])
v6 = d.get('ip_sets', {}).get('copilot_v6', [])
print('flush set inet copilot_egress copilot_v4')
if v4:
    print('add element inet copilot_egress copilot_v4 { ' + ', '.join(v4) + ' }')
print('flush set inet copilot_egress copilot_v6')
if v6:
    print('add element inet copilot_egress copilot_v6 { ' + ', '.join(v6) + ' }')
PY
sudo nft -f /tmp/f8b-sets.nft
sudo nft list table inet copilot_egress > "$BACKUP_DIR/nft-table-during-before.txt"
```

## O3 - Direct model/egress diagnostic

Run exactly one direct sandbox Copilot probe, not via `copilot_cli.run`.
This uses the same security posture as the worker path but keeps stdout/stderr
visible for diagnosis.

```bash
RUN_ID="f8b-direct-$(date -u +%Y%m%dT%H%M%SZ)"
OUT="/tmp/$RUN_ID.out"
ERR="/tmp/$RUN_ID.err"
echo "$RUN_ID" > /tmp/f8b-run-id
JOURNAL_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$JOURNAL_START" > /tmp/f8b-journal-start

PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
TOKEN=$(tr '\0' '\n' < /proc/$PID/environ | awk -F= '$1=="COPILOT_GITHUB_TOKEN"{print $2; exit}')
test -n "$TOKEN" || { echo "TOKEN_MISSING_STOP"; exit 5; }
export COPILOT_GITHUB_TOKEN="$TOKEN"

printf 'Return exactly: F8B_OK\n' | docker run --rm -i \
  --network=copilot-egress \
  --read-only \
  --tmpfs /tmp:size=64m,mode=1777,exec,nosuid,nodev \
  --tmpfs /scratch:size=64m,mode=1777,nosuid,nodev \
  --tmpfs /home/runner/.cache:size=32m,mode=1777 \
  --tmpfs /home/runner/.copilot:size=32m,mode=1777 \
  --memory=1g --memory-swap=1g --cpus=1.0 --pids-limit=256 \
  --cap-drop=ALL --security-opt no-new-privileges \
  --user 10001:10001 --ipc=none \
  --env COPILOT_GITHUB_TOKEN \
  --env NO_COLOR=1 \
  "$IMAGE" \
  /usr/local/bin/copilot-cli-wrapper \
  /bin/sh -lc '
    set -eu
    cat > /tmp/prompt.txt
    prompt=$(cat /tmp/prompt.txt)
    exec copilot --no-color --no-auto-update --no-remote --no-ask-user \
      --disable-builtin-mcps \
      --secret-env-vars=COPILOT_GITHUB_TOKEN \
      --available-tools=view,grep,glob \
      --log-level=debug \
      --model "Claude Opus 4.7" \
      --prompt "$prompt"
' > "$OUT" 2> "$ERR"
RC=$?
unset TOKEN COPILOT_GITHUB_TOKEN
JOURNAL_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$JOURNAL_END" > /tmp/f8b-journal-end
echo "DIRECT_RC=$RC"
echo "stdout_bytes=$(wc -c < "$OUT")"
echo "stderr_bytes=$(wc -c < "$ERR")"
head -80 "$OUT"
head -120 "$ERR"
```

If shell exits before `unset TOKEN COPILOT_GITHUB_TOKEN`, run that unset
manually before doing anything else.

## O4 - Capture drops and classify

```bash
BACKUP_DIR=$(cat /tmp/f8b-backup-dir)
sudo nft list table inet copilot_egress > "$BACKUP_DIR/nft-table-during-after.txt"
echo "=== nft counters ==="
sudo nft list table inet copilot_egress | grep -E 'counter|DROP|accept' || true

echo "=== kernel nft logs ===" > "$BACKUP_DIR/kernel-nft-window.txt"
journalctl -k \
  --since "$(cat /tmp/f8b-journal-start)" \
  --until "$(cat /tmp/f8b-journal-end)" \
  --no-pager 2>/dev/null \
  | grep -i 'copilot-egress' >> "$BACKUP_DIR/kernel-nft-window.txt" || true

cat "$BACKUP_DIR/kernel-nft-window.txt" | tail -80
```

Classify:

- `verde`: direct probe exits 0 with output and no drops.
- `amarillo`: token/model valid but drops occur; list missing dst IPs/hosts if inferable.
- `rojo`: host-wide egress impacted, token printed, rollback fails, or non-scoped nft appears.

## O5 - Rollback

```bash
sudo nft delete table inet copilot_egress 2>/dev/null || true
if [ "$(cat /tmp/f8b-network-created-by-task 2>/dev/null)" = "true" ]; then
  docker network rm copilot-egress 2>/dev/null || true
fi

curl -s -o /dev/null -w "worker_health=%{http_code}\n" http://127.0.0.1:8088/health
sudo nft list table inet copilot_egress 2>/dev/null && echo "TABLE_PRESENT_BAD" || echo "no copilot nft table"
docker network ls --format '{{.Name}}' | grep '^copilot-egress$' && echo "DOCKER_NET_PRESENT" || echo "no copilot-egress docker network"
sudo nft list ruleset 2>/dev/null | grep -E 'hook output.*policy drop|copilot_egress' && echo "BAD_SCOPING" || echo "no host-wide output drop"
```

## O6 - Report and PR

Write:

```text
reports/copilot-cli/f8b-diagnose-egress-and-model-power-2026-05-07.md
```

Include:

- approval string present/absent
- token status by name only
- Copilot CLI version and help snippets for `--model`/tools
- model requested: `Claude Opus 4.7`
- direct run rc/stdout/stderr byte counts and short redacted excerpts
- nft resolver counts
- before/after nft counters
- kernel nft drop logs with no secrets
- rollback proof
- recommended allow-list/model/tool change

Branch:

```bash
git checkout -B rick/f8b-diagnose-egress-and-model-power-2026-05-07 origin/main
git add .agents/tasks/f8b-diagnose-egress-and-model-power-2026-05-07.md
git add -f reports/copilot-cli/f8b-diagnose-egress-and-model-power-2026-05-07.md
git commit -m "evidence(copilot-cli): F8B diagnose egress and model-power path"
git push -u origin rick/f8b-diagnose-egress-and-model-power-2026-05-07
```

Open PR manually if `gh` is unavailable. Request Codex review.
