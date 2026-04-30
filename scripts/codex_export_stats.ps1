$d = "$env:USERPROFILE\Desktop\codex-sessions-export"
$sd = Join-Path $d 'redacted\.codex\sessions'
$ad = Join-Path $d 'redacted\.codex\archived_sessions'
$sc = if (Test-Path $sd) { (Get-ChildItem $sd -Recurse -File -EA SilentlyContinue | Measure-Object).Count } else { 0 }
$ac = if (Test-Path $ad) { (Get-ChildItem $ad -Recurse -File -EA SilentlyContinue | Measure-Object).Count } else { 0 }
$tj = (Get-ChildItem (Join-Path $d 'redacted') -Recurse -File -Include *.json,*.jsonl -EA SilentlyContinue | Measure-Object).Count
$ta = (Get-ChildItem (Join-Path $d 'redacted') -Recurse -File -EA SilentlyContinue | Measure-Object).Count
$sz = [math]::Round((Get-ChildItem (Join-Path $d 'redacted') -Recurse -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
Write-Output "sessions_dir_files: $sc"
Write-Output "archived_dir_files: $ac"
Write-Output "json_jsonl_total:   $tj"
Write-Output "all_files_total:    $ta"
Write-Output "redacted_size_MB:   $sz"
