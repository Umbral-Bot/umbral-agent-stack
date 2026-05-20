#!/usr/bin/env bash
# Notion Poller Cron Wrapper â€” ensures the daemon is always running.
# Cron: */5 * * * * bash ~/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller_cron.log 2>&1
set -euo pipefail

PID_FILE="/tmp/notion_poller.pid"
REPO_DIR="$HOME/umbral-agent-stack"

# Check if daemon is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        # Process exists and is running
        exit 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') Stale PID file (pid=$PID not running). Restarting..."
        rm -f "$PID_FILE"
    fi
fi

# Run from main so daemon uses merged code
if ! REPO="$REPO_DIR" bash "$REPO_DIR/scripts/vps/ensure-main-for-run.sh"; then
    echo "[ensure-main-for-run] blocked; skipping this run" >&2
    exit 0
fi
# Start the daemon
cd "$REPO_DIR"
source .venv/bin/activate
# shellcheck disable=SC1091
source "$REPO_DIR/scripts/vps/load-openclaw-env.sh"
load_openclaw_env "$HOME/.config/openclaw/env"
export PYTHONPATH="$PWD"

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting Notion Poller daemon..."
nohup python3 scripts/vps/notion-poller-daemon.py >> /tmp/notion_poller.log 2>&1 &
echo "$(date '+%Y-%m-%d %H:%M:%S') Daemon started (pid=$!)."
