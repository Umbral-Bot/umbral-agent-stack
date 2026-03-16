param(
  [string]$VpsHost = "100.113.249.25",
  [string]$RemoteUser = "root",
  [string]$VmAddress = "192.168.101.72",
  [int]$RemotePortSsh = 28022,
  [int]$RemotePortHeadless = 28088,
  [int]$RemotePortInteractive = 28089
)

$ErrorActionPreference = "Stop"

$logDir = "C:\openclaw-worker\logs"
$sshExe = (Get-Command ssh.exe -ErrorAction Stop).Source
$forwardArgs = @(
  "-o", "ExitOnForwardFailure=yes",
  "-o", "ServerAliveInterval=30",
  "-o", "ServerAliveCountMax=3",
  "-o", "StrictHostKeyChecking=accept-new",
  "-N",
  "-R", "${RemotePortSsh}:${VmAddress}:22",
  "-R", "${RemotePortHeadless}:${VmAddress}:8088",
  "-R", "${RemotePortInteractive}:${VmAddress}:8089",
  "${RemoteUser}@${VpsHost}"
)

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Get-ExistingTunnelProcess {
  $needle = "-R $RemotePortHeadless`:$VmAddress`:8088"
  Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" |
    Where-Object { $_.CommandLine -like "*$needle*" } |
    Select-Object -First 1
}

$existing = Get-ExistingTunnelProcess
if ($existing) {
  Write-Output "already_running_pid=$($existing.ProcessId)"
  exit 0
}

$stdoutLog = Join-Path $logDir "vm-reverse-tunnel-stdout.log"
$stderrLog = Join-Path $logDir "vm-reverse-tunnel-stderr.log"

$process = Start-Process `
  -FilePath $sshExe `
  -ArgumentList $forwardArgs `
  -WindowStyle Hidden `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog `
  -PassThru

Write-Output "reverse_tunnel_pid=$($process.Id)"
