---
id: "2026-02-28-002"
title: "VM: actualizar Worker al cÃ³digo modular del repo y probar PAD"
status: blocked
assigned_to: codex
created_by: cursor
priority: high
sprint: S5
created_at: "2026-02-28"
updated_at: "2026-02-28T01:18:05-03:00"
---

## Objetivo

El Worker en la VM (PCRick) sigue siendo un prototipo mÃ­nimo (`app.py` de ~20 lÃ­neas en `C:\openclaw-worker\`). Actualizarlo al cÃ³digo modular del repo (`worker/app.py` con dispatch table, tasks, config, etc.) y validar que `windows.pad.run_flow` funciona.

## Contexto

- El repo tiene el Worker modular completo: `worker/app.py`, `worker/config.py`, `worker/tasks/` (ping, notion, windows), `worker/tool_policy.py`, `worker/sanitize.py`, `worker/rate_limit.py`.
- El NSSM service `openclaw-worker` en la VM apunta a `C:\openclaw-worker\app.py` (prototipo).
- Hay que cambiar NSSM para que use el repo (`C:\GitHub\umbral-agent-stack`) con `python -m uvicorn worker.app:app`.
- PAD puede o no estar instalado; documentar si estÃ¡ o no.

## Criterios de aceptaciÃ³n

1. **Actualizar NSSM para usar Worker modular:**
   - Cambiar AppDirectory a `C:\GitHub\umbral-agent-stack`
   - Cambiar comando a `python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088`
   - Mantener las mismas variables de entorno (WORKER_TOKEN, PYTHONPATH)
   - AÃ±adir `PYTHONPATH=C:\GitHub\umbral-agent-stack` si no estÃ¡

2. **Instalar dependencias del repo:**
   ```powershell
   cd C:\GitHub\umbral-agent-stack
   pip install -r worker/requirements.txt
   ```

3. **Reiniciar servicio y verificar:**
   - `Restart-Service openclaw-worker`
   - `Invoke-RestMethod http://localhost:8088/health` â†’ debe mostrar `tasks_registered` con ping, notion.*, windows.pad.run_flow
   - Probar ping: `Invoke-RestMethod -Method POST -Uri http://localhost:8088/run -Headers @{Authorization="Bearer $env:WORKER_TOKEN"} -Body '{"task":"ping","input":{"message":"test"}}' -ContentType 'application/json'`

4. **Verificar PAD:**
   - Â¿EstÃ¡ Power Automate Desktop instalado? `Test-Path "C:\Program Files (x86)\Power Automate Desktop\PAD.Console.Host.exe"`
   - Si sÃ­: crear flujo `EchoTest` simple (mostrar mensaje o escribir archivo) y probar `windows.pad.run_flow`
   - Si no: documentar que PAD no estÃ¡ instalado y que se necesita instalar

5. **Respaldar el prototipo viejo:**
   - Copiar `C:\openclaw-worker\` a `C:\openclaw-worker-backup-2026-02-28\`

6. **Documentar resultado:**
   - Actualizar `runbooks/runbook-vm-worker-setup.md` con la nueva configuraciÃ³n NSSM
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
Tarea creada. El Worker en la VM es un prototipo viejo; hay que cambiarlo al modular del repo y probar PAD si estÃ¡ instalado.

### [codex] 2026-02-28 01:18 -03:00
Ejecucion casi completa; bloqueo por permisos de administrador para reiniciar servicio.

Hecho:
- Verificado NSSM ya apuntando al worker modular del repo:
  - `Application`: `C:\Users\Rick\AppData\Local\Programs\Python\Python311\python.exe`
  - `AppParameters`: `-m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info`
  - `AppDirectory`: `C:\GitHub\umbral-agent-stack`
  - `AppEnvironmentExtra`: incluye `WORKER_TOKEN` y `PYTHONPATH=C:\GitHub\umbral-agent-stack`
- Dependencias del worker instaladas/verificadas (`pip install -r worker/requirements.txt` -> `Requirement already satisfied`).
- Backup del prototipo realizado: `C:\openclaw-worker-backup-2026-02-28\`.
- Verificacion de salud OK:
  - `GET /health` devuelve `tasks_registered` con `ping`, `notion.*`, `windows.pad.run_flow`.
  - `POST /run` con `task=ping` devuelve `ok:true`.
  - Puerto `8088` en `LISTEN`.
- PAD verificado como no instalado:
  - `Test-Path "C:\Program Files (x86)\Power Automate Desktop\PAD.Console.Host.exe"` -> `False`.
- Runbook actualizado:
  - `runbooks/runbook-vm-worker-setup.md`

Bloqueo:
- No fue posible ejecutar reinicio de servicio por permisos:
  - `Restart-Service openclaw-worker` -> `No se puede abrir el servicio ... Acceso denegado`.
  - `nssm restart openclaw-worker` -> `OpenService(): Acceso denegado`.

Siguiente paso requerido (Admin):
- Abrir PowerShell como Administrador y ejecutar:
  - `Restart-Service openclaw-worker`
  - `Invoke-RestMethod http://localhost:8088/health`
