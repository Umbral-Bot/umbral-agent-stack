#!/usr/bin/env bash
set -euo pipefail
EV="${HOME}/.coord-ag-evidence/D3.0"
mkdir -p "$EV"
BK="${EV}/openclaw.json.bak.allowagents.$(date +%Y%m%d%H%M)"
cp -a "${HOME}/.openclaw/openclaw.json" "$BK"
python3 <<'PY'
import json, os, tempfile
P = os.path.expanduser("~/.openclaw/openclaw.json")
cfg = json.load(open(P))
main = next(a for a in cfg["agents"]["list"] if a.get("id") == "main")
sub = main.setdefault("subagents", {})
old = list(sub.get("allowAgents", []))
want = ["rick-orchestrator", "rick-delivery", "rick-qa"]
merged = list(dict.fromkeys(want + old))
sub["allowAgents"] = merged
print("allowAgents:", merged)
st = os.stat(P)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(P))
with os.fdopen(fd, "w") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write("\n")
os.chmod(tmp, st.st_mode & 0o777)
os.replace(tmp, P)
PY
systemctl --user restart openclaw-gateway.service
ok=0
for _ in $(seq 1 30); do
  code=$(curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/health 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then ok=1; break; fi
  sleep 2
done
echo "health_ok=${ok} pid=$(systemctl --user show -p MainPID --value openclaw-gateway.service)"
cd "${HOME}/umbral-agent-stack"
git pull --ff-only origin main
SRC=openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator
DST="${HOME}/.openclaw/workspace/skills/multi-agent-tournament-orchestrator"
mkdir -p "$DST"
rsync -a --delete "$SRC"/ "$DST"/
bash scripts/openclaw/tournament-preflight-dry-run.sh \
  openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/smoke-tournament-spec.yaml \
  2>&1 | tee "${EV}/preflight.log"
