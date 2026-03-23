#!/usr/bin/env bash
# Install cron jobs (run once on VPS).
# Preserves existing crontab entries â€” only adds lines if not present.
set -euo pipefail

DASHBOARD_RICK_LINE="0 * * * * $HOME/umbral-agent-stack/scripts/vps/dashboard-rick-cron.sh >> /tmp/dashboard_rick_cron.log 2>&1"
OPENCLAW_PANEL_LINE="0 */6 * * * $HOME/umbral-agent-stack/scripts/vps/openclaw-panel-cron.sh >> /tmp/openclaw_panel_cron.log 2>&1"
HEALTH_LINE="*/30 * * * * bash $HOME/umbral-agent-stack/scripts/vps/health-check.sh >> /tmp/health_check.log 2>&1"
SUPERVISOR_LINE="*/5 * * * * bash $HOME/umbral-agent-stack/scripts/vps/supervisor.sh >> /tmp/supervisor.log 2>&1"
POLLER_LINE="*/5 * * * * bash $HOME/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller_cron.log 2>&1"
SIM_REPORT_LINE="30 8,14,20 * * * bash $HOME/umbral-agent-stack/scripts/vps/sim-report-cron.sh >> /tmp/sim_report.log 2>&1"
DAILY_DIGEST_LINE="0 22 * * * bash $HOME/umbral-agent-stack/scripts/vps/daily-digest-cron.sh >> /tmp/daily_digest.log 2>&1"
SIM_TO_MAKE_LINE="0 9,15,21 * * * bash $HOME/umbral-agent-stack/scripts/vps/sim-to-make-cron.sh >> /tmp/sim_to_make.log 2>&1"
E2E_VALIDATION_LINE="0 6 * * * bash $HOME/umbral-agent-stack/scripts/vps/e2e-validation-cron.sh >> /tmp/e2e_validation.log 2>&1"
OODA_REPORT_LINE="0 7 * * 1 bash $HOME/umbral-agent-stack/scripts/vps/ooda-report-cron.sh >> /tmp/ooda_report.log 2>&1"
SCHEDULED_TASKS_LINE="* * * * * bash $HOME/umbral-agent-stack/scripts/vps/scheduled-tasks-cron.sh >> /tmp/scheduled_tasks.log 2>&1"
QUOTA_GUARD_LINE="*/15 * * * * bash $HOME/umbral-agent-stack/scripts/vps/quota-guard-cron.sh >> /tmp/quota_guard.log 2>&1"

# --- Dashboard cron split ---
current_crontab="$(crontab -l 2>/dev/null || true)"
filtered_crontab="$(printf '%s\n' "$current_crontab" | grep -vF "dashboard-cron.sh" | grep -vF "dashboard-rick-cron.sh" | grep -vF "openclaw-panel-cron.sh" || true)"
{
    printf '%s\n' "$filtered_crontab"
    printf '%s\n' "$DASHBOARD_RICK_LINE"
    printf '%s\n' "$OPENCLAW_PANEL_LINE"
} | awk 'NF && !seen[$0]++' | crontab -
echo "Dashboard cron split updated (Dashboard Rick hourly + OpenClaw fallback cada 6h)."

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

# --- Quota Guard cron (cada 15 min â€” protege OpenClaw de freeze por cuota Claude) ---
if crontab -l 2>/dev/null | grep -qF "quota-guard-cron.sh"; then
    echo "Quota Guard cron already installed."
else
    (crontab -l 2>/dev/null; echo "$QUOTA_GUARD_LINE") | crontab -
    echo "Quota Guard cron added."
fi

echo ""
echo "Current crontab:"
crontab -l
