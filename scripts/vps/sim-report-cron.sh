#!/usr/bin/env bash
# SIM Daily Report Cron
# Cron recomendado: 30 8,14,20 * * * bash ~/umbral-agent-stack/scripts/vps/sim-report-cron.sh
set -euo pipefail

REPO="${REPO:-$HOME/umbral-agent-stack}"
if ! bash "$REPO/scripts/vps/ensure-main-for-run.sh"; then
    echo "[ensure-main-for-run] blocked; skipping this run" >&2
    exit 0
fi
cd "$REPO"
source .venv/bin/activate
# shellcheck disable=SC1091
source "$HOME/umbral-agent-stack/scripts/vps/load-openclaw-env.sh"
load_openclaw_env "$HOME/.config/openclaw/env"
export PYTHONPATH="$PWD"

python3 scripts/sim_daily_report.py --hours 8 --notion >> /tmp/sim_report.log 2>&1
