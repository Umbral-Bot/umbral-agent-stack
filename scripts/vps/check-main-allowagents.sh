#!/usr/bin/env bash
python3 <<'PY'
import json
c = json.load(open("/home/rick/.openclaw/openclaw.json"))
main = next(a for a in c["agents"]["list"] if a.get("id") == "main")
print("allowAgents:", main.get("subagents", {}).get("allowAgents"))
PY
