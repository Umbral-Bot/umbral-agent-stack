---
id: "2026-03-23-006"
title: "Fase 0: estabilizacion base, merge, deploy y smoke post-diagnostico"
status: blocked
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T07:55:00-03:00
updated_at: 2026-03-23T10:06:00-03:00
---

## Objetivo
Tomar la base tecnica del PR #137, integrarla a `main`, desplegar lo necesario en VPS y VM, y dejar una verificacion post-deploy honesta sobre los caminos minimos definidos para la Fase 0.

## Contexto
- La Fase 0 depende del trabajo ya preparado en `codex/super-diagnostico-interconectividad-r24` / PR #137.
- El objetivo no es reauditar todo, sino estabilizar el baseline tecnico para que las siguientes fases trabajen sobre runtime alineado.
- Cambios clave a desplegar:
  - `scripts/env_loader.py`
  - `scripts/run_worker_task.py`
  - `worker/app.py`
  - `scripts/vps/dispatcher-service.sh`
  - `scripts/verify_stack_vps.py`

## Criterios de aceptacion
- [x] PR #137 mergeado a `main`.
- [x] Este clon queda sincronizado a `origin/main`.
- [x] VPS sincronizada con `main` y servicios reiniciados donde aplique.
- [ ] VM actualizada si aplica para los cambios de `worker/app.py`.
- [x] Smokes post-deploy ejecutados en VPS: `health`, `linear.list_teams`, `google.calendar.list_events`, `gmail.list_drafts`, `/providers/status`, `/quota/status`.
- [x] Log y board actualizados con resultado real, sin afirmar deploys o checks no ejecutados.

## Log
### [codex] 2026-03-23 07:55
- Inicio de Fase 0: registro formal en `.agents`, verificacion de estado del PR #137 y lectura de scripts de deploy/restart para VPS y VM.

### [codex] 2026-03-23 10:06
- PR #137 mergeado a `main` como `a480a0aa8dee9177d3a8ed26bcac583b8afab72e`; este clon sincronizado a `origin/main` en la rama `codex/fase-0-estabilizacion-base`.
- VPS actualizada con `git pull --ff-only origin main` hasta `a480a0aa8dee9177d3a8ed26bcac583b8afab72e` y Worker reiniciado con `scripts/vps/restart-worker.sh`.
- `python3 scripts/verify_stack_vps.py` ejecutado despues del restart: plano base verificado (Worker, Redis, Linear). El script ya refleja el alcance honesto introducido en PR #137.
- Supervisor validado en vivo: `scripts/vps/supervisor.sh` limpio y `/tmp/supervisor.log` muestra ticks cron limpios a las `12:55 UTC` y `13:00 UTC` con `Dispatcher: OK` y `Done. Restarted: none`.
- Smokes VPS ejecutados con exito:
  - `ping`
  - `google.calendar.list_events`
  - `gmail.list_drafts`
  - `GET /providers/status`
  - `GET /quota/status`
- Estado real de la VM: **bloqueada por inaccesibilidad**, no por falta de intento de deploy. Evidencia:
  - desde la VPS, `WORKER_URL_VM=http://100.109.16.40:8088` y `WORKER_URL_VM_INTERACTIVE=http://100.109.16.40:8089` responden timeout en `/health`;
  - `tailscale status --json` en VPS reporta `PCRick` con `Online=false`;
  - desde este host local tampoco responden `192.168.101.72:8088/8089` ni el workaround `127.0.0.1:28088/28089`;
  - Hyper-V PowerShell local no permite operar la VM por permisos (`Get-VM` sin privilegios suficientes).
- Resultado de Fase 0: **baseline VPS estabilizado y verificado**; queda bloqueado el deploy/check de VM hasta que David restaure acceso operativo (encender VM/Tailscale o habilitar un canal de acceso: Hyper-V, SSH, WinRM o tunnel local funcional).
