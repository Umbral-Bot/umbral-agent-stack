---
id: 2026-05-19-001
title: Patch wrapper notion-poller-cron para detectar daemon stale
status: open
priority: P2
assigned_to: unassigned
created_at: 2026-05-19
created_by: coordinador-de-agentes (post-B2-deploy closeout, PR #422)
parent: null
relates_to:
  - 2026-05-19 changelog (B2 deploy)
  - PR #422 (B2 author guard)
blocks: nothing (NON-blocker; mejora de gobernanza de deploys del poller)
---

# 001 — Patch wrapper notion-poller-cron para detectar daemon stale

## Contexto

Durante el deploy de PR #422 (B2 author guard) el 2026-05-19 quedó al descubierto un hueco operativo en el wrapper de cron del notion-poller daemon. La maniobra completa quedó documentada en [`changelog/2026-05-19.md`](../../changelog/2026-05-19.md).

**El bug en una línea**: `scripts/vps/notion-poller-cron.sh` líneas 9-15 cortocircuitan silenciosamente si el PID en `/tmp/notion_poller.pid` está vivo. Esto es correcto para evitar duplicados, pero **no distingue entre "vivo con código actualizado" y "vivo con código viejo en memoria"**.

```bash
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        exit 0   # ← sin respawn, sin log, sin alerta
    fi
fi
```

**Consecuencia observada el 2026-05-19**: el daemon (PID 120685, lstart 2026-05-07) siguió corriendo el código pre-B2 durante 12 días después de mergeado #422. Solo se refrescó tras `SIGTERM` manual + autorización puntual del usuario.

**Por qué importa**: Python no hot-reloadea módulos. Cualquier futuro merge a `dispatcher/notion_poller.py` (u otros módulos importados por el daemon en tiempo de arranque) replicará el problema. El operador VPS hoy no tiene señal automática de que el daemon esté corriendo código stale.

## Scope

**Repo-only**. Modificación al script `scripts/vps/notion-poller-cron.sh`. **NO** se ejecuta el fix en runtime hasta que se merge la PR y se haga deploy controlado (mismo patrón que B2: SIGTERM puntual + wrapper).

### Cambios propuestos (a discutir en la PR, no prescriptivos)

Opciones, ordenadas por preferencia:

1. **Comparar fecha del proceso vs fecha del archivo `dispatcher/notion_poller.py`**:
   ```bash
   PROC_START=$(ps -o lstart= -p "$PID" | xargs -I {} date -d {} +%s)
   FILE_MTIME=$(git -C "$REPO_DIR" log -1 --format=%ct -- dispatcher/notion_poller.py 2>/dev/null \
                || stat -c %Y "$REPO_DIR/dispatcher/notion_poller.py")
   if [ "$PROC_START" -lt "$FILE_MTIME" ]; then
       echo "$(date -Iseconds) Stale daemon (started before module mtime). Restarting..." \
           >> "$LOG_FILE"
       kill "$PID"
       sleep 5
       # fall through to respawn
   else
       exit 0
   fi
   ```

2. **Flag opt-in `STALE_DETECTION=1`** para que el primer rollout no rompa nada por sorpresa.

3. **Solo logging (sin auto-kill)** como variante conservadora: emite warning a `/tmp/notion_poller_cron.log` cuando detecta stale pero no actúa. Operador decide.

### Fuera de scope

- NO migrar el daemon a un systemd unit (decisión separada, distinta priorización).
- NO cambiar el período del cron (sigue `*/5 * * * *`).
- NO tocar `dispatcher/notion_poller.py` ni `scripts/vps/notion-poller-daemon.py`.
- NO tocar otros wrappers de cron (`daily-digest-cron.sh`, `dashboard-cron.sh`, etc.) aunque puedan tener patrones similares — eso es un audit aparte.

## Salvavidas

- **No runtime** durante esta task. La PR queda mergeable pero el deploy se hace después, autorizado explícitamente.
- **No SIGKILL** en la lógica de respawn — solo SIGTERM (el daemon tiene handler graceful verificado, `scripts/vps/notion-poller-daemon.py` líneas 47-50).
- **No tocar** `~/.openclaw/openclaw.json`, gateway, worker, dispatcher.
- **No imprimir** secretos en el wrapper (no hay riesgo concreto, pero el principio aplica).
- **Idempotencia**: si el patch se ejecuta dos veces en el mismo minuto, el segundo run debe ser no-op.

## Acceptance

- PR con cambio limitado a `scripts/vps/notion-poller-cron.sh`.
- Tests manuales en VPS (post-merge, con autorización separada):
  - daemon vivo con código fresco → wrapper no hace nada (no-op).
  - daemon vivo con código viejo → wrapper detecta, kill graceful, respawn, primer poll OK en <90 s.
  - daemon muerto → respawn directo (comportamiento actual preservado).
  - daemon vivo pero el PID file desincronizado (PID reciclado por otro proceso) → wrapper detecta, no toca al PID ajeno, respawnea limpio.
- Sin cambios en `dispatcher/notion_poller.py`, `notion-poller-daemon.py`, ni en otros cron wrappers.
- Changelog del día del merge documenta el deploy + verificación.

## Notas de coordinación

- Owner sugerido: Copilot CLI o Codex (cambio chico, mecánico, repo-only).
- No requiere participación de Coordinador de Agentes para el fix en sí; sí para coordinar el deploy posterior (SIGTERM puntual al daemon vigente al momento del deploy, mismo patrón B2 si todavía no se aplicó este fix).
- Si en el momento del deploy de esta PR el daemon ya está corriendo con el código nuevo del wrapper (caso raro: alguien lo reinició por otra razón), basta esperar el próximo `*/5` natural.

## Capitalización

Una vez mergeado y desplegado, cerrar esta task con referencia al PR y al changelog del día. Si se decide auditar el resto de wrappers de cron por el mismo patrón, abrir task separada — no expandir el scope acá.
