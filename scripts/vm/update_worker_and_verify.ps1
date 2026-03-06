# Actualiza el repo en la VM, reinicia openclaw-worker y verifica que windows.fs.* esten registrados.
# Ejecutar en la VM (PowerShell). Requiere: git, nssm, y que el servicio openclaw-worker exista.

$ErrorActionPreference = "Stop"
$RepoDir = "C:\GitHub\umbral-agent-stack"
$ServiceName = "openclaw-worker"
$HealthUrl = "http://localhost:8088/health"
$RequiredTask = "windows.fs.ensure_dirs"

Write-Host "=== Update Worker and verify windows.fs.* ===" -ForegroundColor Cyan
Write-Host ""

# 1) Comprobar que estamos en el repo correcto (o que existe)
if (-not (Test-Path $RepoDir)) {
    Write-Host "ERROR: No existe $RepoDir. Crear el repo o corregir la ruta." -ForegroundColor Red
    exit 1
}
Push-Location $RepoDir

# 2) Mostrar AppDirectory de NSSM por si el servicio apunta a otra ruta
try {
    $appDir = & nssm get $ServiceName AppDirectory 2>$null
    Write-Host "NSSM AppDirectory: $appDir" -ForegroundColor Gray
    if ($appDir -ne $RepoDir) {
        Write-Host "AVISO: El servicio no apunta a $RepoDir. Reconfigurar con: nssm set $ServiceName AppDirectory $RepoDir" -ForegroundColor Yellow
    }
} catch {
    Write-Host "AVISO: No se pudo leer NSSM AppDirectory (¿nssm en PATH?). Continuando..." -ForegroundColor Yellow
}

# 3) Git pull
Write-Host "Ejecutando: git pull origin main" -ForegroundColor Cyan
& git pull origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: git pull fallo." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 4) Verificar que existe el modulo windows_fs
if (-not (Test-Path "worker\tasks\windows_fs.py")) {
    Write-Host "ERROR: Tras git pull no existe worker\tasks\windows_fs.py. Revisar rama/repo." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "OK: worker\tasks\windows_fs.py presente." -ForegroundColor Green

# 4.5) Instalar/actualizar dependencias del worker (evita ModuleNotFoundError tras pull)
Write-Host "Instalando dependencias: pip install -r worker\requirements.txt" -ForegroundColor Cyan
& python -m pip install -q -r worker\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "AVISO: pip install fallo. El Worker puede no arrancar (ej. ModuleNotFoundError: requests)." -ForegroundColor Yellow
}

# 5) Reiniciar servicio
Write-Host "Reiniciando servicio: nssm restart $ServiceName" -ForegroundColor Cyan
& nssm restart $ServiceName
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: nssm restart fallo. Comprobar que el servicio existe y tienes permisos." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 6) Esperar a que el Worker arranque
Write-Host "Esperando 5 s a que el Worker arranque..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# 7) Health y comprobar tasks_registered
try {
    $health = Invoke-RestMethod -Uri $HealthUrl -Method Get
    $tasks = $health.tasks_registered
    if ($tasks -contains $RequiredTask) {
        Write-Host ""
        Write-Host "OK: /health devuelve tasks_registered con '$RequiredTask' y demas windows.fs.*" -ForegroundColor Green
        Write-Host "Puedes confirmar a Rick: Mergeado + worker reiniciado + policy actualizada." -ForegroundColor Green
        Pop-Location
        exit 0
    }
    Write-Host "ERROR: /health OK pero tasks_registered NO contiene '$RequiredTask'." -ForegroundColor Red
    Write-Host "tasks_registered: $($tasks -join ', ')" -ForegroundColor Gray
    Pop-Location
    exit 1
} catch {
    Write-Host "ERROR: No se pudo obtener $HealthUrl - $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Comprobar: nssm status $ServiceName ; netstat -ano | findstr :8088" -ForegroundColor Yellow
    Pop-Location
    exit 1
}
