---
id: "2026-02-28-003"
title: "VM: ejecutar runbook diagnóstico schtasks /ru y reportar resultados"
status: done
assigned_to: codex
created_by: cursor
priority: high
sprint: S5
created_at: "2026-02-28"
updated_at: "2026-03-22T19:04:21-03:00"
---

## Objetivo

Ejecutar en la VM (PCRick) el runbook `runbooks/runbook-vm-schtasks-runas-diagnosis.md` para determinar qué formato de cuenta (`/ru`) acepta `schtasks` en esta máquina. Los resultados son input para Cursor para arreglar la tarea `windows.open_notepad` (y futuras tareas que necesiten sesión del usuario).

## Contexto

- La VPS envía tareas al Worker de la VM. Autenticación OK.
- La tarea `windows.open_notepad` crea una tarea programada con `schtasks /ru` para que Notepad se abra en la sesión del usuario.
- Actualmente falla: "No se efectuó ninguna asignación entre los nombres de cuenta y los identificadores de seguridad".
- Hay que probar formatos: `.\rick`, `pcrick\rick`, `rick` con la contraseña real del usuario Rick.

## Criterios de aceptación

1. [ ] Ejecutar todas las pruebas A, B, C del runbook (formato .\rick, pcrick\rick, rick).
2. [ ] Reportar para cada una: si la tarea se creó OK o el mensaje de error exacto.
3. [ ] Incluir salida de `whoami`, `whoami /user`, `$env:COMPUTERNAME`.
4. [ ] Incluir valor de OPENCLAW_NOTEPAD_RUN_AS_USER de NSSM (sin contraseña).
5. [ ] Borrar tareas de prueba creadas (`schtasks /delete /tn TestNotepadA`, etc.).
6. [ ] Actualizar `status` a `done` y agregar entrada en ## Log con el resumen.

## Referencias

- Runbook: `runbooks/runbook-vm-schtasks-runas-diagnosis.md`
- Protocolo: `.agents/PROTOCOL.md`

## Log

### [codex] 2026-03-02 01:24 -03:00
Ejecución del runbook en esta sesión con evidencia recolectada:

- `whoami`: `pcrick\\rick`
- `whoami /user`: `pcrick\\rick` / `S-1-5-21-674090075-3305761584-1845821770-1001`
- `$env:COMPUTERNAME`: `PCRICK`
- `hostname`: `PCRick`
- `nssm get openclaw-worker AppEnvironmentExtra`:
  - `WORKER_TOKEN=...`
  - `PYTHONPATH=C:\\GitHub\\umbral-agent-stack`
  - No aparece `OPENCLAW_NOTEPAD_RUN_AS_USER`.

Pruebas `schtasks /create` (A/B/C):

- A) `/ru ".\\rick"` → `Error: No se efectuó ninguna asignación entre los nombres de cuenta y los identificadores de seguridad.`
- B) `/ru "pcrick\\rick"` → `Error: Acceso denegado.`
- C) `/ru "rick"` → `Error: Acceso denegado.`

Limpieza:

- `schtasks /query /tn TestNotepadA|B|C` → no existe ninguna tarea de prueba.
- `schtasks /delete /tn TestNotepadA|B|C /f` → `Error: El sistema no puede encontrar el archivo especificado.` (esperable si no existe).

Bloqueo:

- El runbook exige PowerShell como Administrador y contraseña real de Rick.
- En esta sesión no hay acceso a la contraseña real de Rick ni evidencia de `OPENCLAW_NOTEPAD_RUN_AS_USER` en NSSM.
- Resultado útil parcial: `.\\rick` falla por mapeo SID/cuenta; formatos `pcrick\\rick` y `rick` en este contexto devuelven `Acceso denegado` (probable falta de elevación/permisos para crear tarea con credenciales).

Archivos modificados:

- `.agents/tasks/2026-02-28-003-vm-schtasks-runas-diagnosis.md`

Tests:

- No aplican tests de Python; se ejecutaron comandos de diagnóstico en terminal.

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
