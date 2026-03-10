<#
.SYNOPSIS
    Instalador del Granola Watcher para Windows Task Scheduler.

.DESCRIPTION
    Configura el watcher que monitorea la carpeta de exports de Granola
    y envía automáticamente las transcripciones al Worker local.

    Pasos:
      1. Verifica que Python está instalado
      2. Instala dependencias (requests)
      3. Crea la carpeta GRANOLA_EXPORT_DIR si no existe
      4. Crea el archivo .env con la configuración
      5. Registra la tarea en Windows Task Scheduler (ONLOGON)
      6. Muestra resumen

.NOTES
    No requiere privilegios de administrador.
    Ejecutar desde: C:\GitHub\umbral-agent-stack
#>

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Granola Watcher — Instalador" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------
# 1. Verificar Python
# ---------------------------------------------------------------
Write-Host "[1/6] Verificando Python..." -ForegroundColor Yellow

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python\s+3\.\d+") {
            $pythonCmd = $cmd
            Write-Host "  OK: $ver" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "  ERROR: Python 3 no encontrado. Instálalo desde https://python.org" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------
# 2. Instalar dependencias
# ---------------------------------------------------------------
Write-Host "[2/6] Instalando dependencias..." -ForegroundColor Yellow

try {
    & $pythonCmd -m pip install --quiet --upgrade requests 2>&1 | Out-Null
    Write-Host "  OK: requests instalado" -ForegroundColor Green
} catch {
    Write-Host "  WARN: No se pudo instalar requests — puede que ya esté disponible" -ForegroundColor DarkYellow
}

# ---------------------------------------------------------------
# 3. Crear carpeta de exports
# ---------------------------------------------------------------
Write-Host "[3/6] Configurando carpetas..." -ForegroundColor Yellow

$defaultExportDir = "C:\Granola\exports"
$exportDir = Read-Host "  Carpeta de exports [$defaultExportDir]"
if ([string]::IsNullOrWhiteSpace($exportDir)) { $exportDir = $defaultExportDir }

if (-not (Test-Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
    Write-Host "  Creada: $exportDir" -ForegroundColor Green
} else {
    Write-Host "  Ya existe: $exportDir" -ForegroundColor Green
}

$processedDir = Join-Path $exportDir "processed"
if (-not (Test-Path $processedDir)) {
    New-Item -ItemType Directory -Path $processedDir -Force | Out-Null
}

$granolaRoot = "C:\Granola"
if (-not (Test-Path $granolaRoot)) {
    New-Item -ItemType Directory -Path $granolaRoot -Force | Out-Null
}

# ---------------------------------------------------------------
# 4. Crear archivo .env
# ---------------------------------------------------------------
Write-Host "[4/6] Configurando variables de entorno..." -ForegroundColor Yellow

$defaultWorkerUrl = "http://localhost:8088"
$workerUrl = Read-Host "  Worker URL [$defaultWorkerUrl]"
if ([string]::IsNullOrWhiteSpace($workerUrl)) { $workerUrl = $defaultWorkerUrl }

$workerToken = Read-Host "  Worker Token (requerido)"
while ([string]::IsNullOrWhiteSpace($workerToken)) {
    Write-Host "  El token es requerido." -ForegroundColor Red
    $workerToken = Read-Host "  Worker Token"
}

$notionDbId = Read-Host "  Notion Database ID (opcional, Enter para omitir)"

$defaultPollInterval = "5"
$pollInterval = Read-Host "  Poll interval en segundos [$defaultPollInterval]"
if ([string]::IsNullOrWhiteSpace($pollInterval)) { $pollInterval = $defaultPollInterval }

$envContent = @"
# Granola Watcher — Configuración
# Generado por setup_granola_watcher.ps1 el $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
GRANOLA_EXPORT_DIR=$exportDir
GRANOLA_WORKER_URL=$workerUrl
GRANOLA_WORKER_TOKEN=$workerToken
GRANOLA_NOTION_DATABASE_ID=$notionDbId
GRANOLA_POLL_INTERVAL=$pollInterval
"@

$envPath = "C:\Granola\.env"
Set-Content -Path $envPath -Value $envContent -Encoding UTF8
Write-Host "  Guardado: $envPath" -ForegroundColor Green

# ---------------------------------------------------------------
# 5. Registrar en Task Scheduler
# ---------------------------------------------------------------
Write-Host "[5/6] Registrando en Task Scheduler..." -ForegroundColor Yellow

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$watcherScript = Join-Path $repoRoot "scripts\vm\granola_watcher.py"

if (-not (Test-Path $watcherScript)) {
    $watcherScript = Join-Path $PSScriptRoot "granola_watcher.py"
}

$launcherScript = Join-Path $repoRoot "scripts\vm\start_granola_watcher_hidden.ps1"
if (-not (Test-Path $launcherScript)) {
    $launcherScript = Join-Path $PSScriptRoot "start_granola_watcher_hidden.ps1"
}

$taskAction = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcherScript`""
$taskName = "GranolaWatcher"

try {
    schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
} catch {}

try {
    schtasks /Create /TN $taskName `
        /TR $taskAction `
        /SC ONLOGON /RU $env:USERNAME /F 2>&1 | Out-Null
    Write-Host "  OK: Tarea '$taskName' registrada (inicio al hacer login)" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: No se pudo registrar la tarea: $_" -ForegroundColor Red
    Write-Host "  Puedes ejecutar manualmente: $taskAction" -ForegroundColor DarkYellow
}

# ---------------------------------------------------------------
# 6. Resumen
# ---------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Instalación completada" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Carpeta monitoreada : $exportDir" -ForegroundColor White
Write-Host "  Archivos procesados : $processedDir" -ForegroundColor White
Write-Host "  Worker URL          : $workerUrl" -ForegroundColor White
Write-Host "  Poll interval       : ${pollInterval}s" -ForegroundColor White
Write-Host "  Archivo .env        : $envPath" -ForegroundColor White
Write-Host "  Task Scheduler      : $taskName (ONLOGON)" -ForegroundColor White
Write-Host "  Log file            : C:\Granola\watcher.log" -ForegroundColor White
Write-Host ""
Write-Host "  Para probar: .\scripts\vm\test_granola_watcher.ps1" -ForegroundColor Yellow
Write-Host "  Para desinstalar: .\scripts\vm\uninstall_granola_watcher.ps1" -ForegroundColor Yellow
Write-Host ""
