<#
.SYNOPSIS
  Foundry 1 - Host Windows - Audit ChatGPT 5.5 Deployment (read-only).

.DESCRIPTION
  Read-only audit del Azure OpenAI / AI Services account para verificar el
  deployment de "GPT 5.5", capturar evidencia y ejecutar un smoke test minimo
  (max_tokens=8) sin imprimir secrets.

  NO crea ni modifica deployments. NO cambia quotas. NO imprime keys
  (solo confirma presencia de key1).

.PREREQUISITES
  - Windows host con Azure CLI autenticado (az login).
  - PowerShell 5.1+ o PowerShell 7+.
  - Permisos de lectura sobre el Cognitive Services account.

.PARAMETER ResourceGroup
  Resource Group del Cognitive Services account (ej. rg-umbral-agents-prod).

.PARAMETER AccountName
  Nombre del Azure OpenAI / AI Services account.

.PARAMETER ApiVersion
  API version asumida para Chat Completions. Default: 2024-12-01-preview.

.EXAMPLE
  .\run-foundry-1-audit.ps1 -ResourceGroup "rg-umbral-agents-prod" -AccountName "umbral-aoai-prod"

.NOTES
  Si no recordas el nombre del account, primero ejecuta:
    az resource list --resource-type Microsoft.CognitiveServices/accounts -o table
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ResourceGroup,

  [Parameter(Mandatory = $true)]
  [string]$AccountName,

  [Parameter(Mandatory = $false)]
  [string]$ApiVersion = "2024-12-01-preview"
)

$ErrorActionPreference = "Stop"

$RG   = $ResourceGroup
$ACCT = $AccountName

$EvDir = "C:\GitHub\.coord-ag-evidence\foundry-1"
New-Item -ItemType Directory -Path $EvDir -Force | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Ev    = Join-Path $EvDir "$Stamp-foundry-1-deployment-audit.txt"
"=== Foundry 1 audit @ $Stamp ===" | Set-Content $Ev

# 1) Identidad
$ctx = az account show -o json | ConvertFrom-Json
"SUBSCRIPTION_ID=$($ctx.id)"   | Add-Content $Ev
"TENANT_ID=$($ctx.tenantId)"   | Add-Content $Ev
"USER=$($ctx.user.name)"       | Add-Content $Ev

# 2) Account
$acct = az cognitiveservices account show -g $RG -n $ACCT -o json | ConvertFrom-Json
"ACCT_KIND=$($acct.kind)"                               | Add-Content $Ev
"ACCT_LOCATION=$($acct.location)"                       | Add-Content $Ev
"ACCT_ENDPOINT=$($acct.properties.endpoint)"            | Add-Content $Ev
"ACCT_SKU=$($acct.sku.name)"                            | Add-Content $Ev
"ACCT_PROV_STATE=$($acct.properties.provisioningState)" | Add-Content $Ev

# 3) Deployments
$deps = az cognitiveservices account deployment list -g $RG -n $ACCT -o json | ConvertFrom-Json
"--- DEPLOYMENTS ---" | Add-Content $Ev
$deps | ForEach-Object {
  "NAME=$($_.name) | MODEL=$($_.properties.model.name) v$($_.properties.model.version) | FORMAT=$($_.properties.model.format) | SKU=$($_.sku.name) | CAP=$($_.sku.capacity) | STATE=$($_.properties.provisioningState)" | Add-Content $Ev
}

# 4) Identificar GPT 5.5 (match laxo: 5.5 / 5-5 / 5_5 en name o model.name)
$gpt55 = $deps | Where-Object {
  $_.name -match '5[\.\-_]5' -or $_.properties.model.name -match '5[\.\-_]5'
} | Select-Object -First 1

if (-not $gpt55) {
  "GPT55_FOUND=false" | Add-Content $Ev
  $verdict = @"
===VERDICT===
RESULT=FAIL
REASON=no_deployment_matching_5_5
EVIDENCE=$Ev
"@
  $verdict | Tee-Object -Append $Ev
  return
}

$DEP_NAME = $gpt55.name
$MODEL    = "$($gpt55.properties.model.name):$($gpt55.properties.model.version)"
$ENDPOINT = $acct.properties.endpoint
"GPT55_FOUND=true"            | Add-Content $Ev
"GPT55_DEPLOYMENT=$DEP_NAME"  | Add-Content $Ev
"GPT55_MODEL=$MODEL"          | Add-Content $Ev
"GPT55_ENDPOINT=$ENDPOINT"    | Add-Content $Ev

# 5) API version (override via -ApiVersion si Foundry portal indica otra)
"GPT55_API_VERSION_ASSUMED=$ApiVersion" | Add-Content $Ev

# 6) Auth: presencia de key (sin imprimirla)
$keys       = az cognitiveservices account keys list -g $RG -n $ACCT -o json | ConvertFrom-Json
$keyPresent = -not [string]::IsNullOrEmpty($keys.key1)
"GPT55_KEY_PRESENT=$keyPresent (key1 NO impresa)" | Add-Content $Ev
"GPT55_AUTH_MODE_RECOMMENDED=api-key"             | Add-Content $Ev

# 7) Smoke seguro: 1 POST, max_tokens=8
$sw = $null
if ($keyPresent) {
  $env:_K = $keys.key1
  $url    = "$($ENDPOINT.TrimEnd('/'))/openai/deployments/$DEP_NAME/chat/completions?api-version=$ApiVersion"
  $body   = @{ messages = @(@{ role = "user"; content = "ping" }); max_tokens = 8 } | ConvertTo-Json -Depth 4
  $sw     = [Diagnostics.Stopwatch]::StartNew()
  try {
    $resp = Invoke-RestMethod -Method Post -Uri $url `
      -Headers @{ "api-key" = $env:_K; "Content-Type" = "application/json" } `
      -Body $body -TimeoutSec 30
    $sw.Stop()
    "SMOKE_STATUS=200"                              | Add-Content $Ev
    "SMOKE_LATENCY_MS=$($sw.ElapsedMilliseconds)"   | Add-Content $Ev
    "SMOKE_MODEL_RETURNED=$($resp.model)"           | Add-Content $Ev
    "SMOKE_FINISH=$($resp.choices[0].finish_reason)" | Add-Content $Ev
  } catch {
    if ($sw.IsRunning) { $sw.Stop() }
    "SMOKE_STATUS=ERROR" | Add-Content $Ev
    $msg = $_.Exception.Message -replace [regex]::Escape($env:_K), '<redacted>'
    "SMOKE_ERROR=$msg" | Add-Content $Ev
  } finally {
    Remove-Item Env:_K -ErrorAction SilentlyContinue
  }
}

# 8) Quota visible (best-effort)
try {
  $usage = az cognitiveservices usage list -l $acct.location -o json | ConvertFrom-Json
  $usage | Where-Object { $_.name.value -match $gpt55.properties.model.name } | ForEach-Object {
    "QUOTA_NAME=$($_.name.value) CURRENT=$($_.currentValue) LIMIT=$($_.limit)" | Add-Content $Ev
  }
} catch {
  "QUOTA_QUERY_ERROR=$($_.Exception.Message)" | Add-Content $Ev
}

$smokeOk = ($null -ne $sw) -and ($sw.IsRunning -eq $false)

@"
===VERDICT===
RESULT=PASS
SUBSCRIPTION_ID=$($ctx.id)
RG=$RG
ACCT=$ACCT
GPT55_DEPLOYMENT=$DEP_NAME
GPT55_MODEL=$MODEL
GPT55_ENDPOINT=$ENDPOINT
GPT55_API_VERSION=$ApiVersion
GPT55_AUTH_MODE=api-key
SMOKE_OK=$smokeOk
EVIDENCE=$Ev
"@ | Tee-Object -Append $Ev
