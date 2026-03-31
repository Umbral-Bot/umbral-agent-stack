$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$granolaRoot = "C:\Granola"
$envPath = Join-Path $granolaRoot ".env"
$startupLog = Join-Path $granolaRoot "vm-raw-intake-startup.log"
$smokeScript = Join-Path $repoRoot "scripts\vm\test_granola_vm_raw_intake.ps1"
$launcherScript = Join-Path $repoRoot "scripts\vm\start_granola_vm_raw_intake_hidden.ps1"

function Get-EnvValue {
  param(
    [string]$Path,
    [string]$Key,
    [string]$Default = ""
  )

  if (-not (Test-Path $Path)) {
    return $Default
  }

  foreach ($line in Get-Content $Path -Encoding UTF8) {
    if ($line -match "^\s*${Key}=(.*)$") {
      return $Matches[1].Trim()
    }
  }

  return $Default
}

function Wait-WorkerHealth {
  param(
    [string]$WorkerUrl,
    [int]$Attempts = 20,
    [int]$DelaySeconds = 15
  )

  $healthUrl = "$($WorkerUrl.TrimEnd('/'))/health"
  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    try {
      $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 8 -ErrorAction Stop
      if ($response.StatusCode -eq 200) {
        return $true
      }
    } catch {}

    Start-Sleep -Seconds $DelaySeconds
  }

  return $false
}

New-Item -ItemType Directory -Path $granolaRoot -Force | Out-Null
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] startup check begin" | Out-File -FilePath $startupLog -Encoding UTF8 -Append

$workerUrl = Get-EnvValue -Path $envPath -Key "GRANOLA_WORKER_URL" -Default "http://127.0.0.1:8088"
if (-not (Wait-WorkerHealth -WorkerUrl $workerUrl)) {
  "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] worker unavailable at $workerUrl after startup wait" |
    Out-File -FilePath $startupLog -Encoding UTF8 -Append
  exit 1
}

try {
  & $smokeScript 2>&1 | ForEach-Object {
    "$_" | Out-File -FilePath $startupLog -Encoding UTF8 -Append
  }
} catch {
  "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] startup smoke test failed: $($_.Exception.Message)" |
    Out-File -FilePath $startupLog -Encoding UTF8 -Append
  exit 1
}

try {
  & $launcherScript 2>&1 | ForEach-Object {
    "$_" | Out-File -FilePath $startupLog -Encoding UTF8 -Append
  }
} catch {
  "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] startup intake launch failed: $($_.Exception.Message)" |
    Out-File -FilePath $startupLog -Encoding UTF8 -Append
  exit 1
}

"[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] startup check completed" |
  Out-File -FilePath $startupLog -Encoding UTF8 -Append
