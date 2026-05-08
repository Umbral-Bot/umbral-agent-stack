// =============================================================================
// managed-identity.bicep — User-Assigned Managed Identity compartida
// =============================================================================
// Sub-task: 2026-05-07-040 (O16.1 cross-cutting infra)
// Status: REAL (direct resource — UAMI es primitivo; AVM no agrega valor)
// =============================================================================
// La UAMI provee `principalId` consumido por:
//   - App Insights RBAC (Monitoring Metrics Publisher)  — task 040 (este)
//   - Storage RBAC (Storage Blob Data Contributor)      — task 041
//   - Cosmos RBAC (Built-in Data Contributor)           — task 041
//   - Key Vault RBAC (Secrets User)                     — task 041
//   - AI Search RBAC (Index Data + Service Contributor) — task 042
//   - Service Bus RBAC (Sender + Receiver)              — task 042
//   - Document Intelligence RBAC (Cognitive Services User) — task 042
// =============================================================================

@description('Name of the user-assigned managed identity.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

output resourceId string = uami.id
output principalId string = uami.properties.principalId
output clientId string = uami.properties.clientId
output name string = uami.name
