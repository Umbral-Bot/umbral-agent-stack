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
SIM_TO_MAKE_LINE="0 9,15,21 * * * bash $HOME/umbral-agent-stack/scripts/vps/sim-to-make-cron.sh >> /tmp/sim_to_make.log 2>&1"
E2E_VALIDATION_LINE="0 6 * * * bash $HOME/umbral-agent-stack/scripts/vps/e2e-validation-cron.sh >> /tmp/e2e_validation.log 2>&1"
OODA_REPORT_LINE="0 7 * * 1 bash $HOME/umbral-agent-stack/scripts/vps/ooda-report-cron.sh >> /tmp/ooda_report.log 2>&1"
SCHEDULED_TASKS_LINE="* * * * * bash $HOME/umbral-agent-stack/scripts/vps/scheduled-tasks-cron.sh >> /tmp/scheduled_tasks.log 2>&1"

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

# --- SIM to Make.com cron ---
if crontab -l 2>/dev/null | grep -qF "sim-to-make-cron.sh"; then
    echo "SIM-to-Make cron already installed."
else
    (crontab -l 2>/dev/null; echo "$SIM_TO_MAKE_LINE") | crontab -
    echo "SIM-to-Make cron added."
fi

# --- E2E Validation cron ---
if crontab -l 2>/dev/null | grep -qF "e2e-validation-cron.sh"; then
    echo "E2E Validation cron already installed."
else
    (crontab -l 2>/dev/null; echo "$E2E_VALIDATION_LINE") | crontab -
    echo "E2E Validation cron added."
fi

# --- OODA Report cron (Monday 7:00 UTC) ---
if crontab -l 2>/dev/null | grep -qF "ooda-report-cron.sh"; then
    echo "OODA Report cron already installed."
else
    (crontab -l 2>/dev/null; echo "$OODA_REPORT_LINE") | crontab -
    echo "OODA Report cron added."
fi

# --- Scheduled Tasks cron (every minute) ---
if crontab -l 2>/dev/null | grep -qF "scheduled-tasks-cron.sh"; then
    echo "Scheduled Tasks cron already installed."
else
    (crontab -l 2>/dev/null; echo "$SCHEDULED_TASKS_LINE") | crontab -
    echo "Scheduled Tasks cron added."
fi

echo ""
echo "Current crontab:"
crontab -l
