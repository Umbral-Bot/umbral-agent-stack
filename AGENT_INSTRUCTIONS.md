# Instrucciones para Claude Code — Ronda 2

**Repo:** `C:\GitHub\umbral-agent-stack-claude`  
**Rama:** `feat/claude-poller-daemon`  
**Tarea nueva:** Notion Poller daemon + wrapper cron para VPS

## Contexto

El Notion Poller (`dispatcher/notion_poller.py`) + intent classifier (`dispatcher/intent_classifier.py`) ya están implementados y mergeados en main. Pero **nadie los ejecuta en producción**. Cuando David escribe un comentario en la Control Room de Notion, nada pasa porque el poller no está corriendo.

Necesitamos un daemon simple que corra en la VPS y haga polling cada 60 segundos.

## Tu tarea

### A. Daemon del Notion Poller
Crear `scripts/vps/notion-poller-daemon.py`:
1. Loop infinito que:
   - Importa y ejecuta la función principal del poller (`dispatcher.notion_poller`)
   - Duerme 60 segundos entre iteraciones
   - Captura y loguea cualquier excepción sin crashear
   - Escribe un PID file (`/tmp/notion_poller.pid`) al arrancar
   - Loguea a `/tmp/notion_poller.log`
2. Maneja SIGTERM graciosamente (borra PID file y sale)

### B. Wrapper cron
Crear `scripts/vps/notion-poller-cron.sh`:
1. Verifica si el daemon ya está corriendo (lee PID file, verifica que el proceso existe)
2. Si NO está corriendo, lo levanta en background
3. Si ya está corriendo, no hace nada
4. Diseñado para correr como cron cada 5 minutos: `*/5 * * * *`

### C. Agregar al install-cron.sh
Agregar la línea del poller cron a `scripts/vps/install-cron.sh` de forma idempotente.

### D. Test en VPS
1. Conectar: `ssh rick@100.113.249.25`
2. Env: `cd ~/umbral-agent-stack && source .venv/bin/activate && set -a && source ~/.config/openclaw/env && set +a`
3. Probar: `PYTHONPATH=. python3 scripts/vps/notion-poller-daemon.py &`
4. Escribir un comentario en Notion Control Room (page `30c5f443fb5c80eeb721dc5727b20dca`)
5. Verificar que el poller lo detecta, clasifica y responde

### E. Referencia: cómo funciona el poller actual
- `dispatcher/notion_poller.py` — función `main()` que:
  - Lee comentarios de la Control Room via Worker (`notion.poll_comments`)
  - Clasifica intención con `dispatcher/intent_classifier.py`
  - Encola tareas y responde con contexto
- Worker URL: `WORKER_URL` (http://127.0.0.1:8088)
- Worker token: `WORKER_TOKEN`
- Control Room: `NOTION_CONTROL_ROOM_PAGE_ID`

## Flujo de trabajo
```bash
git add .
git commit -m "feat: notion poller daemon + cron wrapper for VPS"
git push -u origin feat/claude-poller-daemon
gh pr create --base main --title "[Claude Code] Notion Poller daemon" --body "Daemon que corre el poller cada 60s + cron wrapper para auto-restart"
```
