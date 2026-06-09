#Requires -Version 7
<#
.SYNOPSIS
    Smoke-test the editorial blog publish Function with a fixture post.

.DESCRIPTION
    POSTs a fixture (default: scripts/editorial/fixture-post-cand001.json) to the
    Azure Function `publish-editorial-post` and prints the response. Verifies the
    blog blob + index.json path are returned (ADR-010).

    Requires env vars:
      EDITORIAL_BLOG_FUNCTION_URL   full endpoint URL
      EDITORIAL_BLOG_FUNCTION_KEY   function key (x-functions-key)
    Optional:
      WORKER_TOKEN                  shared secret (x-worker-token)

    If the fixture has an empty content_hash it is computed with the documented
    algorithm: sha256(title + NUL + excerpt + NUL + body_markdown).

.EXAMPLE
    $env:EDITORIAL_BLOG_FUNCTION_URL="https://func-umbral-editorial-prod.azurewebsites.net/api/publish-editorial-post"
    $env:EDITORIAL_BLOG_FUNCTION_KEY="<key>"
    $env:WORKER_TOKEN="<token>"
    ./scripts/smoke-publish-editorial-post.ps1

.NOTES
    Runbook: docs/ops/azure-editorial-blog-runbook.md
#>

[CmdletBinding()]
param(
    [string]$FixturePath = (Join-Path $PSScriptRoot 'editorial' 'fixture-post-cand001.json'),
    [int]$TimeoutSec = 30,
    [switch]$PrintOnly
)

$ErrorActionPreference = 'Stop'

function Get-ContentHash([string]$title, [string]$excerpt, [string]$body) {
    $nul = [char]0
    $material = "$title$nul$excerpt$nul$body"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($material)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '')
    } finally {
        $sha.Dispose()
    }
}

if (-not (Test-Path $FixturePath)) {
    Write-Error "Fixture not found: $FixturePath"
    exit 1
}

$post = Get-Content -Raw -Path $FixturePath | ConvertFrom-Json

if ([string]::IsNullOrWhiteSpace($post.content_hash) -or $post.content_hash -eq 'PLACEHOLDER_WILL_BE_FILLED') {
    $post | Add-Member -NotePropertyName content_hash `
        -NotePropertyValue (Get-ContentHash $post.title $post.excerpt $post.body_markdown) -Force
    Write-Host "ℹ Computed content_hash: $($post.content_hash)" -ForegroundColor DarkGray
}

$bodyJson = $post | ConvertTo-Json -Depth 12 -Compress

if ($PrintOnly) {
    Write-Host "▶ Payload (PrintOnly, no network):" -ForegroundColor Cyan
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

Write-Host "▶ POST $functionUrl" -ForegroundColor Cyan
Write-Host "  slug: $($post.slug)"
Write-Host ""

try {
    $resp = Invoke-RestMethod -Method Post -Uri $functionUrl -Headers $headers `
        -Body $bodyJson -TimeoutSec $TimeoutSec
} catch {
    Write-Error "✗ Publish failed: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message -ForegroundColor Red }
    exit 1
}

Write-Host "✓ Response:" -ForegroundColor Green
$resp | ConvertTo-Json -Depth 8

if (-not $resp.published_url) {
    Write-Error "✗ Response missing 'published_url'."
    exit 1
}
Write-Host ""
Write-Host "✓ Published: $($resp.published_url)" -ForegroundColor Green
Write-Host "  blob_path:     $($resp.blob_path)"
Write-Host "  index_updated: $($resp.index_updated)"
