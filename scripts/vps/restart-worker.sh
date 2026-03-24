#!/usr/bin/env bash
# Restart Worker on VPS
set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate

if [ -f "$HOME/.config/openclaw/env" ]; then
    # shellcheck disable=SC1091
    source "$HOME/umbral-agent-stack/scripts/vps/load-openclaw-env.sh"
    load_openclaw_env "$HOME/.config/openclaw/env"
fi

export PYTHONPATH=.

pkill -f "uvicorn worker.app:app --host 127.0.0.1 --port 8088" 2>/dev/null || true
sleep 2

if systemctl --user list-unit-files | grep -q '^umbral-worker\.service'; then
    systemctl --user daemon-reload
    systemctl --user restart umbral-worker
    echo "Worker VPS restarted via systemd."
else
    nohup python -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 --log-level info > /tmp/worker_vps.log 2>&1 &
    echo "Worker VPS restarted via fallback. PID: $!"
fi

sleep 2
curl -s http://127.0.0.1:8088/health | python -m json.tool 2>/dev/null || echo "Health check pending..."
