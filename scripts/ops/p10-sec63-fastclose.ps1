# P10-SEC63 gate safety watchdog (Windows)
# Respects monitor\WINDOW_AUTHORIZED.txt during broker window.
param(
    [string]$EvidRoot = "$env:USERPROFILE\.coord-ag-evidence\pit-p10-sec63-retry-20260623"
)

$ErrorActionPreference = "Continue"
$Mon = Join-Path $EvidRoot "monitor"
New-Item -ItemType Directory -Force -Path $Mon | Out-Null

$log = Join-Path $Mon "fastclose.log"
$pidFile = Join-Path $Mon "watchdog.pid"
$authMarker = Join-Path $Mon "WINDOW_AUTHORIZED.txt"
$emergency = Join-Path $Mon "GATES_EMERGENCY_MANUAL.txt"
$postVerdict = Join-Path $Mon "POSTVERDICT.txt"
$VERDICT = Join-Path $EvidRoot "VERDICT.txt"

$probeWallSec = 35
$closeWallSec = 90
$pollSec = 120
$maxCloseFails = 3

$PID | Set-Content $pidFile -Encoding ascii
"FASTCLOSE start $(Get-Date -Format o) pid=$PID" | Add-Content $log

function Test-WindowAuthorized {
    if (-not (Test-Path $authMarker)) { return $false }
    $line = Get-Content $authMarker -Raw
    if ($line -match 'authorized_until=(.+)') {
        try {
            $until = [datetime]::Parse($Matches[1].Trim())
            return (Get-Date) -lt $until
        } catch { return $false }
    }
    return $false
}

function Invoke-RemoteBash {
    param([string]$Script, [int]$WallSec = 35)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "ssh"
    $psi.Arguments = "-o ConnectTimeout=15 -o BatchMode=yes -o ServerAliveInterval=5 -o ServerAliveCountMax=3 rick@187.77.60.169 bash -s"
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.StandardInput.Write($Script)
    $p.StandardInput.Close()
    if (-not $p.WaitForExit($WallSec * 1000)) {
        try { $p.Kill() } catch {}
        return "PROBE_FAIL wall=${WallSec}s"
    }
    return ($p.StandardOutput.ReadToEnd() + $p.StandardError.ReadToEnd()).Trim()
}

$probeScript = @'
set -euo pipefail
L3=$(grep '^RICK_COPILOT_CLI_EXECUTE=' ~/.config/openclaw/copilot-cli.env | cut -d= -f2)
L4=$(grep 'activated:' ~/umbral-agent-stack/config/tool_policy.yaml | head -1)
NFT=$(sudo -n nft list table inet copilot_egress >/dev/null 2>&1 && echo PRESENT || echo ABSENT)
echo "GATESTATE L3=$L3 L4=$L4 NFT=$NFT"
'@

$closeScript = @'
set -euo pipefail
cd ~/umbral-agent-stack
bash scripts/pit/pit_broker_window.sh close --execute 2>&1 || true
'@

function Get-GateState {
    $out = Invoke-RemoteBash -Script $probeScript -WallSec $probeWallSec
    if ($out -match 'PROBE_FAIL') { return @{ state = "PROBE_FAIL"; raw = $out } }
    $l3 = if ($out -match 'L3=(\w+)') { $Matches[1] } else { "?" }
    $l4 = if ($out -match 'activated:\s*(\w+)') { $Matches[1] } else { "?" }
    $nft = if ($out -match 'NFT=(\w+)') { $Matches[1] } else { "?" }
    $closed = ($l3 -eq "false") -and ($l4 -eq "false") -and ($nft -eq "ABSENT")
    return @{ state = if ($closed) { "CLOSED" } else { "OPEN" }; raw = $out }
}

$closeFails = 0
while (-not (Test-Path $VERDICT)) {
    if (Test-WindowAuthorized) {
        "$(Get-Date -Format o) WINDOW_AUTHORIZED — probe only" | Add-Content $log
        Start-Sleep -Seconds $pollSec
        continue
    }
    $g = Get-GateState
    if ($g.state -eq "PROBE_FAIL") {
        "$(Get-Date -Format o) PROBE_FAIL — no close" | Add-Content $log
        Start-Sleep -Seconds $pollSec
        continue
    }
    if ($g.state -eq "CLOSED") {
        "$(Get-Date -Format o) gates CLOSED OK :: $($g.raw)" | Add-Content $log
        $closeFails = 0
    } else {
        "$(Get-Date -Format o) gates OPEN — close --execute" | Add-Content $log
        Invoke-RemoteBash -Script $closeScript -WallSec $closeWallSec | Add-Content $log
        $g2 = Get-GateState
        if ($g2.state -ne "CLOSED") {
            $closeFails++
            if ($closeFails -ge $maxCloseFails) {
                "EMERGENCY: manual close required — pit_broker_window.sh close --execute" | Set-Content $emergency
            }
        } else { $closeFails = 0 }
    }
    Start-Sleep -Seconds $pollSec
}

$g = Get-GateState
if ($g.state -eq "CLOSED") { "CONFIRMED CLOSED" | Set-Content $postVerdict } else { "GATES OPEN post-VERDICT" | Set-Content $postVerdict }
if (Test-Path $authMarker) { Remove-Item $authMarker -Force }
