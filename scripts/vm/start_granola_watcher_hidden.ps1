$ErrorActionPreference = "Stop"

$repoRoot = "C:\GitHub\umbral-agent-stack"
$watcherScript = Join-Path $repoRoot "scripts\vm\granola_watcher.py"
$pythonExe = "python"
$pythonArgs = @(
  $watcherScript,
  "--poll"
)

function Stop-ExistingGranolaWatcher {
  try {
    $processes = Get-CimInstance Win32_Process -ErrorAction Stop |
      Where-Object {
        $_.Name -eq "python.exe" -and
        $_.CommandLine -like "*granola_watcher.py*"
      }
  } catch {
    return
  }

  foreach ($process in $processes) {
    try {
      Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
      Start-Sleep -Milliseconds 300
    } catch {
      Write-Warning "No se pudo detener Granola watcher PID $($process.ProcessId): $($_.Exception.Message)"
    }
  }
}

Set-Location $repoRoot
Stop-ExistingGranolaWatcher

$process = Start-Process `
  -FilePath $pythonExe `
  -ArgumentList $pythonArgs `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -PassThru

Write-Output "granola_watcher_pid=$($process.Id)"
