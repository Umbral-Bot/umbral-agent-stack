# Fast in-stage redactor using compiled .NET regex + EnumerateFiles + sequential I/O.
# Strategy: one combined alternation regex with named groups for replacement mapping.
$ErrorActionPreference = 'Stop'

$stage = 'C:\AGE_STAGE\ai-agents-export-2026-04-27'
$drive = 'G:\Mi unidad\06_Sistemas y Automatizaciones\90_Archivado\ai-agents-export-2026-04-27'

Add-Type -AssemblyName System.IO

# Map of named-group -> replacement
$repl = [ordered]@{
  PAT       = '[REDACTED-PAT]'
  PAT2      = '[REDACTED-PAT]'
  PAT3      = '[REDACTED-PAT]'
  ANTHROPIC = '[REDACTED-ANTHROPIC]'
  OPENAI    = '[REDACTED-OPENAI]'
  GOOGLE    = '[REDACTED-GOOGLE]'
  SLACK     = '[REDACTED-SLACK]'
  AWS       = '[REDACTED-AWS]'
  JWT       = '[REDACTED-JWT]'
  BEARER    = 'Bearer [REDACTED]'
  PASSWD    = 'password=[REDACTED]'
  USER      = '[USER]'
}

$userEsc = [regex]::Escape($env:USERNAME)
$bigRx = @"
(?<PAT>ghp_[A-Za-z0-9]{30,})|(?<PAT2>github_pat_[A-Za-z0-9_]{50,})|(?<PAT3>gho_[A-Za-z0-9]{30,})|(?<ANTHROPIC>sk-ant-[A-Za-z0-9\-_]{30,})|(?<OPENAI>sk-[A-Za-z0-9]{30,})|(?<GOOGLE>AIza[0-9A-Za-z_\-]{30,})|(?<SLACK>xox[baprs]-[A-Za-z0-9\-]{10,})|(?<AWS>AKIA[0-9A-Z]{16})|(?<JWT>eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,})|(?<BEARER>Bearer\s+[A-Za-z0-9._\-]{20,})|(?<PASSWD>(?i:password)["':\s=]+[^\s"',}]+)|(?<USER>$userEsc)
"@

$rx = [regex]::new($bigRx, [System.Text.RegularExpressions.RegexOptions]::Compiled)

$evaluator = {
  param($m)
  foreach ($g in $script:repl.Keys) {
    if ($m.Groups[$g].Success) { return $script:repl[$g] }
  }
  return $m.Value
}

$textExt = [System.Collections.Generic.HashSet[string]]::new([string[]]@('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp','.xml','.html','.csv'))

Write-Host "Enumerating..." -ForegroundColor Cyan
$swE = [Diagnostics.Stopwatch]::StartNew()
$files = [System.IO.Directory]::EnumerateFiles($stage, '*', [System.IO.SearchOption]::AllDirectories)
$processed = 0
$rewrote = 0
$skipped = 0
$errored = 0
$bytes = 0L
$swR = [Diagnostics.Stopwatch]::StartNew()
$nextLog = 1000

foreach ($f in $files) {
  $ext = [System.IO.Path]::GetExtension($f).ToLower()
  if (-not $textExt.Contains($ext)) { $skipped++; continue }
  $longPath = '\\?\' + $f
  try {
    $fi = [System.IO.FileInfo]::new($longPath)
    if ($fi.Length -gt 50MB) { $skipped++; continue }
    $bytes += $fi.Length
    $content = [System.IO.File]::ReadAllText($longPath)
  } catch { $errored++; continue }
  $new = $rx.Replace($content, $evaluator)
  if ($new -ne $content) {
    try { [System.IO.File]::WriteAllText($longPath, $new); $rewrote++ } catch { $errored++ }
  }
  $processed++
  if ($processed -ge $nextLog) {
    $elapsed = $swR.Elapsed.TotalSeconds
    $rate = if ($elapsed -gt 0) { [math]::Round($processed/$elapsed,1) } else { 0 }
    Write-Host ("  processed {0} | rewrote {1} | skipped {2} | err {3} | {4} f/s | {5} MB read" -f $processed, $rewrote, $skipped, $errored, $rate, [math]::Round($bytes/1MB,1))
    $nextLog += 2000
  }
}

$swR.Stop()
Write-Host ("Redaction done: processed={0} rewrote={1} skipped={2} err={3} elapsed={4}s" -f $processed,$rewrote,$skipped,$errored,[math]::Round($swR.Elapsed.TotalSeconds,1)) -ForegroundColor Green

Write-Host ""
Write-Host "===== Robocopy stage -> Drive =====" -ForegroundColor Cyan
# NOTE: do NOT use \\?\ prefix for robocopy; it interprets that as UNC and fails.
# Modern Windows + robocopy support long paths natively.
New-Item -ItemType Directory -Force -Path $drive | Out-Null
$swC = [Diagnostics.Stopwatch]::StartNew()
& robocopy $stage $drive /E /NFL /NDL /NJH /NJS /NP /R:1 /W:1 /XJ /MT:8 | Out-Null
$swC.Stop()
Write-Host ("Robocopy done in {0}s (exit {1})" -f [math]::Round($swC.Elapsed.TotalSeconds,1), $LASTEXITCODE) -ForegroundColor Green

Write-Host ""
Write-Host "===== Drive final sizes =====" -ForegroundColor Cyan
Get-ChildItem $drive -Directory -EA SilentlyContinue | ForEach-Object {
  $g = Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue
  $sz = [math]::Round((($g | Measure-Object Length -Sum).Sum) / 1MB, 2)
  $cnt = ($g | Measure-Object).Count
  [pscustomobject]@{ Folder = $_.Name; Files = $cnt; SizeMB = $sz }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

$totDrive = (Get-ChildItem $drive -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host ("TOTAL Drive: {0} MB" -f [math]::Round($totDrive/1MB,2)) -ForegroundColor Yellow
