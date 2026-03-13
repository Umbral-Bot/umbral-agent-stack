#!/usr/bin/env bash
# ============================================================
# full-stack-up.sh — Levanta todo el sistema en la VPS
# ============================================================
# Ejecutar en la VPS: bash scripts/vps/full-stack-up.sh
# O desde local: ssh vps-umbral 'cd ~/umbral-agent-stack && bash scripts/vps/full-stack-up.sh'
#
# Requiere: ~/.config/openclaw/env con WORKER_URL, WORKER_TOKEN, REDIS_URL
# ============================================================
set -euo pipefail

REPO="${REPO:-$HOME/umbral-agent-stack}"
OPENCLAW_WS="${OPENCLAW_WS:-$HOME/.openclaw/workspace}"
TEMPLATES="$REPO/openclaw/workspace-templates"

cd "$REPO"

echo "=== 1. Git pull ==="
git pull origin main 2>/dev/null || true

echo ""
echo "=== 2. Venv y dependencias ==="
if [ -d ".venv" ]; then
  source .venv/bin/activate
else
  python3 -m venv .venv
  source .venv/bin/activate
fi
pip install -q --upgrade pip
pip install -q -r worker/requirements.txt -r dispatcher/requirements.txt

echo ""
echo "=== 3. Cargar env ==="
if [ -f "$HOME/.config/openclaw/env" ]; then
  set -a
  source "$HOME/.config/openclaw/env"
  set +a
  echo "   Env cargado desde ~/.config/openclaw/env"
else
  echo "   ⚠️  ~/.config/openclaw/env no existe. Exportar WORKER_URL, WORKER_TOKEN, REDIS_URL."
fi

echo ""
echo "=== 4. Redis ==="
if redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping 2>/dev/null | grep -q PONG; then
  echo "   ✅ Redis OK"
else
  echo "   ❌ Redis no responde. Levantar con: docker run -d -p 6379:6379 redis:7-alpine"
  echo "   O: redis-server --daemonize yes"
  exit 1
fi

echo ""
echo "=== 5. Rick identity (workspace) ==="
mkdir -p "$OPENCLAW_WS"
if [ -d "$TEMPLATES" ]; then
  for f in IDENTITY.md SOUL.md USER.md AGENTS.md TOOLS.md; do
    if [ -f "$TEMPLATES/$f" ]; then
      cp "$TEMPLATES/$f" "$OPENCLAW_WS/$f"
      echo "   Sync: $f -> ~/.openclaw/workspace (traspaso identidad Rick)"
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
  echo "   ✅ OpenClaw: RUNNING"
else
  echo "   ⚠️  OpenClaw no está corriendo. Iniciar: systemctl --user start openclaw"
  systemctl --user start openclaw 2>/dev/null || true
  sleep 2
  systemctl --user is-active openclaw > /dev/null 2>&1 && echo "   ✅ OpenClaw iniciado"
fi

echo ""
echo "=== 7. Worker (VPS) ==="
WORKER_URL="${WORKER_URL:-http://127.0.0.1:8088}"
if curl -sf "${WORKER_URL}/health" > /dev/null 2>&1; then
  echo "   ✅ Worker: OK en $WORKER_URL"
else
  echo "   ⚠️  Worker no responde. Iniciar:"
  echo "   cd $REPO && export \$(grep -v '^#' ~/.config/openclaw/env | xargs) PYTHONPATH=$REPO"
  echo "   python3 -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 &"
  echo "   O: systemctl --user start openclaw-worker-vps"
  if ! pgrep -f "uvicorn worker.app:app" > /dev/null 2>&1; then
    echo "   Intentando iniciar Worker en background..."
    (cd "$REPO" && export $(grep -v '^#' "$HOME/.config/openclaw/env" 2>/dev/null | xargs) PYTHONPATH="$REPO" nohup python3 -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 > /tmp/worker.log 2>&1 &)
    sleep 3
    curl -sf "${WORKER_URL}/health" > /dev/null 2>&1 && echo "   ✅ Worker iniciado" || echo "   ❌ Worker no arrancó"
  fi
fi

echo ""
echo "=== 8. Dispatcher ==="
if systemctl --user is-active openclaw-dispatcher > /dev/null 2>&1; then
  echo "   ✅ Dispatcher: RUNNING (systemd)"
else
  # Try to enable + start via systemd first
  if systemctl --user cat openclaw-dispatcher > /dev/null 2>&1; then
    echo "   ⚠️  Dispatcher no está corriendo. Iniciando via systemd..."
    systemctl --user enable --now openclaw-dispatcher 2>/dev/null || true
    sleep 2
    systemctl --user is-active openclaw-dispatcher > /dev/null 2>&1 \
      && echo "   ✅ Dispatcher iniciado (systemd)" \
      || echo "   ❌ Dispatcher no arrancó via systemd"
  elif pgrep -f "dispatcher.service" > /dev/null 2>&1; then
    echo "   ✅ Dispatcher: OK (proceso nohup)"
  else
    echo "   ⚠️  Dispatcher no está corriendo. Iniciando en background..."
    (cd "$REPO" && export $(grep -v '^#' "$HOME/.config/openclaw/env" 2>/dev/null | xargs) PYTHONPATH="$REPO" nohup python3 -m dispatcher.service > /tmp/dispatcher.log 2>&1 &)
    sleep 2
    pgrep -f "dispatcher.service" > /dev/null 2>&1 \
      && echo "   ✅ Dispatcher iniciado (nohup)" \
      || echo "   ❌ Dispatcher no arrancó"
  fi
fi

echo ""
echo "=== 9. Test E2E (Dispatcher + Worker) ==="
if [ -n "${WORKER_TOKEN:-}" ] && [ -n "${REDIS_URL:-}" ]; then
  export WORKER_URL REDIS_URL WORKER_TOKEN PYTHONPATH="$REPO"
  if python3 scripts/test_s2_dispatcher.py 2>/dev/null; then
    echo "   ✅ E2E OK"
  else
    echo "   ⚠️  E2E falló. ¿Está corriendo dispatcher/service.py?"
    echo "   Iniciar Dispatcher: cd $REPO && PYTHONPATH=$REPO python3 -m dispatcher.service &"
  fi
else
  echo "   ⚠️  WORKER_TOKEN o REDIS_URL no definidos — skipping E2E"
fi

echo ""
echo "=== Resumen ==="
echo "OpenClaw:   $(systemctl --user is-active openclaw 2>/dev/null || echo '?')"
echo "Dispatcher: $(systemctl --user is-active openclaw-dispatcher 2>/dev/null || (pgrep -f 'dispatcher.service' > /dev/null 2>&1 && echo 'running(nohup)' || echo 'NO'))"
echo "Worker:     $(curl -sf ${WORKER_URL}/health 2>/dev/null && echo 'OK' || echo 'NO')"
echo "Redis:      $(redis-cli -u ${REDIS_URL:-redis://localhost:6379/0} ping 2>/dev/null || echo 'NO')"
echo ""
echo "Notion poller: ejecutar manualmente si lo necesitás:"
echo "  python3 -m dispatcher.notion_poller"
echo ""
