// =============================================================================
// document-intelligence.bicep — Document Intelligence (Form Recognizer S0)
// =============================================================================
// Sub-task: 2026-05-07-042 (O16.1 agent-specific services)
// Status: REAL (direct ARM resources)
// =============================================================================
// kind=FormRecognizer S0. AAD-only (disableLocalAuth=true) via UAMI.
// customSubDomainName requerido para AAD. Modelos prebuilt en runtime.
// =============================================================================

@description('Document Intelligence account name.')
param name string

@description('Azure region (validar disponibilidad — eastus2 OK).')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID for Cognitive Services User.')
param principalIdReader string

resource di 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// RBAC: Cognitive Services User → UAMI
// Built-in: a97b65f3-24c7-4388-baec-2e87135dc908
var cogSvcUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

resource diUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: di
  name: guid(di.id, principalIdReader, cogSvcUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cogSvcUserRoleId)
    principalId: principalIdReader
    principalType: 'ServicePrincipal'
  }
}

output resourceId string = di.id
output name string = di.name
output endpoint string = di.properties.endpoint
