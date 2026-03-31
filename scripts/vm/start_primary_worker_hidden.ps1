$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runnerScript = Join-Path $repoRoot "scripts\vm\start_primary_worker.py"
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$workerRoot = "C:\openclaw-worker"
$logDir = Join-Path $workerRoot "logs"
$stdoutLog = Join-Path $logDir "primary-worker-stdout.log"
$stderrLog = Join-Path $logDir "primary-worker-stderr.log"

function Stop-ExistingPrimaryWorker {
  try {
    $connections = Get-NetTCPConnection -LocalPort 8088 -State Listen -ErrorAction Stop
  } catch {
    return
  }

  foreach ($connection in $connections) {
    try {
      Stop-Process -Id $connection.OwningProcess -Force -ErrorAction Stop
      Start-Sleep -Milliseconds 300
    } catch {
      Write-Warning "No se pudo detener el proceso $($connection.OwningProcess) en 8088: $($_.Exception.Message)"
    }
  }
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Set-Location $repoRoot
Stop-ExistingPrimaryWorker

$process = Start-Process `
  -FilePath $pythonExe `
  -ArgumentList @($runnerScript) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog `
  -PassThru

Write-Output "primary_worker_pid=$($process.Id)"
