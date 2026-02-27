---
id: "2026-02-27-002"
title: "VM: documentar configuración exacta del Worker y runbook para levantar todo"
status: done
assigned_to: codex
created_by: cursor
priority: high
sprint: S3/S4
created_at: "2026-02-27"
updated_at: "2026-02-27T13:23:02-03:00"
---

## Objetivo

En la VM Windows (PCRick) donde corre el Worker: documentar la configuración real (NSSM, env, rutas) y dejar un runbook para que cualquiera pueda “levantar todo” lo de la VM de forma reproducible. Sin incluir valores secretos (solo nombres de variables y rutas).

## Contexto

- Queremos migrar / usar el Worker en la VPS “mientras” la VM no está; para eso necesitamos certeza de qué hay hoy en la VM.
- La VM tiene: NSSM `openclaw-worker`, Worker en 8088, repo en `C:\GitHub\umbral-agent-stack`. No está documentado el comando exacto de NSSM ni las variables de entorno inyectadas.
- Ver [docs/20-vm-to-vps-worker-migration.md](../../docs/20-vm-to-vps-worker-migration.md).

## Criterios de aceptación

1. **Documentar configuración actual (sin secretos):**
   - Comando exacto que usa NSSM para el worker (ej. `python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088` y directorio de trabajo).
   - Ruta del ejecutable Python (ej. `py -3` o `C:\...\python.exe`).
   - Nombres de variables de entorno que NSSM inyecta (WORKER_TOKEN, NOTION_*, etc.); no poner valores.
   - Si el worker corre desde `C:\openclaw-worker\` (app.py copiado) o desde el repo `C:\GitHub\umbral-agent-stack` con `worker.app:app`.

2. **Runbook en el repo:**
   - Crear o actualizar `runbooks/runbook-vm-worker-setup.md` con pasos para “levantar todo” en la VM desde cero: instalar Python/deps, configurar NSSM (o equivalente), firewall 8088, definir WORKER_TOKEN (y Notion si aplica), verificación.

3. **Opcional:** Script PowerShell que verifique que el Worker está arriba, que el repo está al día y que las variables necesarias están definidas (sin imprimir valores).

4. **Log:** Añadir entrada en el Log de este archivo con: qué se documentó, ruta del runbook y cualquier hallazgo (ej. si NSSM usa `app:app` desde otro directorio).

## Entregables

- Archivo de documentación de la configuración (puede ser la misma `runbooks/runbook-vm-worker-setup.md` con una sección “Configuración actual documentada” o un `docs/audits/vm-worker-config-YYYY-MM-DD.md`).
- Runbook `runbooks/runbook-vm-worker-setup.md` con pasos reproducibles.

## Referencias

- [docs/20-vm-to-vps-worker-migration.md](../../docs/20-vm-to-vps-worker-migration.md)
- [docs/06-setup-worker-windows.md](../../docs/06-setup-worker-windows.md)
- [scripts/setup-openclaw-service.ps1](../../scripts/setup-openclaw-service.ps1)
- Auditoría VM: [docs/audits/vm-2026-02-27.md](../../docs/audits/vm-2026-02-27.md)

## Log

### [cursor] 2026-02-27

Tarea creada para tener certeza de la configuración de Rick en la VM y poder replicar o migrar. Codex puede ejecutar en la VM los comandos necesarios (nssm, Get-Service, inspección del proceso, etc.) y dejar el runbook en el repo.

### [codex] 2026-02-27 13:23 -03:00

Se documento la configuracion real del servicio `openclaw-worker` en esta VM y se creo el runbook solicitado en `runbooks/runbook-vm-worker-setup.md`.

Hallazgos documentados (sin secretos):
- NSSM usa `C:\Users\Rick\AppData\Local\Programs\Python\Python311\python.exe`.
- Comando real: `-m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info`.
- `AppDirectory` real: `C:\GitHub\umbral-agent-stack` (corre desde repo, no desde `C:\openclaw-worker\app.py`).
- Env inyectadas por NSSM detectadas: `WORKER_TOKEN` y `PYTHONPATH` (`PYTHONPATH=C:\GitHub\umbral-agent-stack`).
- Logs configurados en `C:\openclaw-worker\service-stdout.log` y `C:\openclaw-worker\service-stderr.log`.

Verificaciones ejecutadas:
- Servicio `openclaw-worker` en `Running`, `Automatic`, cuenta `LocalSystem`.
- Puerto `8088` escuchando en `0.0.0.0`.
- Regla de firewall `OpenClaw Worker 8088` presente y habilitada.
- `GET http://localhost:8088/health` responde OK.
