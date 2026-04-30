$ErrorActionPreference = 'Stop'
$srcRoot = 'C:\Users\david\Desktop\codex-sessions-export'
$desktop = [Environment]::GetFolderPath('Desktop')
Write-Output "Real Desktop: $desktop"

$destSafe = Join-Path $desktop 'codex-sessions-export-SAFE'
New-Item -ItemType Directory -Force -Path $destSafe | Out-Null

Write-Output "Copying redacted/ + README.md + INDEX.md to: $destSafe"
Copy-Item -Path (Join-Path $srcRoot 'redacted') -Destination $destSafe -Recurse -Force
Copy-Item -Path (Join-Path $srcRoot 'README.md') -Destination $destSafe -Force
Copy-Item -Path (Join-Path $srcRoot 'INDEX.md') -Destination $destSafe -Force

# Add a NOTICE explaining this is the safe-to-share copy and raw is elsewhere.
$notice = @"
This folder contains ONLY the redacted copy of the Codex sessions export.
The unredacted raw/ folder remains at:
  $srcRoot\raw
(outside OneDrive, NOT synced to the cloud).

If you want to delete the local non-OneDrive copy after moving this folder
to another machine, run:
  Remove-Item -Path '$srcRoot' -Recurse -Force
"@
$notice | Out-File -FilePath (Join-Path $destSafe 'NOTICE.txt') -Encoding utf8

$count = (Get-ChildItem $destSafe -Recurse -File | Measure-Object).Count
$sz = [math]::Round((Get-ChildItem $destSafe -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
Write-Output "Done. Files: $count | Size: $sz MB"
Write-Output "SAFE EXPORT PATH: $destSafe"
