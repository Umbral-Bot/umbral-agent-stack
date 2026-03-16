$ErrorActionPreference = "Stop"

$repoRoot = "C:\GitHub\umbral-agent-stack-codex"
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$batPath = Join-Path $repoRoot "scripts\vm\start_vm_reverse_tunnel.bat"
$shortcutPath = Join-Path $startupDir "StartVmReverseTunnel.lnk"

if (-not (Test-Path $batPath)) {
  throw "No existe $batPath"
}

New-Item -ItemType Directory -Path $startupDir -Force | Out-Null

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Save()

Write-Output "startup_shortcut=$shortcutPath"
