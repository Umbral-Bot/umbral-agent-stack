// =============================================================================
// storage.bicep — Storage Account (Hot tier, Blob)
// =============================================================================
// Sub-task: 2026-05-07-041 (O16.1 data plane)
// Status: REAL (direct ARM resources)
// =============================================================================
// Standard_LRS Hot. 3 containers. RBAC Storage Blob Data Contributor → UAMI.
// =============================================================================

@description('Storage account name (≤24 chars, lowercase, no hyphens).')
@maxLength(24)
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID of the UAMI for Storage Blob Data Contributor role.')
param principalIdContributor string

resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
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
  }
}

var containerNames = [
  'crudos'
  'datasets-curados'
  'eval-results'
]

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for cn in containerNames: {
  parent: blobService
  name: cn
  properties: {
    publicAccess: 'None'
  }
}]

// RBAC: Storage Blob Data Contributor → UAMI
// Built-in ID: ba92f5b4-2d11-453d-a403-e96b0029c9fe
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource sblobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: sa
  name: guid(sa.id, principalIdContributor, storageBlobDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: principalIdContributor
    principalType: 'ServicePrincipal'
  }
}

output resourceId string = sa.id
output name string = sa.name
output blobEndpoint string = sa.properties.primaryEndpoints.blob
