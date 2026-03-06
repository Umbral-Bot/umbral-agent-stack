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

## Configuracion actual documentada (captura: 2026-02-28)

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
- Opcional para `windows.open_notepad`: `OPENCLAW_NOTEPAD_RUN_AS_USER` (ej. `pcrick\rick`) y `OPENCLAW_NOTEPAD_RUN_AS_PASSWORD` (contraseña del usuario), para que el Bloc de notas se abra en la sesión del usuario al iniciar sesión; si no se definen, la tarea se ejecuta en sesión 0 y no se ve.

Red/health:
- Puerto escuchando: `0.0.0.0:8088`
- Firewall rule: `OpenClaw Worker 8088` (Inbound Allow)
- Health local OK: `GET http://localhost:8088/health`

Conclusion:
- El Worker corre desde el repo (`worker.app:app`), no desde `C:\openclaw-worker\app.py`.

Actualizacion 2026-02-28:
- Backup del prototipo legado confirmado en `C:\openclaw-worker-backup-2026-02-28\`.
- `GET http://localhost:8088/health` confirma tareas: `ping`, `notion.*`, `windows.pad.run_flow`.
- Prueba `POST /run` con task `ping` OK.
- PAD no instalado en esta VM (`Test-Path "C:\Program Files (x86)\Power Automate Desktop\PAD.Console.Host.exe"` -> `False`).

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
- Si se usan tareas Notion, agregar `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`; para pipeline Granola también `NOTION_GRANOLA_DB_ID` (usa la misma `NOTION_API_KEY` Rick) en `AppEnvironmentExtra`.
- Para Linear (`linear.list_teams`, `linear.create_issue`): agregar `LINEAR_API_KEY` en `AppEnvironmentExtra`. Script helper: `scripts/vm/add_linear_key_to_worker.ps1 -LinearApiKey "lin_..."` (ejecutar en la VM, luego `nssm restart openclaw-worker` está incluido en el script).
- Para que la tarea `windows.open_notepad` abra el Bloc en la sesión del usuario (no en sesión 0), agregar en `AppEnvironmentExtra`: `OPENCLAW_NOTEPAD_RUN_AS_USER=pcrick\rick` y `OPENCLAW_NOTEPAD_RUN_AS_PASSWORD=<contraseña>` (misma línea, separadas por `\n`).

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

## 7) Actualizar Worker tras merge (p. ej. windows.fs.*, write_bytes_b64)

Si se ha mergeado código nuevo (p. ej. tareas `windows.fs.ensure_dirs`, `windows.fs.list`, `windows.fs.write_bytes_b64`, etc.), el Worker en la VM debe usar ese código. Si `/health` no muestra `windows.fs.ensure_dirs` en `tasks_registered`:

1. **Comprobar NSSM:** el servicio debe tener `AppDirectory` = `C:\GitHub\umbral-agent-stack` (no `C:\openclaw-worker` ni otra ruta). Ver: `nssm get openclaw-worker AppDirectory`. Si es distinto: `nssm set openclaw-worker AppDirectory C:\GitHub\umbral-agent-stack`.
2. **Actualizar y reiniciar** (en la VM, PowerShell como Administrador):

```powershell
cd C:\GitHub\umbral-agent-stack
git pull origin main
nssm restart openclaw-worker
```

O ejecutar el script de verificación (hace pull, restart y comprueba `/health`):

```powershell
cd C:\GitHub\umbral-agent-stack
.\scripts\vm\update_worker_and_verify.ps1
```

3. **Comprobar:** `Invoke-RestMethod http://localhost:8088/health` debe incluir en `tasks_registered` las tareas `windows.fs.ensure_dirs`, `windows.fs.list`, etc.

## 8) Worker como usuario (acceso a G:\ y Drive)

Por defecto el servicio corre como **LocalSystem**, que no tiene acceso a unidades montadas "por usuario" como Google Drive en `G:\`. Si `windows.fs.ensure_dirs` (o list/read_text/write_text) en `G:\Mi unidad\...` devuelve `[WinError 5] Acceso denegado`, hay que hacer que el servicio corra con el **usuario que tiene Drive montado** (ej. Rick).

**En la VM, PowerShell como Administrador:**

1. Abrir NSSM para el servicio:
   ```powershell
   nssm edit openclaw-worker
   ```
2. Pestaña **"Log on"** → marcar **"This account"**.
3. Cuenta: el usuario de la VM (ej. `.\Rick` o `pcrick\rick`). Contraseña: la del usuario.
4. **OK** y reiniciar:
   ```powershell
   nssm restart openclaw-worker
   ```

**Por línea de comandos** (sustituir usuario y contraseña):

```powershell
# Ejemplo: cuenta local Rick en máquina PCRick
nssm set openclaw-worker ObjectName ".\Rick" "CONTRASEÑA_DE_RICK"
nssm restart openclaw-worker
```

Si la VM está en dominio: `nssm set openclaw-worker ObjectName "pcrick\rick" "CONTRASEÑA"`.

Comprobar que el Worker arrancó y que puede acceder a G:\:

```powershell
Invoke-RestMethod http://localhost:8088/health
# Luego Rick puede probar desde la VPS: windows.fs.ensure_dirs en G:\Mi unidad\Rick-David\...
```

**Nota:** Los logs siguen en `C:\openclaw-worker\`. Si el servicio no arranca al cambiar de cuenta, revisar que el usuario tenga permisos sobre esa carpeta y sobre `C:\GitHub\umbral-agent-stack`.

## 9) Operacion diaria

```powershell
nssm status openclaw-worker
nssm restart openclaw-worker
Get-Content C:\openclaw-worker\service-stdout.log -Tail 50
Get-Content C:\openclaw-worker\service-stderr.log -Tail 50
```

Nota:
- `Restart-Service`/`nssm restart` requiere PowerShell elevado (Administrador). Sin elevacion se obtiene `Acceso denegado`.

## 9.1) Si el servicio queda en SERVICE_PAUSED tras restart

**Arreglo rápido (en la VM, PowerShell como Administrador):** ejecutar el script de reparación (instala deps, para el servicio, lo inicia y comprueba health):

```powershell
cd C:\GitHub\umbral-agent-stack
.\scripts\vm\fix_worker_service.ps1
```

Si prefieres hacerlo a mano, pasos:

1. **Ver el error real** (en la VM, PowerShell como Administrador):

   ```powershell
   Get-Content C:\openclaw-worker\service-stderr.log -Tail 80
   Get-Content C:\openclaw-worker\service-stdout.log -Tail 30
   ```

   En `service-stderr.log` suele aparecer el traceback de Python (ModuleNotFoundError, variable de entorno faltante, etc.).

2. **Probar arranque manual** con el mismo entorno que NSSM (sustituir el token por el real):

   ```powershell
   cd C:\GitHub\umbral-agent-stack
   $env:PYTHONPATH = "C:\GitHub\umbral-agent-stack"
   $env:WORKER_TOKEN = "EL_MISMO_QUE_NSSM"
   & "C:\Users\Rick\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info
   ```

   Si falla, el mensaje en consola es el que hay que corregir (dependencia, env, etc.).

3. **Intentar continuar el servicio** (por si NSSM lo dejó en pausa):

   ```powershell
   nssm continue openclaw-worker
   nssm status openclaw-worker
   ```

4. **Si sigue mal:** parar, corregir la causa (pip install, env en NSSM, etc.) y arrancar de nuevo:

   ```powershell
   nssm stop openclaw-worker
   # ... corregir según stderr ...
   nssm start openclaw-worker
   ```

## 10) Checklist rapido de auditoria (sin exponer secretos)

```powershell
nssm get openclaw-worker Application
nssm get openclaw-worker AppParameters
nssm get openclaw-worker AppDirectory
$envExtra = nssm get openclaw-worker AppEnvironmentExtra
$envExtra -split "`r?`n" | Where-Object {$_ -match '^[A-Za-z_][A-Za-z0-9_]*='} | ForEach-Object { ($_ -split '=',2)[0] }
```
