#!/usr/bin/env bash
# =================================================================
# Umbral VPS Health Check
# Verifies core services are running and logs are being written.
# Exit 0 = all OK, Exit 1 = something failed.
#
# Install as cron:
#   */30 * * * * bash ~/umbral-agent-stack/scripts/vps/health-check.sh >> /tmp/health_check.log 2>&1
# =================================================================
set -euo pipefail

WORKER_URL="${WORKER_URL:-http://127.0.0.1:8088}"
OPS_LOG="${UMBRAL_OPS_LOG_DIR:-$HOME/.config/umbral}/ops_log.jsonl"
REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
FAILURES=()
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

echo "=== Health Check â€” $NOW ==="

# ---------------------------------------------------------------
# 1. Redis
# ---------------------------------------------------------------
if redis-cli ping 2>/dev/null | grep -qi "PONG"; then
    echo "[OK]  Redis is running"
else
    echo "[FAIL] Redis is NOT responding"
    FAILURES+=("Redis not responding")
fi

# ---------------------------------------------------------------
# 2. Worker (FastAPI on port 8088)
# ---------------------------------------------------------------
WORKER_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "${WORKER_URL}/health" 2>/dev/null || echo "000")
if [ "$WORKER_STATUS" = "200" ]; then
    echo "[OK]  Worker responding (HTTP 200)"
else
    echo "[FAIL] Worker not responding (HTTP $WORKER_STATUS)"
    FAILURES+=("Worker HTTP $WORKER_STATUS at ${WORKER_URL}/health")
fi

# ---------------------------------------------------------------
# 3. Dispatcher process
# ---------------------------------------------------------------
if pgrep -f "dispatcher.service" > /dev/null 2>&1; then
    echo "[OK]  Dispatcher process running"
else
    echo "[FAIL] Dispatcher process NOT found"
    FAILURES+=("Dispatcher process not running")
fi

# ---------------------------------------------------------------
# 4. Ops log has recent events
# ---------------------------------------------------------------
if [ -f "$OPS_LOG" ]; then
    LINE_COUNT=$(wc -l < "$OPS_LOG" | tr -d ' ')
    echo "[OK]  ops_log.jsonl exists ($LINE_COUNT lines)"
    # Check if last event is within the last 2 hours
    LAST_LINE=$(tail -1 "$OPS_LOG" 2>/dev/null || true)
    if [ -n "$LAST_LINE" ]; then
        LAST_TS=$(echo "$LAST_LINE" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('ts',''))" 2>/dev/null || true)
        if [ -n "$LAST_TS" ]; then
            echo "       Last event: $LAST_TS"
        fi
    fi
else
    echo "[WARN] ops_log.jsonl not found at $OPS_LOG"
    FAILURES+=("ops_log.jsonl not found")
fi

# ---------------------------------------------------------------
# 5. Report result
# ---------------------------------------------------------------
echo ""
if [ ${#FAILURES[@]} -eq 0 ]; then
    echo "âœ“ All checks passed"
    exit 0
else
    echo "âœ— ${#FAILURES[@]} check(s) failed:"
    for f in "${FAILURES[@]}"; do
        echo "  - $f"
    done

    # ---------------------------------------------------------------
    # 6. Post alert to Notion Control Room (best-effort)
    # ---------------------------------------------------------------
    ALERT_TEXT="ðŸš¨ VPS Health Check FAILED â€” $NOW\n"
    for f in "${FAILURES[@]}"; do
        ALERT_TEXT="${ALERT_TEXT}\nâ€¢ $f"
    done

    # Try posting via the worker API (if it's reachable)
    if [ "$WORKER_STATUS" = "200" ]; then
        WORKER_TOKEN="${WORKER_TOKEN:-}"
        if [ -n "$WORKER_TOKEN" ]; then
            curl -sf -X POST "${WORKER_URL}/run" \
                -H "Authorization: Bearer ${WORKER_TOKEN}" \
                -H "Content-Type: application/json" \
                -d "{\"task\": \"notion.add_comment\", \"input\": {\"text\": \"$(echo -e "$ALERT_TEXT")\"}}" \
                > /dev/null 2>&1 && echo "(Alert posted to Notion)" || echo "(Failed to post Notion alert)"
        else
            echo "(WORKER_TOKEN not set â€” skipping Notion alert)"
        fi
    else
        # Fallback: try Python directly if worker is down
        cd "$REPO_DIR" 2>/dev/null && \
        source .venv/bin/activate 2>/dev/null && \
        python3 -c "
from worker import notion_client
notion_client.add_comment(page_id=None, text='''$(echo -e "$ALERT_TEXT")''')
print('(Alert posted to Notion via Python)')
" 2>/dev/null || echo "(Could not post Notion alert â€” worker down and Python fallback failed)"
    fi

    exit 1
fi
