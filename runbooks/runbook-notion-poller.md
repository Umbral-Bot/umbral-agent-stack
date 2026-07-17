# Runbook — Notion Poller (Control Room + scan V2 Granola)

> Estado 2026-07-17: **poller PAUSADO en VPS** (`CAP_POLLER_PAUSED`, contencion del
> plan hibrido). El aislamiento P2a del scan V2 esta **implementado en codigo, NO
> desplegado**. Este runbook describe como reactivar Control Room dejando la
> clasificacion V2 apagada por defecto.

## Topologia real (VPS)

- **Cron watchdog**: `scripts/vps/notion-poller-cron.sh`, crontab de `rick` cada 5 min.
  Solo verifica el PID file y relanza el daemon si no corre. **No** es un `--once`.
- **Daemon persistente**: `scripts/vps/notion-poller-daemon.py` → loop de 60 s sobre
  `dispatcher/notion_poller._do_poll` (PID en `/tmp/notion_poller.pid`, log en
  `/tmp/notion_poller.log`). Maneja SIGTERM limpio.
- Cada ciclo hace: scheduler → comentarios de Control Room + review targets →
  rick-mention / smart replies → **scan V2 de clasificacion Granola (solo si esta
  habilitado por flag; default OFF)**.

## Flag P2a — `NOTION_POLLER_ENABLE_V2_CLASSIFY`

| Valor | Efecto |
|---|---|
| ausente / `""` / `false` / `0` / cualquier cosa no-truthy | **Scan V2 apagado (default)**. Control Room, review targets y smart replies funcionan normal. El poller no lee la DB Granola ni llama `granola.classify_raw`. Log 1 vez por proceso: "V2 classify scan disabled". |
| `true` / `1` / `yes` / `on` (explicito) | Scan V2 activo con gate humano y validacion estricta (ver abajo). |

Razon del default-off (incidente 2026-07-16): el scan clasificaba las primeras 10
filas **sin** respetar `Procesar con agente`, con el Worker sin proveedor LLM vivo, y
marcaba checkpoint de exito con clasificaciones vacias (`?/?/?`). Eso forzo la pausa
total del poller (evidencia `~/.coord-ag-evidence/CAP_POLLER_PAUSED/`).

### Comportamiento con flag ON (P2a)

- **Gate humano obligatorio**: solo considera filas con `Procesar con agente=true`,
  `Estado` no terminal (no Procesada/Archivada/Error), `Estado agente` en
  Pendiente/vacio o `Revision requerida` + `Reprocesar tras revisión=true`, no
  archivadas y sin las 4 propiedades V2 ya completas. Nunca clasifica "las primeras
  N filas" por posicion.
- **Validacion estricta**: una clasificacion solo cuenta como exito si el resultado
  trae `dominio`, `tipo`, `destino` y `resumen` no vacios y sin placeholder `?`.
  Error/vacio/parcial/excepcion → log honesto + backoff (30 min), **sin** checkpoint
  de exito en Redis.
- **Aislamiento**: cualquier fallo del scan V2 no detiene el ciclo general.
- **Metricas por ciclo** (sin titulos/PII):
  `v2_classify_enabled=True scanned=N eligible=N classified=N skipped_gate=N errors=N`.

## Restaurar SOLO Control Room (V2 apagado) — procedimiento

Prerequisito: deploy a main con P2a mergeado + `systemctl --user restart umbral-worker`
NO es necesario (el poller es proceso aparte); si el codigo del dispatcher cambio,
basta relanzar el daemon (lo hace el watchdog).

1. Verificar que `NOTION_POLLER_ENABLE_V2_CLASSIFY` **no** esta seteado truthy en
   `~/.config/openclaw/env` (ausente = off, correcto).
2. Descomentar la linea del cron (marcador `CAP_POLLER_PAUSED`):
   `crontab -e` → quitar el prefijo `# CAP_POLLER_PAUSED ...:` de la linea
   `*/5 * * * * bash .../notion-poller-cron.sh ...`.
3. Esperar ≤5 min: el watchdog relanza el daemon. Verificar:
   - `pgrep -af "notion-poller-daemon[.]py"` → 1 proceso.
   - `tail /tmp/notion_poller.log` → ciclos nuevos + "V2 classify scan disabled".
   - NINGUNA linea `V2 classify scan: v2_classify_enabled=True`.
4. Smoke Control Room: comentario de David en Control Room → reply de Rick.

## Habilitar V2 (futuro, requiere gate de David)

Prerequisitos: P2b (clasificador con proveedor real — decision Rick+GPT-5.6 Luna) +
prompt sincronizado con Enmienda V2.1.1 + GO explicito. Entonces:
`echo "NOTION_POLLER_ENABLE_V2_CLASSIFY=true" >> ~/.config/openclaw/env` y relanzar
el daemon (`pkill -TERM -f "notion-poller-daemon[.]py"`; el watchdog lo relanza con
el env nuevo). **Gotcha**: el patron `[.]py` evita que pkill se auto-mate por SSH.

## Rollback

- Apagar solo V2: quitar/poner en false el flag + relanzar daemon (mismo pkill).
- Pausa total (volver a CAP_POLLER_PAUSED): re-comentar la linea del cron con el
  marcador + `pkill -TERM -f "notion-poller-daemon[.]py"`; verificar
  "Notion Poller daemon stopped." en el log y ausencia de PID file.

## Referencias

- `dispatcher/notion_poller.py` · `tests/test_notion_poller.py`
- `docs/adr/ADR-010-notion-poller-cursor-checkpoint.md`
- `docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md` (§1.3, §5 P2)
- Evidencia pausa: `~/.coord-ag-evidence/CAP_POLLER_PAUSED/` (VPS)
