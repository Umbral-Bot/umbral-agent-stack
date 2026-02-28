# Runbook VM Worker Setup (PCRick)

## Objetivo

Documentar la configuracion actual del Worker en esta VM y dejar pasos reproducibles para levantarlo desde cero usando NSSM.

## Alcance operativo de esta VM

Segun arquitectura (ADR-001), esta VM debe operar como **Execution Plane**:
- SI: `openclaw-worker` (FastAPI) y componentes de ejecucion Windows (PAD/RPA).
- NO: OpenClaw Gateway/Rick como plano de control principal.

Por lo tanto:
- No iniciar ni mantener en produccion un gateway OpenClaw local en esta VM.
- El gateway de control (Rick/OpenClaw) debe correr en la VPS.

## Configuracion actual documentada (captura: 2026-02-27)

Servicio:
- Nombre: `openclaw-worker`
- Estado: `Running`
- Inicio: `Automatic` (`SERVICE_AUTO_START`)
- Cuenta: `LocalSystem`

NSSM (service config):
- `Application`: `C:\Users\Rick\AppData\Local\Programs\Python\Python311\python.exe`
- `AppParameters`: `-m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info`
- `AppDirectory`: `C:\GitHub\umbral-agent-stack`
- `AppStdout`: `C:\openclaw-worker\service-stdout.log`
- `AppStderr`: `C:\openclaw-worker\service-stderr.log`

Variables inyectadas por NSSM (sin secretos):
- `WORKER_TOKEN` (valor oculto)
- `PYTHONPATH` (`C:\GitHub\umbral-agent-stack`)

Red/health:
- Puerto escuchando: `0.0.0.0:8088`
- Firewall rule: `OpenClaw Worker 8088` (Inbound Allow)
- Health local OK: `GET http://localhost:8088/health`

Conclusion:
- El Worker corre desde el repo (`worker.app:app`), no desde `C:\openclaw-worker\app.py`.

## Levantar todo desde cero en esta VM

## 1) Prerrequisitos

En PowerShell (admin cuando aplique):

```powershell
winget install -e --id Python.Python.3.11
winget install -e --id NSSM.NSSM
```

Verificar:

```powershell
python --version
nssm version
```

## 2) Codigo y dependencias

```powershell
cd C:\
if (-not (Test-Path C:\GitHub)) { New-Item -ItemType Directory C:\GitHub | Out-Null }
cd C:\GitHub

# Si no existe el repo:
# git clone <REPO_URL> umbral-agent-stack

cd C:\GitHub\umbral-agent-stack
python -m pip install --upgrade pip
pip install -r worker\requirements.txt
```

## 3) Crear carpeta de logs

```powershell
if (-not (Test-Path C:\openclaw-worker)) { New-Item -ItemType Directory C:\openclaw-worker | Out-Null }
```

## 4) Crear o reconfigurar servicio NSSM

```powershell
$ServiceName = "openclaw-worker"
$PythonExe = "C:\Users\Rick\AppData\Local\Programs\Python\Python311\python.exe"
$RepoDir = "C:\GitHub\umbral-agent-stack"
$CmdArgs = "-m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info"

# Remover si existe (opcional)
if ((Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
  nssm stop $ServiceName
  nssm remove $ServiceName confirm
}

nssm install $ServiceName $PythonExe $CmdArgs
nssm set $ServiceName AppDirectory $RepoDir
nssm set $ServiceName AppEnvironmentExtra "WORKER_TOKEN=CHANGE_ME_WORKER_TOKEN`nPYTHONPATH=$RepoDir"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout "C:\openclaw-worker\service-stdout.log"
nssm set $ServiceName AppStderr "C:\openclaw-worker\service-stderr.log"
nssm set $ServiceName AppStdoutCreationDisposition 4
nssm set $ServiceName AppStderrCreationDisposition 4
nssm set $ServiceName AppRotateFiles 1
nssm set $ServiceName AppRotateBytes 5242880
nssm start $ServiceName
```

Notas:
- Reemplazar `CHANGE_ME_WORKER_TOKEN` por el token real.
- Si se usan tareas Notion, agregar tambien `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, `NOTION_GRANOLA_DB_ID` en `AppEnvironmentExtra`.

## 5) Regla de firewall 8088

```powershell
if (-not (Get-NetFirewallRule -DisplayName "OpenClaw Worker 8088" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "OpenClaw Worker 8088" -Direction Inbound -LocalPort 8088 -Protocol TCP -Action Allow
}
```

## 6) Verificacion

```powershell
nssm status openclaw-worker
Get-NetTCPConnection -LocalPort 8088 -State Listen
Invoke-WebRequest -UseBasicParsing http://localhost:8088/health
```

Prueba `/run`:

```powershell
$token = "CHANGE_ME_WORKER_TOKEN"
$headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }
$body = '{"task":"ping","input":{}}'
Invoke-WebRequest -UseBasicParsing -Method Post -Uri http://localhost:8088/run -Headers $headers -Body $body
```

## 7) Operacion diaria

```powershell
nssm status openclaw-worker
nssm restart openclaw-worker
Get-Content C:\openclaw-worker\service-stdout.log -Tail 50
Get-Content C:\openclaw-worker\service-stderr.log -Tail 50
```

## Checklist rapido de auditoria (sin exponer secretos)

```powershell
nssm get openclaw-worker Application
nssm get openclaw-worker AppParameters
nssm get openclaw-worker AppDirectory
$envExtra = nssm get openclaw-worker AppEnvironmentExtra
$envExtra -split "`r?`n" | Where-Object {$_ -match '^[A-Za-z_][A-Za-z0-9_]*='} | ForEach-Object { ($_ -split '=',2)[0] }
```
