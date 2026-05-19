#!/usr/bin/env bash
# SIM Daily Report Cron
# Cron recomendado: 30 8,14,20 * * * bash ~/umbral-agent-stack/scripts/vps/sim-report-cron.sh
set -euo pipefail

REPO="${REPO:-$HOME/umbral-agent-stack}"
bash "$REPO/scripts/vps/ensure-main-for-run.sh" 2>/dev/null || true
cd "$REPO"
source .venv/bin/activate
# shellcheck disable=SC1091
source "$HOME/umbral-agent-stack/scripts/vps/load-openclaw-env.sh"
load_openclaw_env "$HOME/.config/openclaw/env"
export PYTHONPATH="$PWD"

python3 scripts/sim_daily_report.py --hours 8 --notion >> /tmp/sim_report.log 2>&1
