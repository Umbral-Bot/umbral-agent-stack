#!/bin/bash
# Prueba inventario y conectividad VPS -> Workers en VPS/VM.
# Ejecutar desde la VPS: cd ~/umbral-agent-stack && bash scripts/test_workers_vm.sh

set -e
REPO="${REPO:-$HOME/umbral-agent-stack}"
cd "$REPO"

source ~/.config/openclaw/env 2>/dev/null || true
HEADLESS_URL="${WORKER_URL_VM:-}"
INTERACTIVE_URL="${WORKER_URL_VM_INTERACTIVE:-}"
TOKEN="${WORKER_TOKEN}"
[ -z "$HEADLESS_URL" ] && HEADLESS_URL="http://100.109.16.40:8088"
[ -z "$INTERACTIVE_URL" ] && INTERACTIVE_URL="http://100.109.16.40:8089"

if [ -z "$TOKEN" ]; then
  echo "WORKER_TOKEN no definido (source ~/.config/openclaw/env)"
  exit 1
fi

echo "=== Worker headless (sesion 0) $HEADLESS_URL ==="
curl -sf -H "Authorization: Bearer $TOKEN" "$HEADLESS_URL/health" >/dev/null && echo "health OK" || echo "health fallo"
python3 scripts/run_worker_task.py ping 2>/dev/null | grep -q '"ok"' && echo "ping OK" || echo "ping fallo"

echo ""
echo "=== Inventario VPS + VM ==="
python3 scripts/worker_inventory_smoke.py \
  --target "vps=http://127.0.0.1:8088" \
  --target "vm-headless=$HEADLESS_URL" \
  --target "vm-interactive=$INTERACTIVE_URL" \
  --token "$TOKEN" \
  --smoke

echo ""
echo "=== Worker interactivo (sesion 1) $INTERACTIVE_URL ==="
if curl -sf --connect-timeout 3 -H "Authorization: Bearer $TOKEN" "$INTERACTIVE_URL/health" >/dev/null 2>&1; then
  echo "health OK"
  python3 scripts/run_worker_task.py windows.open_notepad "test interactive" --session interactive --run-now 2>/dev/null | grep -q '"ok"' && echo "open_notepad interactive OK" || echo "open_notepad fallo"
else
  echo "No alcanzable (¿Worker interactivo corriendo en la VM?)"
fi
