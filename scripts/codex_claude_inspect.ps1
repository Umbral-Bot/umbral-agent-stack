$base = 'C:\Users\david\OneDrive\Escritorio\ai-agents-export-2026-04-27\platforms\claude'
foreach ($p in (Get-ChildItem $base -Directory)) {
  Write-Output ("===== " + $p.Name + " =====")
  Get-ChildItem $p.FullName -Directory -EA SilentlyContinue | ForEach-Object {
    $sz = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 2)
    [pscustomobject]@{ Sub = $_.Name; SizeMB = $sz }
  } | Sort-Object SizeMB -Descending | Select-Object -First 20 | Format-Table -AutoSize
}
