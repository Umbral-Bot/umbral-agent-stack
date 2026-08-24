<#
.SYNOPSIS
    Register (or refresh) the daily Windows Scheduled Task that runs the
    Drive->Notion Granola feeder.

.DESCRIPTION
    The Drive folder lives on G:\, which only exists on this Windows machine --
    the VPS cannot see it, which is why this recurrence is a Windows Scheduled
    Task and NOT a new VPS cron.

    The registered task is DRY-RUN by default: it reports what it would ingest
    and writes nothing. Pass -Execute to register a task that actually writes,
    still bounded by -MaxCreates / -MaxUpdates per run.

    Credentials are never written into the task definition. The task inherits
    the user's environment, so NOTION_API_KEY, NOTION_GRANOLA_DB_ID,
    WORKER_URL and WORKER_TOKEN must exist as USER-level environment variables
    (setx, or System Properties > Environment Variables). There is deliberately
    no env-file option here: worker/config.py's ~/.config/openclaw/env fallback
    returns immediately on Windows, so an env file would be a second, private
    credential path. If any of the four is missing, the feeder exits 1 and
    records the reason in its run report instead of writing anything.

    LogonType is deliberately Interactive. Google Drive for Desktop mounts G:\
    per interactive session, so a task running as SYSTEM or S4U would find no
    G:\ at all and every run would die on "Drive root not found". The cost is
    that the task only runs while this user is logged on; -StartWhenAvailable
    then picks up the missed run at the next logon rather than skipping the day.

.EXAMPLE
    # dry-run daily at 08:30 (safe default)
    .\register_granola_drive_feeder_task.ps1

.EXAMPLE
    # real ingest, at most 10 new pages per day
    .\register_granola_drive_feeder_task.ps1 -Execute -MaxCreates 10

.EXAMPLE
    # inspect what is registered, then remove it
    Get-ScheduledTask -TaskName 'UmbralGranolaDriveFeeder'
    Unregister-ScheduledTask -TaskName 'UmbralGranolaDriveFeeder' -Confirm:$false
#>
[CmdletBinding()]
param(
    [string]$TaskName = 'UmbralGranolaDriveFeeder',
    [ValidatePattern('^\d{2}:\d{2}$')]
    [string]$At = '08:30',
    [switch]$Execute,
    [ValidateRange(0, 500)]
    [int]$MaxCreates = 10,
    [ValidateRange(0, 500)]
    [int]$MaxUpdates = 10,
    [string]$PythonExe = '',
    [string]$RepoRoot = '',
    [switch]$WhatIfOnly
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}
$feeder = Join-Path $RepoRoot 'scripts\vm\granola_drive_feeder.py'
if (-not (Test-Path $feeder)) {
    throw "Feeder not found at $feeder. Pass -RepoRoot explicitly."
}

if (-not $PythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { throw 'python not found on PATH. Pass -PythonExe explicitly.' }
    $PythonExe = $cmd.Source
}
# Get-Command can resolve to the Microsoft Store alias stub or a .bat shim
# (pyenv-win, conda), neither of which is a viable Scheduled Task target --
# the task would register cleanly and then fail every morning.
if ($PythonExe -notmatch '\.exe$' -or $PythonExe -match 'WindowsApps') {
    throw "Resolved interpreter '$PythonExe' is not a real python.exe. Pass -PythonExe explicitly."
}

# Real transcripts carry emoji and CJK; the Windows console default (cp1252)
# cannot encode them. The feeder also forces UTF-8 on its own streams, so this
# is belt-and-braces for anything the interpreter prints before main() runs.
$argList = @(
    '-X', 'utf8',
    "`"$feeder`"",
    '--max-creates', $MaxCreates,
    '--max-updates', $MaxUpdates
)
if ($Execute) { $argList += '--execute' }

$arguments = $argList -join ' '

# Bind the trigger to the NEXT occurrence. -At '08:30' alone resolves to TODAY
# at 08:30; combined with -StartWhenAvailable, registering in the afternoon
# makes Task Scheduler treat this morning as a missed run and start it right
# away -- an unattended --execute pass minutes after registration, which is not
# what someone registering "for tomorrow morning" expects.
$parsedAt = [datetime]::ParseExact($At, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$startAt = (Get-Date).Date.AddHours($parsedAt.Hour).AddMinutes($parsedAt.Minute)
if ($startAt -le (Get-Date)) { $startAt = $startAt.AddDays(1) }

Write-Host "Task      : $TaskName"
Write-Host "Runs      : $PythonExe $arguments"
Write-Host "Schedule  : daily at $At (first run $($startAt.ToString('yyyy-MM-dd HH:mm')))"
Write-Host ("Mode      : " + $(if ($Execute) { 'EXECUTE (writes to Notion)' } else { 'DRY-RUN (writes nothing)' }))

if ($WhatIfOnly) {
    Write-Host 'WhatIfOnly set - nothing registered.'
    return
}

$action  = New-ScheduledTaskAction -Execute $PythonExe -Argument $arguments -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $startAt

# Size the limit from the work the caps actually allow: each selected item
# costs a dry-run POST plus (with -Execute) a write POST, and post_task uses a
# 600 s read timeout. A flat 2 h would kill a slow Notion day mid-loop. The
# feeder flushes its report after every item, so a kill stays auditable either
# way.
$maxSeconds = ($MaxCreates + $MaxUpdates) * 2 * 600
$limit = New-TimeSpan -Seconds ([Math]::Max($maxSeconds, 7200))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit $limit -MultipleInstances IgnoreNew

# Fully-qualified (DOMAIN\user or MACHINE\user): the bare $env:USERNAME fails
# to map to a SID on a domain- or Entra-joined machine.
$userId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "Registered. Inspect with: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Run once now with: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Run reports land in: `$env:LOCALAPPDATA\umbral-agent-stack\granola-drive-feeder"
