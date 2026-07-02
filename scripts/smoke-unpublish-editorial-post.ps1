#Requires -Version 7
<#
.SYNOPSIS
    Smoke-test the editorial blog unpublish Function.

.DESCRIPTION
    POSTs a slug or Notion page id to `unpublish-editorial-post`. By default it
    removes the post from index.json and deletes posts/{slug}.json.

    Requires env vars:
      EDITORIAL_BLOG_FUNCTION_URL   full unpublish endpoint URL
      EDITORIAL_BLOG_FUNCTION_KEY   function key (x-functions-key)
    Optional:
      WORKER_TOKEN                  shared secret (x-worker-token)

.EXAMPLE
    $env:EDITORIAL_BLOG_FUNCTION_URL="https://func-umbral-editorial-prod.azurewebsites.net/api/unpublish-editorial-post"
    $env:EDITORIAL_BLOG_FUNCTION_KEY="<key>"
    $env:WORKER_TOKEN="<token>"
    ./scripts/smoke-unpublish-editorial-post.ps1 -Slug criterios-de-aceptacion-antes-de-automatizar-bim

.NOTES
    Runbook: docs/ops/azure-editorial-blog-runbook.md
#>

[CmdletBinding()]
param(
    [string]$Slug,
    [string]$NotionPageId,
    [bool]$DeletePostBlob = $true,
    [int]$TimeoutSec = 30,
    [switch]$PrintOnly
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Slug) -and [string]::IsNullOrWhiteSpace($NotionPageId)) {
    Write-Error "Provide -Slug or -NotionPageId."
    exit 1
}

$payload = [ordered]@{
    delete_post_blob = $DeletePostBlob
}
if (-not [string]::IsNullOrWhiteSpace($Slug)) {
    $payload.slug = $Slug
}
if (-not [string]::IsNullOrWhiteSpace($NotionPageId)) {
    $payload.notion_page_id = $NotionPageId
}

$bodyJson = $payload | ConvertTo-Json -Depth 8 -Compress

if ($PrintOnly) {
    Write-Host "Payload (PrintOnly, no network):" -ForegroundColor Cyan
    Write-Output $bodyJson
    exit 0
}

$functionUrl = $env:EDITORIAL_BLOG_FUNCTION_URL
$functionKey = $env:EDITORIAL_BLOG_FUNCTION_KEY
if ([string]::IsNullOrWhiteSpace($functionUrl)) {
    Write-Error "EDITORIAL_BLOG_FUNCTION_URL is not set."
    exit 1
}
if ([string]::IsNullOrWhiteSpace($functionKey)) {
    Write-Error "EDITORIAL_BLOG_FUNCTION_KEY is not set."
    exit 1
}

$headers = @{ 'Content-Type' = 'application/json' }
$headers['x-functions-key'] = $functionKey
if (-not [string]::IsNullOrWhiteSpace($env:WORKER_TOKEN)) {
    $headers['x-worker-token'] = $env:WORKER_TOKEN
}

Write-Host "POST $functionUrl" -ForegroundColor Cyan
if ($Slug) { Write-Host "  slug: $Slug" }
if ($NotionPageId) { Write-Host "  notion_page_id: $NotionPageId" }
Write-Host "  delete_post_blob: $DeletePostBlob"
Write-Host ""

try {
    $resp = Invoke-RestMethod -Method Post -Uri $functionUrl -Headers $headers `
        -Body $bodyJson -TimeoutSec $TimeoutSec
} catch {
    Write-Error "Unpublish failed: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message -ForegroundColor Red }
    exit 1
}

Write-Host "Response:" -ForegroundColor Green
$resp | ConvertTo-Json -Depth 8

if (-not $resp.ok) {
    Write-Error "Response missing ok=true."
    exit 1
}
Write-Host ""
Write-Host "Unpublished: $($resp.slug)" -ForegroundColor Green
Write-Host "  removed_from_index: $($resp.removed_from_index)"
Write-Host "  index_updated:      $($resp.index_updated)"
Write-Host "  post_blob_deleted:  $($resp.post_blob_deleted)"
