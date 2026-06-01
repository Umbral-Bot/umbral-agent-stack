#!/usr/bin/env bash
set -euo pipefail
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
git checkout -B tournament/umbral-agent-stack-434-484277c0/lane-lane-b
sed -i 's/Tournamnet/Tournament/' docs/ops/smoke-tournament-marker.md
printf '\n' >> docs/ops/smoke-tournament-marker.md
git add docs/ops/smoke-tournament-marker.md
git commit -m 'fix(smoke): typo Tournamnet -> Tournament (lane-b)'
git push -u origin HEAD --force-with-lease
