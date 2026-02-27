# ============================================================
# remove-openclaw-service.ps1
# ============================================================
# Remueve el servicio openclaw-worker de Windows (NSSM).
# ============================================================

$ErrorActionPreference = "Stop"

$ServiceName = "openclaw-worker"

$NssmExe = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $NssmExe) {
    Write-Host "ERROR: NSSM no encontrado en PATH." -ForegroundColor Red
    exit 1
}

# --- Detener servicio ---
Write-Host "Deteniendo servicio '$ServiceName'..." -ForegroundColor Yellow
& $NssmExe stop $ServiceName 2>&1 | Out-Null

# --- Remover servicio ---
Write-Host "Removiendo servicio '$ServiceName'..." -ForegroundColor Yellow
& $NssmExe remove $ServiceName confirm

Write-Host ""
Write-Host "Servicio '$ServiceName' removido." -ForegroundColor Green
Write-Host ""
Write-Host "Nota: Los logs en C:\openclaw-worker\ no se eliminan automáticamente." -ForegroundColor Cyan
