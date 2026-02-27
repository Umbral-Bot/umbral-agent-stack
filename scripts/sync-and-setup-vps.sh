#!/bin/bash
# Sync repo en la VPS (Deploy Key) + venv + deps. Ejecutar en la VPS: bash scripts/sync-and-setup-vps.sh
# Desde tu PC: ssh vps-umbral 'cd ~/umbral-agent-stack && git pull origin main && bash scripts/sync-and-setup-vps.sh'

set -e
REPO="${REPO:-$HOME/umbral-agent-stack}"
cd "$REPO"

echo "=== 1. Git pull (origin main) ==="
git pull origin main

echo "=== 2. Venv y dependencias ==="
if [ -d ".venv" ]; then
  source .venv/bin/activate
  echo "Venv activado: .venv"
else
  echo "No hay .venv; creando..."
  python3 -m venv .venv
  source .venv/bin/activate
fi

pip install -q --upgrade pip
pip install -q -r worker/requirements.txt -r dispatcher/requirements.txt
echo "Deps instaladas."

echo "=== 3. Verificación rápida ==="
python -m pytest tests/ -q --tb=no 2>/dev/null && echo "Pytest OK" || true

echo ""
echo "=== VPS listo. Próximos pasos opcionales ==="
echo "  Worker en VPS:  runbooks/runbook-worker-on-vps.md"
echo "  Dispatcher:     export WORKER_URL=... REDIS_URL=... WORKER_TOKEN=... && python -m dispatcher.service"
echo "  Notion poller:  python -m dispatcher.notion_poller"
