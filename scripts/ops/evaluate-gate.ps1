# P10-SEC63 GATE evaluator (Windows Copilot, FASE W2) - READ-ONLY.
# Parses monitor\ssh-probe.log produced by the SSH monitor and decides GO / NO-GO
# for launching the Copilot-VPS Executor (pit_openclaw_broker_run.sh --broker-real).
#
# This script NEVER opens an ssh session, NEVER touches VPS gates, NEVER launches
# the Executor. It only reads local evidence and emits a verdict artifact.
#
# Usage:
#   powershell -NoProfile -File evaluate-gate.ps1 [-EvidRoot <path>] [-RequiredFailFreeMin 120]
#
# Emits:
#   EVID\GATE-EVAL-<yyyyMMdd-HHmmss>.txt   (canonical evaluation artifact)
#   EVID\GO-STATUS.txt                     (refreshed latest verdict summary)
# Returns: verdict object on the pipeline (Verdict = GO | NO-GO).

param(
    [string]$EvidRoot = "$env:USERPROFILE\.coord-ag-evidence\pit-p10-sec63-retry-20260623",
    [int]$RequiredFailFreeMin = 120
)

$ErrorActionPreference = "Stop"

function Evaluate-Sec63Gate {
    param(
        [string]$EvidRoot,
        [int]$RequiredFailFreeMin = 120
    )

    $mon       = Join-Path $EvidRoot "monitor"
    $log       = Join-Path $mon "ssh-probe.log"
    $abortFile = Join-Path $mon "ABORT_SSH.txt"
    $authFile  = Join-Path $EvidRoot "00-authorization.txt"
    $verdict   = Join-Path $EvidRoot "VERDICT.txt"
    $override  = Join-Path $EvidRoot "RISK_OVERRIDE_SSH.txt"

    # --- parse probe log -----------------------------------------------------
    $events = New-Object System.Collections.Generic.List[object]
    if (Test-Path $log) {
        foreach ($l in (Get-Content $log)) {
            if ($l -match '^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+OK') {
                $events.Add([pscustomobject]@{ ts = [datetime]::ParseExact($Matches[1],'yyyy-MM-dd HH:mm:ss',$null); kind = 'OK'; streak = 0 })
            }
            elseif ($l -match '^===\s*FAIL.*?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?streak=(\d+)') {
                $events.Add([pscustomobject]@{ ts = [datetime]::ParseExact($Matches[1],'yyyy-MM-dd HH:mm:ss',$null); kind = 'FAIL'; streak = [int]$Matches[2] })
            }
        }
    }

    $okN   = ($events | Where-Object kind -eq 'OK').Count
    $failN = ($events | Where-Object kind -eq 'FAIL').Count
    $haveData = $events.Count -gt 0
    $first = if ($haveData) { $events[0].ts }  else { $null }
    $last  = if ($haveData) { $events[-1].ts } else { $null }
    $maxStreak = if ($failN -gt 0) { ($events | Where-Object kind -eq 'FAIL' | Measure-Object streak -Maximum).Maximum } else { 0 }

    # longest continuous fail-free window (OK->OK between FAIL boundaries)
    $runStart = $null; $runLastOk = $null
    $best = [timespan]::Zero; $bestS = $null; $bestE = $null
    foreach ($e in $events) {
        if ($e.kind -eq 'OK') {
            if (-not $runStart) { $runStart = $e.ts }
            $runLastOk = $e.ts
        } else {
            if ($runStart -and $runLastOk) {
                $w = $runLastOk - $runStart
                if ($w -gt $best) { $best = $w; $bestS = $runStart; $bestE = $runLastOk }
            }
            $runStart = $null; $runLastOk = $null
        }
    }
    if ($runStart -and $runLastOk) {
        $w = $runLastOk - $runStart
        if ($w -gt $best) { $best = $w; $bestS = $runStart; $bestE = $runLastOk }
    }

    $lastFail = $events | Where-Object kind -eq 'FAIL' | Select-Object -Last 1
    $curClean = if ($lastFail) { $last - $lastFail.ts } elseif ($haveData) { $last - $first } else { [timespan]::Zero }
    $cut    = if ($haveData) { $last.AddHours(-2) } else { (Get-Date) }
    $fail2h = ($events | Where-Object { $_.kind -eq 'FAIL' -and $_.ts -ge $cut }).Count
    $soak   = if ($haveData) { $last - $first } else { [timespan]::Zero }

    # health proxy (read-only): age of the most recent OK probe
    $lastOk = $events | Where-Object kind -eq 'OK' | Select-Object -Last 1
    $lastOkAgeMin = if ($lastOk) { ((Get-Date) - $lastOk.ts).TotalMinutes } else { [double]::PositiveInfinity }
    $recentProbeOk = ($lastOkAgeMin -le 5)

    # --- safety / authorization checks --------------------------------------
    $abortPresent   = Test-Path $abortFile
    $verdictPresent = Test-Path $verdict
    $overridePresent = Test-Path $override

    $authSentences = @(
        "autorizo P10 sec63 broker-real egress 3 lanes copilot_cli execute real",
        "ok, arranca"
    )
    $authOk = $false
    if (Test-Path $authFile) {
        $authLines = @(Get-Content $authFile | ForEach-Object { $_.Trim() })
        $authOk = ($authSentences | ForEach-Object { $authLines -contains $_ }) -notcontains $false
    }

    # --- GO criteria ---------------------------------------------------------
    $failFreeOk = ($best.TotalMinutes -ge $RequiredFailFreeMin)
    $defaultGo  = $failFreeOk -and (-not $abortPresent) -and $authOk -and $recentProbeOk
    $effectiveGo = $defaultGo -or $overridePresent

    $reasons = New-Object System.Collections.Generic.List[string]
    if (-not $failFreeOk)   { $reasons.Add(("fail-free window {0:n1} min < {1} min required" -f $best.TotalMinutes, $RequiredFailFreeMin)) }
    if ($abortPresent)      { $reasons.Add("ABORT_SSH.txt present (>=3 consecutive fails)") }
    if (-not $authOk)       { $reasons.Add("00-authorization.txt missing one/both required sentences") }
    if (-not $recentProbeOk){ $reasons.Add(("no OK probe in last 5 min (last OK {0:n1} min ago)" -f $lastOkAgeMin)) }
    if ($verdictPresent)    { $reasons.Add("VERDICT.txt already present (run already concluded)") }

    [pscustomobject]@{
        EvalTime            = (Get-Date)
        HaveData            = $haveData
        SoakStart           = $first
        SoakEnd             = $last
        SoakMin             = [math]::Round($soak.TotalMinutes,1)
        OkCount             = $okN
        FailCount           = $failN
        MaxStreak           = $maxStreak
        LongestFailFreeMin  = [math]::Round($best.TotalMinutes,1)
        LongestFailFreeFrom = $bestS
        LongestFailFreeTo   = $bestE
        CurrentCleanMin     = [math]::Round($curClean.TotalMinutes,1)
        FailsLast2h         = $fail2h
        LastOkAgeMin        = [math]::Round($lastOkAgeMin,1)
        RecentProbeOk       = $recentProbeOk
        AbortPresent        = $abortPresent
        AuthOk              = $authOk
        OverridePresent     = $overridePresent
        VerdictPresent      = $verdictPresent
        RequiredFailFreeMin = $RequiredFailFreeMin
        DefaultGo           = $defaultGo
        Verdict             = if ($effectiveGo) { "GO" } else { "NO-GO" }
        Reasons             = $reasons
    }
}

$r = Evaluate-Sec63Gate -EvidRoot $EvidRoot -RequiredFailFreeMin $RequiredFailFreeMin

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evalFile = Join-Path $EvidRoot "GATE-EVAL-$stamp.txt"

$nl = [Environment]::NewLine
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("P10-SEC63 - GATE EVALUATION (Windows Copilot, read-only)")
[void]$sb.AppendLine("=========================================================")
[void]$sb.AppendLine(("Generated : {0:yyyy-MM-dd HH:mm:ss zzz}" -f $r.EvalTime))
[void]$sb.AppendLine("Surface   : Windows workstation - read-only gate eval (no ssh, no gate change, no Executor)")
[void]$sb.AppendLine("Source    : monitor\ssh-probe.log (live VPS truth via SSH monitor)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("GATE CRITERIA (default GO)")
[void]$sb.AppendLine("--------------------------")
[void]$sb.AppendLine((" - continuous fail-free window >= {0} min" -f $r.RequiredFailFreeMin))
[void]$sb.AppendLine(" - ABORT_SSH.txt absent")
[void]$sb.AppendLine(" - 00-authorization.txt present with both sec63 sentences")
[void]$sb.AppendLine(" - recent OK probe (link healthy now)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("MEASURED")
[void]$sb.AppendLine("--------")
if ($r.HaveData) {
    [void]$sb.AppendLine((" soak window ............ {0:yyyy-MM-dd HH:mm:ss} -> {1:yyyy-MM-dd HH:mm:ss}  ({2} min)" -f $r.SoakStart,$r.SoakEnd,$r.SoakMin))
    [void]$sb.AppendLine((" probes ................. {0} OK / {1} FAIL" -f $r.OkCount,$r.FailCount))
    [void]$sb.AppendLine((" max fail streak ........ {0}  (ABORT threshold = 3)" -f $r.MaxStreak))
    [void]$sb.AppendLine((" LONGEST fail-free ...... {0} min  ({1:HH:mm:ss} -> {2:HH:mm:ss})" -f $r.LongestFailFreeMin,$r.LongestFailFreeFrom,$r.LongestFailFreeTo))
    [void]$sb.AppendLine((" current clean streak ... {0} min" -f $r.CurrentCleanMin))
    [void]$sb.AppendLine((" FAILs last 2h .......... {0}" -f $r.FailsLast2h))
    [void]$sb.AppendLine((" last OK probe age ...... {0} min  (recentProbeOk={1})" -f $r.LastOkAgeMin,$r.RecentProbeOk))
} else {
    [void]$sb.AppendLine(" NO PROBE DATA FOUND - monitor\ssh-probe.log empty or missing")
}
[void]$sb.AppendLine("")
[void]$sb.AppendLine("SAFETY / AUTH")
[void]$sb.AppendLine("-------------")
[void]$sb.AppendLine((" ABORT_SSH.txt .......... {0}" -f $(if ($r.AbortPresent) {'PRESENT'} else {'absent'})))
[void]$sb.AppendLine((" 00-authorization.txt ... {0}" -f $(if ($r.AuthOk) {'OK (both sentences)'} else {'INCOMPLETE'})))
[void]$sb.AppendLine((" VERDICT.txt ............ {0}" -f $(if ($r.VerdictPresent) {'PRESENT'} else {'absent (pre-run)'})))
[void]$sb.AppendLine((" RISK_OVERRIDE_SSH.txt .. {0}" -f $(if ($r.OverridePresent) {'PRESENT (David override active)'} else {'absent'})))
[void]$sb.AppendLine("")
[void]$sb.AppendLine(("VERDICT: {0}" -f $r.Verdict))
[void]$sb.AppendLine("--------")
if ($r.Verdict -eq "GO") {
    if ($r.OverridePresent -and -not $r.DefaultGo) {
        [void]$sb.AppendLine(" GO BY OVERRIDE - default criteria NOT met; RISK_OVERRIDE_SSH.txt present.")
    } else {
        [void]$sb.AppendLine(" Default GO criteria satisfied. Proceed to FASE W3 (window marker) then Copilot-VPS Executor.")
    }
} else {
    [void]$sb.AppendLine(" Executor NOT launched. Continue soak. Re-evaluate in 30-60 min.")
    foreach ($why in $r.Reasons) { [void]$sb.AppendLine(("   - {0}" -f $why)) }
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine(" OVERRIDE: only if David writes literally: GO P10 sec63 at own risk")
    [void]$sb.AppendLine("           (then create EVID\RISK_OVERRIDE_SSH.txt with metrics and re-run).")
}
[void]$sb.AppendLine("")
[void]$sb.AppendLine("SURFACE SPLIT: Executor (pit_openclaw_broker_run.sh --broker-real) is Copilot-VPS only.")
[void]$sb.AppendLine("Windows never runs it, never opens gates, never restarts the gateway.")

$sb.ToString() | Set-Content $evalFile -Encoding utf8

# refresh GO-STATUS.txt with the latest summary
$go = New-Object System.Text.StringBuilder
[void]$go.AppendLine(("P10-SEC63 GATE STATUS - {0:yyyy-MM-dd HH:mm:ss}" -f $r.EvalTime))
[void]$go.AppendLine("====================================")
[void]$go.AppendLine(("Verdict: {0}" -f $r.Verdict) + $(if ($r.Verdict -eq 'NO-GO') {'  (Executor NOT launched - correct)'} else {'  (proceed to W3 handoff)'}))
[void]$go.AppendLine("")
[void]$go.AppendLine("Last evaluation:")
[void]$go.AppendLine(("- Longest fail-free window: {0} min (need >= {1} min continuous)" -f $r.LongestFailFreeMin,$r.RequiredFailFreeMin))
[void]$go.AppendLine(("- Total FAIL(TIMEOUT): {0}   FAILs last 2h: {1}" -f $r.FailCount,$r.FailsLast2h))
[void]$go.AppendLine(("- Max fail streak: {0} (ABORT at 3)   ABORT_SSH.txt: {1}" -f $r.MaxStreak,$(if ($r.AbortPresent) {'present'} else {'absent'})))
[void]$go.AppendLine(("- 00-authorization.txt: {0}" -f $(if ($r.AuthOk) {'OK'} else {'INCOMPLETE'})))
[void]$go.AppendLine(("- Override: {0}" -f $(if ($r.OverridePresent) {'PRESENT'} else {'absent'})))
[void]$go.AppendLine(("- Artifact: GATE-EVAL-{0}.txt" -f $stamp))
[void]$go.AppendLine("")
[void]$go.AppendLine("Next: continue soak; re-evaluate in 30-60 min; Executor stays parked until GO.")
$go.ToString() | Set-Content (Join-Path $EvidRoot "GO-STATUS.txt") -Encoding utf8

Write-Host ("GATE VERDICT = {0}   (longest fail-free {1} min / need {2})" -f $r.Verdict,$r.LongestFailFreeMin,$r.RequiredFailFreeMin)
Write-Host ("Artifact: {0}" -f $evalFile)
$r
