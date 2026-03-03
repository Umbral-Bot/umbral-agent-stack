# Anade LINEAR_API_KEY al entorno del Worker (NSSM) en la VM y reinicia el servicio.
# Ejecutar EN LA VM con PowerShell (como Administrador para nssm restart).
#
# Uso:
#   .\scripts\vm\add_linear_key_to_worker.ps1 -LinearApiKey "lin_xxxxxxxx"
# O con la key en variable de entorno (no dejar en historial):
#   $env:LINEAR_API_KEY = "lin_xxx"; .\scripts\vm\add_linear_key_to_worker.ps1

param(
    [Parameter(Mandatory = $false)]
    [string]$LinearApiKey = $env:LINEAR_API_KEY
)

$ErrorActionPreference = "Stop"
$ServiceName = "openclaw-worker"

if (-not $LinearApiKey) {
    Write-Host "ERROR: Indicar -LinearApiKey 'lin_...' o definir env LINEAR_API_KEY." -ForegroundColor Red
    exit 1
}

Write-Host "=== Anadir LINEAR_API_KEY al Worker (VM) ===" -ForegroundColor Cyan

$current = & nssm get $ServiceName AppEnvironmentExtra 2>$null
if (-not $current) {
    Write-Host "ERROR: No se pudo leer AppEnvironmentExtra (servicio $ServiceName existe? nssm en PATH?)." -ForegroundColor Red
    exit 1
}

$lines = $current -split "`r?`n" | Where-Object { $_.Trim() -ne "" }
$lines = $lines | Where-Object { $_ -notmatch '^LINEAR_API_KEY=' }
$newLines = $lines + "LINEAR_API_KEY=$LinearApiKey"
$newValue = $newLines -join "`n"

& nssm set $ServiceName AppEnvironmentExtra $newValue
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: nssm set AppEnvironmentExtra fallo." -ForegroundColor Red
    exit 1
}
Write-Host "OK: LINEAR_API_KEY anadida al entorno del servicio." -ForegroundColor Green

Write-Host "Reiniciando servicio..." -ForegroundColor Cyan
& nssm restart $ServiceName
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: nssm restart fallo (ejecutar como Administrador?)." -ForegroundColor Red
    exit 1
}
Write-Host "OK: Servicio reiniciado. Rick puede re-probar linear.list_teams." -ForegroundColor Green
