#!/usr/bin/env bash
set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate 2>/dev/null || true

if [ -f ~/.config/openclaw/env ]; then
  set -a
  source ~/.config/openclaw/env
  set +a
fi

export PYTHONPATH=.
python3 scripts/dashboard_report_vps.py --trigger cron.hourly
