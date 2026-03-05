<#
.SYNOPSIS
    Smoke test para el Granola Watcher.

.DESCRIPTION
    Verifica que el watcher está correctamente configurado:
      1. Crea un archivo .md de prueba en GRANOLA_EXPORT_DIR
      2. Ejecuta el watcher en modo --once
      3. Verifica que el archivo fue movido a processed/
      4. Verifica la respuesta del Worker
#>

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Granola Watcher — Smoke Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

function Test-Step {
    param([string]$Name, [scriptblock]$Test)
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  [OK]   $Name" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host "  [FAIL] $Name" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        Write-Host "  [FAIL] $Name — $_" -ForegroundColor Red
        $script:failed++
    }
}

# --- Cargar configuración ---

$envPath = "C:\Granola\.env"
$exportDir = $null
$workerUrl = $null
$workerToken = $null

if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line -split "=", 2
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            switch ($key) {
                "GRANOLA_EXPORT_DIR"    { $exportDir = $val }
                "GRANOLA_WORKER_URL"    { $workerUrl = $val }
                "GRANOLA_WORKER_TOKEN"  { $workerToken = $val }
            }
        }
    }
}

if (-not $exportDir) { $exportDir = "C:\Granola\exports" }
if (-not $workerUrl) { $workerUrl = "http://localhost:8088" }

$processedDir = Join-Path $exportDir "processed"

# --- Tests ---

Test-Step "Carpeta de exports existe" {
    Test-Path $exportDir
}

Test-Step "Archivo .env existe" {
    Test-Path $envPath
}

Test-Step "Worker Token configurado" {
    -not [string]::IsNullOrWhiteSpace($workerToken)
}

Test-Step "Worker accesible" {
    try {
        $response = Invoke-WebRequest -Uri "$workerUrl/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $response.StatusCode -eq 200
    } catch {
        Write-Host "    (Worker no responde en $workerUrl — asegurate de que esta corriendo)" -ForegroundColor DarkYellow
        $false
    }
}

# --- Crear archivo de prueba ---
$testFile = Join-Path $exportDir "_smoke_test_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
$testContent = @"
# Smoke Test Meeting

**Date:** $(Get-Date -Format "yyyy-MM-dd")
**Attendees:** Test User

## Notes

This is an automated smoke test for the Granola Watcher.

## Action Items

- [ ] Verify watcher works (Test User, $(Get-Date -Format "yyyy-MM-dd"))
"@

Test-Step "Crear archivo .md de prueba" {
    Set-Content -Path $testFile -Value $testContent -Encoding UTF8
    Test-Path $testFile
}

# --- Ejecutar watcher en modo --once ---
$testFileName = Split-Path $testFile -Leaf
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$watcherScript = Join-Path $repoRoot "scripts\vm\granola_watcher.py"

if (-not (Test-Path $watcherScript)) {
    $watcherScript = Join-Path $PSScriptRoot "granola_watcher.py"
}

Write-Host ""
Write-Host "  Ejecutando watcher --once..." -ForegroundColor Yellow

$env:GRANOLA_EXPORT_DIR = $exportDir
$env:GRANOLA_WORKER_URL = $workerUrl
$env:GRANOLA_WORKER_TOKEN = $workerToken

try {
    $output = & python $watcherScript --once 2>&1
    $watcherExitCode = $LASTEXITCODE
    Write-Host "  Salida del watcher:"
    $output | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
} catch {
    $watcherExitCode = 1
    Write-Host "  Error ejecutando watcher: $_" -ForegroundColor Red
}

Test-Step "Watcher ejecuto sin errores" {
    $watcherExitCode -eq 0 -or $null -eq $watcherExitCode
}

Test-Step "Archivo movido a processed/" {
    $processedFile = Join-Path $processedDir $testFileName
    Test-Path $processedFile
}

Test-Step "Archivo ya no esta en exports/" {
    -not (Test-Path $testFile)
}

# --- Resumen ---
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Resultados: $passed OK, $failed FAIL" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($failed -gt 0) { exit 1 }
