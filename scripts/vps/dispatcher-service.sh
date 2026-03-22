#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-$HOME/umbral-agent-stack}"
ENV_FILE="${ENV_FILE:-$HOME/.config/openclaw/env}"
SYSTEMD_USER_DIR="${SYSTEMD_USER_DIR:-$HOME/.config/systemd/user}"
SERVICE_NAME="${SERVICE_NAME:-openclaw-dispatcher}"
SERVICE_TEMPLATE="${SERVICE_TEMPLATE:-$REPO/openclaw/systemd/${SERVICE_NAME}.service.template}"
SERVICE_FILE="${SERVICE_FILE:-$SYSTEMD_USER_DIR/${SERVICE_NAME}.service}"
DISPATCHER_PATTERN="${DISPATCHER_PATTERN:-python3 -m dispatcher.service}"

dispatcher_pids() {
    pgrep -u "$USER" -f "$DISPATCHER_PATTERN" || true
}

dispatcher_count() {
    local count
    count="$(dispatcher_pids | wc -l | tr -d ' ')"
    if [ -z "$count" ]; then
        count=0
    fi
    echo "$count"
}

service_exists() {
    systemctl --user cat "$SERVICE_NAME" > /dev/null 2>&1
}

service_active() {
    systemctl --user is-active "$SERVICE_NAME" > /dev/null 2>&1
}

ensure_env_loaded() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        # shellcheck disable=SC1090
        source "$ENV_FILE"
        set +a
    fi

    if [ -f "$REPO/.venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "$REPO/.venv/bin/activate"
    fi

    export PYTHONPATH="$REPO"
}

ensure_unit() {
    mkdir -p "$SYSTEMD_USER_DIR"
    if [ ! -f "$SERVICE_TEMPLATE" ]; then
        echo "Dispatcher template not found: $SERVICE_TEMPLATE" >&2
        return 1
    fi
    sed "s|%h|$HOME|g" "$SERVICE_TEMPLATE" > "$SERVICE_FILE"
    systemctl --user daemon-reload
}

status_dispatcher() {
    local state="inactive"
    local count
    local pids

    if service_active; then
        state="active"
    fi
    count="$(dispatcher_count)"
    pids="$(dispatcher_pids | tr '\n' ' ' | sed 's/ $//')"
    if [ -z "$pids" ]; then
        pids="none"
    fi

    echo "service_state=$state"
    echo "process_count=$count"
    echo "pids=$pids"

    if [ "$state" = "active" ] && [ "$count" -eq 1 ]; then
        return 0
    fi
    return 1
}

stop_dispatcher() {
    if service_exists; then
        systemctl --user stop "$SERVICE_NAME" || true
    fi
}

kill_strays() {
    local pids=()

    mapfile -t pids < <(dispatcher_pids)
    if [ "${#pids[@]}" -eq 0 ]; then
        return 0
    fi

    kill "${pids[@]}" 2> /dev/null || true
    sleep 2

    mapfile -t pids < <(dispatcher_pids)
    if [ "${#pids[@]}" -eq 0 ]; then
        return 0
    fi

    kill -9 "${pids[@]}" 2> /dev/null || true
    sleep 1
}

reconcile_dispatcher() {
    ensure_env_loaded
    ensure_unit
    stop_dispatcher
    kill_strays
    systemctl --user enable --now "$SERVICE_NAME"
    sleep 2
    status_dispatcher
}

start_dispatcher() {
    if status_dispatcher > /dev/null 2>&1; then
        echo "Dispatcher already running via systemd with a single process."
        return 0
    fi

    if [ "$(dispatcher_count)" -gt 0 ]; then
        echo "Dispatcher drift detected; reconciling via systemd."
        reconcile_dispatcher
        return
    fi

    ensure_env_loaded
    ensure_unit
    systemctl --user enable --now "$SERVICE_NAME"
    sleep 2
    status_dispatcher
}

smoke_dispatcher() {
    ensure_env_loaded
    cd "$REPO"
    python3 scripts/test_s2_dispatcher.py
}

ACTION="${1:-status}"

case "$ACTION" in
    ensure-unit)
        ensure_unit
        ;;
    start)
        start_dispatcher
        ;;
    stop)
        stop_dispatcher
        kill_strays
        ;;
    reconcile)
        reconcile_dispatcher
        ;;
    status)
        status_dispatcher
        ;;
    smoke)
        smoke_dispatcher
        ;;
    *)
        echo "Usage: $0 {ensure-unit|start|stop|reconcile|status|smoke}" >&2
        exit 1
        ;;
esac
