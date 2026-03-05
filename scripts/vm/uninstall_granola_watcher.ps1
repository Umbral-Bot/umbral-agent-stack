<#
.SYNOPSIS
    Desinstala el Granola Watcher del Windows Task Scheduler.

.DESCRIPTION
    Elimina la tarea programada "GranolaWatcher" y opcionalmente
    limpia los archivos de configuración.
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Granola Watcher — Desinstalador" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$taskName = "GranolaWatcher"

$taskExists = schtasks /Query /TN $taskName 2>&1
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
    Write-Host "  OK: Tarea '$taskName' eliminada del Task Scheduler." -ForegroundColor Green
} else {
    Write-Host "  INFO: La tarea '$taskName' no existia en Task Scheduler." -ForegroundColor Yellow
}

$cleanupChoice = Read-Host "  Eliminar C:\Granola\.env? [s/N]"
if ($cleanupChoice -eq "s" -or $cleanupChoice -eq "S") {
    if (Test-Path "C:\Granola\.env") {
        Remove-Item "C:\Granola\.env" -Force
        Write-Host "  OK: C:\Granola\.env eliminado." -ForegroundColor Green
    }
    if (Test-Path "C:\Granola\watcher.log") {
        Remove-Item "C:\Granola\watcher.log" -Force
        Write-Host "  OK: C:\Granola\watcher.log eliminado." -ForegroundColor Green
    }
} else {
    Write-Host "  INFO: Archivos de configuracion conservados." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Desinstalacion completada." -ForegroundColor Cyan
Write-Host ""
