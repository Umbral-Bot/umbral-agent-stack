param(
  [string]$VpsHost = "100.113.249.25",
  [string]$RemoteUser = "root",
  [string]$VmAddress = "",
  [int]$RemotePortSsh = 28022,
  [int]$RemotePortHeadless = 28088,
  [int]$RemotePortInteractive = 28089
)

$ErrorActionPreference = "Stop"

$logDir = "C:\openclaw-worker\logs"
$sshExe = (Get-Command ssh.exe -ErrorAction Stop).Source

function Get-CandidateAddresses {
  $addresses = @()
  if ($VmAddress) { $addresses += $VmAddress }
  foreach ($name in @(
    "OPENCLAW_VM_FALLBACK_ADDRESS",
    "OPENCLAW_VM_TAILSCALE_IP",
    "VM_TAILSCALE_IP",
    "OPENCLAW_VM_INTERNAL_IP"
  )) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not $value) { $value = [Environment]::GetEnvironmentVariable($name, "User") }
    if (-not $value) { $value = [Environment]::GetEnvironmentVariable($name, "Machine") }
    if ($value) { $addresses += $value.Trim() }
  }
  $addresses += "192.168.101.72"
  return $addresses | Where-Object { $_ } | Select-Object -Unique
}

function Test-VmHealth {
  param([string]$Address)
  foreach ($port in @(8088, 8089)) {
    $null = & curl.exe -sSf --max-time 4 "http://$Address`:$port/health"
    if ($LASTEXITCODE -ne 0) {
      return $false
    }
  }
  return $true
}

function Resolve-VmAddress {
  $candidates = @(Get-CandidateAddresses)
  foreach ($candidate in $candidates) {
    if (Test-VmHealth -Address $candidate) {
      return $candidate
    }
  }
  throw "No VM candidate address responded on 8088/8089. Candidates tried: $($candidates -join ', ')"
}

$resolvedVmAddress = Resolve-VmAddress
$forwardArgs = @(
  "-o", "ExitOnForwardFailure=yes",
  "-o", "ServerAliveInterval=30",
  "-o", "ServerAliveCountMax=3",
  "-o", "StrictHostKeyChecking=accept-new",
  "-N",
  "-R", "${RemotePortSsh}:${resolvedVmAddress}:22",
  "-R", "${RemotePortHeadless}:${resolvedVmAddress}:8088",
  "-R", "${RemotePortInteractive}:${resolvedVmAddress}:8089",
  "${RemoteUser}@${VpsHost}"
)

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Get-ExistingTunnelProcess {
  $needle = "-R $RemotePortHeadless`:"
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
Write-Output "vm_address=$resolvedVmAddress"
