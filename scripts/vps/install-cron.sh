#!/usr/bin/env bash
# Install dashboard cron job (run once on VPS)
echo "*/15 * * * * $HOME/umbral-agent-stack/scripts/vps/dashboard-cron.sh >> /tmp/dashboard_cron.log 2>&1" | crontab -
echo "Cron installed:"
crontab -l
