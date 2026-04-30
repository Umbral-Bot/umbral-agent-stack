$ErrorActionPreference='Stop'
$dest = "$env:USERPROFILE\Desktop\codex-sessions-export"
$textExt = @('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp')
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
$counts = @{}
$samples = @{}
Get-ChildItem -Path "$dest\redacted" -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $f = $_
  if ($textExt -notcontains $f.Extension.ToLower()) { return }
  if ($f.Length -gt 50MB) { return }
  try { $content = [System.IO.File]::ReadAllText($f.FullName) } catch { return }
  foreach ($p in $patterns) {
    $ms = [regex]::Matches($content, $p.Pattern)
    if ($ms.Count -gt 0) {
      if (-not $counts.ContainsKey($p.Name)) { $counts[$p.Name] = 0; $samples[$p.Name] = New-Object System.Collections.ArrayList }
      $counts[$p.Name] += $ms.Count
      if ($samples[$p.Name].Count -lt 5) {
        $sample = $ms[0].Value
        if ($sample.Length -gt 100) { $sample = $sample.Substring(0,100) }
        [void]$samples[$p.Name].Add(("{0} :: {1}" -f $f.Name, $sample))
      }
    }
  }
}
"===== counts =====" | Out-File -FilePath "$dest\..\residual_report.txt" -Encoding utf8
$counts.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "{0}: {1}" -f $_.Key, $_.Value } | Out-File -FilePath "$dest\..\residual_report.txt" -Append -Encoding utf8
"" | Out-File -FilePath "$dest\..\residual_report.txt" -Append
"===== samples =====" | Out-File -FilePath "$dest\..\residual_report.txt" -Append -Encoding utf8
foreach ($k in $samples.Keys) {
  "--- $k ---" | Out-File -FilePath "$dest\..\residual_report.txt" -Append -Encoding utf8
  $samples[$k] | Out-File -FilePath "$dest\..\residual_report.txt" -Append -Encoding utf8
}
Write-Output "Done. See $dest\..\residual_report.txt"
