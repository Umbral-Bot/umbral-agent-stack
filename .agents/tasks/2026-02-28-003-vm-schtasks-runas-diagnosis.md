---
id: "2026-02-28-003"
title: "VM: ejecutar runbook diagnóstico schtasks /ru y reportar resultados"
status: assigned
assigned_to: codex
created_by: cursor
priority: high
sprint: S5
created_at: "2026-02-28"
updated_at: "2026-02-28"
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

