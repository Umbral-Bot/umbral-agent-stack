// =============================================================================
// ai-search.bicep — AI Search (Basic tier — Opción B conservadora)
// =============================================================================
// Sub-task: 2026-05-07-042 (O16.1 agent-specific services)
// Status: REAL (direct ARM resources)
// =============================================================================
// Basic = $75/mes base, 1 partition x 1 replica, 2GB, 15 indexes, semantic free.
// Promover a S1 cuando KB >5GB o queries >60/min sostenido.
// AAD-first via UAMI (authOptions: aadOrApiKey).
// =============================================================================

@description('AI Search service name.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID for Search Service Contributor.')
param principalIdContributor string

@description('Principal ID for Search Index Data Contributor.')
param principalIdDataContributor string

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    disableLocalAuth: false
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    semanticSearch: 'free'
  }
}

// RBAC: Search Service Contributor (mgmt: crear/eliminar indexes)
// Built-in: 7ca78c08-252a-4471-8644-bb5ff32d4ba0
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource searchSvcContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, principalIdContributor, searchServiceContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: principalIdContributor
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Search Index Data Contributor (data plane: read/write docs)
// Built-in: 8ebe5a00-799e-43f5-93ac-243d3dce84a7
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

resource searchIdxContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, principalIdDataContributor, searchIndexDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: principalIdDataContributor
    principalType: 'ServicePrincipal'
  }
}

output resourceId string = search.id
output serviceName string = search.name
output endpoint string = 'https://${search.name}.search.windows.net'
