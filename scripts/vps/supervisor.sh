#!/usr/bin/env bash
# =================================================================
# Umbral VPS Service Supervisor
# Checks that Worker and Dispatcher are running; restarts if down.
# Designed for cron every 5 minutes:
#   */5 * * * * bash ~/umbral-agent-stack/scripts/vps/supervisor.sh >> /tmp/supervisor.log 2>&1
# =================================================================
set -euo pipefail

REPO="${REPO:-$HOME/umbral-agent-stack}"
ENV_FILE="${ENV_FILE:-$HOME/.config/openclaw/env}"
WORKER_HOST="${WORKER_HOST:-127.0.0.1}"
WORKER_PORT="${WORKER_PORT:-8088}"
WORKER_URL="${WORKER_URL:-http://${WORKER_HOST}:${WORKER_PORT}}"
LOG_PREFIX="[supervisor $(date -u +"%Y-%m-%d %H:%M UTC")]"
RESTARTED=()

# ---------------------------------------------------------------
# Load env vars (WORKER_TOKEN, REDIS_URL, etc.)
# ---------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Ensure venv
if [ -f "$REPO/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$REPO/.venv/bin/activate"
fi

export PYTHONPATH="${REPO}"

# ---------------------------------------------------------------
# 1. Check & restart Worker (uvicorn worker.app:app)
# ---------------------------------------------------------------
check_worker() {
    # First try HTTP health check (most reliable)
    if curl -sf -o /dev/null -w "" "${WORKER_URL}/health" 2>/dev/null; then
        echo "${LOG_PREFIX} Worker: OK"
        return 0
    fi

    # Process might be starting up — check if process exists
    if pgrep -f "uvicorn worker.app" > /dev/null 2>&1; then
        echo "${LOG_PREFIX} Worker: process found but not responding (may be starting)"
        return 0
    fi

    return 1
}

restart_worker() {
    echo "${LOG_PREFIX} Worker: DOWN — restarting..."
    cd "$REPO"
    # Re-source env so Worker gets same WORKER_TOKEN as dashboard/cron
    if [ -f "$ENV_FILE" ]; then
        set -a
        # shellcheck disable=SC1090
        source "$ENV_FILE"
        set +a
    fi
    export PYTHONPATH="${REPO}"
    nohup python3 -m uvicorn worker.app:app \
        --host "${WORKER_HOST}" \
        --port "${WORKER_PORT}" \
        >> /tmp/worker.log 2>&1 &
    local pid=$!
    sleep 3

    if curl -sf -o /dev/null "${WORKER_URL}/health" 2>/dev/null; then
        echo "${LOG_PREFIX} Worker: restarted (PID $pid)"
        RESTARTED+=("Worker")
    else
        echo "${LOG_PREFIX} Worker: FAILED to restart (PID $pid)"
        RESTARTED+=("Worker(FAILED)")
    fi
}

# ---------------------------------------------------------------
# 2. Check & restart Dispatcher (python3 -m dispatcher.service)
# ---------------------------------------------------------------
check_dispatcher() {
    if pgrep -f "dispatcher.service" > /dev/null 2>&1; then
        echo "${LOG_PREFIX} Dispatcher: OK"
        return 0
    fi
    return 1
}

restart_dispatcher() {
    echo "${LOG_PREFIX} Dispatcher: DOWN — restarting..."
    cd "$REPO"
    nohup python3 -m dispatcher.service \
        > /tmp/dispatcher.log 2>&1 &
    local pid=$!
    sleep 2

    if pgrep -f "dispatcher.service" > /dev/null 2>&1; then
        echo "${LOG_PREFIX} Dispatcher: restarted (PID $pid)"
        RESTARTED+=("Dispatcher")
    else
        echo "${LOG_PREFIX} Dispatcher: FAILED to restart (PID $pid)"
        RESTARTED+=("Dispatcher(FAILED)")
    fi
}

# ---------------------------------------------------------------
# 3. Check Redis (required by both services)
# ---------------------------------------------------------------
check_redis() {
    if redis-cli ping 2>/dev/null | grep -qi "PONG"; then
        echo "${LOG_PREFIX} Redis: OK"
        return 0
    fi

    echo "${LOG_PREFIX} Redis: DOWN — attempting restart..."
    redis-server --daemonize yes 2>/dev/null || true
    sleep 1

    if redis-cli ping 2>/dev/null | grep -qi "PONG"; then
        echo "${LOG_PREFIX} Redis: restarted"
        RESTARTED+=("Redis")
        return 0
    else
        echo "${LOG_PREFIX} Redis: FAILED to restart"
        RESTARTED+=("Redis(FAILED)")
        return 1
    fi
}

# ---------------------------------------------------------------
# Execute checks
# ---------------------------------------------------------------

# Redis first (prerequisite)
check_redis || true

# Worker
check_worker || restart_worker

# Dispatcher
check_dispatcher || restart_dispatcher

# ---------------------------------------------------------------
# Post alert to Notion if anything was restarted (Worker POST /run).
# Worker must have NOTION_API_KEY and NOTION_CONTROL_ROOM_PAGE_ID set.
# ---------------------------------------------------------------
if [ ${#RESTARTED[@]} -gt 0 ]; then
    # Single line so JSON is not broken by newlines in -d
    ALERT="🔄 Supervisor auto-restart — $(date -u +"%Y-%m-%d %H:%M UTC") — Restarted: ${RESTARTED[*]}"

    WORKER_TOKEN="${WORKER_TOKEN:-}"
    if [ -n "$WORKER_TOKEN" ]; then
        # Wait for Worker to be ready after restart (it may need a few seconds)
        sleep 4
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${WORKER_URL}/run" \
            -H "Authorization: Bearer ${WORKER_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"task\": \"notion.add_comment\", \"input\": {\"text\": $(printf '%s' "$ALERT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}}")
        http_code=$(echo "$response" | tail -n1)
        if [ "$http_code" = "HTTP_CODE:200" ]; then
            echo "${LOG_PREFIX} Alert posted to Notion"
        else
            echo "${LOG_PREFIX} Failed to post Notion alert ($http_code)"
            echo "${LOG_PREFIX} Response: $(echo "$response" | sed '$d')"
        fi
    fi
fi

echo "${LOG_PREFIX} Done. Restarted: ${RESTARTED[*]:-none}"
