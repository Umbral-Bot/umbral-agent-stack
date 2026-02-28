#!/usr/bin/env bash
# Restart Worker on VPS
set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
export PYTHONPATH=.

pkill -f "uvicorn worker.app" 2>/dev/null || true
sleep 2

nohup python -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 --log-level info > /tmp/worker_vps.log 2>&1 &
echo "Worker VPS restarted. PID: $!"
sleep 2
curl -s http://127.0.0.1:8088/health | python -m json.tool 2>/dev/null || echo "Health check pending..."
