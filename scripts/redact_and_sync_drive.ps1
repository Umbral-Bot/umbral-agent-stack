# Parallel redactor for the curated stage.
$ErrorActionPreference = 'Stop'

$stage = 'C:\AGE_STAGE\ai-agents-export-2026-04-27'
$drive = 'G:\Mi unidad\06_Sistemas y Automatizaciones\90_Archivado\ai-agents-export-2026-04-27'

$textExt = @('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp','.xml','.html','.csv')
$userName = $env:USERNAME

Write-Host "Enumerating files..." -ForegroundColor Cyan
$sw = [Diagnostics.Stopwatch]::StartNew()
$files = Get-ChildItem $stage -Recurse -File -EA SilentlyContinue |
  Where-Object { ($textExt -contains $_.Extension.ToLower()) -and ($_.Length -le 50MB) }
Write-Host ("Files to redact: {0}  ({1} MB)  enum={2}s" -f $files.Count,
  [math]::Round((($files | Measure-Object Length -Sum).Sum)/1MB,1),
  [math]::Round($sw.Elapsed.TotalSeconds,1)) -ForegroundColor Cyan

$counter = [ref]0
$total = $files.Count
$swR = [Diagnostics.Stopwatch]::StartNew()

$files | ForEach-Object -ThrottleLimit 12 -Parallel {
  $patterns = @(
    @{ P='ghp_[A-Za-z0-9]{30,}';                                              R='[REDACTED-PAT]' },
    @{ P='github_pat_[A-Za-z0-9_]{50,}';                                      R='[REDACTED-PAT]' },
    @{ P='gho_[A-Za-z0-9]{30,}';                                              R='[REDACTED-PAT]' },
    @{ P='sk-ant-[A-Za-z0-9\-_]{30,}';                                        R='[REDACTED-ANTHROPIC]' },
    @{ P='sk-[A-Za-z0-9]{30,}';                                               R='[REDACTED-OPENAI]' },
    @{ P='AIza[0-9A-Za-z_\-]{30,}';                                           R='[REDACTED-GOOGLE]' },
    @{ P='xox[baprs]-[A-Za-z0-9\-]{10,}';                                     R='[REDACTED-SLACK]' },
    @{ P='AKIA[0-9A-Z]{16}';                                                  R='[REDACTED-AWS]' },
    @{ P='eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}';  R='[REDACTED-JWT]' },
    @{ P='Bearer\s+[A-Za-z0-9._\-]{20,}';                                     R='Bearer [REDACTED]' },
    @{ P='(?i)password["'':\s=]+[^\s"'',}]+';                                 R='password=[REDACTED]' }
  )
  $userRx = [regex]::Escape($using:userName)
  $longPath = '\\?\' + $_.FullName
  try {
    $content = [System.IO.File]::ReadAllText($longPath)
  } catch { return }
  $orig = $content
  foreach ($p in $patterns) { $content = [regex]::Replace($content, $p.P, $p.R) }
  $content = [regex]::Replace($content, $userRx, '[USER]')
  if ($content -ne $orig) {
    try { [System.IO.File]::WriteAllText($longPath, $content) } catch {}
  }
}

$swR.Stop()
Write-Host ("Redaction complete in {0}s" -f [math]::Round($swR.Elapsed.TotalSeconds,1)) -ForegroundColor Green

Write-Host ""
Write-Host "===== Mirroring stage -> Google Drive =====" -ForegroundColor Cyan
$srcLP = '\\?\' + $stage
$dstLP = '\\?\' + $drive
New-Item -ItemType Directory -Force -Path $drive | Out-Null
$swC = [Diagnostics.Stopwatch]::StartNew()
$mirArgs = @($srcLP, $dstLP, '/E','/NFL','/NDL','/NJH','/NJS','/NP','/R:1','/W:1','/XJ','/MT:8')
& robocopy @mirArgs | Out-Null
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
