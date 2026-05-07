---
id: f8c-retry-after-github-meta-egress-fix-2026-05-07
title: "F8C retry direct Copilot diagnostic with GitHub Meta CIDR egress"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-07
report: reports/copilot-cli/f8c-retry-after-github-meta-egress-fix-2026-05-07.md
---

# F8C retry direct Copilot diagnostic with GitHub Meta CIDR egress

## Objective

Validate the resolver fix from PR F8C: `scripts/copilot_egress_resolver.py`
can opt into GitHub Meta CIDRs and populate the scoped nft sets with the
GitHub load-balancer CIDR that F8B proved was missing.

F8B evidence:

- Direct probe requested `--model "Claude Opus 4.7"`.
- Copilot CLI accepted the flag.
- Token was valid (`GITHUB_USER_HTTP=200`).
- Probe exited `1` with stdout 0 bytes and readiness marker only on stderr.
- nft dropped 35 packets to `140.82.113.21`
  (`lb-140-82-113-21-iad.github.com`).
- That IP is inside GitHub Meta `api` CIDR `140.82.112.0/20`.

This task must determine whether adding GitHub Meta CIDRs removes the scoped
egress drops and lets the direct probe reach Copilot backend.

## Hard approval gate

David's invocation must include exactly:

```text
APPROVE_F8C_GITHUB_META_EGRESS_RETRY=YES
```

If absent, stop `rojo` and do not create nft tables, Docker networks, or
direct Copilot runs.

## Rules

- Do **not** call `copilot_cli.run` in this task.
- Use exactly one direct sandbox probe.
- Keep token value secret; print `COPILOT_GITHUB_TOKEN=present_by_name` only.
- Do not use `--allow-all-tools`, `--allow-all`, or `--yolo`.
- Do not enable write tools.
- Do not modify repo files from inside the Copilot sandbox.
- Open scoped nft/Docker network only inside the diagnostic window.
- Always rollback nft table and Docker network if this task created it.
- Capture structured metrics JSON with:
  `docker_start_ms`, `container_ready_ms`, `copilot_exit_ms`,
  `nft_drop_delta`, `first_stdout_byte_ms`.
- No Plan B ADR in this task. Plan B is not armed unless drops persist for
  destinations that cannot be mapped to GitHub Meta CIDRs.

## O0 - Sync and source checks

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
git log --oneline -5

grep -n -- '--include-github-meta' scripts/copilot_egress_resolver.py
grep -n 'GITHUB_META_KEYS' scripts/copilot_egress_resolver.py
grep -n 'github_meta' scripts/copilot_egress_resolver.py | head -10
python3 scripts/verify_copilot_egress_contract.py
```

Stop `rojo` if the GitHub Meta resolver code is missing or the egress contract
verifier fails.

## O1 - Token and CLI capability check

Restart worker once to load current secrets, then validate the token without
printing it:

```bash
cd ~/umbral-agent-stack
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
    headers={"Authorization": f"token {token}", "User-Agent": "umbral-f8c-token-check"},
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

Stop `amarillo` if token is missing or invalid. Do not open gates or nft.

## O2 - Resolver with GitHub Meta CIDRs

```bash
cd ~/umbral-agent-stack
python3 scripts/copilot_egress_resolver.py \
  --include-github-meta \
  --non-strict \
  --format json > /tmp/f8c-egress.json

python3 - <<'PY'
import json
d = json.load(open('/tmp/f8c-egress.json', encoding='utf-8'))
v4 = d.get('ip_sets', {}).get('copilot_v4', [])
v6 = d.get('ip_sets', {}).get('copilot_v6', [])
meta = d.get('github_meta', {})
print(f"copilot_v4_count={len(v4)}")
print(f"copilot_v6_count={len(v6)}")
print(f"github_meta_included={meta.get('included')}")
print(f"github_meta_errors={meta.get('errors')}")
print("has_140_82_112_0_20=", "140.82.112.0/20" in v4)
if "140.82.112.0/20" not in v4:
    raise SystemExit("MISSING_GITHUB_META_API_CIDR_STOP")
if not v4 and not v6:
    raise SystemExit("NO_EGRESS_IPS_STOP")
PY
```

Stop `rojo` if `140.82.112.0/20` is missing.

## O3 - Scoped network and nft window

Create or reuse the dedicated Docker network, apply scoped nft, and populate
sets from `/tmp/f8c-egress.json`:

```bash
cd ~/umbral-agent-stack

if docker network inspect copilot-egress >/dev/null 2>&1; then
  BRIDGE_NAME=$(docker network inspect copilot-egress -f '{{index .Options "com.docker.network.bridge.name"}}')
  test "$BRIDGE_NAME" = "br-copilot" || { echo "BRIDGE_MISMATCH_STOP got=$BRIDGE_NAME"; exit 4; }
  echo false > /tmp/f8c-network-created-by-task
  echo "network exists, bridge=$BRIDGE_NAME"
else
  docker network create \
    --driver bridge \
    --opt com.docker.network.bridge.name=br-copilot \
    --opt com.docker.network.bridge.enable_icc=false \
    copilot-egress
  echo true > /tmp/f8c-network-created-by-task
fi

BACKUP_DIR="/home/rick/.copilot/backups/f8c-github-meta-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
sudo nft list ruleset > "$BACKUP_DIR/nft-ruleset-before.nft" 2>/dev/null || true
chmod 0600 "$BACKUP_DIR"/* 2>/dev/null
echo "$BACKUP_DIR" > /tmp/f8c-backup-dir
echo "BACKUP_DIR=$BACKUP_DIR"

sudo nft -c -f infra/networking/copilot-egress.nft.example
sudo nft -f infra/networking/copilot-egress.nft.example

python3 - <<'PY' > /tmp/f8c-sets.nft
import json
d = json.load(open('/tmp/f8c-egress.json', encoding='utf-8'))
v4 = d.get('ip_sets', {}).get('copilot_v4', [])
v6 = d.get('ip_sets', {}).get('copilot_v6', [])
print('flush set inet copilot_egress copilot_v4')
if v4:
    print('add element inet copilot_egress copilot_v4 { ' + ', '.join(v4) + ' }')
print('flush set inet copilot_egress copilot_v6')
if v6:
    print('add element inet copilot_egress copilot_v6 { ' + ', '.join(v6) + ' }')
PY
sudo nft -f /tmp/f8c-sets.nft
sudo nft list table inet copilot_egress > "$BACKUP_DIR/nft-table-during-before.txt"
grep -n '140.82.112.0/20' "$BACKUP_DIR/nft-table-during-before.txt"
```

Stop and rollback if nft parse/apply/populate fails.

## O4 - Exactly one direct sandbox probe

Run a direct probe through the same hardened sandbox shape used by F8B. This
does not call the Worker task.

```bash
cd ~/umbral-agent-stack
IMAGE=$(docker image ls --format '{{.Repository}}:{{.Tag}}' | grep '^umbral-sandbox-copilot-cli:' | head -1)
test -n "$IMAGE" || { echo "NO_SANDBOX_IMAGE_STOP"; exit 5; }
echo "IMAGE=$IMAGE"

RUN_ID="f8c-direct-$(date -u +%Y%m%dT%H%M%SZ)"
OUT="/tmp/$RUN_ID.out"
ERR="/tmp/$RUN_ID.err"
echo "$RUN_ID" > /tmp/f8c-run-id
JOURNAL_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$JOURNAL_START" > /tmp/f8c-journal-start
HOST_T0_MS=$(python3 -c 'import time; print(time.time_ns()//1_000_000)')

PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
TOKEN=$(tr '\0' '\n' < /proc/$PID/environ | awk -F= '$1=="COPILOT_GITHUB_TOKEN"{print $2; exit}')
test -n "$TOKEN" && echo "token captured present_by_name" || { echo "TOKEN_MISSING_STOP"; exit 5; }
export COPILOT_GITHUB_TOKEN="$TOKEN"

printf 'Return exactly: F8C_OK\n' | docker run --rm -i \
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
    READY_NS=$(date +%s%N)
    READY_MS=$((READY_NS/1000000))
    echo "F8C_CONTAINER_READY_MS=$READY_MS" >&2
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
echo "$JOURNAL_END" > /tmp/f8c-journal-end
HOST_T1_MS=$(python3 -c 'import time; print(time.time_ns()//1_000_000)')

echo "$HOST_T0_MS" > /tmp/f8c-host-t0
echo "$HOST_T1_MS" > /tmp/f8c-host-t1
echo "$OUT" > /tmp/f8c-out-path
echo "$ERR" > /tmp/f8c-err-path
echo "$RC" > /tmp/f8c-rc

echo "DIRECT_RC=$RC"
echo "stdout_bytes=$(wc -c < "$OUT")"
echo "stderr_bytes=$(wc -c < "$ERR")"
head -80 "$OUT"
head -200 "$ERR"
```

Do not run a second direct probe.

## O5 - Evidence, drops, metrics

```bash
cd ~/umbral-agent-stack
BACKUP_DIR=$(cat /tmp/f8c-backup-dir)
sudo nft list table inet copilot_egress > "$BACKUP_DIR/nft-table-during-after.txt"
sudo journalctl -k --since "$(cat /tmp/f8c-journal-start)" --until "$(cat /tmp/f8c-journal-end)" --no-pager 2>/dev/null \
  | grep -i 'copilot-egress' > "$BACKUP_DIR/kernel-nft-window.txt" || true

awk '
/copilot-egress accept v4:/ { for(i=1;i<=NF;i++){ if($i ~ /^DST=/){sub("DST=","",$i); accept[$i]++}} }
/copilot-egress DROP scoped:/ { for(i=1;i<=NF;i++){ if($i ~ /^DST=/){sub("DST=","",$i); drop[$i]++}} }
END {
  print "ACCEPTED:"; for (k in accept) printf "  %5d  %s\n", accept[k], k
  print "DROPPED:";  for (k in drop)   printf "  %5d  %s\n", drop[k], k
}' "$BACKUP_DIR/kernel-nft-window.txt" | tee "$BACKUP_DIR/drop-summary.txt"

cp /tmp/f8c-egress.json "$BACKUP_DIR/" 2>/dev/null || true
cp "$(cat /tmp/f8c-out-path)" "$BACKUP_DIR/direct.out" 2>/dev/null || true
cp "$(cat /tmp/f8c-err-path)" "$BACKUP_DIR/direct.err" 2>/dev/null || true

python3 - "$(cat /tmp/f8c-host-t0)" "$(cat /tmp/f8c-host-t1)" "$(cat /tmp/f8c-out-path)" "$(cat /tmp/f8c-err-path)" "$BACKUP_DIR" <<'PY'
import json, pathlib, re, sys
t0 = int(sys.argv[1]); t1 = int(sys.argv[2])
out_path = pathlib.Path(sys.argv[3]); err_path = pathlib.Path(sys.argv[4])
backup = pathlib.Path(sys.argv[5])
ready_ms = None
m = re.search(r"F8C_CONTAINER_READY_MS=(\d+)", err_path.read_text(errors="replace"))
if m:
    ready_ms = int(m.group(1))
def drop_counter(text):
    m = re.search(r"counter packets\s+(\d+)\s+bytes\s+(\d+)\s+drop", text)
    if not m:
        return {"packets": 0, "bytes": 0}
    return {"packets": int(m.group(1)), "bytes": int(m.group(2))}
before = drop_counter((backup / "nft-table-during-before.txt").read_text(errors="replace"))
after = drop_counter((backup / "nft-table-during-after.txt").read_text(errors="replace"))
payload = {
    "docker_start_ms": 0,
    "container_ready_ms": None if ready_ms is None else ready_ms - t0,
    "copilot_exit_ms": t1 - t0,
    "nft_drop_delta": {"packets": after["packets"] - before["packets"], "bytes": after["bytes"] - before["bytes"]},
    "first_stdout_byte_ms": None if out_path.stat().st_size == 0 else t1 - t0,
    "stdout_bytes": out_path.stat().st_size,
    "stderr_bytes": err_path.stat().st_size,
}
(backup / "f8c-metrics.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(json.dumps(payload, indent=2, sort_keys=True))
PY

PAT='ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{60,}|gho_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|ghu_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|xoxb-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]+PRIVATE KEY-----'
for f in "$BACKUP_DIR/direct.out" "$BACKUP_DIR/direct.err" "$BACKUP_DIR/f8c-egress.json" "$BACKUP_DIR/f8c-metrics.json"; do
  echo -n "$(basename "$f"): "
  grep -EH "$PAT" "$f" >/dev/null 2>&1 && echo "LEAK" || echo "clean"
done
```

## O6 - Rollback

```bash
sudo nft delete table inet copilot_egress 2>/dev/null && echo "nft table deleted" || echo "no nft table"
if [ "$(cat /tmp/f8c-network-created-by-task 2>/dev/null)" = "true" ]; then
  docker network rm copilot-egress 2>/dev/null && echo "docker network removed" || echo "docker network rm skipped/error"
fi

curl -s -o /dev/null -w "worker_health=%{http_code}\n" http://127.0.0.1:8088/health
sudo nft list table inet copilot_egress 2>/dev/null && echo "TABLE_PRESENT_BAD" || echo "no copilot nft table"
docker network ls --format '{{.Name}}' | grep '^copilot-egress$' && echo "DOCKER_NET_PRESENT" || echo "no copilot-egress docker network"
sudo nft list ruleset 2>/dev/null | grep -E 'hook output.*policy drop|copilot_egress' && echo "BAD_SCOPING" || echo "no host-wide output drop, no residual copilot_egress"
```

Rollback is mandatory regardless of probe outcome.

## O7 - Verdict, report, branch, PR

Create `reports/copilot-cli/f8c-retry-after-github-meta-egress-fix-2026-05-07.md`
with:

- resolver output summary, including whether `140.82.112.0/20` was present
- direct probe rc/stdout/stderr byte counts
- metrics JSON
- nft accept/drop destination summary
- secret scan result
- rollback proof
- final verdict

Verdict rules:

- `verde`: direct probe exits `0`, stdout contains `F8C_OK`, and
  `nft_drop_delta.packets == 0`.
- `amarillo`: direct probe exits non-zero, but all drops map to GitHub Meta
  CIDRs or provider/model auth returns an explicit non-secret error.
- `rojo`: token missing/invalid, resolver lacks `140.82.112.0/20`, host-wide
  nft drop appears, secret leak, rollback failure, or dropped destinations do
  not map to GitHub Meta/public provider CIDRs.

Open a PR with reviewer `codex` if possible; otherwise include `cc @codex`
in the PR body and report that reviewer assignment failed.

## Log

