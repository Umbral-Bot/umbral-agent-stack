#!/usr/bin/env bash
set -euo pipefail
EV="${HOME}/.coord-ag-evidence/D3.2"
mkdir -p "$EV"
OC="/home/rick/.npm-global/bin/openclaw"
SPEC="${HOME}/umbral-agent-stack/openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d32-issue-440-o2-backup-alerts-spec.yaml"
SID="d32-tournament-$(date +%Y%m%d%H%M)"
MSG="David authorized D3.2 tournament (O2 backup alerts). Execute skill multi-agent-tournament-orchestrator using spec: ${SPEC}. Follow all phases in the skill and docs/79. Issue #440 registry backup failure alert (2 consecutive days). David authorized merge winner when rubric satisfied. Post final metrics JSON as comment on issue #440. Cap 2 lanes. Lane without PR URL = incomplete. Evidence dir: ${EV}."
echo "session_id=${SID}" | tee "${EV}/session.txt"
echo "spec=${SPEC}" | tee -a "${EV}/session.txt"
"${OC}" agent --agent main --session-id "${SID}" --timeout 7200 --json --message "${MSG}" \
  2>&1 | tee "${EV}/openclaw-agent.log"
