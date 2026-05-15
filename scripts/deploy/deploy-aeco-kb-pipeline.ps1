#Requires -Version 7.0
<#
.SYNOPSIS
    Deploy AECO KB pipeline (3 ACA Jobs) usando GHCR privado + ghcr-pat desde Key Vault.

.DESCRIPTION
    Operacionaliza C-Vía 3: mantener GHCR packages privados y pasar el PAT al
    ACA Job via registry credentials (passwordSecretRef -> ghcr-pat).

    Flujo seguro:
      1. Resuelve parámetros desde el RG (read-only az queries).
      2. Lee ghcr-pat desde Key Vault (sin imprimir el valor).
      3. Ejecuta `az deployment group what-if` SIEMPRE.
      4. Si -WhatIfOnly (default), termina ahí.
      5. Si NO -WhatIfOnly, pide confirmación interactiva explícita ("DEPLOY").
      6. Limpia variables sensibles al final.

.PARAMETER ResourceGroup
    RG destino. Default: rg-umbral-agents-prod.

.PARAMETER Location
    Azure region. Default: eastus2.

.PARAMETER KeyVaultName
    Key Vault que contiene el secret ghcr-pat. Default: kv-umbral-agents-prod.

.PARAMETER GhcrSecretName
    Nombre del secret en Key Vault. Default: ghcr-pat.

.PARAMETER BicepFile
    Path al bicep umbrella. Default: infra/azure/aeco-kb-pipeline.bicep (relativo al repo root).

.PARAMETER DeployPdfParser
    Si $true, despliega el job aeco-pdf-parser. Default $false (Q2: solo crawler + index-pipeline).

.PARAMETER WhatIfOnly
    Si $true (default), solo ejecuta what-if y termina. Si $false, pide confirmación
    explícita y luego ejecuta deploy real.

.PARAMETER UamiName
    Nombre del UAMI. Override si difiere. Default auto-discovery por prefix uami-umbral-agents.

.PARAMETER ContainerAppsEnvName
    Nombre del Container Apps Environment. Default auto-discovery.

.PARAMETER StorageAccountName
    Storage account. Default: stumbralagentsprod.

.PARAMETER SearchServiceName
    AI Search service. Default: srch-umbral-kb-prod.

.PARAMETER DiAccountName
    Document Intelligence Cognitive Services account. Default auto-discovery.

.EXAMPLE
    # Modo seguro: solo what-if
    .\deploy-aeco-kb-pipeline.ps1

.EXAMPLE
    # Deploy real (requiere confirmación interactiva "DEPLOY")
    .\deploy-aeco-kb-pipeline.ps1 -WhatIfOnly:$false

.EXAMPLE
    # Deploy incluyendo pdf-parser
    .\deploy-aeco-kb-pipeline.ps1 -WhatIfOnly:$false -DeployPdfParser

.NOTES
    Requiere: az CLI 2.83+, autenticado con principal con Reader+Deploy en RG y
              Key Vault Secrets User en el KV.
    NUNCA imprime el PAT ni el contenido del Authorization header.
#>

[CmdletBinding()]
param(
    [string]$ResourceGroup = 'rg-umbral-agents-prod',
    [string]$Location = 'eastus2',
    [string]$KeyVaultName = 'kv-umbral-agents-prod',
    [string]$GhcrSecretName = 'ghcr-pat',
    [string]$BicepFile = 'infra/azure/aeco-kb-pipeline.bicep',
    [bool]$DeployPdfParser = $false,
    [bool]$WhatIfOnly = $true,
    [string]$UamiName,
    [string]$ContainerAppsEnvName,
    [string]$StorageAccountName = 'stumbralagentsprod',
    [string]$SearchServiceName = 'srch-umbral-kb-prod',
    [string]$DiAccountName
)

$ErrorActionPreference = 'Stop'
$script:Pat = $null
$script:DeploymentName = "aeco-kb-pipeline-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

function Write-Section($title) {
    Write-Host ""
    Write-Host "=== $title ===" -ForegroundColor Cyan
}

function Resolve-Params {
    Write-Section "Resolviendo parámetros (read-only)"

    # UAMI
    if (-not $UamiName) {
        $script:UamiName = az identity list -g $ResourceGroup --query "[?starts_with(name, 'uami-umbral-agents')].name | [0]" -o tsv
        if (-not $script:UamiName) { throw "No se encontró UAMI con prefix 'uami-umbral-agents' en $ResourceGroup. Especificar -UamiName." }
    } else { $script:UamiName = $UamiName }
    $uamiInfo = az identity show -g $ResourceGroup -n $script:UamiName --query "{id:id, clientId:clientId}" -o json | ConvertFrom-Json
    $script:UamiId = $uamiInfo.id
    $script:UamiClientId = $uamiInfo.clientId
    Write-Host "  UAMI: $($script:UamiName)"

    # Container Apps Environment
    if (-not $ContainerAppsEnvName) {
        $script:CaeName = az containerapp env list -g $ResourceGroup --query "[0].name" -o tsv
        if (-not $script:CaeName) { throw "No se encontró Container Apps Environment en $ResourceGroup. Especificar -ContainerAppsEnvName." }
    } else { $script:CaeName = $ContainerAppsEnvName }
    $script:CaeId = az containerapp env show -g $ResourceGroup -n $script:CaeName --query id -o tsv
    Write-Host "  CAE: $($script:CaeName)"

    # Document Intelligence
    if (-not $DiAccountName) {
        $script:DiName = az cognitiveservices account list -g $ResourceGroup --query "[?kind=='FormRecognizer'].name | [0]" -o tsv
        if (-not $script:DiName) { throw "No se encontró Document Intelligence (FormRecognizer) en $ResourceGroup. Especificar -DiAccountName." }
    } else { $script:DiName = $DiAccountName }
    $script:DiEndpoint = az cognitiveservices account show -g $ResourceGroup -n $script:DiName --query properties.endpoint -o tsv
    Write-Host "  DI: $($script:DiName) -> $($script:DiEndpoint)"

    # Storage + Search (validar existencia, no resolver IDs)
    $sa = az storage account show -g $ResourceGroup -n $StorageAccountName --query name -o tsv 2>$null
    if (-not $sa) { throw "Storage account $StorageAccountName no existe en $ResourceGroup." }
    Write-Host "  Storage: $StorageAccountName"

    $sr = az search service show -g $ResourceGroup -n $SearchServiceName --query name -o tsv 2>$null
    if (-not $sr) { throw "Search service $SearchServiceName no existe en $ResourceGroup." }
    Write-Host "  Search: $SearchServiceName"

    Write-Host "  Location: $Location"
    Write-Host "  DeployPdfParser: $DeployPdfParser"
}

function Read-GhcrPatFromKeyVault {
    Write-Section "Leyendo ghcr-pat desde Key Vault (sin imprimir valor)"

    # Verificar existencia primero
    $secretMeta = az keyvault secret show --vault-name $KeyVaultName --name $GhcrSecretName --query "{enabled:attributes.enabled, expires:attributes.expires}" -o json 2>$null | ConvertFrom-Json
    if (-not $secretMeta) { throw "STOP: secret '$GhcrSecretName' no existe en Key Vault '$KeyVaultName'." }
    if (-not $secretMeta.enabled) { throw "STOP: secret '$GhcrSecretName' está deshabilitado." }
    Write-Host "  Secret presente, enabled=true, expires=$($secretMeta.expires)"

    # Leer valor
    $script:Pat = az keyvault secret show --vault-name $KeyVaultName --name $GhcrSecretName --query value -o tsv
    if (-not $script:Pat) { throw "STOP: secret value vacío." }
    $patLen = $script:Pat.Length
    if ($patLen -lt 30) { throw "STOP: PAT length $patLen < 30 (corrupto?). NO se intentará deploy." }
    Write-Host "  PAT length: $patLen chars (valor NO impreso)"
}

function Test-GhcrAuth {
    Write-Section "Smoke GHCR auth (1 package, NO imprimir headers)"
    $b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($script:Pat))
    $accept = 'application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json,application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json'
    $r = Invoke-WebRequest -Uri "https://ghcr.io/v2/umbral-bot/aeco-source-crawler/manifests/v1" `
                           -Headers @{Authorization = "Bearer $b64"; Accept = $accept } `
                           -SkipHttpErrorCheck
    $b64 = $null
    Remove-Variable b64 -ErrorAction SilentlyContinue
    if ($r.StatusCode -ne 200) { throw "STOP: GHCR auth falló con HTTP $($r.StatusCode). PAT inválido o sin scope read:packages." }
    Write-Host "  GHCR auth OK (HTTP 200)"
}

function Invoke-WhatIf {
    Write-Section "Ejecutando what-if (read-only)"
    Write-Host "  Deployment name: $($script:DeploymentName)"
    Write-Host "  Bicep: $BicepFile"

    $whatIfOutput = az deployment group what-if `
        --resource-group $ResourceGroup `
        --name $script:DeploymentName `
        --template-file $BicepFile `
        --parameters location=$Location `
                     environmentId=$script:CaeId `
                     userAssignedIdentityId=$script:UamiId `
                     userAssignedIdentityClientId=$script:UamiClientId `
                     storageAccountName=$StorageAccountName `
                     searchServiceName=$SearchServiceName `
                     diEndpoint=$script:DiEndpoint `
                     deployPdfParser=$DeployPdfParser `
                     ghcrPat=$script:Pat `
        --result-format FullResourcePayloads `
        2>&1
    $exitCode = $LASTEXITCODE
    Write-Host ""
    Write-Host "--- what-if output ---"
    # Filtrar líneas que pudieran contener el PAT (defensive — el what-if no debería imprimir secure params)
    $whatIfOutput | ForEach-Object {
        $line = $_.ToString()
        if ($script:Pat -and $line.Contains($script:Pat)) {
            Write-Host "  <REDACTED line containing secret value>" -ForegroundColor Red
        } else {
            Write-Host $line
        }
    }
    Write-Host "--- end what-if ---"
    if ($exitCode -ne 0) { throw "STOP: what-if exit code $exitCode." }
}

function Invoke-Deploy {
    Write-Section "DEPLOY REAL (requiere confirmación)"
    Write-Host "Vas a ejecutar `az deployment group create` sobre $ResourceGroup." -ForegroundColor Yellow
    Write-Host "Bicep: $BicepFile" -ForegroundColor Yellow
    Write-Host "DeployPdfParser: $DeployPdfParser" -ForegroundColor Yellow
    Write-Host ""
    $confirm = Read-Host "Escribe exactamente 'DEPLOY' (mayúsculas) para confirmar"
    if ($confirm -ne 'DEPLOY') {
        Write-Host "Confirmación NO recibida. Abortando deploy." -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "Ejecutando deploy..." -ForegroundColor Cyan
    az deployment group create `
        --resource-group $ResourceGroup `
        --name $script:DeploymentName `
        --template-file $BicepFile `
        --parameters location=$Location `
                     environmentId=$script:CaeId `
                     userAssignedIdentityId=$script:UamiId `
                     userAssignedIdentityClientId=$script:UamiClientId `
                     storageAccountName=$StorageAccountName `
                     searchServiceName=$SearchServiceName `
                     diEndpoint=$script:DiEndpoint `
                     deployPdfParser=$DeployPdfParser `
                     ghcrPat=$script:Pat `
        --output table
    if ($LASTEXITCODE -ne 0) { throw "STOP: deploy exit code $LASTEXITCODE." }
}

function Clear-Sensitive {
    Write-Section "Cleanup variables sensibles"
    $script:Pat = $null
    Remove-Variable -Name Pat -Scope Script -ErrorAction SilentlyContinue
    [System.GC]::Collect()
    Write-Host "  PAT removido de memoria."
}

# ============================================================================
# Main
# ============================================================================
try {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  AECO KB Pipeline Deploy — C-Vía 3 (GHCR privado + KV PAT)   ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host "Mode: $(if ($WhatIfOnly) {'WhatIfOnly (NO deploy)'} else {'WhatIf + Deploy (con confirmación)'})"

    Resolve-Params
    Read-GhcrPatFromKeyVault
    Test-GhcrAuth
    Invoke-WhatIf

    if ($WhatIfOnly) {
        Write-Section "Modo WhatIfOnly — NO se ejecuta deploy"
        Write-Host "Para ejecutar deploy real: .\deploy-aeco-kb-pipeline.ps1 -WhatIfOnly:`$false"
    } else {
        Invoke-Deploy
    }
}
finally {
    Clear-Sensitive
}
