#!/usr/bin/env bash
# ============================================================
# full-stack-up.sh - Bring up the stack on the VPS
# ============================================================
# Run on the VPS: bash scripts/vps/full-stack-up.sh
# Or remotely: ssh vps-umbral 'cd ~/umbral-agent-stack && bash scripts/vps/full-stack-up.sh'
#
# Requires: ~/.config/openclaw/env with WORKER_URL, WORKER_TOKEN, REDIS_URL
# ============================================================
set -euo pipefail

REPO="${REPO:-$HOME/umbral-agent-stack}"
OPENCLAW_WS="${OPENCLAW_WS:-$HOME/.openclaw/workspace}"
TEMPLATES="$REPO/openclaw/workspace-templates"
DISPATCHER_CTL="$REPO/scripts/vps/dispatcher-service.sh"

cd "$REPO"

echo "=== 1. Git pull ==="
git pull origin main 2>/dev/null || true

echo ""
echo "=== 2. Venv y dependencias ==="
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
pip install -q --upgrade pip
pip install -q -r worker/requirements.txt -r dispatcher/requirements.txt

echo ""
echo "=== 3. Cargar env ==="
if [ -f "$HOME/.config/openclaw/env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$HOME/.config/openclaw/env"
  set +a
  echo "   Env cargado desde ~/.config/openclaw/env"
else
  echo "   ~/.config/openclaw/env no existe. Exportar WORKER_URL, WORKER_TOKEN, REDIS_URL."
fi

echo ""
echo "=== 4. Redis ==="
if redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping 2>/dev/null | grep -q PONG; then
  echo "   Redis OK"
else
  echo "   Redis no responde. Levantar con: redis-server --daemonize yes"
  exit 1
fi

echo ""
echo "=== 5. Rick identity (workspace) ==="
mkdir -p "$OPENCLAW_WS"
if [ -d "$TEMPLATES" ]; then
  for f in IDENTITY.md SOUL.md USER.md AGENTS.md TOOLS.md; do
    if [ -f "$TEMPLATES/$f" ]; then
      cp "$TEMPLATES/$f" "$OPENCLAW_WS/$f"
      echo "   Sync: $f -> ~/.openclaw/workspace"
    else
      echo "   Template $f no encontrado"
    fi
  done
else
  echo "   Templates no encontrados en $TEMPLATES"
fi

echo ""
echo "=== 6. OpenClaw service ==="
if systemctl --user is-active openclaw > /dev/null 2>&1; then
  echo "   OpenClaw: RUNNING"
else
  echo "   OpenClaw no esta corriendo. Iniciando..."
  systemctl --user start openclaw 2>/dev/null || true
  sleep 2
  if systemctl --user is-active openclaw > /dev/null 2>&1; then
    echo "   OpenClaw iniciado"
  else
    echo "   OpenClaw sigue inactivo"
  fi
fi

echo ""
echo "=== 7. Worker (VPS) ==="
WORKER_URL="${WORKER_URL:-http://127.0.0.1:8088}"
if curl -sf "${WORKER_URL}/health" > /dev/null 2>&1; then
  echo "   Worker: OK en $WORKER_URL"
else
  echo "   Worker no responde. Intentando iniciar en background..."
  if ! pgrep -f "uvicorn worker.app:app" > /dev/null 2>&1; then
    (
      cd "$REPO"
      PYTHONPATH="$REPO" nohup python3 -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 > /tmp/worker.log 2>&1 &
    )
    sleep 3
  fi
  if curl -sf "${WORKER_URL}/health" > /dev/null 2>&1; then
    echo "   Worker iniciado"
  else
    echo "   Worker no arranco"
  fi
fi

echo ""
echo "=== 8. Dispatcher ==="
if bash "$DISPATCHER_CTL" start; then
  echo "   Dispatcher canonicalized via systemd"
else
  echo "   Dispatcher could not be reconciled via systemd"
fi

echo ""
echo "=== 9. Test E2E (Redis -> Dispatcher -> Worker) ==="
if [ -n "${WORKER_TOKEN:-}" ] && [ -n "${REDIS_URL:-}" ]; then
  export WORKER_URL REDIS_URL WORKER_TOKEN PYTHONPATH="$REPO"
  if bash "$DISPATCHER_CTL" smoke 2>/dev/null; then
    echo "   E2E OK"
  else
    echo "   E2E fallo. Reconciliar Dispatcher:"
    echo "   cd $REPO && bash scripts/vps/dispatcher-service.sh reconcile"
  fi
else
  echo "   WORKER_TOKEN o REDIS_URL no definidos - skipping E2E"
fi

echo ""
echo "=== Resumen ==="
echo "OpenClaw:   $(systemctl --user is-active openclaw 2>/dev/null || echo '?')"
echo "Dispatcher:"
bash "$DISPATCHER_CTL" status || true
echo "Worker:     $(curl -sf "${WORKER_URL}/health" 2>/dev/null && echo 'OK' || echo 'NO')"
echo "Redis:      $(redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping 2>/dev/null || echo 'NO')"
echo ""
echo "Notion poller: ejecutar manualmente si lo necesitas:"
echo "  python3 -m dispatcher.notion_poller"
echo ""
