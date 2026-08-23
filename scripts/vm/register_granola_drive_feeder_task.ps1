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
    the user's environment, so NOTION_API_KEY / NOTION_GRANOLA_DB_ID /
    WORKER_URL / WORKER_TOKEN must be set as user-level environment variables
    (or an -EnvFile passed, which is dot-sourced by the wrapper at run time).

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
    [string]$At = '08:30',
    [switch]$Execute,
    [int]$MaxCreates = 10,
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

# Real transcripts carry emoji and CJK; the Windows console default (cp1252)
# cannot encode them and would crash the JSON dump mid-run.
$argList = @(
    '-X', 'utf8',
    "`"$feeder`"",
    '--max-creates', $MaxCreates,
    '--max-updates', $MaxUpdates
)
if ($Execute) { $argList += '--execute' }

$arguments = $argList -join ' '

Write-Host "Task      : $TaskName"
Write-Host "Runs      : $PythonExe $arguments"
Write-Host "Schedule  : daily at $At"
Write-Host ("Mode      : " + $(if ($Execute) { 'EXECUTE (writes to Notion)' } else { 'DRY-RUN (writes nothing)' }))

if ($WhatIfOnly) {
    Write-Host 'WhatIfOnly set - nothing registered.'
    return
}

$action    = New-ScheduledTaskAction -Execute $PythonExe -Argument $arguments -WorkingDirectory $RepoRoot
$trigger   = New-ScheduledTaskTrigger -Daily -At $At
# StartWhenAvailable so a run missed while the machine was off is picked up on
# the next boot instead of silently skipped -- a skipped day is a day of
# transcripts that never reach Notion.
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "Registered. Inspect with: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Run once now with: Start-ScheduledTask -TaskName '$TaskName'"
