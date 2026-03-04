#!/usr/bin/env bash
# Install cron jobs (run once on VPS).
# Preserves existing crontab entries — only adds lines if not present.
set -euo pipefail

DASHBOARD_LINE="*/15 * * * * $HOME/umbral-agent-stack/scripts/vps/dashboard-cron.sh >> /tmp/dashboard_cron.log 2>&1"
HEALTH_LINE="*/30 * * * * bash $HOME/umbral-agent-stack/scripts/vps/health-check.sh >> /tmp/health_check.log 2>&1"
SUPERVISOR_LINE="*/5 * * * * bash $HOME/umbral-agent-stack/scripts/vps/supervisor.sh >> /tmp/supervisor.log 2>&1"
POLLER_LINE="*/5 * * * * bash $HOME/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller_cron.log 2>&1"
SIM_REPORT_LINE="30 8,14,20 * * * bash $HOME/umbral-agent-stack/scripts/vps/sim-report-cron.sh >> /tmp/sim_report.log 2>&1"
DAILY_DIGEST_LINE="0 22 * * * bash $HOME/umbral-agent-stack/scripts/vps/daily-digest-cron.sh >> /tmp/daily_digest.log 2>&1"

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

# --- Supervisor cron ---
if crontab -l 2>/dev/null | grep -qF "supervisor.sh"; then
    echo "Supervisor cron already installed."
else
    (crontab -l 2>/dev/null; echo "$SUPERVISOR_LINE") | crontab -
    echo "Supervisor cron added."
fi

# --- Notion Poller cron ---
if crontab -l 2>/dev/null | grep -qF "notion-poller-cron.sh"; then
    echo "Notion Poller cron already installed."
else
    (crontab -l 2>/dev/null; echo "$POLLER_LINE") | crontab -
    echo "Notion Poller cron added."
fi

# --- SIM report cron ---
if crontab -l 2>/dev/null | grep -qF "sim-report-cron.sh"; then
    echo "SIM report cron already installed."
else
    (crontab -l 2>/dev/null; echo "$SIM_REPORT_LINE") | crontab -
    echo "SIM report cron added."
fi

# --- Daily digest cron ---
if crontab -l 2>/dev/null | grep -qF "daily-digest-cron.sh"; then
    echo "Daily digest cron already installed."
else
    (crontab -l 2>/dev/null; echo "$DAILY_DIGEST_LINE") | crontab -
    echo "Daily digest cron added."
fi

echo ""
echo "Current crontab:"
crontab -l
