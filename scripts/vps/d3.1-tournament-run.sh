#!/usr/bin/env bash
set -euo pipefail
EV="${HOME}/.coord-ag-evidence/D3.1"
mkdir -p "$EV"
OC="/home/rick/.npm-global/bin/openclaw"
SPEC="${HOME}/umbral-agent-stack/openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d31-issue-403-tournament-spec.yaml"
SID="d31-tournament-$(date +%Y%m%d%H%M)"
MSG="David authorized D3.1 first REAL tournament (2026-06-01). Execute skill multi-agent-tournament-orchestrator using spec: ${SPEC}. Follow all phases in the skill and docs/79. Issue #403 SQLite hardening. David authorized merge winner when rubric satisfied. Post final metrics JSON as comment on issue #403. Cap 2 lanes. Evidence dir: ${EV}."
echo "session_id=${SID}" | tee "${EV}/session.txt"
echo "spec=${SPEC}" | tee -a "${EV}/session.txt"
"${OC}" agent --agent main --session-id "${SID}" --timeout 7200 --json --message "${MSG}" \
  2>&1 | tee "${EV}/openclaw-agent.log"
