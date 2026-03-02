---
id: "2026-02-28-004"
title: "VM: diagnóstico schtasks sin /ru — SID error pese a debug_used_ru: false"
status: blocked
assigned_to: codex
created_by: cursor
priority: high
sprint: S5
created_at: "2026-02-28"
updated_at: "2026-03-02T01:45:34-03:00"
---

## Objetivo

El Worker `windows.open_notepad` devuelve error SID mapeo aunque `debug_used_ru: false` (no usamos /ru). Ejecutar en la VM pruebas para entender la causa y dejar input para Cursor.

## Contexto

- VPS → VM Worker OK. Task windows.open_notepad devuelve ok: false, scheduled: false.
- Error: "No se efectuó ninguna asignación entre los nombres de cuenta y los identificadores de seguridad. (39,4):UserId:"
- debug_used_ru: false → run_as_user está vacío, no se usa /ru.
- Hipótesis: tarea UmbralOpenNotepad preexistente creada con /ru inválido; al sobrescribir con /f puede fallar.
- Se agregó borrado previo en el Worker; aún así, Codex debe verificar en la VM.

## Criterios de aceptación

1. [ ] En la VM (PowerShell como Admin): `schtasks /query /tn UmbralOpenNotepad` — ¿existe? Si sí, `schtasks /delete /tn UmbralOpenNotepad /f`.
2. [ ] Crear tarea manualmente SIN /ru: crear un .bat temporal en TEMP que abra notepad, luego `schtasks /create /tn UmbralOpenNotepad /tr "path\to\bat" /sc onlogon /f`. Reportar si OK o error.
3. [ ] Si OK: `schtasks /delete /tn UmbralOpenNotepad /f` para limpiar.
4. [ ] Actualizar status a done y agregar Log con: existencia previa, resultado del create manual, y recomendaciones.

## Referencias

- Worker: `worker/tasks/windows.py` (handle_windows_open_notepad)
- Protocolo: `.agents/PROTOCOL.md`

## Log

### [codex] 2026-03-02 01:45 -03:00
Diagnóstico manual ejecutado en VM para `schtasks` sin `/ru`.

Contexto de sesión:

- `whoami` -> `pcrick\\rick`
- `whoami /groups` -> `Mandatory Label\\Medium Mandatory Level` (sesión no elevada)
- `net session` -> `Error de sistema 5. Acceso denegado.`

Paso 1 (existencia previa):

- `schtasks /query /tn UmbralOpenNotepad` -> `Error: El sistema no puede encontrar el archivo especificado.` (exit 1)
- `schtasks /delete /tn UmbralOpenNotepad /f` -> `Error: El sistema no puede encontrar el archivo especificado.` (exit 1)

Paso 2 (create manual SIN `/ru`):

- Se creó BAT temporal: `C:\\Users\\Rick\\AppData\\Local\\Temp\\umbral-open-notepad-test.bat`
- Comando ejecutado: `schtasks /create /tn UmbralOpenNotepad /tr C:\\Users\\Rick\\AppData\\Local\\Temp\\umbral-open-notepad-test.bat /sc onlogon /f`
- Resultado: `Error: Acceso denegado.` (exit 1)

Paso 3 (limpieza):

- `schtasks /query /tn UmbralOpenNotepad` -> no existe (exit 1)
- `schtasks /delete /tn UmbralOpenNotepad /f` -> no existe (exit 1)
- BAT temporal eliminado.

Recomendaciones para Cursor:

1. Repetir exactamente estos comandos en PowerShell/cmd **ejecutado como Administrador**.
2. Si como Admin sigue fallando sin `/ru`, inspeccionar ACL/permiso del servicio que ejecuta Worker y policy de Task Scheduler en la VM.
3. Dado que no existía `UmbralOpenNotepad`, la hipótesis de conflicto por tarea preexistente no explica este fallo en esta sesión; el error apunta a privilegios del contexto de ejecución.

Archivos modificados:

- `.agents/tasks/2026-02-28-004-vm-schtasks-create-no-ru-diagnosis.md`

Tests:

- No aplican tests de Python; diagnóstico por comandos en VM.

