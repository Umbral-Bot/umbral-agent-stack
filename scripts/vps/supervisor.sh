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

    # Process might be starting up â€” check if process exists
    if pgrep -f "uvicorn worker.app" > /dev/null 2>&1; then
        echo "${LOG_PREFIX} Worker: process found but not responding (may be starting)"
        return 0
    fi

    return 1
}

restart_worker() {
    echo "${LOG_PREFIX} Worker: DOWN â€” restarting..."
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
    echo "${LOG_PREFIX} Dispatcher: DOWN â€” restarting..."
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

    echo "${LOG_PREFIX} Redis: DOWN â€” attempting restart..."
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
# 4. Post alert to Notion (best-effort).
#    If NOTION_SUPERVISOR_API_KEY and NOTION_SUPERVISOR_ALERT_PAGE_ID are set:
#      posts directly to Notion API so the comment appears as the "Supervisor"
#      integration (Dashboard Rick page). Otherwise calls Worker notion.add_comment.
# ---------------------------------------------------------------
post_notion_alert() {
    local alert_text="$1"
    local response
    local http_status
    local response_body

    # Prefer direct Notion API with Supervisor identity (Dashboard Rick page)
    if [ -n "${NOTION_SUPERVISOR_API_KEY:-}" ] && [ -n "${NOTION_SUPERVISOR_ALERT_PAGE_ID:-}" ]; then
        local payload
        payload="$(
            python3 - "$alert_text" "${NOTION_SUPERVISOR_ALERT_PAGE_ID}" <<'PY'
import json
import sys
text = sys.argv[1]
page_id = sys.argv[2]
body = {"parent": {"page_id": page_id}, "rich_text": [{"type": "text", "text": {"content": text}}]}
print(json.dumps(body))
PY
        )"
        response="$(
            curl -sS -X POST "https://api.notion.com/v1/comments" \
                -H "Authorization: Bearer ${NOTION_SUPERVISOR_API_KEY}" \
                -H "Notion-Version: 2022-06-28" \
                -H "Content-Type: application/json" \
                -d "${payload}" \
                -w $'\n%{http_code}'
        )" || {
            echo "${LOG_PREFIX} Failed to post Notion alert (request error)"
            return 1
        }
        http_status="$(printf '%s\n' "$response" | tail -n 1)"
        response_body="$(printf '%s\n' "$response" | sed '$d')"
        if [ "$http_status" = "200" ]; then
            echo "${LOG_PREFIX} Alert posted to Notion (Dashboard Rick, as Supervisor)"
            return 0
        fi
        echo "${LOG_PREFIX} Failed to post Notion alert (HTTP ${http_status})"
        [ -n "$response_body" ] && echo "${LOG_PREFIX} Response: $response_body"
        return 1
    fi

    # Fallback: via Worker (uses NOTION_API_KEY; comment appears as Rick integration)
    local worker_token="${WORKER_TOKEN:-}"
    local alert_page_id="${NOTION_SUPERVISOR_ALERT_PAGE_ID:-${NOTION_CONTROL_ROOM_PAGE_ID:-}}"
    local payload
    if [ -z "$worker_token" ]; then
        echo "${LOG_PREFIX} WORKER_TOKEN not set - skipping Notion alert"
        return 1
    fi
    payload="$(
        python3 - "$alert_text" "$alert_page_id" <<'PY'
import json
import sys
text = sys.argv[1]
page_id = sys.argv[2]
input_payload = {"text": text}
if page_id:
    input_payload["page_id"] = page_id
print(json.dumps({"task": "notion.add_comment", "input": input_payload}))
PY
    )"
    response="$(
        curl -sS -X POST "${WORKER_URL}/run" \
            -H "Authorization: Bearer ${worker_token}" \
            -H "Content-Type: application/json" \
            -d "${payload}" \
            -w $'\n%{http_code}'
    )" || {
        echo "${LOG_PREFIX} Failed to post Notion alert (request error)"
        return 1
    }
    http_status="$(printf '%s\n' "$response" | tail -n 1)"
    response_body="$(printf '%s\n' "$response" | sed '$d')"
    if [ "$http_status" = "200" ]; then
        if [ -n "$alert_page_id" ]; then
            echo "${LOG_PREFIX} Alert posted to Notion (page ${alert_page_id})"
        else
            echo "${LOG_PREFIX} Alert posted to Notion (default Control Room)"
        fi
        return 0
    fi
    echo "${LOG_PREFIX} Failed to post Notion alert (HTTP ${http_status})"
    [ -n "$response_body" ] && echo "${LOG_PREFIX} Response: $response_body"
    return 1
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
# ---------------------------------------------------------------
if [ ${#RESTARTED[@]} -gt 0 ]; then
    ALERT="ðŸ”„ Supervisor auto-restart â€” $(date -u +"%Y-%m-%d %H:%M UTC") â€” Restarted: ${RESTARTED[*]}"

    # Wait for Worker to be ready after restart (it may need a few seconds)
    sleep 4
    post_notion_alert "$ALERT" || true
fi

echo "${LOG_PREFIX} Done. Restarted: ${RESTARTED[*]:-none}"
