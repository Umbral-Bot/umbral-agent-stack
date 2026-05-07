// infra/azure/keyvault.bicep
// RBAC-mode Key Vault. No access policies — managed identity grants only.

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

@description('Tenant ID. Defaults to subscription tenant.')
param tenantId string = subscription().tenantId

var kvName = 'kv-umbral-o16-${env}'

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: kvName
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled' // dev default; prod should use private endpoint
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

output keyVaultId string = kv.id
output keyVaultUri string = kv.properties.vaultUri
