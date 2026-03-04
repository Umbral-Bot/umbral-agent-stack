#!/usr/bin/env bash
# SIM Daily Research Cron — Encola tareas de research diario
# Cron recomendado: 0 8,14,20 * * * bash ~/umbral-agent-stack/scripts/vps/sim-daily-cron.sh
set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate
set -a && source ~/.config/openclaw/env 2>/dev/null && set +a
export PYTHONPATH="$PWD"

python3 scripts/sim_daily_research.py >> /tmp/sim_daily.log 2>&1
