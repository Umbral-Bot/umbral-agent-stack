#!/usr/bin/env bash
set -euo pipefail
EV="${HOME}/.coord-ag-evidence/D3.0"
mkdir -p "$EV"
OC="/home/rick/.npm-global/bin/openclaw"
SPEC="${HOME}/umbral-agent-stack/openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/smoke-tournament-spec.yaml"
SID="d30-smoke-$(date +%Y%m%d%H%M)"
MSG="David authorized D3.0 tournament smoke (2026-06-01). Execute skill multi-agent-tournament-orchestrator using spec: ${SPEC}. Follow all phases in the skill and docs/79 section 7. David authorized merge winner for this smoke. Post final metrics JSON as comment on issue #434. Tournament id umbral-agent-stack-434-484277c0."
echo "session_id=${SID}" | tee "${EV}/session.txt"
"${OC}" agent --agent main --session-id "${SID}" --timeout 3600 --json --message "${MSG}" \
  2>&1 | tee "${EV}/openclaw-agent.log"
