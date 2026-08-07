#!/usr/bin/env bash
set -euo pipefail

raw="$(cat)"
if [ -z "$raw" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
  exit 0
fi

python3 - <<'PY' <<< "$raw"
import json, re, sys
raw = sys.stdin.read().strip()

def emit(decision, reason=None):
    payload = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision}}
    if reason:
        payload["hookSpecificOutput"]["permissionDecisionReason"] = reason
    print(json.dumps(payload, separators=(",", ":")))

if not raw:
    emit("allow")
    raise SystemExit

try:
    event = json.loads(raw)
except Exception:
    emit("ask", "Could not parse tool input for deployed-repo guard.")
    raise SystemExit

tool = str(event.get("tool_name") or "")
input_data = event.get("tool_input") or {}

allowed_paths = [".claude/", ".github/copilot-instructions.md"]

def add_candidates(value, out):
    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            out.append(value)
        return
    if isinstance(value, list):
        for item in value:
            add_candidates(item, out)
        return
    if isinstance(value, dict):
        for key in ("path", "file_path", "filePath", "targetFilePath", "old_file_path", "new_file_path", "oldFilePath", "newFilePath", "files"):
            if key in value:
                add_candidates(value[key], out)

candidates = []
add_candidates(input_data, candidates)

def normalize(path):
    p = path.replace('\\', '/').strip()
    while p.startswith('./'):
        p = p[2:]
    return p

def is_allowed_repo_path(path):
    p = normalize(path)
    return any(p == ap or p.startswith(ap) for ap in allowed_paths)

if tool in {"Write", "Edit", "MultiEdit"}:
    for path in candidates:
        if not is_allowed_repo_path(path):
            emit("ask", "This VPS repo is the deployed runtime reference. Edit /home/rick/umbral-agent-stack-main-clean for code changes unless the user explicitly asks to modify the deployed repo.")
            raise SystemExit

if tool == "Bash":
    command = str(input_data.get("command") or input_data.get("commandLine") or "")
    looks_like_write = re.search(r'(>|>>|\brm\b|\bmv\b|\bcp\b|\binstall\b|\btee\b|\bsed\s+-i\b|\bperl\s+-pi\b|\btruncate\b|\bpython3?\b.*\bwrite\b|\bgit\s+(pull|apply|am|cherry-pick|merge|rebase|reset|restore|checkout)\b)', command, re.I)
    touches_deployed = "/home/rick/umbral-agent-stack" in command and "/home/rick/umbral-agent-stack-main-clean" not in command
    if looks_like_write and touches_deployed:
        emit("ask", "This command appears to modify the deployed VPS repo. Use the clean repo unless the user explicitly requested a production-repo change.")
        raise SystemExit

emit("allow")
PY
