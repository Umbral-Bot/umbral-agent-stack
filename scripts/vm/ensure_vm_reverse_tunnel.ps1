param(
  [string]$VpsHost = "100.113.249.25",
  [string]$RemoteUser = "root",
  [string]$VmAddress = "",
  [int]$RemotePortSsh = 28022,
  [int]$RemotePortHeadless = 28088,
  [int]$RemotePortInteractive = 28089
)

$ErrorActionPreference = "Stop"
$startScript = Join-Path $PSScriptRoot "start_vm_reverse_tunnel.ps1"

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

function Get-TunnelProcesses {
  $needle = "-R $RemotePortHeadless`:"
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

$resolvedVmAddress = Resolve-VmAddress
$existing = @(Get-TunnelProcesses)
if ($existing.Count -gt 0 -and (Test-RemoteHealth)) {
  Write-Output "tunnel_healthy_pids=$($existing.ProcessId -join ',')"
  Write-Output "vm_address=$resolvedVmAddress"
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
  -VmAddress $resolvedVmAddress `
  -RemotePortSsh $RemotePortSsh `
  -RemotePortHeadless $RemotePortHeadless `
  -RemotePortInteractive $RemotePortInteractive

Start-Sleep -Seconds 4

if (-not (Test-RemoteHealth)) {
  throw "Tunnel started but remote health check failed"
}

$current = @(Get-TunnelProcesses)
Write-Output "tunnel_recovered_pids=$($current.ProcessId -join ',')"
Write-Output "vm_address=$resolvedVmAddress"
