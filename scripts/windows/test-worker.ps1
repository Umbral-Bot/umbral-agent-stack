# ============================================================
# test-worker.ps1 — Prueba el worker (health + run)
# ============================================================

$ErrorActionPreference = "Stop"

$WorkerUrl = if ($env:WORKER_URL) { $env:WORKER_URL } else { "http://localhost:8088" }
$Token = if ($env:WORKER_TOKEN) { $env:WORKER_TOKEN } else { "CHANGE_ME_WORKER_TOKEN" }

Write-Host "=== Testing Worker at $WorkerUrl ===" -ForegroundColor Cyan

# --- Health ---
Write-Host ""
Write-Host "1. GET /health" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$WorkerUrl/health" -Method GET
    Write-Host "   ✅ Health OK: ok=$($health.ok), ts=$($health.ts)" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Health FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Verificar que el worker está corriendo." -ForegroundColor Yellow
    exit 1
}

# --- Run (ping) ---
Write-Host ""
Write-Host "2. POST /run (task=ping)" -ForegroundColor Yellow
try {
    $headers = @{
        "Content-Type"  = "application/json"
        "Authorization" = "Bearer $Token"
    }
    $body = '{"task":"ping","input":{"test":true,"from":"test-worker.ps1"}}'
    $result = Invoke-RestMethod -Uri "$WorkerUrl/run" -Method POST -Headers $headers -Body $body
    Write-Host "   ✅ Run OK: ok=$($result.ok), task=$($result.task)" -ForegroundColor Green
    Write-Host "   Result: $($result.result | ConvertTo-Json -Compress)" -ForegroundColor Cyan
}
catch {
    $status = $_.Exception.Response.StatusCode.value__
    Write-Host "   ❌ Run FAILED (HTTP $status): $($_.Exception.Message)" -ForegroundColor Red
    if ($status -eq 401) {
        Write-Host "   Verificar WORKER_TOKEN." -ForegroundColor Yellow
    }
    elseif ($status -eq 500) {
        Write-Host "   WORKER_TOKEN puede no estar configurado en el server." -ForegroundColor Yellow
    }
    exit 1
}

Write-Host ""
Write-Host "=== Todas las pruebas pasaron ✅ ===" -ForegroundColor Green
