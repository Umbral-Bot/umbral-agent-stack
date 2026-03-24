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
DISPATCHER_CTL="${DISPATCHER_CTL:-$REPO/scripts/vps/dispatcher-service.sh}"
LOG_PREFIX="[supervisor $(date -u +"%Y-%m-%d %H:%M UTC")]"
RESTARTED=()

format_service_list_es() {
    if [ ${#RESTARTED[@]} -eq 0 ]; then
        echo "ninguno"
        return 0
    fi

    python3 - "${RESTARTED[@]}" <<'PY'
import sys

mapping = {
    "Worker": "Worker",
    "Dispatcher": "Dispatcher",
    "Redis": "Redis",
    "Worker(FAILED)": "Worker (falló)",
    "Dispatcher(FAILED)": "Dispatcher (falló)",
    "Redis(FAILED)": "Redis (falló)",
}

items = [mapping.get(arg, arg) for arg in sys.argv[1:]]
print(", ".join(items) if items else "ninguno")
PY
}

# ---------------------------------------------------------------
# Load env vars (WORKER_TOKEN, REDIS_URL, etc.)
# ---------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1091
    source "$REPO/scripts/vps/load-openclaw-env.sh"
    load_openclaw_env "$ENV_FILE"
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
    if curl -sf -o /dev/null -w "" "${WORKER_URL}/health" 2>/dev/null; then
        echo "${LOG_PREFIX} Worker: OK"
        return 0
    fi

    if pgrep -f "uvicorn worker.app" > /dev/null 2>&1; then
        echo "${LOG_PREFIX} Worker: process found but not responding (may be starting)"
        return 0
    fi

    return 1
}

restart_worker() {
    echo "${LOG_PREFIX} Worker: DOWN - restarting..."
    cd "$REPO"
    if [ -f "$ENV_FILE" ]; then
        # shellcheck disable=SC1091
        source "$REPO/scripts/vps/load-openclaw-env.sh"
        load_openclaw_env "$ENV_FILE"
    fi
    export PYTHONPATH="${REPO}"

    if systemctl --user list-unit-files | grep -q '^umbral-worker\.service'; then
        systemctl --user daemon-reload
        systemctl --user restart umbral-worker
        local pid
        pid="$(systemctl --user show -p MainPID --value umbral-worker 2>/dev/null || echo 0)"
    else
        nohup python3 -m uvicorn worker.app:app \
            --host "${WORKER_HOST}" \
            --port "${WORKER_PORT}" \
            >> /tmp/worker.log 2>&1 &
        local pid=$!
    fi
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
# 2. Check & restart Dispatcher (canonical path: systemd)
# ---------------------------------------------------------------
check_dispatcher() {
    local status_output
    if status_output="$(bash "$DISPATCHER_CTL" status 2>&1)"; then
        echo "${LOG_PREFIX} Dispatcher: OK"
        return 0
    fi

    echo "${LOG_PREFIX} Dispatcher: drift detected"
    while IFS= read -r line; do
        [ -n "$line" ] && echo "${LOG_PREFIX}   ${line}"
    done <<< "$status_output"
    return 1
}

restart_dispatcher() {
    echo "${LOG_PREFIX} Dispatcher: DOWN or drifted - reconciling via systemd..."
    if bash "$DISPATCHER_CTL" reconcile > /tmp/dispatcher_reconcile.log 2>&1; then
        echo "${LOG_PREFIX} Dispatcher: reconciled"
        RESTARTED+=("Dispatcher")
    else
        echo "${LOG_PREFIX} Dispatcher: FAILED to reconcile"
        cat /tmp/dispatcher_reconcile.log 2>/dev/null || true
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

    echo "${LOG_PREFIX} Redis: DOWN - attempting restart..."
    redis-server --daemonize yes 2>/dev/null || true
    sleep 1

    if redis-cli ping 2>/dev/null | grep -qi "PONG"; then
        echo "${LOG_PREFIX} Redis: restarted"
        RESTARTED+=("Redis")
        return 0
    fi

    echo "${LOG_PREFIX} Redis: FAILED to restart"
    RESTARTED+=("Redis(FAILED)")
    return 1
}

# ---------------------------------------------------------------
# 4. Post alert to Notion (best-effort).
#    If NOTION_SUPERVISOR_API_KEY and NOTION_SUPERVISOR_ALERT_PAGE_ID are set:
#      posts directly to Notion API so the comment appears as the "Supervisor"
#      integration. Otherwise calls Worker notion.add_comment.
# ---------------------------------------------------------------
resolve_alert_route() {
    python3 "$REPO/scripts/notion_alert_target.py" --format shell 2>/dev/null || true
}

post_notion_alert() {
    local alert_text="$1"
    local response
    local http_status
    local response_body
    local route_shell=""
    local ALERT_ROUTE_OK="false"
    local ALERT_MODE=""
    local TARGET_PAGE_ID=""
    local ALERT_REASON=""

    route_shell="$(resolve_alert_route)"
    if [ -n "$route_shell" ]; then
        eval "$route_shell"
    fi

    if [ "$ALERT_ROUTE_OK" != "true" ]; then
        echo "${LOG_PREFIX} No active Notion target for supervisor alerts (reason=${ALERT_REASON:-unknown})"
        return 1
    fi

    if [ "$ALERT_MODE" = "direct_supervisor" ] && [ -n "${NOTION_SUPERVISOR_API_KEY:-}" ] && [ -n "$TARGET_PAGE_ID" ]; then
        local payload
        payload="$(
            python3 - "$alert_text" "$TARGET_PAGE_ID" <<'PY'
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
            echo "${LOG_PREFIX} Alert posted to Notion (Supervisor identity)"
            return 0
        fi
        echo "${LOG_PREFIX} Failed to post Notion alert (HTTP ${http_status})"
        [ -n "$response_body" ] && echo "${LOG_PREFIX} Response: $response_body"
        return 1
    fi

    if [ "$ALERT_MODE" != "worker_alert_page" ]; then
        echo "${LOG_PREFIX} Falling back to Worker Notion alert route (${ALERT_MODE:-unknown}, reason=${ALERT_REASON:-unknown})"
    fi

    local worker_token="${WORKER_TOKEN:-}"
    local alert_page_id="${TARGET_PAGE_ID:-${NOTION_CONTROL_ROOM_PAGE_ID:-}}"
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
            -H "X-Umbral-Caller: cron.supervisor" \
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

ACTION="${1:-run}"
if [ "$ACTION" = "test-alert" ]; then
    shift || true
    ALERT="${*:-Prueba de alerta del Supervisor - $(date -u +"%Y-%m-%d %H:%M UTC")}"
    if post_notion_alert "$ALERT"; then
        echo "${LOG_PREFIX} Test alert completed"
        exit 0
    fi
    echo "${LOG_PREFIX} Test alert failed"
    exit 1
fi

# ---------------------------------------------------------------
# Execute checks
# ---------------------------------------------------------------
check_redis || true
check_worker || restart_worker
check_dispatcher || restart_dispatcher

# ---------------------------------------------------------------
# Post alert to Notion if anything was restarted.
# ---------------------------------------------------------------
if [ ${#RESTARTED[@]} -gt 0 ]; then
    ALERT="Supervisor: reinicio automatico - $(date -u +"%Y-%m-%d %H:%M UTC") - Servicios reiniciados: $(format_service_list_es)"
    sleep 4
    post_notion_alert "$ALERT" || true
fi

echo "${LOG_PREFIX} Done. Restarted: ${RESTARTED[*]:-none}"
