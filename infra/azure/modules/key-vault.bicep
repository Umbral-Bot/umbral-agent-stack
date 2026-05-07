// =============================================================================
// key-vault.bicep — Key Vault (Standard, RBAC mode)
// =============================================================================
// Sub-task: 2026-05-07-041 (O16.1 data plane)
// Status: REAL (direct ARM resources)
// =============================================================================
// Standard SKU, RBAC mode (no access policies), soft-delete 90d, purge-protect
// on. Public access enabled (Q3 Private Endpoint). RBAC Secrets User → UAMI;
// Administrator → David (opcional, vacío = skip).
// =============================================================================

@description('Key Vault name (≤24 chars, globally unique).')
@maxLength(24)
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('AAD tenant ID (default: current sub).')
param tenantId string = subscription().tenantId

@description('Principal ID for Key Vault Secrets User (UAMI).')
param principalIdReader string

@description('Object ID for Key Vault Administrator (David). Empty = skip.')
param principalIdAdmin string = ''

@description('App Insights connection string (output de task 040). Vacío = no crear secret.')
@secure()
param appInsightsConnectionString string = ''

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// RBAC: Key Vault Secrets User → UAMI
// Built-in ID: 4633458b-17de-457c-b1cd-3cf7ff1ed1e9
var kvSecretsUserRoleId = '4633458b-17de-457c-b1cd-3cf7ff1ed1e9'

resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: kv
  name: guid(kv.id, principalIdReader, kvSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: principalIdReader
    principalType: 'ServicePrincipal'
  }
}

// RBAC opcional: Key Vault Administrator → David (User principal)
// Built-in ID: 00482a5a-887f-4fb3-b363-3b7fe8e74483
var kvAdminRoleId = '00482a5a-887f-4fb3-b363-3b7fe8e74483'

resource kvAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalIdAdmin)) {
  scope: kv
  name: guid(kv.id, principalIdAdmin, kvAdminRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvAdminRoleId)
    principalId: principalIdAdmin
    principalType: 'User'
  }
}

// Secret: AppInsights connection string (cierra loop de task 040 → KV).
// Solo se crea si el caller pasa el valor (main.bicep lo wirea desde mod_logs).
resource appInsightsConnSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(appInsightsConnectionString)) {
  parent: kv
  name: 'appinsights-connection-string'
  properties: {
    value: appInsightsConnectionString
    contentType: 'text/plain'
  }
}

output resourceId string = kv.id
output name string = kv.name
output vaultUri string = kv.properties.vaultUri
