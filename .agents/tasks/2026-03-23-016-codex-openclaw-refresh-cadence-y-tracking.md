---
id: "2026-03-23-016"
title: "OpenClaw: separar cadencia de refresh y dejar tracking de gasto/actividad"
status: in_progress
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-23T14:15:00-03:00
updated_at: 2026-03-23T16:35:00-03:00
---

## Objetivo
Separar la actualización periódica del dashboard técnico (`Dashboard Rick`) de la del panel humano (`OpenClaw`) para reducir churn operativo en Notion, y dejar tracking explícito dentro del sistema de qué se ejecuta, cuánto tarda y qué gasto/actividad genera cada refresh.

## Contexto
- `scripts/vps/dashboard-cron.sh` sigue ejecutando juntos `dashboard_report_vps.py` y `openclaw_panel_vps.py` cada 15 minutos.
- `scripts/dashboard_report_vps.py` ya tiene fingerprint y puede hacer skip si no cambió nada.
- `scripts/openclaw_panel_vps.py` todavía recompone la shell aunque no haya cambios reales.
- David pidió además trazabilidad de “lo que se gasta en cada cosa dentro de OpenClaw”, idealmente dentro del sistema y no solo en logs sueltos.

## Criterios de aceptación
- [ ] `Dashboard Rick` y `OpenClaw` quedan desacoplados en cadencia operativa.
- [ ] `OpenClaw` puede saltarse escrituras cuando no cambió el snapshot, con fingerprint propio.
- [ ] El sistema registra tracking operativo de los refreshes de dashboard/panel: duración, skip/update/fallo y actividad Notion relevante.
- [ ] `OpenClaw` puede refrescarse por cambio real en entidades operativas (al menos proyectos / entregables / bandeja puente) además de un fallback lento.
- [ ] Runbook/cron/docs quedan alineados con el nuevo comportamiento.

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
