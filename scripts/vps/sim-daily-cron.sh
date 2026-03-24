#!/usr/bin/env bash
# SIM Daily Research Cron â€” Encola tareas de research diario
# Cron recomendado: 0 8,14,20 * * * bash ~/umbral-agent-stack/scripts/vps/sim-daily-cron.sh
set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate
# shellcheck disable=SC1091
source "$HOME/umbral-agent-stack/scripts/vps/load-openclaw-env.sh"
load_openclaw_env "$HOME/.config/openclaw/env"
export PYTHONPATH="$PWD"

python3 scripts/sim_daily_research.py >> /tmp/sim_daily.log 2>&1
