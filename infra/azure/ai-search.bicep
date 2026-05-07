// infra/azure/ai-search.bicep
// Azure AI Search basic SKU. Will host KB indexes aeco-kb-{lang}-vYYYYMMDD.
// SKU note: 'free' tier doesn't support managed identity / replicas; 'basic' is
// the minimum that supports managed identity + scale-down. Expect ~$75/mo idle.

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

@description('Search SKU. basic is minimum supporting managed identity.')
@allowed([
  'basic'
  'standard'
])
param sku string = 'basic'

var searchName = 'srch-umbral-o16-${env}-${uniqueString(resourceGroup().id)}'

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: substring(searchName, 0, min(60, length(searchName)))
  location: location
  tags: tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled' // dev default; prod private endpoint
    semanticSearch: 'free'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: false // toggle to true after managed identity is wired
  }
}

output endpoint string = 'https://${search.name}.search.windows.net'
output searchId string = search.id
