# ============================================================
# setup-openclaw-service.ps1
# ============================================================
# Instala el worker FastAPI como servicio de Windows usando NSSM.
#
# Pre-requisitos:
#   - NSSM instalado (https://nssm.cc/download)
#     Agregar nssm.exe al PATH o colocarlo en C:\nssm\nssm.exe
#   - Python 3.11+ con fastapi y uvicorn instalados
#   - worker/app.py copiado a C:\openclaw-worker\app.py
# ============================================================

$ErrorActionPreference = "Stop"

$ServiceName = "openclaw-worker"
$AppDir = "C:\openclaw-worker"
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
$Token = "CHANGE_ME_WORKER_TOKEN"

# --- Verificar NSSM ---
$NssmExe = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $NssmExe) {
    Write-Host "ERROR: NSSM no encontrado en PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Instalar NSSM:" -ForegroundColor Yellow
    Write-Host "  1. Descargar desde https://nssm.cc/download"
    Write-Host "  2. Extraer nssm.exe (win64) a un directorio en PATH"
    Write-Host "     Ejemplo: C:\nssm\nssm.exe"
    Write-Host "  3. Agregar al PATH: [Environment]::SetEnvironmentVariable('PATH', `$env:PATH + ';C:\nssm', 'Machine')"
    Write-Host ""
    exit 1
}

# --- Verificar Python ---
if (-not $PythonExe) {
    Write-Host "ERROR: Python no encontrado en PATH." -ForegroundColor Red
    exit 1
}
Write-Host "Python: $PythonExe" -ForegroundColor Cyan

# --- Verificar directorio de trabajo ---
if (-not (Test-Path "$AppDir\app.py")) {
    Write-Host "ERROR: $AppDir\app.py no encontrado." -ForegroundColor Red
    Write-Host "Copiar worker/app.py a $AppDir\app.py primero." -ForegroundColor Yellow
    exit 1
}

# --- Verificar si el servicio ya existe ---
$existing = & $NssmExe status $ServiceName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "WARN: Servicio '$ServiceName' ya existe. Estado: $existing" -ForegroundColor Yellow
    Write-Host "Para reinstalar, primero ejecutar: .\remove-openclaw-service.ps1" -ForegroundColor Yellow
    exit 1
}

# --- Instalar servicio ---
Write-Host "Instalando servicio '$ServiceName'..." -ForegroundColor Green

& $NssmExe install $ServiceName $PythonExe "-m uvicorn app:app --host 0.0.0.0 --port 8088 --log-level info"
& $NssmExe set $ServiceName AppDirectory $AppDir
& $NssmExe set $ServiceName AppEnvironmentExtra "WORKER_TOKEN=$Token"
& $NssmExe set $ServiceName Start SERVICE_AUTO_START
& $NssmExe set $ServiceName AppStdout "$AppDir\service-stdout.log"
& $NssmExe set $ServiceName AppStderr "$AppDir\service-stderr.log"
& $NssmExe set $ServiceName AppStdoutCreationDisposition 4
& $NssmExe set $ServiceName AppStderrCreationDisposition 4
& $NssmExe set $ServiceName AppRotateFiles 1
& $NssmExe set $ServiceName AppRotateBytes 5242880

Write-Host ""
Write-Host "Servicio instalado. Iniciando..." -ForegroundColor Green
& $NssmExe start $ServiceName

Write-Host ""
Write-Host "=== Verificación ===" -ForegroundColor Cyan
& $NssmExe status $ServiceName
Write-Host ""
Write-Host "Puerto 8088:" -ForegroundColor Cyan
netstat -ano | findstr :8088
Write-Host ""
Write-Host "IMPORTANTE: Cambiar CHANGE_ME_WORKER_TOKEN por un token real:" -ForegroundColor Yellow
Write-Host "  nssm set $ServiceName AppEnvironmentExtra 'WORKER_TOKEN=MI_TOKEN_REAL'" -ForegroundColor Yellow
Write-Host "  nssm restart $ServiceName" -ForegroundColor Yellow
