$dest = 'G:\Mi unidad\06_Sistemas y Automatizaciones\90_Archivado\ai-agents-export-2026-04-27'
$src  = 'C:\Users\david\OneDrive\Escritorio\ai-agents-export-2026-04-27'

Write-Output "===== DRIVE destination ====="
Get-ChildItem $dest -Directory -EA SilentlyContinue | ForEach-Object {
  $sz = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 2)
  $cnt = (Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object).Count
  [pscustomobject]@{ Folder = $_.Name; Files = $cnt; SizeMB = $sz }
} | Format-Table -AutoSize
$tot = (Get-ChildItem $dest -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Output ("TOTAL Drive: " + [math]::Round($tot/1MB,2) + " MB")

Write-Output ""
Write-Output "===== Drive\platforms (level 1) ====="
$plat = Join-Path $dest 'platforms'
if (Test-Path $plat) {
  Get-ChildItem $plat -Directory | ForEach-Object {
    $sz = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 2)
    [pscustomobject]@{ Sub = $_.Name; SizeMB = $sz }
  } | Sort-Object SizeMB -Descending | Format-Table -AutoSize
}

Write-Output ""
Write-Output "===== SOURCE (SAFE on OneDrive) - check for online-only placeholders ====="
$srcAttr = Get-ChildItem $src -Recurse -File -Force -EA SilentlyContinue | Group-Object {
  if ($_.Attributes -band [System.IO.FileAttributes]::Offline) { 'Offline(cloud-only)' }
  else { 'Local' }
} | Select-Object Name, Count
$srcAttr | Format-Table -AutoSize
