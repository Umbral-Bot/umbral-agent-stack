# Deploy del Worker en la VM Hyper-V
# Ejecutar como: $env:WORKER_TOKEN='tu-token'; .\deploy-vm.ps1

$ErrorActionPreference = "Continue"

if (-not $env:WORKER_TOKEN) {
    Write-Host "ERROR: WORKER_TOKEN no definido." -ForegroundColor Red
    Write-Host "  Ejecuta: `$env:WORKER_TOKEN='tu-token-secreto'; .\deploy-vm.ps1" -ForegroundColor Yellow
    exit 1
}
$TOKEN = $env:WORKER_TOKEN

function Show-TokenMask([string]$t) {
    if ([string]::IsNullOrEmpty($t)) { return "(vacío)" }
    if ($t.Length -le 8) { return "****" }
    return "$($t.Substring(0, 4))...$($t.Substring($t.Length - 4))"
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Umbral Worker Deploy" -ForegroundColor Cyan
Write-Host "  $timestamp" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- FASE 0: Diagnostico ---
Write-Host "[FASE 0] Diagnostico del entorno..." -ForegroundColor Yellow

Write-Host "  Procesos Python:" -ForegroundColor Gray
Get-Process -Name *python* -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, Path -AutoSize

Write-Host "  Puerto 8088:" -ForegroundColor Gray
$port8088 = Get-NetTCPConnection -LocalPort 8088 -ErrorAction SilentlyContinue
if ($port8088) {
    $port8088 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
        Write-Host "    PID=$_ Proceso=$($proc.ProcessName)" -ForegroundColor Green
    }
}
else {
    Write-Host "    (nada escucha en 8088)" -ForegroundColor DarkYellow
}
Write-Host ""

# --- FASE 1: Repositorio Git ---
Write-Host "[FASE 1] Repositorio Git..." -ForegroundColor Yellow

$repoRoot = $null

# Buscar repo existente
$searchPaths = @(
    "C:\GitHub\umbral-agent-stack",
    "D:\GitHub\umbral-agent-stack",
    "$env:USERPROFILE\GitHub\umbral-agent-stack",
    "$env:USERPROFILE\umbral-agent-stack"
)

foreach ($candidate in $searchPaths) {
    if (Test-Path "$candidate\.git") {
        $repoRoot = $candidate
        Write-Host "  Repo existente: $repoRoot" -ForegroundColor Green
        break
    }
}

if ($repoRoot) {
    Write-Host "  git fetch/switch/pull --ff-only origin main..." -ForegroundColor Gray
    Push-Location $repoRoot
    $currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
    if ($currentBranch -ne "main") {
        git switch main 2>&1
    }
    git fetch origin main 2>&1
    git pull --ff-only origin main 2>&1
    $lastCommit = git log --oneline -1
    Write-Host "  Ultimo commit: $lastCommit" -ForegroundColor Green
    Pop-Location
}
else {
    Write-Host "  Repo no encontrado. Clonando..." -ForegroundColor DarkYellow
    $cloneDir = "C:\GitHub"
    if (-not (Test-Path $cloneDir)) { New-Item -ItemType Directory -Path $cloneDir -Force | Out-Null }
    Push-Location $cloneDir
    git clone https://github.com/Umbral-Bot/umbral-agent-stack.git 2>&1
    Pop-Location
    $repoRoot = "C:\GitHub\umbral-agent-stack"
}

# Verificar que worker/app.py existe
if (-not (Test-Path "$repoRoot\worker\app.py")) {
    Write-Host "  ERROR: worker/app.py no existe." -ForegroundColor Red
    exit 1
}
Write-Host "  worker/app.py encontrado" -ForegroundColor Green
Write-Host ""

# --- FASE 2: Dependencias Python ---
Write-Host "[FASE 2] Dependencias Python..." -ForegroundColor Yellow

$pyVer = python --version 2>&1
Write-Host "  $pyVer" -ForegroundColor Green

Write-Host "  Instalando requirements..." -ForegroundColor Gray
python -m pip install -r "$repoRoot\worker\requirements.txt" --quiet 2>&1
Write-Host "  Instalando test deps..." -ForegroundColor Gray
python -m pip install pytest httpx fakeredis --quiet 2>&1

$mods = @("fastapi", "uvicorn", "pydantic", "httpx", "pytest")
foreach ($m in $mods) {
    $ver = python -c "import $m; print($m.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    OK $m $ver" -ForegroundColor Green
    }
    else {
        Write-Host "    FALTA $m" -ForegroundColor Red
    }
}
Write-Host ""

# --- FASE 3: Archivos esperados ---
Write-Host "[FASE 3] Archivos esperados..." -ForegroundColor Yellow

$files = @(
    "$repoRoot\worker\app.py",
    "$repoRoot\worker\models\__init__.py",
    "$repoRoot\tests\test_worker.py",
    "$repoRoot\scripts\worker_inventory_smoke.py"
)
foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "  OK $f" -ForegroundColor Green
    }
    else {
        Write-Host "  FALTA $f" -ForegroundColor Red
    }
}

$appContent = Get-Content "$repoRoot\worker\app.py" -Raw
$versionMatch = [regex]::Match($appContent, 'version\s*=\s*"([^"]+)"')
if ($versionMatch.Success) {
    Write-Host "  Version detectada: $($versionMatch.Groups[1].Value)" -ForegroundColor Green
}
else {
    Write-Host "  ADVERTENCIA: no se pudo detectar la version declarada en worker/app.py" -ForegroundColor DarkYellow
}
Write-Host ""

# --- FASE 4: Tests ---
Write-Host "[FASE 4] Ejecutar tests..." -ForegroundColor Yellow

$env:PYTHONPATH = $repoRoot
$env:WORKER_TOKEN = $TOKEN
Push-Location "$repoRoot\worker"
python -m pytest "$repoRoot\tests\test_worker.py" -v 2>&1
$testResult = $LASTEXITCODE
Pop-Location

if ($testResult -eq 0) {
    Write-Host "  TESTS: PASSED" -ForegroundColor Green
}
else {
    Write-Host "  TESTS: FAILED (exit $testResult)" -ForegroundColor Red
}
Write-Host ""

# --- FASE 5: Reiniciar worker ---
Write-Host "[FASE 5] Servicio worker..." -ForegroundColor Yellow

# Matar proceso actual en 8088 (un PID por proceso; Get-NetTCPConnection devuelve una fila por socket)
$existing = Get-NetTCPConnection -LocalPort 8088 -ErrorAction SilentlyContinue
if ($existing) {
    $existing | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        Write-Host "  Deteniendo PID $_..." -ForegroundColor Gray
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 3
}

$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    Write-Host "ERROR: 'python' no está en PATH. Instala Python 3.11+ o agrega al PATH." -ForegroundColor Red
    exit 1
}

$logDir = "C:\openclaw-worker\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$uvicornOut = Join-Path $logDir "uvicorn-deploy-stdout.log"
$uvicornErr = Join-Path $logDir "uvicorn-deploy-stderr.log"

# Mismo proceso PowerShell ya tiene TOKEN/PYTHONPATH; el hijo hereda + logs a archivo (si falla el bind, mirar stderr)
$env:WORKER_TOKEN = $TOKEN
$env:PYTHONPATH = $repoRoot
Write-Host "  Iniciando worker (token $(Show-TokenMask $TOKEN), logs: $uvicornOut / $uvicornErr)..." -ForegroundColor Gray
try {
    Start-Process -FilePath $pythonExe `
        -ArgumentList "-m", "uvicorn", "worker.app:app", "--host", "0.0.0.0", "--port", "8088" `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $uvicornOut `
        -RedirectStandardError $uvicornErr
}
catch {
    Write-Host "  ERROR al iniciar uvicorn: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Dar tiempo a imports + bind del puerto
$healthOk = $false
for ($i = 1; $i -le 8; $i++) {
    Start-Sleep -Seconds 2
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:8088/health" -UseBasicParsing -TimeoutSec 3
        $healthOk = $true
        break
    }
    catch {
        Write-Host "  Esperando worker en 8088... intento $i/8" -ForegroundColor DarkGray
    }
}
if ($healthOk) {
    Write-Host "  Worker respondiendo en 8088" -ForegroundColor Green
}
else {
    Write-Host "  ADVERTENCIA: aún no responde /health. Revisa: $uvicornErr" -ForegroundColor Yellow
}

Write-Host "  Refrescando worker interactivo 8089..." -ForegroundColor Gray
$interactiveTask = "StartInteractiveWorkerHiddenNow"
schtasks /Query /TN $interactiveTask *> $null
if ($LASTEXITCODE -eq 0) {
    schtasks /Run /TN $interactiveTask 2>&1
}
else {
    $interactiveScript = Join-Path $repoRoot "scripts\vm\start_interactive_worker.ps1"
    if (Test-Path $interactiveScript) {
        powershell -NoProfile -ExecutionPolicy Bypass -File $interactiveScript 2>&1
    }
    else {
        Write-Host "  ADVERTENCIA: no se encontro launcher para 8089." -ForegroundColor DarkYellow
    }
}
Start-Sleep -Seconds 4
Write-Host ""

# --- FASE 6: Verificacion final ---
Write-Host "[FASE 6] Verificacion final..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$overallOk = $true

# Health
Write-Host "  Health check..." -ForegroundColor Gray
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8088/health" -Method GET -TimeoutSec 5
    $hOk = $health.ok
    $hVer = $health.version
    Write-Host "  Health: OK=$hOk Version=$hVer" -ForegroundColor Green
}
catch {
    $err = $_.Exception.Message
    Write-Host "  Health: FAILED - $err" -ForegroundColor Red
    $overallOk = $false
}

# Legacy format
Write-Host "  Test legacy format..." -ForegroundColor Gray
try {
    $headers = @{ "Authorization" = "Bearer $TOKEN"; "Content-Type" = "application/json" }
    $bodyObj = @{ task = "ping"; input = @{ hello = "deploy-test" } }
    $bodyJson = $bodyObj | ConvertTo-Json -Compress
    $legacy = Invoke-RestMethod -Uri "http://localhost:8088/run" -Method POST -Headers $headers -Body $bodyJson -TimeoutSec 5
    $lId = $legacy.task_id
    $lOk = $legacy.ok
    Write-Host "  Legacy: task_id=$lId ok=$lOk" -ForegroundColor Green
}
catch {
    $err = $_.Exception.Message
    Write-Host "  Legacy: FAILED - $err" -ForegroundColor Red
    $overallOk = $false
}

# Envelope format
Write-Host "  Test envelope format..." -ForegroundColor Gray
try {
    $envObj = @{ schema_version = "0.1"; team = "system"; task_type = "health"; task = "ping"; input = @{ hello = "envelope-test" } }
    $envJson = $envObj | ConvertTo-Json -Compress
    $envelope = Invoke-RestMethod -Uri "http://localhost:8088/run" -Method POST -Headers $headers -Body $envJson -TimeoutSec 5
    $eId = $envelope.task_id
    $eTm = $envelope.team
    $eOk = $envelope.ok
    Write-Host "  Envelope: task_id=$eId team=$eTm ok=$eOk" -ForegroundColor Green
}
catch {
    $err = $_.Exception.Message
    Write-Host "  Envelope: FAILED - $err" -ForegroundColor Red
    $overallOk = $false
}

# GET /tasks
Write-Host "  Test GET /tasks..." -ForegroundColor Gray
try {
    $authH = @{ "Authorization" = "Bearer $TOKEN" }
    $tasks = Invoke-RestMethod -Uri "http://localhost:8088/tasks" -Method GET -Headers $authH -TimeoutSec 5
    $tCount = @($tasks.tasks).Count
    Write-Host "  Tasks: $tCount tareas en store" -ForegroundColor Green
}
catch {
    $err = $_.Exception.Message
    Write-Host "  Tasks: FAILED - $err" -ForegroundColor Red
    $overallOk = $false
}

# Inventory parity
Write-Host "  Inventory smoke 8088 vs 8089..." -ForegroundColor Gray
Push-Location $repoRoot
python "$repoRoot\scripts\worker_inventory_smoke.py" `
    --target "vm-headless=http://localhost:8088" `
    --target "vm-interactive=http://localhost:8089" `
    --token "$TOKEN" `
    --smoke 2>&1
$inventoryResult = $LASTEXITCODE
Pop-Location
if ($inventoryResult -eq 0) {
    Write-Host "  Inventory smoke: PASSED" -ForegroundColor Green
}
else {
    Write-Host "  Inventory smoke: FAILED (exit $inventoryResult)" -ForegroundColor Red
    $overallOk = $false
}

Write-Host ""
$endTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploy completado - $endTime" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Copia el output completo y pegalo en la conversacion." -ForegroundColor Yellow
Write-Host ""

if ($overallOk) {
    exit 0
}

exit 1
