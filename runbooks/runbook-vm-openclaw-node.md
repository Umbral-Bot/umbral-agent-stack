# Runbook: OpenClaw Node — arranque automático en la VM (PCRick)

## Objetivo

Configurar el OpenClaw node en la VM para que se conecte al Gateway de la VPS automáticamente al reiniciar Windows, usando NSSM (igual que el Worker).

## Prerequisitos

- NSSM instalado (`nssm version`)
- OpenClaw CLI instalado y en PATH (`openclaw --version`)
- Token de Gateway sincronizado con el VPS (`gateway.auth.token`)

## Opción A: Servicio NSSM (recomendado)

Ejecutar en **PowerShell como Administrador** en la VM:

```powershell
$ServiceName = "openclaw-node"
$NodeToken = "TU_TOKEN_GATEWAY_AQUI"  # El mismo que gateway.auth.token en la VPS

# Si openclaw es .ps1 (npm), usar powershell; si es .exe, usar ruta directa
$OpenClawPath = (Get-Command openclaw -ErrorAction Stop).Source
$UsePowershell = $OpenClawPath -like "*.ps1"
if ($UsePowershell) {
  $AppExe = "powershell.exe"
  $AppArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$OpenClawPath`" node run --host srv1431451.tail0b266a.ts.net --port 18789 --tls"
} else {
  $AppExe = $OpenClawPath
  $AppArgs = "node run --host srv1431451.tail0b266a.ts.net --port 18789 --tls"
}

# Crear carpeta de logs si no existe
if (-not (Test-Path C:\openclaw-worker)) { New-Item -ItemType Directory C:\openclaw-worker | Out-Null }

# Remover servicio si ya existe
if ((Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
  nssm stop $ServiceName
  nssm remove $ServiceName confirm
}

# Instalar
nssm install $ServiceName $AppExe $AppArgs
nssm set $ServiceName AppDirectory "C:\Users\Rick"
nssm set $ServiceName AppEnvironmentExtra "OPENCLAW_GATEWAY_TOKEN=$NodeToken"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout "C:\openclaw-worker\openclaw-node-stdout.log"
nssm set $ServiceName AppStderr "C:\openclaw-worker\openclaw-node-stderr.log"
nssm set $ServiceName AppStdoutCreationDisposition 4
nssm set $ServiceName AppStderrCreationDisposition 4
nssm set $ServiceName AppRotateFiles 1
nssm set $ServiceName AppRotateBytes 5242880
nssm start $ServiceName
```

**Importante:** Sustituye `TU_TOKEN_GATEWAY_AQUI` por el token real (el mismo que usaste en la VM al probar manualmente, p. ej. `c65704824463d26d45a8042c9eacb936d6aa49c6e3a030b9c2a849a4518d34c0`).

## Verificación

```powershell
nssm status openclaw-node
Get-Content C:\openclaw-worker\openclaw-node-stdout.log -Tail 20
```

En el VPS:

```bash
openclaw devices list
```

PCRick debe aparecer como `Paired` y, cuando el node esté conectado, Rick mostrará el nodo como activo.

## Comandos útiles

```powershell
nssm status openclaw-node
nssm restart openclaw-node
nssm stop openclaw-node
nssm start openclaw-node
```

## Actualizar el token

Si cambias el token en el VPS y necesitas actualizarlo en la VM:

```powershell
nssm set openclaw-node AppEnvironmentExtra "OPENCLAW_GATEWAY_TOKEN=NUEVO_TOKEN"
nssm restart openclaw-node
```

## Opción B: Tarea programada (alternativa)

Si prefieres no usar NSSM, puedes usar una Scheduled Task que se ejecute al inicio de sesión:

1. Crear script `C:\openclaw-worker\start-openclaw-node.ps1`:

```powershell
$env:OPENCLAW_GATEWAY_TOKEN = "TU_TOKEN_GATEWAY_AQUI"
openclaw node run --host srv1431451.tail0b266a.ts.net --port 18789 --tls
```

2. Crear la tarea:

```powershell
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\openclaw-worker\start-openclaw-node.ps1"
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User "Rick"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "OpenClaw Node" -Action $Action -Trigger $Trigger -Settings $Settings
```

3. Probar: `Start-ScheduledTask -TaskName "OpenClaw Node"`

**Nota:** La tarea solo corre cuando Rick inicia sesión. El servicio NSSM corre aunque nadie haya iniciado sesión.
