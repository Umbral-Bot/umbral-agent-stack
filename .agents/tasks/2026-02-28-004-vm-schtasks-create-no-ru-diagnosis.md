---
id: "2026-02-28-004"
title: "VM: diagnóstico schtasks sin /ru — SID error pese a debug_used_ru: false"
status: assigned
assigned_to: codex
created_by: cursor
priority: high
sprint: S5
created_at: "2026-02-28"
updated_at: "2026-02-28"
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

