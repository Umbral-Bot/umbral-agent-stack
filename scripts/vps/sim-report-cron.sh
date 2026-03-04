#!/usr/bin/env bash
# SIM Daily Report Cron
# Cron recomendado: 30 8,14,20 * * * bash ~/umbral-agent-stack/scripts/vps/sim-report-cron.sh
set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate
set -a && source ~/.config/openclaw/env 2>/dev/null && set +a
export PYTHONPATH="$PWD"

python3 scripts/sim_daily_report.py --hours 8 --notion >> /tmp/sim_report.log 2>&1
