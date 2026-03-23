---
id: "2026-03-23-016"
title: "OpenClaw: separar cadencia de refresh y dejar tracking de gasto/actividad"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-23T14:15:00-03:00
updated_at: 2026-03-23T18:05:00-03:00
---

## Objetivo
Separar la actualización periódica del dashboard técnico (`Dashboard Rick`) de la del panel humano (`OpenClaw`) para reducir churn operativo en Notion, y dejar tracking explícito dentro del sistema de qué se ejecuta, cuánto tarda y qué gasto/actividad genera cada refresh.

## Contexto
- `scripts/vps/dashboard-cron.sh` sigue ejecutando juntos `dashboard_report_vps.py` y `openclaw_panel_vps.py` cada 15 minutos.
- `scripts/dashboard_report_vps.py` ya tiene fingerprint y puede hacer skip si no cambió nada.
- `scripts/openclaw_panel_vps.py` todavía recompone la shell aunque no haya cambios reales.
- David pidió además trazabilidad de “lo que se gasta en cada cosa dentro de OpenClaw”, idealmente dentro del sistema y no solo en logs sueltos.

## Criterios de aceptación
- [x] `Dashboard Rick` y `OpenClaw` quedan desacoplados en cadencia operativa.
- [x] `OpenClaw` puede saltarse escrituras cuando no cambió el snapshot, con fingerprint propio.
- [x] El sistema registra tracking operativo de los refreshes de dashboard/panel: duración, skip/update/fallo y actividad Notion relevante.
- [x] `OpenClaw` puede refrescarse por cambio real en entidades operativas (al menos proyectos / entregables / bandeja puente) además de un fallback lento.
- [x] Runbook/cron/docs quedan alineados con el nuevo comportamiento.

## Log
### [codex] 2026-03-23 14:15
Abro tarea para separar `Dashboard Rick` vs `OpenClaw`, endurecer el refresh del panel humano y dejar tracking explícito de ejecución/gasto operativo dentro del sistema.

### [codex] 2026-03-23 16:35
Implementación lista en rama local:
- `OpenClaw` ahora tiene fingerprint propio, dirty flag, skip explícito y `system_activity` en `ops_log`.
- Los upserts de proyecto / entregable / bandeja puente disparan refresh por cambio real.
- `Dashboard Rick` registra también `updated/skipped/failed` y ahora muestra una sección `Actividad de paneles`.
- Los crons se separaron: `dashboard-rick-cron.sh` horario y `openclaw-panel-cron.sh` cada 6h como fallback.
- Suite validada localmente: `1217 passed, 4 skipped, 1 warning`.

Pendiente antes de cerrar la tarea:
- smoke en VPS con la rama para instalar cron nuevo y verificar que ambos scripts corren con `--trigger` correcto;
- luego merge + deploy en `main`.

### [codex] 2026-03-23 18:05
Cierre completo:
- PR principal mergeado: `#150` (`7815ac7` en `main`).
- VPS sincronizada a `main` y `bash scripts/vps/install-cron.sh` aplicado.
- `crontab` quedó con:
  - `dashboard-rick-cron.sh` cada hora
  - `openclaw-panel-cron.sh` cada 6 horas
- Smoke real post-deploy en VPS:
  - `python3 scripts/dashboard_report_vps.py --trigger deploy.main --force` -> actualizado
  - `python3 scripts/openclaw_panel_vps.py --trigger deploy.main --force` -> actualizado
  - segundo `python3 scripts/openclaw_panel_vps.py --trigger deploy.main` -> `skipped` por fingerprint
- `ops_log` confirma tracking en sistema:
  - `dashboard_rick updated deploy.main 3 1 4`
  - `openclaw_panel updated deploy.main 17 19`
  - `openclaw_panel skipped deploy.main 4 0`

Resultado: `Dashboard Rick` queda horario, `OpenClaw` pasa a refresh por cambio real + fallback lento, y el sistema ya deja tracking visible del gasto/actividad operativo de ambos paneles.
