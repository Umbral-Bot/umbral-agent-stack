$ErrorActionPreference='Stop'
$dest = "$env:USERPROFILE\Desktop\codex-sessions-export"
$textExt = @('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp')

$redactionMarkers = @(
  '[REDACTED]','[REDACTED-PAT]','[REDACTED-OPENAI]','[REDACTED-ANTHROPIC]',
  '[REDACTED-GOOGLE]','[REDACTED-SLACK]','[REDACTED-AWS]','[REDACTED-JWT]'
)

$patterns = @(
  @{ Name='ghp';   Pattern = 'ghp_[A-Za-z0-9]{30,}' },
  @{ Name='gh_pat';Pattern = 'github_pat_[A-Za-z0-9_]{50,}' },
  @{ Name='gho';   Pattern = 'gho_[A-Za-z0-9]{30,}' },
  @{ Name='ant';   Pattern = 'sk-ant-[A-Za-z0-9\-_]{30,}' },
  @{ Name='oai';   Pattern = 'sk-[A-Za-z0-9]{30,}' },
  @{ Name='goog';  Pattern = 'AIza[0-9A-Za-z_\-]{30,}' },
  @{ Name='slack'; Pattern = 'xox[baprs]-[A-Za-z0-9\-]{10,}' },
  @{ Name='aws';   Pattern = 'AKIA[0-9A-Z]{16}' },
  @{ Name='jwt';   Pattern = 'eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}' },
  @{ Name='bearer';Pattern = 'Bearer\s+[A-Za-z0-9._\-]{20,}' },
  @{ Name='pwd';   Pattern = '(?i)password["'':\s=]+[^\s"'',}]+' }
)

$residuals = New-Object System.Collections.ArrayList
Get-ChildItem -Path "$dest\redacted" -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $f = $_
  if ($textExt -notcontains $f.Extension.ToLower()) { return }
  if ($f.Length -gt 50MB) { return }
  try { $content = [System.IO.File]::ReadAllText($f.FullName) } catch { return }
  foreach ($p in $patterns) {
    foreach ($m in [regex]::Matches($content, $p.Pattern)) {
      $val = $m.Value
      $isRedactedMarker = $false
      foreach ($mk in $redactionMarkers) {
        if ($val.Contains($mk)) { $isRedactedMarker = $true; break }
      }
      if ($isRedactedMarker) { continue }
      $upto = $content.Substring(0, $m.Index)
      $line = ($upto -split "`n").Count
      $sample = if ($val.Length -gt 80) { $val.Substring(0,80) } else { $val }
      [void]$residuals.Add([pscustomobject]@{
        File = $f.FullName
        Line = $line
        Pattern = $p.Name
        Sample = $sample
      })
    }
  }
}

$out = "$env:USERPROFILE\Desktop\residual_report.txt"
"Residual real secrets: $($residuals.Count)" | Out-File $out -Encoding utf8
$residuals | Select-Object -First 50 | Format-Table -AutoSize | Out-String | Out-File $out -Append -Encoding utf8

Write-Output "Total real residual matches: $($residuals.Count)"
if ($residuals.Count -gt 0) {
  $residuals | Select-Object -First 20 | Format-Table -AutoSize
}
