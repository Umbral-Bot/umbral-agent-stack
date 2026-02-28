---
id: "2026-02-28-001"
title: "VM: deshabilitar tasks legacy y limpiar Gateway (regularización fase 1)"
status: assigned
assigned_to: codex
created_by: cursor
priority: high
sprint: S4
created_at: "2026-02-28"
updated_at: "2026-02-28T00:00:00-03:00"
---

## Objetivo

Ejecutar la fase 1 del plan de regularización documentado en `docs/audits/vm-openclaw-audit-2026-02-27.md`. Deshabilitar (sin borrar) las Scheduled Tasks legacy y asegurar que solo quede activo `openclaw-worker` como servicio de ejecución.

## Contexto

- La auditoría 003 encontró 4 Scheduled Tasks en la VM que no deben correr ahí según ADR-001:
  - `OpenClaw Gateway` (gateway local, ya hay uno en VPS)
  - `OpenClaw-TelegramAudioAgent` (error en ejecución, depende de Google Drive)
  - `Rick-Granola-Sync-Daily` (integración Notion, debe migrar a VPS)
  - `Rick-Multiagent-Progress-30min` (check multiagente, debe migrar a VPS)
- El Gateway de la VPS ya está operativo. La VM solo debe ser Execution Plane.

## Criterios de aceptación

1. **Deshabilitar las 4 Scheduled Tasks** (no borrar):
   ```powershell
   Disable-ScheduledTask -TaskName "OpenClaw Gateway"
   Disable-ScheduledTask -TaskName "OpenClaw-TelegramAudioAgent"
   Disable-ScheduledTask -TaskName "Rick-Granola-Sync-Daily"
   Disable-ScheduledTask -TaskName "Rick-Multiagent-Progress-30min"
   ```

2. **Respaldar los scripts de las automatizaciones** antes de desactivar:
   - Copiar `C:\Users\Rick\.openclaw\workspace\scripts\` a `C:\Users\Rick\.openclaw\workspace\scripts-backup-2026-02-28\` (o similar).
   - Documentar ruta del Telegram Audio Agent: `G:\Mi unidad\Rick-David\telegram-audio-agent\`.

3. **Verificar que `openclaw-worker` sigue sano:**
   - `Get-Service openclaw-worker` → Running
   - `Invoke-RestMethod http://localhost:8088/health` → OK
   - `Get-NetTCPConnection -LocalPort 8088` → LISTEN

4. **Verificar que no hay Gateway corriendo en la VM:**
   - `Get-NetTCPConnection -LocalPort 18789 -ErrorAction SilentlyContinue` → nada
   - `Get-Process | Where-Object { $_.ProcessName -like '*openclaw*' -and $_.Id -ne (Get-Service openclaw-worker).ProcessId }` → vacío (o solo el worker)

5. **Documentar resultado:**
   - Actualizar `docs/audits/vm-openclaw-audit-2026-02-27.md` con sección "Fase 1 ejecutada" indicando qué se deshabilitó y estado de verificación.

6. **Push al repo** con los cambios.

## Entregables

- 4 Scheduled Tasks deshabilitadas (no borradas).
- Respaldo de scripts.
- Worker verificado OK.
- Auditoría actualizada.
- Push al repo.

## Referencias

- Auditoría: [docs/audits/vm-openclaw-audit-2026-02-27.md](../../docs/audits/vm-openclaw-audit-2026-02-27.md)
- Runbook: [runbooks/runbook-vm-worker-setup.md](../../runbooks/runbook-vm-worker-setup.md)
- ADR-001: [docs/adr/ADR-001-rick-location.md](../../docs/adr/ADR-001-rick-location.md)
- Protocolo: [.agents/PROTOCOL.md](../../.agents/PROTOCOL.md)

## Log

### [cursor] 2026-02-28 00:00
Tarea creada. Fase 1 del plan de regularización. Codex debe deshabilitar las 4 tasks legacy, respaldar scripts, verificar Worker sano y pushear.
