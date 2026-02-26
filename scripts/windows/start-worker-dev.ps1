# ============================================================
# start-worker-dev.ps1 — Inicia el worker en modo desarrollo
# ============================================================

$ErrorActionPreference = "Stop"

$AppDir = "C:\openclaw-worker"

if (-not (Test-Path "$AppDir\app.py")) {
    Write-Host "ERROR: $AppDir\app.py no encontrado." -ForegroundColor Red
    Write-Host "Ejecutar primero: .\scripts\windows\install-worker.ps1" -ForegroundColor Yellow
    exit 1
}

# --- Token ---
if (-not $env:WORKER_TOKEN) {
    Write-Host "WARN: WORKER_TOKEN no definido. /run devolverá 500." -ForegroundColor Yellow
    Write-Host "Configurar: `$env:WORKER_TOKEN='MI_TOKEN'" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "=== Iniciando Worker (dev mode) ===" -ForegroundColor Green
Write-Host "Directorio: $AppDir"
Write-Host "URL: http://0.0.0.0:8088"
Write-Host "Ctrl+C para detener"
Write-Host ""

Push-Location $AppDir
try {
    python -m uvicorn app:app --host 0.0.0.0 --port 8088 --log-level info --reload
}
finally {
    Pop-Location
}
