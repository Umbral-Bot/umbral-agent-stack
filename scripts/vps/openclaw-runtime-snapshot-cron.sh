#!/usr/bin/env bash
set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate 2>/dev/null || true

if [ -f ~/.config/openclaw/env ]; then
  # shellcheck disable=SC1091
  source "$HOME/umbral-agent-stack/scripts/vps/load-openclaw-env.sh"
  load_openclaw_env "$HOME/.config/openclaw/env"
fi

export PYTHONPATH=.
mkdir -p reports/runtime/generated

python3 scripts/openclaw_runtime_snapshot.py \
  --days 7 \
  --sessions-root "$HOME/.openclaw/agents" \
  --format json > reports/runtime/generated/openclaw-runtime-snapshot-latest.json

python3 scripts/openclaw_runtime_snapshot.py \
  --days 7 \
  --sessions-root "$HOME/.openclaw/agents" \
  --format markdown > reports/runtime/generated/openclaw-runtime-snapshot-latest.md
