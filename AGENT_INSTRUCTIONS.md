# Instrucciones para Claude Code (Opus 4.6)

**Repo:** `C:\GitHub\umbral-agent-stack-claude`  
**Rama:** `feat/claude-dispatcher-resilience`  
**Tarea:** 2026-03-04-011 (UMB-18)

## Contexto
Este es TU clon del repo. Trabaja solo aquí. No toques otros clones.

## Tu tarea

### A. Resiliencia del Dispatcher
Implementa en `dispatcher/service.py`:

1. **Fire-and-forget real** para `_notion_upsert()` y `_notify_linear_completion()`:
   - Envolver cada llamada en `threading.Thread(target=..., daemon=True).start()`
   - Un 404 de Notion no debe bloquear el worker

2. **Retry automático para timeouts**:
   - Si `httpx.ReadTimeout` o `httpx.WriteTimeout` y `retry_count < 2`, re-encolar la tarea
   - Agregar campo `retry_count` al envelope
   - Agregar método `task_retried()` a `infra/ops_logger.py`

3. **Graceful handling de Worker caído**:
   - Si connection refused, loguear + `time.sleep(5)` antes de reintentar dequeue
   - Evitar loops de error con miles de líneas de log

### B. Tests
- Crear tests en `tests/test_dispatcher_resilience.py` para verificar:
  - Que fire-and-forget no bloquea
  - Que retry se encola correctamente
  - Que connection refused no crashea

## Conectividad VPS (para testing)
- SSH: `ssh rick@100.113.249.25` (via Tailscale)
- Worker: `http://127.0.0.1:8088/health`
- Redis: `redis-cli ping`

## Flujo de trabajo
```bash
git checkout feat/claude-dispatcher-resilience
# Trabaja...
git add .
git commit -m "feat: dispatcher resilience - fire-and-forget, retry, graceful errors"
git push -u origin feat/claude-dispatcher-resilience
gh pr create --base main --title "[Claude Code] Dispatcher resilience" --body "UMB-18: fire-and-forget, retry, graceful errors"
```

## Protocolo
- NO edites `.agents/board.md` (lo hace Cursor)
- Actualiza tu task file: `.agents/tasks/2026-03-04-011-hackathon-claude-code-dispatcher-resilience.md`
- Cuando termines, avísale a David para que Cursor revise y mergee
