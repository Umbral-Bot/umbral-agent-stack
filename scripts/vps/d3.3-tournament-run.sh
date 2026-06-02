#!/usr/bin/env bash
set -euo pipefail
EV="${HOME}/.coord-ag-evidence/D3.3"
mkdir -p "$EV"
OC="/home/rick/.npm-global/bin/openclaw"
SPEC="${HOME}/umbral-agent-stack/openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d33-issue-445-sync-skills-adapters-spec.yaml"
SID="d33-tournament-$(date +%Y%m%d%H%M)"
MSG="David authorized D3.3 tournament (O3 sync_skills adapters). Execute skill multi-agent-tournament-orchestrator using spec: ${SPEC}. Follow all phases in the skill and docs/79. Issue #445 platform adapters codex+cursor dry-run. David authorized merge winner when rubric satisfied. Post final metrics JSON as comment on issue #445. Cap 2 lanes. Lane without PR URL = incomplete. Evidence dir: ${EV}."
echo "session_id=${SID}" | tee "${EV}/session.txt"
echo "spec=${SPEC}" | tee -a "${EV}/session.txt"
"${OC}" agent --agent main --session-id "${SID}" --timeout 7200 --json --message "${MSG}" \
  2>&1 | tee "${EV}/openclaw-agent.log"
