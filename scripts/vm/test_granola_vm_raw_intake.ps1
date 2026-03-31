<#
.SYNOPSIS
    Smoke test del flujo seguro Granola -> raw desde la VM.
#>

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Granola VM Raw Intake - Smoke Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$envPath = "C:\Granola\.env"
$config = @{}
if (Test-Path $envPath) {
    Get-Content $envPath -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line -split "=", 2
            $config[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
}

$cachePath = $config["GRANOLA_CACHE_PATH"]
$workerUrl = $config["GRANOLA_WORKER_URL"]
$workerToken = $config["GRANOLA_WORKER_TOKEN"]

if (-not $cachePath) { $cachePath = Join-Path $env:APPDATA "Granola\cache-v6.json" }
if (-not $workerUrl) { $workerUrl = "http://127.0.0.1:8088" }

Write-Host "  Cache path : $cachePath" -ForegroundColor White
Write-Host "  Worker URL : $workerUrl" -ForegroundColor White

if (-not (Test-Path $cachePath)) {
    throw "No existe el cache de Granola: $cachePath"
}
if ([string]::IsNullOrWhiteSpace($workerToken)) {
    throw "GRANOLA_WORKER_TOKEN no está configurado en C:\Granola\.env"
}

try {
    $health = Invoke-WebRequest -Uri "$workerUrl/health" -UseBasicParsing -TimeoutSec 8 -ErrorAction Stop
    if ($health.StatusCode -ne 200) {
        throw "Health check devolvió $($health.StatusCode)"
    }
    Write-Host "  [OK] Worker health" -ForegroundColor Green
} catch {
    throw "Worker no accesible en $workerUrl: $_"
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runnerScript = Join-Path $repoRoot "scripts\vm\granola_vm_raw_intake.py"

$output = & python $runnerScript --json 2>&1
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "  Salida del runner:" -ForegroundColor Yellow
$output | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }

if ($exitCode -ne 0) {
    throw "granola_vm_raw_intake.py devolvió exit code $exitCode"
}

Write-Host ""
Write-Host "  Smoke test completado." -ForegroundColor Green
