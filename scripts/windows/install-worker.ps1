# ============================================================
# install-worker.ps1 — Setup inicial del worker en Windows
# ============================================================
# Crea directorio de trabajo, copia archivos, instala deps.
# ============================================================

$ErrorActionPreference = "Stop"

$AppDir = "C:\openclaw-worker"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$WorkerDir = Join-Path $RepoRoot "worker"

Write-Host "=== Instalando Worker ===" -ForegroundColor Green

# --- Crear directorio ---
if (-not (Test-Path $AppDir)) {
    New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
    Write-Host "Creado: $AppDir"
}
else {
    Write-Host "Directorio ya existe: $AppDir"
}

# --- Copiar archivos ---
Write-Host "Copiando archivos del worker..."
Copy-Item "$WorkerDir\app.py" "$AppDir\app.py" -Force
Copy-Item "$WorkerDir\requirements.txt" "$AppDir\requirements.txt" -Force
Write-Host "  app.py -> $AppDir\app.py"
Write-Host "  requirements.txt -> $AppDir\requirements.txt"

# --- Instalar dependencias ---
Write-Host ""
Write-Host "Instalando dependencias Python..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r "$AppDir\requirements.txt"

Write-Host ""
Write-Host "=== Worker instalado ===" -ForegroundColor Green
Write-Host ""
Write-Host "Siguiente paso:" -ForegroundColor Yellow
Write-Host "  1. Configurar token: `$env:WORKER_TOKEN='CHANGE_ME_WORKER_TOKEN'"
Write-Host "  2. Probar en dev: cd $AppDir && python -m uvicorn app:app --host 0.0.0.0 --port 8088"
Write-Host "  3. Instalar servicio: .\scripts\setup-openclaw-service.ps1"
