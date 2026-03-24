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
    [string]$BootstrapSshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$BootstrapKnownHostsPath = "$env:USERPROFILE\.ssh\known_hosts",
    [string]$SshKeyPath = "C:\openclaw-worker\.ssh\id_ed25519",
    [string]$KnownHostsPath = "C:\openclaw-worker\.ssh\known_hosts",
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
$SshKeygenExe = Get-RequiredCommand "ssh-keygen.exe"
$OpenClawExe = Get-RequiredCommand "openclaw"
$IcaclsExe = Get-RequiredCommand "icacls.exe"

if ([string]::IsNullOrWhiteSpace($GatewayToken)) {
    if (Test-Path $GatewayTokenFile) {
        $cachedToken = Get-Content -Path $GatewayTokenFile -Raw -ErrorAction Stop
        if (-not [string]::IsNullOrWhiteSpace($cachedToken)) {
            $GatewayToken = $cachedToken.Trim()
        }
    }
}

if ([string]::IsNullOrWhiteSpace($GatewayToken)) {
    throw "GatewayToken no puede quedar vacio y tampoco existe '$GatewayTokenFile'."
}

if (-not (Test-Path $BootstrapSshKeyPath)) {
    throw "No se encontro la clave SSH bootstrap en '$BootstrapSshKeyPath'."
}

New-Item -ItemType Directory -Path (Split-Path -Parent $KnownHostsPath) -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

if ((-not (Test-Path $KnownHostsPath)) -and (Test-Path $BootstrapKnownHostsPath)) {
    Copy-Item -Path $BootstrapKnownHostsPath -Destination $KnownHostsPath -Force
}

if (-not (Test-Path $SshKeyPath)) {
    Write-Host "Generando clave SSH dedicada para el servicio..." -ForegroundColor Green
    & $SshKeygenExe "-t" "ed25519" "-f" $SshKeyPath "-N" "" "-C" "pcrick-openclaw-service"
    if ($LASTEXITCODE -ne 0) {
        throw "ssh-keygen fallo al crear '$SshKeyPath'."
    }
}

if (-not (Test-Path "$SshKeyPath.pub")) {
    throw "No se encontro la clave publica del servicio en '$SshKeyPath.pub'."
}

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
Write-Host "Bootstrap SSH key: $BootstrapSshKeyPath"
Write-Host "SSH key: $SshKeyPath"
Write-Host "known_hosts: $KnownHostsPath"
Write-Host ""

Write-Host "Probando SSH bootstrap sin interaccion..." -ForegroundColor Green
& $SshExe "-i" $BootstrapSshKeyPath "-o" "BatchMode=yes" "-o" "IdentitiesOnly=yes" "-o" "StrictHostKeyChecking=accept-new" "-o" "UserKnownHostsFile=$BootstrapKnownHostsPath" $GatewaySshTarget "exit"
if ($LASTEXITCODE -ne 0) {
    throw "La prueba SSH bootstrap sin interaccion fallo. Autoriza la clave publica en la VPS antes de continuar."
}

Write-Host "Ajustando ACLs estrictas para la clave del servicio..." -ForegroundColor Green
& $IcaclsExe (Split-Path -Parent $SshKeyPath) "/inheritance:r" "/grant:r" "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron fijar ACLs sobre '$(Split-Path -Parent $SshKeyPath)'."
}
& $IcaclsExe $SshKeyPath "/inheritance:r" "/grant:r" "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo otorgar lectura a SYSTEM sobre '$SshKeyPath'."
}
& $IcaclsExe "$SshKeyPath.pub" "/inheritance:r" "/grant:r" "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron fijar ACLs sobre '$SshKeyPath.pub'."
}
& $IcaclsExe $KnownHostsPath "/inheritance:r" "/grant:r" "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron fijar ACLs sobre '$KnownHostsPath'."
}
Set-Content -Path $GatewayTokenFile -Value $GatewayToken -NoNewline
& $IcaclsExe $GatewayTokenFile "/grant" "SYSTEM:R" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo otorgar lectura a SYSTEM sobre '$GatewayTokenFile'."
}

Write-Host "Autorizando clave del servicio en la VPS..." -ForegroundColor Green
Get-Content "$SshKeyPath.pub" | & $SshExe "-i" $BootstrapSshKeyPath "-o" "BatchMode=yes" "-o" "IdentitiesOnly=yes" "-o" "StrictHostKeyChecking=accept-new" "-o" "UserKnownHostsFile=$BootstrapKnownHostsPath" $GatewaySshTarget "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys && sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys"
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo autorizar la clave del servicio en la VPS."
}

Write-Host "Probando SSH del servicio sin interaccion..." -ForegroundColor Green
& $SshExe "-i" $SshKeyPath "-o" "BatchMode=yes" "-o" "IdentitiesOnly=yes" "-o" "StrictHostKeyChecking=accept-new" "-o" "UserKnownHostsFile=$KnownHostsPath" $GatewaySshTarget "exit"
if ($LASTEXITCODE -ne 0) {
    throw "La prueba SSH del servicio fallo. Revisa ACLs o authorized_keys."
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
