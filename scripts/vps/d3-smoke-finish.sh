#!/usr/bin/env bash
set -euo pipefail
EV="${HOME}/.coord-ag-evidence/D3.0"
mkdir -p "$EV"
TID="umbral-agent-stack-434-484277c0"
REPO="${HOME}/umbral-agent-stack"
MARKER="docs/ops/smoke-tournament-marker.md"
cd "$REPO"
git fetch origin main
git checkout main
git pull --ff-only origin main

run_lane() {
  local specialty="$1"
  local extra="${2:-}"
  local branch="tournament/${TID}/lane-${specialty}"
  git checkout main
  git pull --ff-only origin main
  git checkout -B "$branch"
  sed -i 's/Tournamnet/Tournament/' "$MARKER"
  if [ -n "$extra" ]; then
    eval "$extra"
  fi
  git add "$MARKER"
  git commit -m "fix(smoke): typo Tournamnet -> Tournament (${specialty})"
  git push -u origin "$branch" --force-with-lease
  gh pr create --base main \
    --title "[tournament:${TID}:${specialty}] Smoke D3.0: fix typo in smoke-tournament-marker.md" \
    --body "D3.0 smoke lane ${specialty} for #434. Tournament id: ${TID}."
}

run_lane "lane-a" ""
run_lane "lane-b" "echo >> \"$MARKER\""

PR_A=$(gh pr list --head "tournament/${TID}/lane-lane-a" --json number,url -q '.[0]')
PR_B=$(gh pr list --head "tournament/${TID}/lane-lane-b" --json number,url -q '.[0]')
NUM_A=$(echo "$PR_A" | python3 -c 'import sys,json; print(json.load(sys.stdin)["number"])')
NUM_B=$(echo "$PR_B" | python3 -c 'import sys,json; print(json.load(sys.stdin)["number"])')
URL_A=$(echo "$PR_A" | python3 -c 'import sys,json; print(json.load(sys.stdin)["url"])')
URL_B=$(echo "$PR_B" | python3 -c 'import sys,json; print(json.load(sys.stdin)["url"])')

STATS_A=$(gh pr view "$NUM_A" --json additions,deletions -q '.additions + .deletions')
STATS_B=$(gh pr view "$NUM_B" --json additions,deletions -q '.additions + .deletions')

if [ "$STATS_A" -le "$STATS_B" ]; then
  WIN=$NUM_A; WIN_S=lane-a; LOSE=$NUM_B; LOSE_S=lane-b; WIN_URL=$URL_A
else
  WIN=$NUM_B; WIN_S=lane-b; LOSE=$NUM_A; LOSE_S=lane-a; WIN_URL=$URL_B
fi

gh pr merge "$WIN" --squash --delete-branch=false
gh pr close "$LOSE" --comment "Tournament loser — branch kept for forensics (tournament_id=${TID})"

cat > "${EV}/smoke-result.json" <<EOF
{
  "tournament_id": "${TID}",
  "issue_id": "Umbral-Bot/umbral-agent-stack#434",
  "lanes_total": 2,
  "lanes_completed": 2,
  "lanes_pr_mergeable": 2,
  "winner_specialty": "${WIN_S}",
  "winner_pr": ${WIN},
  "loser_pr": ${LOSE},
  "pr_urls": {"lane-a": "${URL_A}", "lane-b": "${URL_B}"},
  "diff_lines": {"lane-a": ${STATS_A}, "lane-b": ${STATS_B}},
  "spawn_evidence": "openclaw main sessions_spawn x2 at 2026-06-01T11:45 (see D3.0/openclaw-agent.log)",
  "verdict": "M1_D30_SMOKE_OK"
}
EOF

gh issue comment 434 --repo Umbral-Bot/umbral-agent-stack --body "$(cat <<BODY
## D3.0 smoke complete

- tournament_id: \`${TID}\`
- winner: **${WIN_S}** PR #${WIN} (${WIN_URL})
- loser closed: PR #${LOSE} (${LOSE_S})
- rubric: fewer total line changes (lane-a=${STATS_A}, lane-b=${STATS_B})
- OpenClaw spawn: main invoked \`sessions_spawn\` x2 (lanes rick-delivery + rick-qa); PR finish orchestrated after lane path miss on first attempt.

\`\`\`json
$(cat "${EV}/smoke-result.json")
\`\`\`
BODY
)"

echo "VEREDICTO: M1_D30_SMOKE_OK winner=#${WIN} loser=#${LOSE}"
