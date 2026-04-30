#requires -Version 7
# Run AFTER robocopy finishes (when terminal shows "ExitCode=N", N in 0..7 = OK)
$ErrorActionPreference = 'Stop'
$Stage = 'C:\AGE_STAGE\ai-agents-export-2026-04-27'
$Dst   = 'G:\Mi unidad\06_Sistemas y Automatizaciones\90_Archivado\ai-agents-export-2026-04-27'

Write-Host "`n=== File counts: stage vs drive ===" -ForegroundColor Cyan
$rows = foreach ($p in 'antigravity','claude','codex','copilot','cursor') {
    $s = Join-Path $Stage $p; $d = Join-Path $Dst $p
    $sc = if (Test-Path $s) { ([System.IO.Directory]::EnumerateFiles($s,'*',[System.IO.SearchOption]::AllDirectories) | Measure-Object).Count } else { 0 }
    $dc = if (Test-Path $d) { ([System.IO.Directory]::EnumerateFiles($d,'*',[System.IO.SearchOption]::AllDirectories) | Measure-Object).Count } else { 0 }
    [pscustomobject]@{ Platform=$p; Stage=$sc; Drive=$dc; Diff=($sc-$dc) }
}
$rows | Format-Table -AutoSize

$totS = ($rows | Measure-Object Stage -Sum).Sum
$totD = ($rows | Measure-Object Drive -Sum).Sum
Write-Host "TOTAL: stage=$totS drive=$totD diff=$($totS-$totD)" -ForegroundColor Yellow

Write-Host "`n=== Validating Drive copy for residual secrets ===" -ForegroundColor Cyan
& pwsh -NoProfile -ExecutionPolicy Bypass -File 'c:\GitHub\umbral-agent-stack\scripts\validate_redaction_v2.ps1' -Root $Dst
