#!/usr/bin/env bash
# Install cron jobs (run once on VPS).
# Preserves existing crontab entries — only adds lines if not present.
set -euo pipefail

DASHBOARD_LINE="*/15 * * * * $HOME/umbral-agent-stack/scripts/vps/dashboard-cron.sh >> /tmp/dashboard_cron.log 2>&1"
HEALTH_LINE="*/30 * * * * bash $HOME/umbral-agent-stack/scripts/vps/health-check.sh >> /tmp/health_check.log 2>&1"

# --- Dashboard cron ---
if crontab -l 2>/dev/null | grep -qF "dashboard-cron.sh"; then
    echo "Dashboard cron already installed."
else
    (crontab -l 2>/dev/null; echo "$DASHBOARD_LINE") | crontab -
    echo "Dashboard cron added."
fi

# --- Health check cron ---
if crontab -l 2>/dev/null | grep -qF "health-check.sh"; then
    echo "Health check cron already installed."
else
    (crontab -l 2>/dev/null; echo "$HEALTH_LINE") | crontab -
    echo "Health check cron added."
fi

echo ""
echo "Current crontab:"
crontab -l
