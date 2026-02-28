---
id: "2026-02-28-002"
title: "VM: actualizar Worker al código modular del repo y probar PAD"
status: assigned
assigned_to: codex
created_by: cursor
priority: high
sprint: S5
created_at: "2026-02-28"
updated_at: "2026-02-28T01:00:00-03:00"
---

## Objetivo

El Worker en la VM (PCRick) sigue siendo un prototipo mínimo (`app.py` de ~20 líneas en `C:\openclaw-worker\`). Actualizarlo al código modular del repo (`worker/app.py` con dispatch table, tasks, config, etc.) y validar que `windows.pad.run_flow` funciona.

## Contexto

- El repo tiene el Worker modular completo: `worker/app.py`, `worker/config.py`, `worker/tasks/` (ping, notion, windows), `worker/tool_policy.py`, `worker/sanitize.py`, `worker/rate_limit.py`.
- El NSSM service `openclaw-worker` en la VM apunta a `C:\openclaw-worker\app.py` (prototipo).
- Hay que cambiar NSSM para que use el repo (`C:\GitHub\umbral-agent-stack`) con `python -m uvicorn worker.app:app`.
- PAD puede o no estar instalado; documentar si está o no.

## Criterios de aceptación

1. **Actualizar NSSM para usar Worker modular:**
   - Cambiar AppDirectory a `C:\GitHub\umbral-agent-stack`
   - Cambiar comando a `python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088`
   - Mantener las mismas variables de entorno (WORKER_TOKEN, PYTHONPATH)
   - Añadir `PYTHONPATH=C:\GitHub\umbral-agent-stack` si no está

2. **Instalar dependencias del repo:**
   ```powershell
   cd C:\GitHub\umbral-agent-stack
   pip install -r worker/requirements.txt
   ```

3. **Reiniciar servicio y verificar:**
   - `Restart-Service openclaw-worker`
   - `Invoke-RestMethod http://localhost:8088/health` → debe mostrar `tasks_registered` con ping, notion.*, windows.pad.run_flow
   - Probar ping: `Invoke-RestMethod -Method POST -Uri http://localhost:8088/run -Headers @{Authorization="Bearer $env:WORKER_TOKEN"} -Body '{"task":"ping","input":{"message":"test"}}' -ContentType 'application/json'`

4. **Verificar PAD:**
   - ¿Está Power Automate Desktop instalado? `Test-Path "C:\Program Files (x86)\Power Automate Desktop\PAD.Console.Host.exe"`
   - Si sí: crear flujo `EchoTest` simple (mostrar mensaje o escribir archivo) y probar `windows.pad.run_flow`
   - Si no: documentar que PAD no está instalado y que se necesita instalar

5. **Respaldar el prototipo viejo:**
   - Copiar `C:\openclaw-worker\` a `C:\openclaw-worker-backup-2026-02-28\`

6. **Documentar resultado:**
   - Actualizar `runbooks/runbook-vm-worker-setup.md` con la nueva configuración NSSM
   - Agregar log en esta tarea

7. **Push al repo.**

## Referencias

- Worker modular: `worker/` en el repo
- NSSM config previa: `runbooks/runbook-vm-worker-setup.md`
- PAD handler: `worker/tasks/windows.py`
- Tool policy: `config/tool_policy.yaml`
- Protocolo: `.agents/PROTOCOL.md`

## Log

### [cursor] 2026-02-28 01:00
Tarea creada. El Worker en la VM es un prototipo viejo; hay que cambiarlo al modular del repo y probar PAD si está instalado.
