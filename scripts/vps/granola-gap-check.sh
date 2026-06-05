#!/usr/bin/env bash
# Granola Gap Check — VPS cron wrapper
# Checks Notion raw DB for recent pages that lack traceability or content.
# Designed to run daily on VPS even without the VM cache file.
#
# Cron: 0 8 * * * bash ~/umbral-agent-stack/scripts/vps/granola-gap-check.sh >> /tmp/granola_gap_check.log 2>&1
#
# Exit codes:
#   0 = no issues
#   2 = recent gaps detected (requires review)
#   1 = script error
set -euo pipefail

REPO_DIR="$HOME/umbral-agent-stack"
ENV_FILE="$HOME/.config/openclaw/env"
LOG_DIR="/tmp"
JSON_OUTPUT="$LOG_DIR/granola_gap_check_latest.json"

cd "$REPO_DIR"
source .venv/bin/activate
source "$REPO_DIR/scripts/vps/load-openclaw-env.sh"
load_openclaw_env "$ENV_FILE"
export PYTHONPATH="$PWD"

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting Granola gap check..."

# Run the Notion-only health check. The helper understands the flattened
# read_database shape (Fecha -> {"start": ...}) and raw Notion property shape.
set +e
python3 scripts/granola_gap_check.py > "$JSON_OUTPUT" 2>&1
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 2 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') WARNING: Recent gaps detected. See $JSON_OUTPUT"
elif [ $EXIT_CODE -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') OK: No recent gaps."
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: Gap check failed (exit=$EXIT_CODE). See $JSON_OUTPUT"
fi

exit $EXIT_CODE
