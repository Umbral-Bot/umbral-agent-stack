# Validate redaction: scan stage and Drive for residual secret patterns.
# Two-pass: collect raw matches, then ignore lines that are already [REDACTED*] markers.
param(
  [string]$Root = 'C:\AGE_STAGE\ai-agents-export-2026-04-27'
)

$ErrorActionPreference = 'Stop'
Write-Host "Validating: $Root" -ForegroundColor Cyan
$textExt = [System.Collections.Generic.HashSet[string]]::new([string[]]@('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp','.xml','.html','.csv'))

$rawRx = [regex]::new('(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|gho_[A-Za-z0-9]{30,}|sk-ant-[A-Za-z0-9\-_]{30,}|sk-[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_\-]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,})', [System.Text.RegularExpressions.RegexOptions]::Compiled)

$residuals = New-Object System.Collections.ArrayList
$scanned = 0
foreach ($f in [System.IO.Directory]::EnumerateFiles($Root, '*', [System.IO.SearchOption]::AllDirectories)) {
  $ext = [System.IO.Path]::GetExtension($f).ToLower()
  if (-not $textExt.Contains($ext)) { continue }
  try {
    $fi = [System.IO.FileInfo]::new('\\?\' + $f)
    if ($fi.Length -gt 50MB) { continue }
    $c = [System.IO.File]::ReadAllText('\\?\' + $f)
  } catch { continue }
  $scanned++
  $matches = $rawRx.Matches($c)
  foreach ($m in $matches) {
    # ignore matches inside a [REDACTED-...] marker (false positives)
    $start = [Math]::Max(0, $m.Index - 12)
    $ctxBefore = $c.Substring($start, $m.Index - $start)
    if ($ctxBefore -match '\[REDACTED') { continue }
    $null = $residuals.Add([pscustomobject]@{
      File = $f
      Match = $m.Value.Substring(0, [Math]::Min(40, $m.Value.Length))
    })
  }
}

Write-Host ("Files scanned: {0}" -f $scanned) -ForegroundColor Cyan
Write-Host ("Residual hits: {0}" -f $residuals.Count) -ForegroundColor $(if ($residuals.Count -eq 0) { 'Green' } else { 'Red' })
if ($residuals.Count -gt 0) {
  $residuals | Group-Object File | Sort-Object Count -Descending | Select-Object -First 30 | Format-Table Count, Name -AutoSize
}
