#Requires -Version 7
<#
.SYNOPSIS
    Preview Bicep deployment changes without applying them.

.DESCRIPTION
    Runs `az deployment sub what-if` — muestra qué se crearía / modificaría / eliminaría.
    NO consume créditos. Útil antes de un deploy real.

.NOTES
    Task: 2026-05-07-039 (O16.1 kickoff)
#>

[CmdletBinding()]
param(
    [string]$Location = 'eastus2',
    [string]$TemplateFile = (Join-Path $PSScriptRoot '..' 'main.bicep'),
    [string]$ParametersFile = (Join-Path $PSScriptRoot '..' 'main.bicepparam')
)

$ErrorActionPreference = 'Stop'

Write-Host "▶ Running what-if analysis..." -ForegroundColor Cyan
Write-Host ""

az deployment sub what-if `
    --location $Location `
    --template-file $TemplateFile `
    --parameters $ParametersFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "✗ What-if failed."
    exit $LASTEXITCODE
}
