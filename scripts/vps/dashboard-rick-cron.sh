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
python3 scripts/dashboard_report_vps.py --trigger cron.hourly
