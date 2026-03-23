---
id: "2026-03-23-009"
title: "Supervisor: publicar alertas en espanol"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R23
created_at: 2026-03-23T12:57:00-03:00
updated_at: 2026-03-23T13:26:00-03:00
---

## Objetivo
Hacer que las alertas generadas por `scripts/vps/supervisor.sh` se publiquen en espanol en Notion para que David pueda entenderlas directamente.

## Contexto
- El smoke previo de Fase 1 dejo un comentario manual en ingles (`Supervisor phase-1 follow-up smoke ...`).
- El mensaje automatico canónico del script tambien estaba en ingles (`Supervisor auto-restart - ... - Restarted: ...`).
- La integracion directa del Supervisor a la pagina dedicada ya quedo restaurada; ahora falta pulir el contenido del comentario.

## Criterios de aceptacion
- [x] El texto por defecto de `test-alert` queda en espanol.
- [x] El texto canónico de reinicio automatico queda en espanol.
- [x] Se valida localmente la sintaxis del script.
- [x] Se valida en la VPS con un smoke real que publique un comentario en espanol.
- [x] Task y board quedan actualizados.

## Log
### [codex] 2026-03-23 12:57
Tarea creada para hispanizar las alertas del Supervisor. Siguiente paso: ajustar el mensaje canónico y validarlo en la VPS.

### [codex] 2026-03-23 13:26
Actualice `scripts/vps/supervisor.sh` para que:
- `test-alert` use por defecto `Prueba de alerta del Supervisor - ...`
- el comentario canónico de reinicio sea `Supervisor: reinicio automatico - ... - Servicios reiniciados: ...`
- los estados fallidos queden formateados en espanol (`Worker (falló)`, etc.)

Validacion:
- Sintaxis: `ssh vps-umbral "cd ~/umbral-agent-stack && bash -n scripts/vps/supervisor.sh"` -> OK
- Smoke real: `ssh vps-umbral "cd ~/umbral-agent-stack && bash scripts/vps/supervisor.sh test-alert"` -> `Alert posted to Notion (Supervisor identity)` / `Test alert completed`
- Verificacion por API de Notion en la pagina dedicada: comentario mas reciente = `Prueba de alerta del Supervisor - 2026-03-23 16:24 UTC`

La captura en ingles que vio David correspondia al smoke manual anterior de Fase 1. El flujo canónico ya queda en espanol.
