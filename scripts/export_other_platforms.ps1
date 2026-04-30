<#
  Exports Cursor / Antigravity / GitHub Copilot / Claude data dirs.
  - raw -> local Desktop (non-OneDrive): C:\Users\david\Desktop\codex-sessions-export\platforms\<platform>\<source-name>
  - redacted -> OneDrive Desktop:        C:\Users\david\OneDrive\Escritorio\codex-sessions-export-SAFE\platforms\<platform>\<source-name>
  - Skips known Electron binary caches.
  - Same secret-redaction patterns as the Codex export.
#>

$ErrorActionPreference = 'Stop'

$rawBase      = 'C:\Users\david\Desktop\codex-sessions-export\platforms'
$redactedBase = 'C:\Users\david\OneDrive\Escritorio\codex-sessions-export-SAFE\platforms'
New-Item -ItemType Directory -Force -Path $rawBase | Out-Null
New-Item -ItemType Directory -Force -Path $redactedBase | Out-Null

# Source paths grouped by platform. Case-insensitive Windows: dedupe by lower-case.
$sources = @(
  @{ Platform='cursor';      Path='C:\Users\david\AppData\Roaming\Cursor'      },
  @{ Platform='cursor';      Path='C:\Users\david\.cursor'                     },
  @{ Platform='antigravity'; Path='C:\Users\david\AppData\Roaming\Antigravity' },
  @{ Platform='antigravity'; Path='C:\Users\david\.antigravity'                },
  @{ Platform='copilot';     Path='C:\Users\david\.copilot'                    },
  @{ Platform='claude';      Path='C:\Users\david\AppData\Roaming\Claude'      },
  @{ Platform='claude';      Path='C:\Users\david\AppData\Local\Claude'        },
  @{ Platform='claude';      Path='C:\Users\david\.claude'                     }
)

# Robocopy directory exclusions (binary caches that bloat without value)
$xd = @(
  'Cache','Code Cache','GPUCache','CachedData','blob_storage',
  'CacheStorage','ShaderCache','DawnCache','DawnGraphiteCache','GrShaderCache',
  'Crashpad','Partitions','Network','Code Cache - Index','component_crx_cache',
  'extensions_crx_cache','optimization_guide_prediction_model_downloads',
  'GraphiteDawnCache'
)

# --- Step A: copy each source to raw/<platform>/<leaf>
foreach ($s in $sources) {
  if (-not (Test-Path $s.Path)) { continue }
  $leaf = Split-Path -Leaf $s.Path
  $dest = Join-Path (Join-Path $rawBase $s.Platform) $leaf
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Write-Output ("[RAW]   {0} -> {1}" -f $s.Path, $dest)
  $args = @($s.Path, $dest, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1', '/XJ')
  foreach ($d in $xd) { $args += '/XD'; $args += $d }
  & robocopy @args | Out-Null
}

# --- Step B: mirror raw -> redacted base then redact
Write-Output "Mirroring raw -> redacted (this may take a while)..."
foreach ($plat in (Get-ChildItem $rawBase -Directory)) {
  $destPlat = Join-Path $redactedBase $plat.Name
  New-Item -ItemType Directory -Force -Path $destPlat | Out-Null
  & robocopy $plat.FullName $destPlat /E /NFL /NDL /NJH /NJS /NP /R:1 /W:1 /XJ | Out-Null
}

# --- Step C: redact text files in redacted base
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
$processed = 0; $skipped = 0
Get-ChildItem -Path $redactedBase -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $f = $_
  if ($textExt -notcontains $f.Extension.ToLower()) { $skipped++; return }
  if ($f.Length -gt 50MB) { $skipped++; return }
  try { $content = [System.IO.File]::ReadAllText($f.FullName) } catch { $skipped++; return }
  $orig = $content
  foreach ($p in $patterns) { $content = [regex]::Replace($content, $p.Pattern, $p.Repl) }
  $content = [regex]::Replace($content, $userName, '[USER]')
  if ($content -ne $orig) { [System.IO.File]::WriteAllText($f.FullName, $content) }
  $processed++
}
Write-Output ("Redaction processed={0} skipped={1}" -f $processed, $skipped)

# --- Step D: validation (ignore redaction markers themselves)
$markers = @('[REDACTED]','[REDACTED-PAT]','[REDACTED-OPENAI]','[REDACTED-ANTHROPIC]','[REDACTED-GOOGLE]','[REDACTED-SLACK]','[REDACTED-AWS]','[REDACTED-JWT]')
$residuals = New-Object System.Collections.ArrayList
Get-ChildItem -Path $redactedBase -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $f = $_
  if ($textExt -notcontains $f.Extension.ToLower()) { return }
  if ($f.Length -gt 50MB) { return }
  try { $content = [System.IO.File]::ReadAllText($f.FullName) } catch { return }
  foreach ($p in $patterns) {
    foreach ($m in [regex]::Matches($content, $p.Pattern)) {
      $val = $m.Value
      $hit = $false
      foreach ($mk in $markers) { if ($val.Contains($mk)) { $hit = $true; break } }
      if ($hit) { continue }
      [void]$residuals.Add([pscustomobject]@{ File=$f.FullName; Sample=($val.Substring(0,[Math]::Min(60,$val.Length))) })
    }
  }
}
Write-Output ("Residual real-secret matches: {0}" -f $residuals.Count)
if ($residuals.Count -gt 0) {
  $residuals | Select-Object -First 20 | Format-Table -AutoSize
}

# --- Step E: per-platform sizes
Write-Output ""
Write-Output "===== Per-platform size in redacted ====="
foreach ($plat in (Get-ChildItem $redactedBase -Directory)) {
  $cnt = (Get-ChildItem $plat.FullName -Recurse -File -EA SilentlyContinue | Measure-Object).Count
  $sz  = [math]::Round((Get-ChildItem $plat.FullName -Recurse -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
  Write-Output ("  {0,-15} files={1,-7} size={2}MB" -f $plat.Name, $cnt, $sz)
}

# --- Step F: append README info
$readme = 'C:\Users\david\OneDrive\Escritorio\codex-sessions-export-SAFE\README.md'
$note = @"

## Additional platforms exported

- Cursor:      AppData\Roaming\Cursor + ~\.cursor
- Antigravity: AppData\Roaming\Antigravity + ~\.antigravity
- Copilot:     ~\.copilot
- Claude:      AppData\Roaming\Claude + AppData\Local\Claude + ~\.claude

Each platform is under platforms/<platform>/<source-leaf>/.
Binary cache directories were excluded (Cache, GPUCache, blob_storage,
ShaderCache, IndexedDB-internal stores, etc.) to keep the export reasonable.
Same redaction patterns applied. raw/ copies are stored locally at:
  C:\Users\david\Desktop\codex-sessions-export\platforms\
(NOT in OneDrive).
"@
Add-Content -Path $readme -Value $note
Write-Output "README appended."

Write-Output ""
Write-Output "DONE."
Write-Output ("SAFE folder (OneDrive): C:\Users\david\OneDrive\Escritorio\codex-sessions-export-SAFE")
Write-Output ("RAW folder (local):     C:\Users\david\Desktop\codex-sessions-export")
