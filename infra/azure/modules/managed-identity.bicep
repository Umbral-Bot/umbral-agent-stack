// =============================================================================
// managed-identity.bicep — User-Assigned Managed Identity compartida
// =============================================================================
// Sub-task: 2026-05-07-040 (O16.1 cross-cutting infra)
// AVM ref: br/public:avm/res/managed-identity/user-assigned-identity:0.4.0
// Status: PLACEHOLDER — impl en 040
// =============================================================================
// Params esperados:
//   - name (string): 'uami-umbral-agents-${environment}'
//   - location (string)
//   - tags (object)
//
// Outputs esperados:
//   - resourceId (string)
//   - principalId (string)  ← clave para roleAssignments en otros modules
//   - clientId (string)
// =============================================================================

@description('Name of the user-assigned managed identity.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

// TODO 040 — replace with AVM reference:
// module uami 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.0' = {
//   name: 'uami-deploy'
//   params: {
//     name: name
//     location: location
//     tags: tags
//   }
// }

// Stub para que validate pase
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

output resourceId string = uami.id
output principalId string = uami.properties.principalId
output clientId string = uami.properties.clientId
