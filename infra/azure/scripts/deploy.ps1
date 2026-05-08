#Requires -Version 7
<#
.SYNOPSIS
    Deploy Bicep template to Azure (real provisioning — consume créditos).

.DESCRIPTION
    Runs `az deployment sub create`. Pide confirmación explícita antes de aplicar.

.NOTES
    Task: 2026-05-07-039 (O16.1 kickoff)
    NO ejecutar hasta que sub-tasks 040-043 estén implementadas (smoke deploy en 044).
#>

[CmdletBinding()]
param(
    [string]$Location = 'eastus2',
    [string]$TemplateFile = (Join-Path $PSScriptRoot '..' 'main.bicep'),
    [string]$ParametersFile = (Join-Path $PSScriptRoot '..' 'main.bicepparam'),
    [string]$DeploymentName = "umbral-agents-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
)

$ErrorActionPreference = 'Stop'

# Verifica login + sub
$account = az account show --output json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Error "No estás logueado. Corré: az login"
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host " AZURE DEPLOY — REAL PROVISIONING (CONSUME CRÉDITOS)" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Subscription: $($account.name) ($($account.id))"
Write-Host "  User:         $($account.user.name)"
Write-Host "  Location:     $Location"
Write-Host "  Deployment:   $DeploymentName"
Write-Host "  Template:     $TemplateFile"
Write-Host ""

$confirm = Read-Host "¿Continuar? Escribí 'DEPLOY' (mayúsculas) para confirmar"
if ($confirm -ne 'DEPLOY') {
    Write-Host "Cancelado." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "▶ Deploying..." -ForegroundColor Cyan
az deployment sub create `
    --name $DeploymentName `
    --location $Location `
    --template-file $TemplateFile `
    --parameters $ParametersFile `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Deploy succeeded: $DeploymentName" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verify resources:"
    Write-Host "  az resource list --resource-group rg-umbral-agents-prod --output table"
} else {
    Write-Host ""
    Write-Error "✗ Deploy failed."
    exit $LASTEXITCODE
}
