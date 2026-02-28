#!/usr/bin/env bash
# Cron wrapper for dashboard_report_vps.py
# Install: crontab -e → */15 * * * * ~/umbral-agent-stack/scripts/vps/dashboard-cron.sh >> /tmp/dashboard_cron.log 2>&1

set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate

# Load secrets
export UMBRAL_SECRETS_KEY="$(cat ~/.config/umbral/.fernet_key 2>/dev/null || true)"
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
export PYTHONPATH=.

python scripts/dashboard_report_vps.py
