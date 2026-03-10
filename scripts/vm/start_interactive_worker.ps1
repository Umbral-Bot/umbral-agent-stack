$ErrorActionPreference = "Stop"

$repoRoot = "C:\GitHub\umbral-agent-stack"
$tokenPath = "C:\openclaw-worker\worker_token"
$pythonExe = "python"
$pythonArgs = @(
  "-m",
  "uvicorn",
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
$env:OPENCLAW_INTERACTIVE_SESSION = "1"

if (Test-Path $tokenPath) {
  $token = [System.IO.File]::ReadAllText($tokenPath, [System.Text.Encoding]::UTF8)
  $token = $token.Trim([char]0xFEFF, [char]0x0D, [char]0x0A, ' ')
  if ($token) {
    $env:WORKER_TOKEN = $token
  }
}

Stop-ExistingInteractiveWorker

$process = Start-Process `
  -FilePath $pythonExe `
  -ArgumentList $pythonArgs `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -PassThru

Write-Output "interactive_worker_pid=$($process.Id)"
