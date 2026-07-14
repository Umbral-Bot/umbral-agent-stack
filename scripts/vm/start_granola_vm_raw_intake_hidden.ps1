# Launcher for the Granola VM raw intake.
#
# Observability fix (spec b0004): previously this used `Start-Process -PassThru`
# without `-Wait` and only printed the PID, so it always returned 0 to Task
# Scheduler even when the Python process failed immediately. That is how a dead
# intake stayed invisible (LastTaskResult: 0). We now block on the process with
# `-Wait` and propagate its real exit code, so the *next* failure surfaces at
# once. Verify the propagation mechanism with:
#   scripts/vm/verify_granola_wrapper_exitcode.ps1
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runnerScript = Join-Path $repoRoot "scripts\vm\granola_vm_raw_intake.py"
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$granolaRoot = "C:\Granola"
$stdoutLog = Join-Path $granolaRoot "vm-raw-intake-stdout.log"
$stderrLog = Join-Path $granolaRoot "vm-raw-intake-stderr.log"

function Stop-ExistingGranolaVmRawIntake {
  try {
    $processes = Get-CimInstance Win32_Process -ErrorAction Stop |
      Where-Object {
        $_.Name -eq "python.exe" -and
        $_.CommandLine -like "*granola_vm_raw_intake.py*"
      }
  } catch {
    return
  }

  foreach ($process in $processes) {
    try {
      Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
      Start-Sleep -Milliseconds 300
    } catch {
      Write-Warning "No se pudo detener Granola VM raw intake PID $($process.ProcessId): $($_.Exception.Message)"
    }
  }
}

New-Item -ItemType Directory -Path $granolaRoot -Force | Out-Null
Set-Location $repoRoot
Stop-ExistingGranolaVmRawIntake

$process = Start-Process `
  -FilePath $pythonExe `
  -ArgumentList @($runnerScript, "--execute") `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog `
  -PassThru `
  -Wait

if ($null -eq $process) {
  Write-Error "granola_vm_raw_intake failed to start"
  exit 1
}

$exitCode = $process.ExitCode
Write-Output "granola_vm_raw_intake_pid=$($process.Id)"
Write-Output "granola_vm_raw_intake_exit=$exitCode"
exit $exitCode
