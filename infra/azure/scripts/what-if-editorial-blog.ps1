#Requires -Version 7
<#
.SYNOPSIS
    Preview the editorial blog layer (ADR-010) Bicep changes without applying them.

.DESCRIPTION
    Runs `az deployment sub what-if` against main.bicep with the editorial blog
    flag forced ON (`deployEditorialBlog=true`), so you can preview the Storage +
    Function + CDN resources before a real deploy. NO consume créditos.

    The rest of the stack (UAMI, Storage data plane, Cosmos, etc.) is also present
    in the what-if because main.bicep is a single subscription-scope deployment;
    review the `Microsoft.Web/*`, `Microsoft.Cdn/*` and the `steditorial*` storage
    account lines for the editorial layer specifically.

.PARAMETER WorkerToken
    Optional shared secret injected as `editorialWorkerToken` (x-worker-token).
    Defaults to a throwaway placeholder for what-if (never deployed from here).

.NOTES
    ADR: docs/adr/ADR-010-azure-editorial-blog-cms.md
    Runbook: docs/ops/azure-editorial-blog-runbook.md
#>

[CmdletBinding()]
param(
    [string]$Location = 'eastus2',
    [string]$TemplateFile = (Join-Path $PSScriptRoot '..' 'main.bicep'),
    [bool]$PublicBlobRead = $false,
    [bool]$DeployCdn = $true,
    [string]$WorkerToken = 'whatif-placeholder-not-deployed'
)

$ErrorActionPreference = 'Stop'

Write-Host "▶ Editorial blog what-if (deployEditorialBlog=true)..." -ForegroundColor Cyan
Write-Host "  Template:        $TemplateFile"
Write-Host "  Location:        $Location"
Write-Host "  PublicBlobRead:  $PublicBlobRead"
Write-Host "  DeployCdn:       $DeployCdn"
Write-Host ""

$account = az account show --output json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Error "No estás logueado. Corré: az login"
    exit 1
}
Write-Host "✓ Logged in as: $($account.user.name) ($($account.name))" -ForegroundColor Green
Write-Host ""

az deployment sub what-if `
    --location $Location `
    --template-file $TemplateFile `
    --parameters `
        deployEditorialBlog=true `
        editorialPublicBlobRead=$($PublicBlobRead.ToString().ToLower()) `
        deployEditorialCdn=$($DeployCdn.ToString().ToLower()) `
        editorialWorkerToken=$WorkerToken

if ($LASTEXITCODE -ne 0) {
    Write-Error "✗ What-if failed."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "✓ What-if complete. Review Microsoft.Web/*, Microsoft.Cdn/* and steditorial* lines." -ForegroundColor Green
