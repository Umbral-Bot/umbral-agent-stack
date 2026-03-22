#!/bin/bash
# Sync repo on the VPS (Deploy Key) + venv + deps.
# Run on the VPS: bash scripts/sync-and-setup-vps.sh
# Or remotely: ssh vps-umbral 'cd ~/umbral-agent-stack && git pull origin main && bash scripts/sync-and-setup-vps.sh'

set -e
REPO="${REPO:-$HOME/umbral-agent-stack}"
cd "$REPO"

echo "=== 1. Git pull (origin main) ==="
git pull origin main

echo "=== 2. Venv y dependencias ==="
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  echo "Venv activado: .venv"
else
  echo "No hay .venv; creando..."
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

pip install -q --upgrade pip
pip install -q -r worker/requirements.txt -r dispatcher/requirements.txt
echo "Deps instaladas."

echo "=== 3. Verificacion rapida ==="
python -m pytest tests/ -q --tb=no 2>/dev/null && echo "Pytest OK" || true

echo ""
echo "=== VPS listo. Proximos pasos opcionales ==="
echo "  Worker en VPS:  runbooks/runbook-worker-on-vps.md"
echo "  Dispatcher:     bash scripts/vps/dispatcher-service.sh start"
echo "  Notion poller:  python -m dispatcher.notion_poller"
