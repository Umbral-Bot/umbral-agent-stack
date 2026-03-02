# Runbook: Worker interactivo (sesión 1) en VM

## Objetivo

Levantar el Worker interactivo en la sesión del usuario (Rick) para que la VPS pueda ejecutar tareas con interfaz gráfica (Notepad, PAD, etc.) visibles en pantalla.

## Alcance

- **Worker sesión 0** (servicio): puerto 8088, ya configurado con NSSM.
- **Worker sesión 1** (interactivo): puerto 8089, corre bajo Rick al iniciar sesión.

## Prerrequisitos

- Repo en `C:\GitHub\umbral-agent-stack`.
- Python 3.11 instalado.
- WORKER_TOKEN definido (mismo que el servicio).

## 0) Actualizar Worker en la VM (una vez)

En la VM: `cd C:\GitHub\umbral-agent-stack`, `git pull origin main`, `nssm restart openclaw-worker`.  
Luego desde la VPS se puede crear el token y arrancar el interactivo con:

```bash
bash scripts/setup_interactive_worker_from_vps.sh
```

## 1) Crear Tarea programada al logon de Rick

Ejecutar en PowerShell **como Administrador**:

```powershell
$TaskName = "UmbralInteractiveWorker"
$PythonExe = "C:\Users\Rick\AppData\Local\Programs\Python\Python311\python.exe"
$RepoDir = "C:\GitHub\umbral-agent-stack"
$BatPath = "$RepoDir\scripts\vm\start_interactive_worker.bat"

schtasks /create /tn $TaskName /tr $BatPath /sc onlogon /ru "pcrick\rick" /rp "CONTRASEÑA_DE_RICK" /f
```

Sustituir `CONTRASEÑA_DE_RICK` por la contraseña real. Si falla con error de SID, probar formato `.\rick`.

## 2) Token para el Worker interactivo

El .bat lee `WORKER_TOKEN` desde `C:\openclaw-worker\worker_token` si existe (una línea con el token).

En la VM (una vez):

```powershell
if (-not (Test-Path C:\openclaw-worker)) { New-Item -ItemType Directory C:\openclaw-worker -Force }
# Pegar el mismo token que usa el servicio NSSM (no commitear):
Set-Content -Path C:\openclaw-worker\worker_token -Value "EL_MISMO_TOKEN_QUE_NSSM"
```

Alternativa: `setx WORKER_TOKEN "valor"` y cerrar sesión/volver a entrar.

## 3) Regla de firewall para 8089

```powershell
New-NetFirewallRule -DisplayName "OpenClaw Worker Interactive 8089" -Direction Inbound -LocalPort 8089 -Protocol TCP -Action Allow
```

## 4) Verificación

Con Rick logueado en la VM:

```powershell
Invoke-RestMethod http://localhost:8089/health
```

Debe devolver `{"ok": true, ...}`.

Desde la VPS:

```bash
WORKER_URL=http://100.109.16.40:8089 WORKER_TOKEN=xxx python3 scripts/run_worker_task.py ping
```

O añadir en `~/.config/openclaw/env` (VPS):

```
WORKER_URL_VM_INTERACTIVE=http://100.109.16.40:8089
```

Y ejecutar:

```bash
python3 scripts/run_worker_task.py windows.open_notepad "hola" --session interactive --run-now
```

## 5) Env en VPS

En `~/.config/openclaw/env`:

```
WORKER_URL_VM=http://100.109.16.40:8088
WORKER_URL_VM_INTERACTIVE=http://100.109.16.40:8089
WORKER_TOKEN=xxx
```

## Referencias

- Control dual: `docs/32-vps-vm-dual-session-control.md`
- Worker setup: `runbooks/runbook-vm-worker-setup.md`
