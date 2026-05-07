// infra/azure/storage.bicep
// StorageV2 account with three blob containers + lifecycle (Cool 30d, Archive 90d).
// Containers: datasets, kb-raw, kb-processed.

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

var accountName = toLower('stumbralo16${env}${uniqueString(resourceGroup().id)}')

resource sa 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: substring(accountName, 0, min(24, length(accountName)))
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false // managed identity only
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled' // dev default; prod should use private endpoint
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobSvc 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: sa
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

var containerNames = [
  'datasets'
  'kb-raw'
  'kb-processed'
]

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = [for c in containerNames: {
  parent: blobSvc
  name: c
  properties: {
    publicAccess: 'None'
  }
}]

resource lifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2024-01-01' = {
  parent: sa
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'tier-cool-30d-archive-90d'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [ 'blockBlob' ]
              prefixMatch: containerNames
            }
            actions: {
              baseBlob: {
                tierToCool: {
                  daysAfterModificationGreaterThan: 30
                }
                tierToArchive: {
                  daysAfterModificationGreaterThan: 90
                }
              }
            }
          }
        }
      ]
    }
  }
}

output accountName string = sa.name
output accountId string = sa.id
output blobEndpoint string = sa.properties.primaryEndpoints.blob
