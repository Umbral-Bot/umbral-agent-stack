<#
.SYNOPSIS
  Exports Codex CLI sessions to Desktop with redacted copy.
  Local-only. No network. No git. Read-only on source.
#>

$ErrorActionPreference = 'Stop'

# --- Step 1: detect sources ---
$candidates = @(
  "$env:USERPROFILE\.codex",
  "$env:APPDATA\codex",
  "$env:LOCALAPPDATA\codex",
  "$env:USERPROFILE\.config\codex",
  "$env:USERPROFILE\AppData\Roaming\codex",
  "$env:USERPROFILE\AppData\Local\codex"
) | Select-Object -Unique

$found = @()
foreach ($p in $candidates) {
  if (Test-Path $p) { $found += $p }
}

if ($found.Count -eq 0) {
  Write-Output "No standard path found, scanning USERPROFILE..."
  $extra = Get-ChildItem -Path $env:USERPROFILE -Recurse -ErrorAction SilentlyContinue -Filter "session*.json" |
            Select-Object -ExpandProperty FullName
  $extra | ForEach-Object { Write-Output "FOUND: $_" }
  if (-not $extra) { throw "No Codex sessions found." }
  $found = $extra
}

Write-Output ("Detected: " + ($found -join ', '))

# --- Step 2: dest folders ---
$dest = "$env:USERPROFILE\Desktop\codex-sessions-export"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path "$dest\raw" | Out-Null
New-Item -ItemType Directory -Force -Path "$dest\redacted" | Out-Null

# --- Step 3: copy raw ---
foreach ($src in $found) {
  $leaf = Split-Path -Leaf $src
  $target = Join-Path "$dest\raw" $leaf
  Write-Output "Copying $src -> $target"
  Copy-Item -Path $src -Destination $target -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Step 4: redact ---
Write-Output "Mirroring raw -> redacted..."
Copy-Item -Path "$dest\raw\*" -Destination "$dest\redacted" -Recurse -Force -ErrorAction SilentlyContinue

$textExt = @('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp')

$patterns = @(
  @{ Pattern = 'ghp_[A-Za-z0-9]{30,}';                                            Repl = '[REDACTED-PAT]' },
  @{ Pattern = 'github_pat_[A-Za-z0-9_]{50,}';                                    Repl = '[REDACTED-PAT]' },
  @{ Pattern = 'gho_[A-Za-z0-9]{30,}';                                            Repl = '[REDACTED-PAT]' },
  @{ Pattern = 'sk-ant-[A-Za-z0-9\-_]{30,}';                                      Repl = '[REDACTED-ANTHROPIC]' },
  @{ Pattern = 'sk-[A-Za-z0-9]{30,}';                                             Repl = '[REDACTED-OPENAI]' },
  @{ Pattern = 'AIza[0-9A-Za-z_\-]{30,}';                                         Repl = '[REDACTED-GOOGLE]' },
  @{ Pattern = 'xox[baprs]-[A-Za-z0-9\-]{10,}';                                   Repl = '[REDACTED-SLACK]' },
  @{ Pattern = 'AKIA[0-9A-Z]{16}';                                                Repl = '[REDACTED-AWS]' },
  @{ Pattern = 'eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}'; Repl = '[REDACTED-JWT]' },
  @{ Pattern = 'Bearer\s+[A-Za-z0-9._\-]{20,}';                                   Repl = 'Bearer [REDACTED]' },
  @{ Pattern = '(?i)password["'':\s=]+[^\s"'',}]+';                               Repl = 'password=[REDACTED]' }
)

$userName = [regex]::Escape($env:USERNAME)
$processed = 0
$skipped = 0
$totalFiles = (Get-ChildItem -Path "$dest\redacted" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Output "Redacting up to $totalFiles files..."

Get-ChildItem -Path "$dest\redacted" -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $f = $_
  if ($textExt -notcontains $f.Extension.ToLower()) { $skipped++; return }
  if ($f.Length -gt 50MB) { $skipped++; return }
  try {
    $content = [System.IO.File]::ReadAllText($f.FullName)
  } catch { $skipped++; return }
  $orig = $content
  foreach ($p in $patterns) {
    $content = [regex]::Replace($content, $p.Pattern, $p.Repl)
  }
  # username path scrub
  $content = [regex]::Replace($content, $userName, '[USER]')
  if ($content -ne $orig) {
    [System.IO.File]::WriteAllText($f.FullName, $content)
  }
  $processed++
}
Write-Output "Redaction processed=$processed skipped=$skipped"

# --- Step 5: README ---
$readme = "$dest\README.md"
$exportDate = Get-Date
$hostName = [System.Net.Dns]::GetHostName()
$user = $env:USERNAME

$extCounts = Get-ChildItem -Path "$dest\redacted" -Recurse -File -ErrorAction SilentlyContinue |
  Group-Object { $_.Extension.ToLower() } |
  Sort-Object Count -Descending |
  Select-Object Name, Count

$totalSize = (Get-ChildItem -Path "$dest\redacted" -Recurse -File -ErrorAction SilentlyContinue |
  Measure-Object -Property Length -Sum).Sum
$totalSizeMB = [math]::Round($totalSize / 1MB, 2)

$recent = Get-ChildItem -Path "$dest\redacted" -Recurse -File -Include *.json,*.jsonl -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 20

$lines = @()
$lines += "# Codex Sessions Export"
$lines += ""
$lines += "- Export date: $exportDate"
$lines += "- Hostname: $hostName"
$lines += "- User: $user"
$lines += ""
$lines += "## Source paths detected"
foreach ($p in $found) { $lines += ("- " + '`' + $p + '`') }
$lines += ""
$lines += "## File count by extension (redacted/)"
$lines += ""
$lines += "| Extension | Count |"
$lines += "|-----------|-------|"
foreach ($e in $extCounts) {
  $extName = if ([string]::IsNullOrEmpty($e.Name)) { "(none)" } else { $e.Name }
  $lines += "| $extName | $($e.Count) |"
}
$lines += ""
$lines += "## Total size"
$lines += ""
$lines += "$totalSizeMB MB"
$lines += ""
$lines += "## 20 most recently modified .json/.jsonl files (redacted/)"
$lines += ""
foreach ($r in $recent) {
  $rel = $r.FullName.Substring("$dest\redacted".Length).TrimStart('\')
  $lines += "- $($r.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')) | $rel"
}
$lines += ""
$lines += "## WARNING"
$lines += ""
$lines += "**``raw/`` contains UNREDACTED secrets - DO NOT SHARE.**"
$lines += "Only share ``redacted/``."
[System.IO.File]::WriteAllLines($readme, $lines)
Write-Output "README written: $readme"

# --- Step 6: INDEX ---
$indexLines = @()
$indexLines += "# Index of redacted JSON sessions"
$indexLines += ""
Get-ChildItem -Path "$dest\redacted" -Recurse -File -Include *.json,*.jsonl -ErrorAction SilentlyContinue | ForEach-Object {
  $rel = $_.FullName.Substring("$dest\redacted".Length).TrimStart('\')
  $size = $_.Length
  $mtime = $_.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
  $preview = ""
  try {
    $fs = [System.IO.File]::OpenRead($_.FullName)
    $buf = New-Object byte[] 200
    $n = $fs.Read($buf, 0, 200)
    $fs.Close()
    $preview = [System.Text.Encoding]::UTF8.GetString($buf, 0, $n) -replace '[\r\n]', ' '
  } catch { $preview = "(unreadable)" }
  $indexLines += "## $rel"
  $indexLines += ""
  $indexLines += "- size: $size bytes"
  $indexLines += "- mtime: $mtime"
  $indexLines += "- preview: ``$preview``"
  $indexLines += ""
}
[System.IO.File]::WriteAllLines("$dest\INDEX.md", $indexLines)
Write-Output "INDEX written"

# --- Step 7: validation re-scan ---
Write-Output "Re-scanning redacted/ for residual secrets..."
$residuals = @()
Get-ChildItem -Path "$dest\redacted" -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $f = $_
  if ($textExt -notcontains $f.Extension.ToLower()) { return }
  if ($f.Length -gt 50MB) { return }
  try { $content = [System.IO.File]::ReadAllText($f.FullName) } catch { return }
  foreach ($p in $patterns) {
    $m = [regex]::Match($content, $p.Pattern)
    if ($m.Success) {
      # find line number
      $upto = $content.Substring(0, $m.Index)
      $line = ($upto -split "`n").Count
      $residuals += [pscustomobject]@{
        File = $f.FullName
        Line = $line
        Pattern = $p.Pattern
        Sample = $m.Value.Substring(0, [Math]::Min(40, $m.Value.Length))
      }
    }
  }
}

# --- Step 8: report ---
$sessionCount = (Get-ChildItem -Path "$dest\redacted" -Recurse -File -Include *.json,*.jsonl -ErrorAction SilentlyContinue | Measure-Object).Count

Write-Output ""
Write-Output "================ FINAL REPORT ================"
Write-Output "Export folder: $dest"
Write-Output "Total session files (.json/.jsonl) under redacted/: $sessionCount"
if ($residuals.Count -gt 0) {
  Write-Output "RESIDUAL SECRETS FOUND ($($residuals.Count)):"
  $residuals | Select-Object -First 30 | Format-Table -AutoSize | Out-String | Write-Output
  Write-Output "ABORT: do NOT share redacted/ until cleaned."
} else {
  Write-Output "Residual secrets: NONE detected."
}
Write-Output ""
Write-Output "To move to other machine: USB / OneDrive personal / SCP."
Write-Output "DO NOT send via chat or email."
Write-Output "=============================================="
