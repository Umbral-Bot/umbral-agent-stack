#!/usr/bin/env bash
# Notion Poller Cron Wrapper â€” ensures the daemon is always running.
# Cron: */5 * * * * bash ~/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller_cron.log 2>&1
set -euo pipefail

PID_FILE="/tmp/notion_poller.pid"
FINGERPRINT_FILE="/tmp/notion_poller.fingerprint"
REPO_DIR="$HOME/umbral-agent-stack"
ENV_FILE="$HOME/.config/openclaw/env"
DAEMON_PATTERN="scripts/vps/notion-poller-daemon.py"

compute_fingerprint() {
    local path
    for path in \
        "$REPO_DIR/dispatcher/notion_poller.py" \
        "$REPO_DIR/scripts/vps/notion-poller-daemon.py" \
        "$REPO_DIR/scripts/vps/load-openclaw-env.sh" \
        "$ENV_FILE"
    do
        if [ -f "$path" ]; then
            sha256sum "$path"
        else
            printf 'missing %s\n' "$path"
        fi
    done | sha256sum | awk '{print $1}'
}

CURRENT_FINGERPRINT="$(compute_fingerprint)"

existing_daemon_pids() {
    pgrep -f "$DAEMON_PATTERN" || true
}

stop_daemon_pid() {
    local pid="$1"
    local attempt

    kill "$pid" 2>/dev/null || true
    for attempt in $(seq 1 20); do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.5
    done

    kill -9 "$pid" 2>/dev/null || true
    for attempt in $(seq 1 10); do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.2
    done
}

# Check if daemon is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        RUNNING_PIDS="$(existing_daemon_pids)"
        RUNNING_COUNT="$(printf '%s\n' "$RUNNING_PIDS" | sed '/^$/d' | wc -l | tr -d ' ')"
        PREVIOUS_FINGERPRINT=""
        if [ -f "$FINGERPRINT_FILE" ]; then
            PREVIOUS_FINGERPRINT="$(cat "$FINGERPRINT_FILE" 2>/dev/null || true)"
        fi
        if [ "$PREVIOUS_FINGERPRINT" = "$CURRENT_FINGERPRINT" ] && [ "$RUNNING_COUNT" = "1" ]; then
            # Process exists, is running, and matches the current code/env snapshot
            exit 0
        fi
        echo "$(date '+%Y-%m-%d %H:%M:%S') Restarting notion poller (pid=$PID, running_count=$RUNNING_COUNT)."
        for running_pid in $RUNNING_PIDS; do
            stop_daemon_pid "$running_pid"
        done
        rm -f "$PID_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') Stale PID file (pid=$PID not running). Restarting..."
        rm -f "$PID_FILE"
    fi
fi

for running_pid in $(existing_daemon_pids); do
    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleaning stray notion poller process (pid=$running_pid)."
    stop_daemon_pid "$running_pid"
done
rm -f "$PID_FILE"

# Start the daemon
cd "$REPO_DIR"
source .venv/bin/activate
# shellcheck disable=SC1091
source "$REPO_DIR/scripts/vps/load-openclaw-env.sh"
load_openclaw_env "$HOME/.config/openclaw/env"
export PYTHONPATH="$PWD"

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting Notion Poller daemon..."
nohup python3 scripts/vps/notion-poller-daemon.py >> /tmp/notion_poller.log 2>&1 &
printf '%s\n' "$CURRENT_FINGERPRINT" > "$FINGERPRINT_FILE"
for _ in $(seq 1 20); do
    if [ -f "$PID_FILE" ]; then
        break
    fi
    sleep 0.2
done
echo "$(date '+%Y-%m-%d %H:%M:%S') Daemon started (pid=$!)."
