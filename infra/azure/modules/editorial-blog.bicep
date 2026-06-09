// =============================================================================
// editorial-blog.bicep — Editorial Blog CMS (Blob + Function + optional CDN)
// =============================================================================
// ADR: docs/adr/ADR-010-azure-editorial-blog-cms.md
// Runbook: docs/ops/azure-editorial-blog-runbook.md
// =============================================================================
// Self-contained module for the editorial blog publishing layer:
//   * dedicated Storage account + `editorial-posts` container
//       posts/{slug}.json   (full post)
//       index.json          (light listing, published_at desc)
//   * Linux Consumption Function App (Python 3.12) hosting
//     POST /api/publish-editorial-post
//   * System-assigned Managed Identity → Storage Blob Data Contributor
//     (the function writes blobs via DefaultAzureCredential, no account key)
//   * optional Azure CDN (Standard_Microsoft) in front of the blob origin
//
// Deployed only when main.bicep `deployEditorialBlog = true`. No production
// deploy happens from this PR — `what-if` / `validate` only.
// =============================================================================

@description('Storage account name for editorial blog (<=24 chars, lowercase, no hyphens).')
@maxLength(24)
param storageAccountName string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Blob container that holds posts/{slug}.json + index.json.')
param containerName string = 'editorial-posts'

@description('Linux Consumption Function App name (globally unique).')
param functionAppName string

@description('App Service Plan (Consumption Y1) name.')
param planName string

@description('Application Insights connection string (optional; empty = skip wiring).')
param appInsightsConnectionString string = ''

@description('Canonical public base URL for the blog (used to build canonical_url).')
param canonicalBaseUrl string = 'https://umbralbim.io'

@description('''Shared secret the Worker sends as x-worker-token, validated by the
function in addition to the Azure function key. Pass via secure param / Key Vault
reference — NEVER commit. Empty = function relies on the function key only.''')
@secure()
param workerToken string = ''

@description('''Allow anonymous (public) blob read on the container. v1 default is
false — front the origin with the CDN endpoint or short-lived SAS. Set true only
if you intentionally serve the JSON directly from the blob endpoint.''')
param enablePublicBlobRead bool = false

@description('Deploy an Azure CDN (Standard_Microsoft) endpoint in front of the blob origin.')
param deployCdn bool = true

// -----------------------------------------------------------------------------
// Storage account + container
// -----------------------------------------------------------------------------

resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: enablePublicBlobRead
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowSharedKeyAccess: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: sa
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
    cors: {
      corsRules: [
        {
          // SPA (umbralbim.io) fetches index.json + posts/{slug}.json client-side.
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'HEAD', 'OPTIONS']
          allowedHeaders: ['*']
          exposedHeaders: ['*']
          maxAgeInSeconds: 3600
        }
      ]
    }
  }
}

resource editorialContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: enablePublicBlobRead ? 'Blob' : 'None'
  }
}

// -----------------------------------------------------------------------------
// Function App (Linux Consumption, Python 3.12)
// -----------------------------------------------------------------------------

var storageSuffix = environment().suffixes.storage
var storageHost = '${sa.name}.blob.${storageSuffix}'
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${sa.name};EndpointSuffix=${storageSuffix};AccountKey=${sa.listKeys().keys[0].value}'

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // Linux
  }
}

var baseAppSettings = [
  {
    name: 'AzureWebJobsStorage'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTSHARE'
    value: toLower(functionAppName)
  }
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: 'python'
  }
  {
    name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
    value: 'true'
  }
  {
    // App code uses DefaultAzureCredential against this account (MI, no key).
    name: 'EDITORIAL_BLOG_STORAGE_ACCOUNT'
    value: sa.name
  }
  {
    name: 'EDITORIAL_BLOG_CONTAINER'
    value: containerName
  }
  {
    name: 'EDITORIAL_BLOG_CANONICAL_BASE_URL'
    value: canonicalBaseUrl
  }
  {
    name: 'EDITORIAL_BLOG_CDN_BASE_URL'
    value: deployCdn ? 'https://${cdnEndpoint!.properties.hostName}' : ''
  }
  {
    name: 'WORKER_TOKEN'
    value: workerToken
  }
]

var appInsightsSettings = empty(appInsightsConnectionString) ? [] : [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsightsConnectionString
  }
]

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    reserved: true
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      appSettings: concat(baseAppSettings, appInsightsSettings)
    }
  }
}

// RBAC: Storage Blob Data Contributor → function system-assigned MI.
// Built-in ID: ba92f5b4-2d11-453d-a403-e96b0029c9fe
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource funcBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: sa
  name: guid(sa.id, func.id, storageBlobDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: func.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// -----------------------------------------------------------------------------
// Azure CDN (optional) — Standard_Microsoft in front of the blob origin
// -----------------------------------------------------------------------------

resource cdnProfile 'Microsoft.Cdn/profiles@2023-05-01' = if (deployCdn) {
  name: '${functionAppName}-cdn'
  location: 'global'
  tags: tags
  sku: {
    name: 'Standard_Microsoft'
  }
}

resource cdnEndpoint 'Microsoft.Cdn/profiles/endpoints@2023-05-01' = if (deployCdn) {
  parent: cdnProfile
  name: storageAccountName
  location: 'global'
  tags: tags
  properties: {
    originHostHeader: storageHost
    isHttpAllowed: false
    isHttpsAllowed: true
    queryStringCachingBehavior: 'IgnoreQueryString'
    optimizationType: 'GeneralWebDelivery'
    isCompressionEnabled: true
    contentTypesToCompress: [
      'application/json'
      'application/javascript'
      'text/plain'
      'text/html'
      'text/css'
    ]
    origins: [
      {
        name: 'origin-storage'
        properties: {
          hostName: storageHost
          httpsPort: 443
        }
      }
    ]
  }
}

// -----------------------------------------------------------------------------
// Outputs
// -----------------------------------------------------------------------------

output storageAccountName string = sa.name
output storageBlobEndpoint string = sa.properties.primaryEndpoints.blob
output containerName string = containerName
output functionAppName string = func.name
output functionDefaultHostName string = func.properties.defaultHostName
output functionPublishUrl string = 'https://${func.properties.defaultHostName}/api/publish-editorial-post'
output functionPrincipalId string = func.identity.principalId
output cdnEndpointHostName string = deployCdn ? cdnEndpoint!.properties.hostName : ''
output publicReadBaseUrl string = deployCdn ? 'https://${cdnEndpoint!.properties.hostName}/${containerName}' : '${sa.properties.primaryEndpoints.blob}${containerName}'
