$ErrorActionPreference = "Stop"

$repoRoot = "C:\GitHub\umbral-agent-stack"
$tokenPath = "C:\openclaw-worker\worker_token"
$logDir = "C:\openclaw-worker\logs"
$uvicornExe = (Get-Command uvicorn.exe -ErrorAction Stop).Source
$uvicornArgs = @(
  "worker.app:app",
  "--host",
  "0.0.0.0",
  "--port",
  "8089",
  "--log-level",
  "info"
)

function Stop-ExistingInteractiveWorker {
  try {
    $connections = Get-NetTCPConnection -LocalPort 8089 -State Listen -ErrorAction Stop
  } catch {
    return
  }

  foreach ($connection in $connections) {
    try {
      Stop-Process -Id $connection.OwningProcess -Force -ErrorAction Stop
      Start-Sleep -Milliseconds 300
    } catch {
      Write-Warning "No se pudo detener el proceso $($connection.OwningProcess) en 8089: $($_.Exception.Message)"
    }
  }
}

Set-Location $repoRoot
$env:PYTHONPATH = $repoRoot
$env:PYTHONIOENCODING = "utf-8"
$env:OPENCLAW_INTERACTIVE_SESSION = "1"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if (Test-Path $tokenPath) {
  $token = [System.IO.File]::ReadAllText($tokenPath, [System.Text.Encoding]::UTF8)
  $token = $token.Trim([char]0xFEFF, [char]0x0D, [char]0x0A, ' ')
  if ($token) {
    $env:WORKER_TOKEN = $token
  }
}

Stop-ExistingInteractiveWorker

$stdoutLog = Join-Path $logDir "interactive-worker-stdout.log"
$stderrLog = Join-Path $logDir "interactive-worker-stderr.log"

$process = Start-Process `
  -FilePath $uvicornExe `
  -ArgumentList $uvicornArgs `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog `
  -PassThru

Write-Output "interactive_worker_pid=$($process.Id)"
