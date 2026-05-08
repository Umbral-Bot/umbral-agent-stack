#Requires -Version 7
<#
.SYNOPSIS
    Validate Bicep deployment without provisioning resources.

.DESCRIPTION
    Runs `az deployment sub validate` against main.bicep + main.bicepparam.
    NO consume créditos. Sirve para verificar sintaxis + ARM constraints.

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

Write-Host "▶ Validating Bicep template..." -ForegroundColor Cyan
Write-Host "  Template:   $TemplateFile"
Write-Host "  Parameters: $ParametersFile"
Write-Host "  Location:   $Location"
Write-Host ""

# Verifica login
$account = az account show --output json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Error "No estás logueado. Corré: az login"
    exit 1
}
Write-Host "✓ Logged in as: $($account.user.name) ($($account.name))" -ForegroundColor Green
Write-Host ""

# Validate
az deployment sub validate `
    --location $Location `
    --template-file $TemplateFile `
    --parameters $ParametersFile `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Validation passed." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Error "✗ Validation failed."
    exit $LASTEXITCODE
}
