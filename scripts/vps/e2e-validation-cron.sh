#!/usr/bin/env bash
# =================================================================
# Umbral E2E Validation — Cron wrapper
# Runs the full E2E validation suite and posts results to Notion.
# On failure, posts an alert to Notion Control Room.
#
# Schedule: daily at 06:00 UTC
#   0 6 * * * bash ~/umbral-agent-stack/scripts/vps/e2e-validation-cron.sh >> /tmp/e2e_validation.log 2>&1
# =================================================================
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
LOG_FILE="/tmp/e2e_validation.log"

cd "$REPO_DIR"

# Activate virtualenv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo ""
echo "=== E2E Validation — $(date -u +"%Y-%m-%d %H:%M UTC") ==="

# Run E2E validation suite with Notion posting
PYTHONPATH="$REPO_DIR" python3 scripts/e2e_validation.py --notion 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[OK] E2E validation passed"
else
    echo "[FAIL] E2E validation had failures (exit code $EXIT_CODE)"

    # Post failure alert to Notion (best-effort, separate from --notion flag)
    WORKER_URL="${WORKER_URL:-http://127.0.0.1:8088}"
    WORKER_TOKEN="${WORKER_TOKEN:-}"
    if [ -n "$WORKER_TOKEN" ]; then
        ALERT="Rick: [E2E ALERT] Validation suite has failures — $(date -u +'%Y-%m-%d %H:%M UTC'). Check /tmp/e2e_validation.log for details."
        curl -sf -X POST "${WORKER_URL}/run" \
            -H "Authorization: Bearer ${WORKER_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"task\": \"notion.add_comment\", \"input\": {\"text\": \"$ALERT\"}}" \
            > /dev/null 2>&1 && echo "(Alert posted to Notion)" || echo "(Failed to post Notion alert)"
    fi
fi

exit $EXIT_CODE
