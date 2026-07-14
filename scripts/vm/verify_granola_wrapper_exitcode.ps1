# Verification harness for the Granola VM raw-intake wrapper exit-code fix.
#
# start_granola_vm_raw_intake_hidden.ps1 relies on this exact mechanism:
#   $p = Start-Process ... -Wait -PassThru   # blocks until the child exits
#   exit $p.ExitCode                          # propagates the real result
#
# Before the fix the wrapper used -PassThru WITHOUT -Wait and only printed the
# PID, so it always returned 0 to Task Scheduler even when the Python process
# failed. This harness proves the propagation works for both a failing and a
# succeeding child, so the launcher no longer masks failures.
#
# Run on the VM (or any Windows host with python on PATH):
#   pwsh -File scripts/vm/verify_granola_wrapper_exitcode.ps1
# Exit 0 = all cases passed; exit 1 = a case failed.

$ErrorActionPreference = "Stop"

$python = (Get-Command python -ErrorAction Stop).Source
$failures = 0

function Assert-ExitPropagated {
  param([int]$Expected)

  $p = Start-Process `
    -FilePath $python `
    -ArgumentList @("-c", "import sys; sys.exit($Expected)") `
    -WindowStyle Hidden `
    -PassThru `
    -Wait

  if ($null -eq $p) {
    Write-Output "FAIL (expected=$Expected): Start-Process returned null"
    return $false
  }
  if ($p.ExitCode -ne $Expected) {
    Write-Output "FAIL (expected=$Expected): got ExitCode=$($p.ExitCode)"
    return $false
  }
  Write-Output "PASS: Start-Process -Wait -PassThru propagated ExitCode=$($p.ExitCode)"
  return $true
}

foreach ($code in @(0, 1, 42)) {
  if (-not (Assert-ExitPropagated -Expected $code)) { $failures++ }
}

if ($failures -gt 0) {
  Write-Error "verify_granola_wrapper_exitcode: $failures case(s) failed"
  exit 1
}

Write-Output "verify_granola_wrapper_exitcode: all cases passed"
exit 0
