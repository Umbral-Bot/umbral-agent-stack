#!/usr/bin/env bash
# Install dashboard cron job (run once on VPS).
# Preserves existing crontab entries — only adds dashboard line if not present.
set -euo pipefail

CRON_LINE="*/15 * * * * $HOME/umbral-agent-stack/scripts/vps/dashboard-cron.sh >> /tmp/dashboard_cron.log 2>&1"

if crontab -l 2>/dev/null | grep -qF "dashboard-cron.sh"; then
    echo "Dashboard cron already installed."
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Dashboard cron added."
fi

echo "Current crontab:"
crontab -l
