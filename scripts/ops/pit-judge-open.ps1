<#
.SYNOPSIS
    Abre el PIT judge de Mission Control desde Windows (P5.2b).

.DESCRIPTION
    1. Verifica que el túnel SSH al Mission Control de la VPS esté vivo
       (http://127.0.0.1:<Port>/health). Si no responde, ofrece levantarlo:
       ssh -N -L <Port>:127.0.0.1:8089 <SshTarget>  (en ventana aparte).
    2. Pide el MISSION_CONTROL_TOKEN una sola vez (input oculto) y lo copia
       al portapapeles para pegarlo en la página de acceso. El token NUNCA
       se imprime, no viaja por URL y no queda en el historial.
    3. Abre http://127.0.0.1:<Port>/pit/access en el browser default.

    Read-only (ADR-009): este script no toca la VPS más allá del túnel SSH.

.EXAMPLE
    .\scripts\ops\pit-judge-open.ps1
    .\scripts\ops\pit-judge-open.ps1 -Port 18090 -SshTarget vps-umbral
#>
[CmdletBinding()]
param(
    # Puerto local del túnel (8089 local suele estar ocupado → default 18089).
    [int]$Port = 18089,
    # Host SSH (alias de ~/.ssh/config) que llega a la VPS de Umbral.
    [string]$SshTarget = "vps-umbral",
    # Puerto remoto donde escucha Mission Control en la VPS (bind 127.0.0.1).
    [int]$RemotePort = 8089
)

$ErrorActionPreference = "Stop"
$healthUrl = "http://127.0.0.1:$Port/health"
$accessUrl = "http://127.0.0.1:$Port/pit/access"

function Test-McHealth {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 3 -UseBasicParsing
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

Write-Host "PIT judge · Mission Control" -ForegroundColor Cyan
Write-Host "Verificando túnel en $healthUrl ..." -ForegroundColor DarkGray

if (-not (Test-McHealth)) {
    Write-Host "Túnel caído — no llego a Mission Control en 127.0.0.1:$Port." -ForegroundColor Yellow
    $answer = Read-Host "¿Levanto el túnel SSH ahora? (ssh -N -L ${Port}:127.0.0.1:${RemotePort} $SshTarget) [S/n]"
    if ($answer -and $answer.Trim().ToLower().StartsWith("n")) {
        Write-Host "Abortado. Levantá el túnel a mano y volvé a correr el script." -ForegroundColor Red
        exit 1
    }
    Start-Process -FilePath "ssh" -ArgumentList @(
        "-N", "-L", "${Port}:127.0.0.1:${RemotePort}", $SshTarget
    )
    Write-Host "Esperando a que el túnel responda (máx 20 s)..." -ForegroundColor DarkGray
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline -and -not (Test-McHealth)) {
        Start-Sleep -Seconds 2
    }
    if (-not (Test-McHealth)) {
        Write-Host "El túnel sigue sin responder. Revisá la ventana de ssh (clave/alias '$SshTarget')." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Túnel OK ✓" -ForegroundColor Green

# Token una sola vez: oculto en consola, va directo al portapapeles.
$secureToken = Read-Host "Pegá tu MISSION_CONTROL_TOKEN (queda en el portapapeles, no se imprime)" -AsSecureString
$token = [System.Net.NetworkCredential]::new("", $secureToken).Password
if ([string]::IsNullOrWhiteSpace($token)) {
    Write-Host "Sin token — abro igual la página de acceso; pegalo a mano ahí." -ForegroundColor Yellow
} else {
    Set-Clipboard -Value $token
    Write-Host "Token copiado al portapapeles ✓ (pegalo en el form con Ctrl+V)" -ForegroundColor Green
}

Write-Host "Abriendo $accessUrl ..." -ForegroundColor DarkGray
Start-Process $accessUrl
