<#
  Curated AI agents export.
  Stages locally under C:\AGE_STAGE\ai-agents-export-2026-04-27 (short path),
  redacts secrets, then robocopies to Google Drive using \\?\ long-path prefix.
#>

$ErrorActionPreference = 'Stop'

$stage = 'C:\AGE_STAGE\ai-agents-export-2026-04-27'
$drive = 'G:\Mi unidad\06_Sistemas y Automatizaciones\90_Archivado\ai-agents-export-2026-04-27'

# Wipe stage to ensure clean curated build
if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force -Path $stage | Out-Null

# Universal junk to exclude (cache, binary, recoverable)
$xdGlobal = @(
  'Cache','Code Cache','GPUCache','CachedData','CachedExtensionVSIXs','CachedProfilesData',
  'blob_storage','CacheStorage','ShaderCache','DawnCache','DawnGraphiteCache','GrShaderCache',
  'Crashpad','Network','Service Worker','WebStorage','Shared Dictionary',
  'component_crx_cache','extensions_crx_cache','optimization_guide_prediction_model_downloads',
  'process-monitor','clp','DawnWebGPUCache','Code Cache - Index'
)
$xfGlobal = @('*.exe','*.dll','*.vhdx','*.pak','*.node','*.lib','*.crash','*.dmp')

function Robo-Copy {
  param([string]$Src, [string]$Dst, [string[]]$Xd = @(), [string[]]$Xf = @())
  if (-not (Test-Path $Src)) { Write-Output "  SKIP (missing): $Src"; return }
  New-Item -ItemType Directory -Force -Path $Dst | Out-Null
  $args = @($Src, $Dst, '/E','/NFL','/NDL','/NJH','/NJS','/NP','/R:1','/W:1','/XJ','/MT:8')
  foreach ($d in ($xdGlobal + $Xd)) { $args += '/XD'; $args += $d }
  foreach ($f in ($xfGlobal + $Xf)) { $args += '/XF'; $args += $f }
  Write-Output ("  COPY $Src -> $Dst")
  & robocopy @args | Out-Null
}

# ----- CODEX -----
Write-Output "== CODEX =="
$codexSrc = "$env:USERPROFILE\.codex"
$codexDst = "$stage\codex"
Robo-Copy $codexSrc $codexDst -Xd @('cache','tmp','.tmp','.sandbox','.sandbox-bin','.sandbox-secrets','vendor_imports') `
  -Xf @('*.sqlite-wal','*.sqlite-shm','logs_2.sqlite')

# ----- CURSOR -----
Write-Output "== CURSOR =="
# AppData\Roaming\Cursor: keep User + IndexedDB + Local Storage + Session Storage
$cursorRoamSrc = "$env:APPDATA\Cursor"
$cursorRoamDst = "$stage\cursor\Cursor"
foreach ($keep in @('User','IndexedDB','Local Storage','Session Storage','logs','clp','Dictionaries')) {
  $s = Join-Path $cursorRoamSrc $keep
  $d = Join-Path $cursorRoamDst $keep
  Robo-Copy $s $d
}
# .cursor: drop extensions/cache, keep everything else
Robo-Copy "$env:USERPROFILE\.cursor" "$stage\cursor\.cursor" -Xd @('extensions','tmp','cache','.cache')

# ----- ANTIGRAVITY -----
Write-Output "== ANTIGRAVITY =="
$agRoamSrc = "$env:APPDATA\Antigravity"
$agRoamDst = "$stage\antigravity\Antigravity"
foreach ($keep in @('User','IndexedDB','Local Storage','Session Storage','logs','Dictionaries')) {
  $s = Join-Path $agRoamSrc $keep
  $d = Join-Path $agRoamDst $keep
  Robo-Copy $s $d
}
Robo-Copy "$env:USERPROFILE\.antigravity" "$stage\antigravity\.antigravity" -Xd @('extensions','tmp','cache','.cache')

# ----- COPILOT (small, keep all) -----
Write-Output "== COPILOT =="
Robo-Copy "$env:USERPROFILE\.copilot" "$stage\copilot\.copilot"

# ----- CLAUDE -----
Write-Output "== CLAUDE =="
$claudeRoamSrc = "$env:APPDATA\Claude"
$claudeRoamDst = "$stage\claude\Claude"
foreach ($keep in @('IndexedDB','Local Storage','Session Storage','User Data','Claude Extensions','local-agent-mode-sessions','logs','Dictionaries')) {
  $s = Join-Path $claudeRoamSrc $keep
  $d = Join-Path $claudeRoamDst $keep
  Robo-Copy $s $d -Xd @('Cache','Code Cache','GPUCache','blob_storage','Service Worker','CacheStorage')
}
# Local AppData Claude (very small)
Robo-Copy "$env:LOCALAPPDATA\Claude" "$stage\claude\Claude_Local"
# .claude (skills/agents/configs - keep ALL)
Robo-Copy "$env:USERPROFILE\.claude" "$stage\claude\.claude"

Write-Output ""
Write-Output "===== Stage build complete. Sizes: ====="
Get-ChildItem $stage -Directory | ForEach-Object {
  $sz = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 2)
  $cnt = (Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object).Count
  [pscustomobject]@{ Platform = $_.Name; Files = $cnt; SizeMB = $sz }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize
$tot = (Get-ChildItem $stage -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Output ("TOTAL stage: " + [math]::Round($tot/1MB,2) + " MB (" + [math]::Round($tot/1GB,2) + " GB)")

# ----- REDACTION -----
Write-Output ""
Write-Output "===== Redacting secrets in stage ====="
$textExt = @('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp','.xml','.html','.csv')
$patterns = @(
  @{ Pattern='ghp_[A-Za-z0-9]{30,}';                                              Repl='[REDACTED-PAT]' },
  @{ Pattern='github_pat_[A-Za-z0-9_]{50,}';                                      Repl='[REDACTED-PAT]' },
  @{ Pattern='gho_[A-Za-z0-9]{30,}';                                              Repl='[REDACTED-PAT]' },
  @{ Pattern='sk-ant-[A-Za-z0-9\-_]{30,}';                                        Repl='[REDACTED-ANTHROPIC]' },
  @{ Pattern='sk-[A-Za-z0-9]{30,}';                                               Repl='[REDACTED-OPENAI]' },
  @{ Pattern='AIza[0-9A-Za-z_\-]{30,}';                                           Repl='[REDACTED-GOOGLE]' },
  @{ Pattern='xox[baprs]-[A-Za-z0-9\-]{10,}';                                     Repl='[REDACTED-SLACK]' },
  @{ Pattern='AKIA[0-9A-Z]{16}';                                                  Repl='[REDACTED-AWS]' },
  @{ Pattern='eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}';  Repl='[REDACTED-JWT]' },
  @{ Pattern='Bearer\s+[A-Za-z0-9._\-]{20,}';                                     Repl='Bearer [REDACTED]' },
  @{ Pattern='(?i)password["'':\s=]+[^\s"'',}]+';                                 Repl='password=[REDACTED]' }
)
$userName = [regex]::Escape($env:USERNAME)
$proc = 0; $skip = 0
Get-ChildItem $stage -Recurse -File -EA SilentlyContinue | ForEach-Object {
  $f = $_
  if ($textExt -notcontains $f.Extension.ToLower()) { $skip++; return }
  if ($f.Length -gt 50MB) { $skip++; return }
  try {
    # Use \\?\ prefix to handle long paths
    $longPath = '\\?\' + $f.FullName
    $content = [System.IO.File]::ReadAllText($longPath)
  } catch { $skip++; return }
  $orig = $content
  foreach ($p in $patterns) { $content = [regex]::Replace($content, $p.Pattern, $p.Repl) }
  $content = [regex]::Replace($content, $userName, '[USER]')
  if ($content -ne $orig) {
    try { [System.IO.File]::WriteAllText('\\?\' + $f.FullName, $content); $proc++ } catch { $skip++ }
  } else { $proc++ }
}
Write-Output ("Redacted text files: $proc | skipped binary/large: $skip")

# ----- ROBOCOPY STAGE -> DRIVE with \\?\ long path prefix -----
Write-Output ""
Write-Output "===== Mirroring stage -> Google Drive (with long-path support) ====="
$srcLP = '\\?\' + $stage
$dstLP = '\\?\' + $drive
New-Item -ItemType Directory -Force -Path $drive | Out-Null
# /MIR mirrors (deletes obsolete) - we want additive curated. Use /E to add only.
$mirArgs = @($srcLP, $dstLP, '/E','/NFL','/NDL','/NJH','/NJS','/NP','/R:1','/W:1','/XJ','/MT:8')
& robocopy @mirArgs | Out-Null

Write-Output ""
Write-Output "===== Drive final sizes ====="
Get-ChildItem $drive -Directory -EA SilentlyContinue | ForEach-Object {
  $sz = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 2)
  $cnt = (Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object).Count
  [pscustomobject]@{ Folder = $_.Name; Files = $cnt; SizeMB = $sz }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize
$totDrive = (Get-ChildItem $drive -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Output ("TOTAL Drive: " + [math]::Round($totDrive/1MB,2) + " MB")

Write-Output ""
Write-Output "Stage kept at: $stage"
Write-Output "Drive folder:  $drive"
