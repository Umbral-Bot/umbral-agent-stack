#!/usr/bin/env bash
# Cron wrapper for dashboard_report_vps.py + openclaw_panel_vps.py
# Requiere: WORKER_TOKEN, NOTION_API_KEY, NOTION_DASHBOARD_PAGE_ID, REDIS_URL en ~/.config/openclaw/env
# Install: crontab -e â†’ */15 * * * * ~/umbral-agent-stack/scripts/vps/dashboard-cron.sh >> /tmp/dashboard_cron.log 2>&1

set -uo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate 2>/dev/null || true

# Load env (WORKER_TOKEN, NOTION_*, REDIS_URL, etc.)
if [ -f ~/.config/openclaw/env ]; then
  set -a
  source ~/.config/openclaw/env
  set +a
fi
export PYTHONPATH=.

status=0

if ! python3 scripts/dashboard_report_vps.py; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') dashboard_report_vps.py failed" >&2
  status=1
fi

if ! python3 scripts/openclaw_panel_vps.py; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') openclaw_panel_vps.py failed" >&2
  status=1
fi

exit "$status"
