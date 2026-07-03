# P10-SEC63 external SSH + Hostinger monitor (Windows)
# Usage: powershell -NoProfile -File p10-sec63-ssh-monitor.ps1 [-EvidRoot <path>]
param(
    [string]$EvidRoot = "$env:USERPROFILE\.coord-ag-evidence\pit-p10-sec63-retry-20260623"
)

$ErrorActionPreference = "Continue"
$Mon = Join-Path $EvidRoot "monitor"
New-Item -ItemType Directory -Force -Path $Mon | Out-Null

$log = Join-Path $Mon "ssh-probe.log"
$statusFile = Join-Path $Mon "status.json"
$abortFile = Join-Path $Mon "ABORT_SSH.txt"
$hostingerLog = Join-Path $Mon "hostinger-snapshots.jsonl"
$pidFile = Join-Path $Mon "monitor.pid"
$VERDICT = Join-Path $EvidRoot "VERDICT.txt"

$VMID = 1431451
$sshTarget = "rick@187.77.60.169"
$probeTimeoutSec = 35
$failStreakAbort = 3
$hostingerEverySec = 300

$PID | Set-Content $pidFile -Encoding ascii
"MONITOR start $(Get-Date -Format o) pid=$PID" | Out-File $log -Encoding utf8

function Invoke-SshProbe {
    param([int]$WallSec = 35)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "ssh"
    $psi.Arguments = @(
        "-o", "ConnectTimeout=15",
        "-o", "BatchMode=yes",
        "-o", "ConnectionAttempts=1",
        "-o", "ServerAliveInterval=5",
        "-o", "ServerAliveCountMax=3",
        $sshTarget,
        "echo OK"
    ) -join " "
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    if (-not $p.WaitForExit($WallSec * 1000)) {
        try { $p.Kill() } catch {}
        return @{ ok = $false; out = "FAIL(TIMEOUT) wall=${WallSec}s"; code = -1 }
    }
    $out = ($p.StandardOutput.ReadToEnd() + $p.StandardError.ReadToEnd()).Trim()
    return @{ ok = ($p.ExitCode -eq 0); out = $out; code = $p.ExitCode }
}

$ok = 0; $fail = 0; $failStreak = 0
$lastHostinger = [datetime]::MinValue

while (-not (Test-Path $VERDICT)) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $r = Invoke-SshProbe -WallSec $probeTimeoutSec
    if ($r.ok) {
        $ok++; $failStreak = 0
        "[$ts] OK ($ok ok / $fail fail)" | Tee-Object -FilePath $log -Append
    } else {
        $fail++; $failStreak++
        @("=== FAIL $ts streak=$failStreak ===", $r.out) | Tee-Object -FilePath $log -Append
        if ($failStreak -ge $failStreakAbort) {
            "ABORT_SSH $failStreak consecutive at $ts" | Set-Content $abortFile -Encoding utf8
        }
    }

    @{
        ts = (Get-Date -Format o)
        ok = $ok
        fail = $fail
        failStreak = $failStreak
        lastProbe = $r.out
    } | ConvertTo-Json -Compress | Set-Content $statusFile -Encoding utf8

    if (((Get-Date) - $lastHostinger).TotalSeconds -ge $hostingerEverySec) {
        $lastHostinger = Get-Date
        if ($env:HOSTINGER_API_TOKEN) {
            try {
                $h = @{ Authorization = "Bearer $env:HOSTINGER_API_TOKEN" }
                $from = (Get-Date).ToUniversalTime().AddHours(-1).ToString("o")
                $to = (Get-Date).ToUniversalTime().ToString("o")
                $vm = Invoke-RestMethod "https://developers.hostinger.com/api/vps/v1/virtual-machines/$VMID" -Headers $h
                $met = Invoke-RestMethod "https://developers.hostinger.com/api/vps/v1/virtual-machines/${VMID}/metrics?date_from=$from&date_to=$to" -Headers $h
                @{ ts = (Get-Date -Format o); state = $vm.state; hostname = $vm.hostname; metrics = $met } |
                    ConvertTo-Json -Depth 6 -Compress | Add-Content $hostingerLog
            } catch {
                @{ ts = (Get-Date -Format o); error = $_.Exception.Message } |
                    ConvertTo-Json -Compress | Add-Content $hostingerLog
            }
        }
    }

    Start-Sleep -Seconds 30
}

"MONITOR end ok=$ok fail=$fail $(Get-Date -Format o)" | Add-Content $log -Encoding utf8
