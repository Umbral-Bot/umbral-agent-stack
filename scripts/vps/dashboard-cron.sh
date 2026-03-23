#!/usr/bin/env bash
# Compatibility shim for older crontabs.
# Prefer the dedicated cron scripts installed by install-cron.sh:
#   - dashboard-rick-cron.sh   (hourly)
#   - openclaw-panel-cron.sh   (every 6h fallback)

set -uo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate 2>/dev/null || true

if [ -f ~/.config/openclaw/env ]; then
  set -a
  source ~/.config/openclaw/env
  set +a
fi
export PYTHONPATH=.

status=0
utc_hour="$(date -u +%H)"
utc_minute="$(date -u +%M)"
dirty_flag="$HOME/.config/umbral/openclaw_panel_dirty.json"

if [ "$utc_minute" = "00" ]; then
  if ! python3 scripts/dashboard_report_vps.py --trigger cron.hourly; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') dashboard_report_vps.py failed" >&2
    status=1
  fi

  if [ -f "$dirty_flag" ] || [ $((10#$utc_hour % 6)) -eq 0 ]; then
    if ! python3 scripts/openclaw_panel_vps.py --trigger cron.fallback; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') openclaw_panel_vps.py failed" >&2
      status=1
    fi
  fi
fi

exit "$status"
