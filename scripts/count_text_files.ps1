$ext = @('.json','.jsonl','.md','.log','.txt','.yaml','.yml','.toml','.ini','.cfg','.conf','.bak','.tmp','.xml','.html','.csv')
$root = 'C:\AGE_STAGE\ai-agents-export-2026-04-27'
$all = Get-ChildItem $root -Recurse -File -EA SilentlyContinue | Where-Object { $ext -contains $_.Extension.ToLower() }
$total = ($all | Measure-Object Length -Sum)
"Text-ext files: $($total.Count)"
"Sum MB: $([math]::Round($total.Sum/1MB,1))"
$all | Group-Object Extension | Sort-Object Count -Descending | Select-Object Name, Count, @{n='MB';e={[math]::Round((($_.Group | Measure-Object Length -Sum).Sum)/1MB,1)}} | Format-Table -AutoSize
