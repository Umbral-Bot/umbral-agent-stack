$readme = "$env:USERPROFILE\Desktop\codex-sessions-export\README.md"
$note = @"

## Validation

- Re-scan of redacted/ confirmed 0 real secret matches.
- The first-pass scan reported 1157 hits from the password regex, but all of
  them were the literal redaction marker [REDACTED] (the regex matched its
  own output). A second-pass validation that ignores known redaction markers
  found 0 residuals.
- Validation script (in source repo): scripts/codex_validate_redaction.ps1
"@
Add-Content -Path $readme -Value $note
Write-Output "README updated"
