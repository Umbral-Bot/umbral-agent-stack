$base = 'C:\Users\david\OneDrive\Escritorio\ai-agents-export-2026-04-27'

Write-Output "===== TOP-LEVEL ====="
Get-ChildItem $base -Directory | ForEach-Object {
  $sz = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
  $cnt = (Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object).Count
  [pscustomobject]@{ Folder=$_.Name; Files=$cnt; SizeMB=$sz }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

$total = (Get-ChildItem $base -Recurse -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Output ("TOTAL SAFE: {0} MB ({1} GB)" -f [math]::Round($total/1MB,2), [math]::Round($total/1GB,2))

Write-Output ""
Write-Output "===== PLATFORMS subdirs ====="
Get-ChildItem (Join-Path $base 'platforms') -Directory | ForEach-Object {
  $plat = $_
  Get-ChildItem $plat.FullName -Directory | ForEach-Object {
    $sub = $_
    $sz = [math]::Round((Get-ChildItem $sub.FullName -Recurse -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    $cnt = (Get-ChildItem $sub.FullName -Recurse -File -EA SilentlyContinue | Measure-Object).Count
    [pscustomobject]@{ Platform=$plat.Name; Source=$sub.Name; Files=$cnt; SizeMB=$sz }
  }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

Write-Output ""
Write-Output "===== TOP 15 heaviest leaf dirs (depth 3 inside platforms) ====="
$leafs = @()
Get-ChildItem (Join-Path $base 'platforms') -Recurse -Directory -EA SilentlyContinue | Where-Object {
  $rel = $_.FullName.Substring($base.Length).TrimStart('\')
  ($rel -split '\\').Count -le 5
} | ForEach-Object {
  $sz = (Get-ChildItem $_.FullName -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  $leafs += [pscustomobject]@{ Dir=$_.FullName.Substring($base.Length).TrimStart('\'); SizeMB=[math]::Round($sz/1MB,2) }
}
$leafs | Sort-Object SizeMB -Descending | Select-Object -First 15 | Format-Table -AutoSize

Write-Output ""
Write-Output "===== TOP 10 individual files ====="
Get-ChildItem $base -Recurse -File -EA SilentlyContinue |
  Sort-Object Length -Descending |
  Select-Object -First 10 |
  ForEach-Object {
    [pscustomobject]@{
      SizeMB = [math]::Round($_.Length/1MB,2)
      File   = $_.FullName.Substring($base.Length).TrimStart('\')
    }
  } | Format-Table -AutoSize
