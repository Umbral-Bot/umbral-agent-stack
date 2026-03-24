# Instala la persistencia real del node OpenClaw en la VM Windows (PCRick)
# para un gateway remoto que corre en loopback en la VPS.
#
# Flujo:
# 1. crea/actualiza un servicio NSSM que mantiene un tunel SSH local:
#      127.0.0.1:<LocalTunnelPort> -> VPS 127.0.0.1:<GatewayPort>
# 2. usa el CLI oficial `openclaw node install` apuntando al extremo local del tunel
# 3. reinicia el node y deja comandos de verificacion
#
# Ejecutar en la VM con PowerShell. Recomendado: PowerShell como Administrador
# si NSSM o el servicio del node requieren elevacion.

[CmdletBinding()]
param(
    [string]$GatewayToken = "",

    [string]$GatewaySshTarget = "rick@187.77.60.169",
    [string]$DisplayName = "PCRick",
    [string]$TunnelServiceName = "openclaw-node-tunnel",
    [string]$LogDir = "C:\openclaw-worker",
    [string]$GatewayTokenFile = "C:\openclaw-worker\openclaw-gateway-token",
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$KnownHostsPath = "$env:USERPROFILE\.ssh\known_hosts",
    [int]$LocalTunnelPort = 18790,
    [int]$GatewayPort = 18789
)

$ErrorActionPreference = "Stop"

function Get-RequiredCommand {
    param([string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "No se encontro '$Name' en PATH."
    }
    return $command.Source
}

function Invoke-Nssm {
    param(
        [string[]]$Arguments,
        [switch]$AllowFailure
    )
    & $script:NssmExe @Arguments
    if (-not $AllowFailure -and $LASTEXITCODE -ne 0) {
        throw "NSSM fallo: $($Arguments -join ' ')"
    }
}

function Test-LocalTunnel {
    param([int]$Port)
    try {
        $tcp = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
        return [bool]$tcp.TcpTestSucceeded
    } catch {
        return $false
    }
}

$NssmExe = Get-RequiredCommand "nssm"
$SshExe = Get-RequiredCommand "ssh.exe"
$OpenClawExe = Get-RequiredCommand "openclaw"
$IcaclsExe = Get-RequiredCommand "icacls.exe"

if ([string]::IsNullOrWhiteSpace($GatewayToken)) {
    if (Test-Path $GatewayTokenFile) {
        $GatewayToken = (Get-Content -Path $GatewayTokenFile -Raw -ErrorAction Stop).Trim()
    }
}

if ([string]::IsNullOrWhiteSpace($GatewayToken)) {
    throw "GatewayToken no puede quedar vacio y tampoco existe '$GatewayTokenFile'."
}

if (-not (Test-Path $SshKeyPath)) {
    throw "No se encontro la clave SSH en '$SshKeyPath'."
}

New-Item -ItemType Directory -Path (Split-Path -Parent $KnownHostsPath) -Force | Out-Null

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$stdoutLog = Join-Path $LogDir "openclaw-node-tunnel-stdout.log"
$stderrLog = Join-Path $LogDir "openclaw-node-tunnel-stderr.log"

$tunnelArgs = @(
    "-i", $SshKeyPath,
    "-o", "ExitOnForwardFailure=yes",
    "-o", "BatchMode=yes",
    "-o", "IdentitiesOnly=yes",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "UserKnownHostsFile=$KnownHostsPath",
    "-N",
    "-L", "$LocalTunnelPort`:127.0.0.1`:$GatewayPort",
    $GatewaySshTarget
)

Write-Host "=== OpenClaw node persistence (PCRick) ===" -ForegroundColor Cyan
Write-Host "Tunnel target: $GatewaySshTarget"
Write-Host "Local tunnel: 127.0.0.1:$LocalTunnelPort -> VPS 127.0.0.1:$GatewayPort"
Write-Host "Gateway token file: $GatewayTokenFile"
Write-Host "SSH key: $SshKeyPath"
Write-Host "known_hosts: $KnownHostsPath"
Write-Host ""

Write-Host "Probando SSH sin interaccion..." -ForegroundColor Green
& $SshExe "-i" $SshKeyPath "-o" "BatchMode=yes" "-o" "IdentitiesOnly=yes" "-o" "StrictHostKeyChecking=accept-new" "-o" "UserKnownHostsFile=$KnownHostsPath" $GatewaySshTarget "exit"
if ($LASTEXITCODE -ne 0) {
    throw "La prueba SSH sin interaccion fallo. Autoriza la clave publica en la VPS antes de continuar."
}

Write-Host "Ajustando ACLs para que el servicio pueda leer la clave SSH..." -ForegroundColor Green
& $IcaclsExe $SshKeyPath "/grant" "SYSTEM:R" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo otorgar lectura a SYSTEM sobre '$SshKeyPath'."
}
& $IcaclsExe $KnownHostsPath "/grant" "SYSTEM:R" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo otorgar lectura a SYSTEM sobre '$KnownHostsPath'."
}
Set-Content -Path $GatewayTokenFile -Value $GatewayToken -NoNewline
& $IcaclsExe $GatewayTokenFile "/grant" "SYSTEM:R" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo otorgar lectura a SYSTEM sobre '$GatewayTokenFile'."
}

# Reinstalar el servicio de tunel para asegurar args y logs correctos.
Invoke-Nssm -Arguments @("stop", $TunnelServiceName) -AllowFailure
Invoke-Nssm -Arguments @("remove", $TunnelServiceName, "confirm") -AllowFailure
Invoke-Nssm -Arguments @("install", $TunnelServiceName, $SshExe, ($tunnelArgs -join " "))
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "AppDirectory", $env:USERPROFILE)
Invoke-Nssm -Arguments @(
    "set",
    $TunnelServiceName,
    "AppEnvironmentExtra",
    "HOME=$env:USERPROFILE",
    "USERPROFILE=$env:USERPROFILE",
    "HOMEDRIVE=$env:HOMEDRIVE",
    "HOMEPATH=$env:HOMEPATH"
)
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "Start", "SERVICE_AUTO_START")
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "AppStdout", $stdoutLog)
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "AppStderr", $stderrLog)
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "AppStdoutCreationDisposition", "4")
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "AppStderrCreationDisposition", "4")
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "AppRotateFiles", "1")
Invoke-Nssm -Arguments @("set", $TunnelServiceName, "AppRotateBytes", "5242880")

Write-Host "Iniciando servicio de tunel: $TunnelServiceName" -ForegroundColor Green
Invoke-Nssm -Arguments @("start", $TunnelServiceName)
Start-Sleep -Seconds 4

if (-not (Test-LocalTunnel -Port $LocalTunnelPort)) {
    Write-Host "ERROR: el tunel local no responde en 127.0.0.1:$LocalTunnelPort" -ForegroundColor Red
    Write-Host "Revisa logs:" -ForegroundColor Yellow
    Write-Host "  $stdoutLog"
    Write-Host "  $stderrLog"
    exit 1
}

$env:OPENCLAW_GATEWAY_TOKEN = $GatewayToken

Write-Host "Instalando servicio oficial del node OpenClaw..." -ForegroundColor Green
& $OpenClawExe node install --host 127.0.0.1 --port $LocalTunnelPort --display-name $DisplayName --force
if ($LASTEXITCODE -ne 0) {
    throw "openclaw node install fallo."
}

Write-Host "Reiniciando node OpenClaw..." -ForegroundColor Green
& $OpenClawExe node restart
if ($LASTEXITCODE -ne 0) {
    throw "openclaw node restart fallo."
}

Write-Host ""
Write-Host "=== Verificacion local ===" -ForegroundColor Cyan
& $OpenClawExe node status

Write-Host ""
Write-Host "=== Siguiente paso en la VPS ===" -ForegroundColor Yellow
Write-Host "1. openclaw devices list"
Write-Host "2. Si aparece nueva solicitud, aprobarla:"
Write-Host "   openclaw devices approve <requestId>"
Write-Host "3. Confirmar estado del node:"
Write-Host "   openclaw nodes status"
Write-Host ""
Write-Host "Si PCRick ya estaba paired, normalmente bastara con verificar que pase de 'paired · disconnected' a 'connected'." -ForegroundColor Gray
