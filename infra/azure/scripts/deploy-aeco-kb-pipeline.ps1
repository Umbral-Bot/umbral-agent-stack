#Requires -Version 7
<#
.SYNOPSIS
    Deploy O16.2 AECO KB pipeline (3 ACA Jobs) — resource-group scope.

.DESCRIPTION
    Runs `az deployment group create` contra rg-umbral-agents-prod con todos los
    parámetros pre-resueltos (UAMI, CAE, Storage, Search, DI, Foundry).

    Pide confirmación explícita antes de aplicar (operationalSafety).

.PREREQUISITES
    - Task 2026-05-08-052 cerrada (3 imágenes Docker en GHCR — PRIVATE):
        ghcr.io/umbral-bot/aeco-source-crawler:latest
        ghcr.io/umbral-bot/aeco-pdf-parser:latest
        ghcr.io/umbral-bot/aeco-index-pipeline:latest
    - Variable de entorno `GHCR_PAT` con PAT classic (scope read:packages)
      para que ACA Jobs hagan pull de las imágenes privadas. Ejemplo:
        $env:GHCR_PAT = 'ghp_xxxxxxxxxxxx'
    - `az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4`
    - Sub activa: f14f61f0-e692-4fbb-900d-73e55a632374

.NOTES
    Task: 2026-05-08-050 (pipeline e2e) — pendiente cierre por bloqueo 052.
    Audit: docs/audits/2026-05-08-o16-2-smoke-deploy.md
#>

[CmdletBinding()]
param(
    [string]$ResourceGroup = 'rg-umbral-agents-prod',
    [string]$Location = 'eastus2',
    [string]$TemplateFile = (Join-Path $PSScriptRoot '..' 'aeco-kb-pipeline.bicep'),
    [string]$DeploymentName = "aeco-kb-pipeline-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

# Pre-resolved params (verificados 2026-05-08 contra sub Sponsorship)
$envId = '/subscriptions/f14f61f0-e692-4fbb-900d-73e55a632374/resourceGroups/rg-umbral-agents-prod/providers/Microsoft.App/managedEnvironments/cae-umbral-agents-prod'
$uamiId = '/subscriptions/f14f61f0-e692-4fbb-900d-73e55a632374/resourcegroups/rg-umbral-agents-prod/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-umbral-agents-prod'
$uamiClientId = '095eb650-63d4-451c-ba21-c03bbe563784'
$storageAccount = 'stumbralagentsprod'
$searchService = 'srch-umbral-kb-prod'
$diEndpoint = 'https://di-umbral-prod.cognitiveservices.azure.com/'

$account = az account show --output json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Error "No estás logueado. Corré: az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4"
    exit 1
}

$ghcrPat = $env:GHCR_PAT
if (-not $ghcrPat) {
    Write-Error "Falta `$env:GHCR_PAT (PAT classic con scope read:packages para pull de imágenes privadas).`nSetéalo con: `$env:GHCR_PAT = 'ghp_...'"
    exit 1
}

$action = if ($WhatIf) { 'WHAT-IF' } else { 'DEPLOY' }

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host " O16.2 AECO KB PIPELINE — $action" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Subscription:    $($account.name) ($($account.id))"
Write-Host "  User:            $($account.user.name)"
Write-Host "  Resource group:  $ResourceGroup"
Write-Host "  Location:        $Location"
Write-Host "  Deployment:      $DeploymentName"
Write-Host "  Template:        $TemplateFile"
Write-Host ""
Write-Host "  Pre-resolved parameters:"
Write-Host "    environmentId:         $envId"
Write-Host "    userAssignedIdentity:  $uamiId"
Write-Host "    uamiClientId:          $uamiClientId"
Write-Host "    storageAccountName:    $storageAccount"
Write-Host "    searchServiceName:     $searchService"
Write-Host "    diEndpoint:            $diEndpoint"
Write-Host "    ghcrPat:               *** (len=$($ghcrPat.Length))"
Write-Host ""

if (-not $WhatIf) {
    $confirm = Read-Host "¿Continuar? Escribí 'DEPLOY' (mayúsculas) para confirmar"
    if ($confirm -ne 'DEPLOY') {
        Write-Host "Cancelado." -ForegroundColor Yellow
        exit 0
    }
}

$cmd = if ($WhatIf) { 'what-if' } else { 'create' }

Write-Host ""
Write-Host "▶ Running az deployment group $cmd..." -ForegroundColor Cyan

az deployment group $cmd `
    --name $DeploymentName `
    --resource-group $ResourceGroup `
    --template-file $TemplateFile `
    --parameters location=$Location `
    --parameters environmentId=$envId `
    --parameters userAssignedIdentityId=$uamiId `
    --parameters userAssignedIdentityClientId=$uamiClientId `
    --parameters storageAccountName=$storageAccount `
    --parameters searchServiceName=$searchService `
    --parameters diEndpoint=$diEndpoint `
    --parameters ghcrPat=$ghcrPat `
    --output table

if ($LASTEXITCODE -eq 0 -and -not $WhatIf) {
    Write-Host ""
    Write-Host "✓ Deploy succeeded: $DeploymentName" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. bash scripts/aeco-kb/run_pipeline.sh buildingsmart minvu iram nmx"
    Write-Host "  2. python scripts/aeco-kb/verify_kb.py --min-chunks 500"
    Write-Host "  3. Portal Foundry → AgenteUB → File Search → connection 'aeco-kb-search'"
    Write-Host "     index 'aeco-kb-es-current' (ver runbooks/o16-2-agenteub-filesearch-wiring.md)"
    Write-Host "  4. python scripts/aeco-kb/smoke_agenteub_kb.py"
}
