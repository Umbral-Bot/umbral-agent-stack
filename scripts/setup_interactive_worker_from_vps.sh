#!/bin/bash
# Desde la VPS: crea worker_token en la VM y arranca el Worker interactivo (8089).
# Requiere que la VM haya hecho: git pull origin main && nssm restart openclaw-worker

set -e
cd "$(dirname "$0")/.."
source ~/.config/openclaw/env 2>/dev/null || true

echo "1. Escribiendo token en VM (C:\\openclaw-worker\\worker_token)..."
python3 scripts/run_worker_task.py windows.write_worker_token '{}' || { echo "Falló (¿VM actualizada y reiniciada?)"; exit 1; }

echo "2. Arrancando Worker interactivo en VM (puerto 8089)..."
python3 scripts/run_worker_task.py windows.start_interactive_worker '{}' || { echo "Falló"; exit 1; }

echo "3. Esperando 5s..."
sleep 5

echo "4. Comprobando 8089..."
curl -sf --connect-timeout 5 -H "Authorization: Bearer $WORKER_TOKEN" "${WORKER_URL_VM_INTERACTIVE:-http://100.109.16.40:8089}/health" && echo " OK" || echo " 8089 no respondió aún (puede tardar más)."
