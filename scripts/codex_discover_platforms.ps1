$cands = @(
  'Cursor','cursor','.cursor',
  'Antigravity','antigravity','.antigravity','Antigravity Assistant','antigravity-assistant',
  'GitHub Copilot','github-copilot','copilot','.copilot',
  'Claude','claude','.claude','Claude Code','Anthropic','anthropic'
)
$roots = @(
  $env:APPDATA,
  $env:LOCALAPPDATA,
  $env:USERPROFILE,
  (Join-Path $env:USERPROFILE '.config')
)
foreach ($r in $roots) {
  if (-not (Test-Path $r)) { continue }
  foreach ($c in $cands) {
    $p = Join-Path $r $c
    if (Test-Path $p) {
      $cnt = (Get-ChildItem $p -Recurse -File -EA SilentlyContinue | Measure-Object).Count
      $sz  = [math]::Round((Get-ChildItem $p -Recurse -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
      Write-Output ("FOUND  {0}   files={1}   size={2}MB" -f $p, $cnt, $sz)
    }
  }
}
