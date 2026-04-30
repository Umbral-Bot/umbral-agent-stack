$base = 'C:\Users\david\OneDrive\Escritorio\ai-agents-export-2026-04-27\platforms\cursor'
foreach ($d in (Get-ChildItem $base -Directory)) {
  Write-Output ""
  Write-Output ("===== " + $d.Name + " =====")
  Get-ChildItem $d.FullName -Directory | ForEach-Object {
    $sz = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    [pscustomobject]@{ Sub = $_.Name; SizeMB = $sz }
  } | Sort-Object SizeMB -Descending | Select-Object -First 12 | Format-Table -AutoSize
}
