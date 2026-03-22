param(
  [string]$VpsHost = "100.113.249.25",
  [string]$RemoteUser = "root",
  [string]$VmAddress = "192.168.101.72",
  [int]$RemotePortSsh = 28022,
  [int]$RemotePortHeadless = 28088,
  [int]$RemotePortInteractive = 28089
)

$ErrorActionPreference = "Stop"
$startScript = Join-Path $PSScriptRoot "start_vm_reverse_tunnel.ps1"

function Get-TunnelProcesses {
  $needle = "-R $RemotePortHeadless`:$VmAddress`:8088"
  Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" |
    Where-Object { $_.CommandLine -like "*$needle*" }
}

function Test-RemoteHealth {
  $sshExe = (Get-Command ssh.exe -ErrorAction Stop).Source
  $remote = "curl -sf --connect-timeout 5 http://127.0.0.1:$RemotePortHeadless/health >/dev/null && curl -sf --connect-timeout 5 http://127.0.0.1:$RemotePortInteractive/health >/dev/null"
  $proc = Start-Process `
    -FilePath $sshExe `
    -ArgumentList @("-o", "BatchMode=yes", "${RemoteUser}@${VpsHost}", $remote) `
    -WindowStyle Hidden `
    -PassThru `
    -Wait
  return $proc.ExitCode -eq 0
}

$existing = @(Get-TunnelProcesses)
if ($existing.Count -gt 0 -and (Test-RemoteHealth)) {
  Write-Output "tunnel_healthy_pids=$($existing.ProcessId -join ',')"
  exit 0
}

foreach ($proc in $existing) {
  try {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
  } catch {
    Write-Warning "No se pudo detener tunnel pid=$($proc.ProcessId): $($_.Exception.Message)"
  }
}

& $startScript `
  -VpsHost $VpsHost `
  -RemoteUser $RemoteUser `
  -VmAddress $VmAddress `
  -RemotePortSsh $RemotePortSsh `
  -RemotePortHeadless $RemotePortHeadless `
  -RemotePortInteractive $RemotePortInteractive

Start-Sleep -Seconds 4

if (-not (Test-RemoteHealth)) {
  throw "Tunnel started but remote health check failed"
}

$current = @(Get-TunnelProcesses)
Write-Output "tunnel_recovered_pids=$($current.ProcessId -join ',')"
