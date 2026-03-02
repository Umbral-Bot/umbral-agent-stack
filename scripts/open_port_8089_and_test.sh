#!/bin/bash
# Desde la VPS: abre puerto 8089 en la VM (firewall) y prueba el Worker interactivo.
# Si falla con 400, en la VM ejecuta primero:
#   cd C:\GitHub\umbral-agent-stack && git pull origin main && nssm restart openclaw-worker

set -e
cd "$(dirname "$0")/.."
source ~/.config/openclaw/env 2>/dev/null || true
URL_VM="${WORKER_URL_VM:-http://100.109.16.40:8088}"
URL_8089="${WORKER_URL_VM_INTERACTIVE:-http://100.109.16.40:8089}"

echo "1. Añadiendo regla firewall puerto 8089 en la VM..."
if ! python3 scripts/run_worker_task.py windows.firewall_allow_port '{}' 2>/dev/null | grep -q '"ok": true'; then
  echo "   Falló. En la VM ejecuta: cd C:\\GitHub\\umbral-agent-stack && git pull origin main && nssm restart openclaw-worker"
  echo "   Luego vuelve a ejecutar este script."
  exit 1
fi

echo "2. Comprobando 8089 (5s)..."
sleep 5
if curl -sf --connect-timeout 10 -H "Authorization: Bearer $WORKER_TOKEN" "$URL_8089/health" >/dev/null; then
  echo "   8089 OK."
  echo "3. Abriendo Notepad en sesión interactiva..."
  python3 scripts/run_worker_task.py windows.open_notepad "hola desde 8089" --session interactive --run-now
else
  echo "   8089 no responde. ¿Worker interactivo corriendo en la VM? (.\scripts\vm\start_interactive_worker.bat)"
  exit 1
fi
