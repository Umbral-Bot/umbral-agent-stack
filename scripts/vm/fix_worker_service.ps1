# Repara el servicio openclaw-worker en la VM: dependencias, stop limpio y start.
# Ejecutar en la VM como Administrador: PowerShell -ExecutionPolicy Bypass -File .\scripts\vm\fix_worker_service.ps1
# O: cd C:\GitHub\umbral-agent-stack ; .\scripts\vm\fix_worker_service.ps1

$ErrorActionPreference = "Stop"
$RepoDir = "C:\GitHub\umbral-agent-stack"
$ServiceName = "openclaw-worker"
$HealthUrl = "http://localhost:8088/health"

Write-Host "=== Fix Worker service (VM) ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $RepoDir)) {
    Write-Host "ERROR: No existe $RepoDir." -ForegroundColor Red
    exit 1
}
Push-Location $RepoDir

# 1) Dependencias del worker (evita ModuleNotFoundError: requests, etc.)
Write-Host "1. Instalando dependencias del worker..." -ForegroundColor Cyan
& python -m pip install -q -r worker\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install fallo." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "   OK." -ForegroundColor Green

# 2) Parar el servicio (si esta PAUSED o RUNNING, forzar stop)
Write-Host "2. Parando servicio $ServiceName..." -ForegroundColor Cyan
& nssm stop $ServiceName 2>$null
$maxWait = 15
$waited = 0
do {
    Start-Sleep -Seconds 2
    $waited += 2
    $status = & nssm status $ServiceName 2>$null
    if ($status -match "STOPPED" -or $status -match "The service is not running") {
        Write-Host "   Servicio detenido." -ForegroundColor Green
        break
    }
    Write-Host "   Estado: $status (esperando...)" -ForegroundColor Gray
} while ($waited -lt $maxWait)
if ($waited -ge $maxWait) {
    Write-Host "   AVISO: El servicio no quedo en STOPPED tras ${maxWait}s. Intentando start igualmente." -ForegroundColor Yellow
}

# 3) Iniciar el servicio
Write-Host "3. Iniciando servicio $ServiceName..." -ForegroundColor Cyan
& nssm start $ServiceName
if ($LASTEXITCODE -ne 0) {
    Write-Host "   AVISO: nssm start devolvio error. Comprobar: nssm status $ServiceName" -ForegroundColor Yellow
}
Start-Sleep -Seconds 5
$status = & nssm status $ServiceName 2>$null
Write-Host "   Estado: $status" -ForegroundColor $(if ($status -match "RUNNING") { "Green" } else { "Yellow" })

# 4) Health check
Write-Host "4. Comprobando /health..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5
    if ($health.ok -eq $true) {
        Write-Host "   OK: Worker respondiendo. tasks_registered: $($health.tasks_registered.Count) tareas." -ForegroundColor Green
        Pop-Location
        exit 0
    }
} catch {
    Write-Host "   ERROR: No se pudo conectar a $HealthUrl - $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Revisar logs: Get-Content C:\openclaw-worker\service-stderr.log -Tail 50" -ForegroundColor Yellow
    Pop-Location
    exit 1
}
Pop-Location
exit 0
