<#
.SYNOPSIS
    Configura el intake seguro de Granola -> raw desde la VM Windows.

.DESCRIPTION
    Registra una tarea programada que ejecuta el runner VM raw intake.
    Este flujo usa el cache/API local de Granola y llama al Worker por /run.

    No hace:
      - raw -> canonical
      - promoción a session_capitalizable
      - buckets ambiguos sin revisión explícita
#>

$ErrorActionPreference = "Stop"

function Upsert-EnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $lines = @()
    if (Test-Path $Path) {
        $lines = Get-Content $Path -Encoding UTF8
    }

    $updated = $false
    $result = foreach ($line in $lines) {
        if ($line -match "^\s*${Key}=") {
            $updated = $true
            "${Key}=${Value}"
        } else {
            $line
        }
    }

    if (-not $updated) {
        $result += "${Key}=${Value}"
    }

    Set-Content -Path $Path -Value $result -Encoding UTF8
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Granola VM Raw Intake - Instalador" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python\s+3\.\d+") {
            $pythonCmd = $cmd
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    throw "Python 3 no encontrado."
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$launcherScript = Join-Path $repoRoot "scripts\vm\start_granola_vm_raw_intake_hidden.ps1"
if (-not (Test-Path $launcherScript)) {
    throw "No se encontró el launcher: $launcherScript"
}

$granolaRoot = "C:\Granola"
$envPath = Join-Path $granolaRoot ".env"
$reportDir = Join-Path $granolaRoot "reports"
New-Item -ItemType Directory -Force -Path $granolaRoot | Out-Null
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

$defaultCachePath = Join-Path $env:APPDATA "Granola\cache-v6.json"
$cachePath = Read-Host "  Granola cache path [$defaultCachePath]"
if ([string]::IsNullOrWhiteSpace($cachePath)) { $cachePath = $defaultCachePath }

$defaultWorkerUrl = "http://127.0.0.1:8088"
$workerUrl = Read-Host "  Worker URL local [$defaultWorkerUrl]"
if ([string]::IsNullOrWhiteSpace($workerUrl)) { $workerUrl = $defaultWorkerUrl }

$workerToken = Read-Host "  Worker Token (requerido)"
while ([string]::IsNullOrWhiteSpace($workerToken)) {
    Write-Host "  El Worker Token es requerido." -ForegroundColor Red
    $workerToken = Read-Host "  Worker Token"
}

$defaultBucket = "batch1_recent_unique"
$bucket = Read-Host "  Bucket seguro por defecto [$defaultBucket]"
if ([string]::IsNullOrWhiteSpace($bucket)) { $bucket = $defaultBucket }

$defaultMaxItems = "5"
$maxItems = Read-Host "  Máximo de reuniones por corrida [$defaultMaxItems]"
if ([string]::IsNullOrWhiteSpace($maxItems)) { $maxItems = $defaultMaxItems }

$defaultHours = "4"
$hours = Read-Host "  Cadencia de la tarea programada en horas [$defaultHours]"
if ([string]::IsNullOrWhiteSpace($hours)) { $hours = $defaultHours }

if (-not (Test-Path $envPath)) {
    Set-Content -Path $envPath -Value @(
        "# Granola VM raw intake"
    ) -Encoding UTF8
}

Upsert-EnvValue -Path $envPath -Key "GRANOLA_CACHE_PATH" -Value $cachePath
Upsert-EnvValue -Path $envPath -Key "GRANOLA_WORKER_URL" -Value $workerUrl
Upsert-EnvValue -Path $envPath -Key "GRANOLA_WORKER_TOKEN" -Value $workerToken
Upsert-EnvValue -Path $envPath -Key "GRANOLA_VM_REPORT_DIR" -Value $reportDir
Upsert-EnvValue -Path $envPath -Key "GRANOLA_VM_BATCH_BUCKET" -Value $bucket
Upsert-EnvValue -Path $envPath -Key "GRANOLA_VM_MAX_ITEMS_PER_RUN" -Value $maxItems
Upsert-EnvValue -Path $envPath -Key "GRANOLA_VM_RECENT_DAYS" -Value "7"
Upsert-EnvValue -Path $envPath -Key "GRANOLA_VM_MAX_RAW_ITEMS" -Value "200"

$taskAction = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcherScript`""
$taskName = "GranolaVmRawIntake"

try {
    schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
} catch {}

schtasks /Create /TN $taskName `
    /TR $taskAction `
    /SC HOURLY /MO $hours /RU $env:USERNAME /F 2>&1 | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Instalación completada" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Repo root            : $repoRoot" -ForegroundColor White
Write-Host "  Cache path           : $cachePath" -ForegroundColor White
Write-Host "  Worker URL           : $workerUrl" -ForegroundColor White
Write-Host "  Bucket seguro        : $bucket" -ForegroundColor White
Write-Host "  Max items por corrida: $maxItems" -ForegroundColor White
Write-Host "  Report dir           : $reportDir" -ForegroundColor White
Write-Host "  Task Scheduler       : $taskName (cada ${hours}h)" -ForegroundColor White
Write-Host ""
Write-Host "  Requisito previo: el Worker local en 8088 debe estar sano." -ForegroundColor Yellow
Write-Host "  Smoke test: .\\scripts\\vm\\test_granola_vm_raw_intake.ps1" -ForegroundColor Yellow
Write-Host ""
