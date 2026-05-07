// =============================================================================
// key-vault.bicep — Key Vault (Standard, RBAC mode)
// =============================================================================
// Sub-task: 2026-05-07-041 (O16.1 data plane)
// AVM ref: br/public:avm/res/key-vault/vault:0.11.0
// Status: PLACEHOLDER — impl en 041
// =============================================================================
// Params esperados:
//   - name (string): 'kv-umbral-${env}-001' (≤24 chars, único global)
//   - location (string)
//   - tags (object)
//   - tenantId (string) — auto-resuelto via subscription().tenantId
//   - principalIdReader (string)  ← uami para Key Vault Secrets User
//   - principalIdAdmin (string)   ← David objectId para Key Vault Administrator
//
// Outputs esperados:
//   - resourceId (string)
//   - vaultUri (string)
//
// Settings clave:
//   - sku: 'standard'
//   - enableRbacAuthorization: true (NO access policies)
//   - softDelete: 90d retention
//   - purgeProtection: true (Sponsorship — protege contra delete accidental)
//   - publicNetworkAccess: 'enabled' (Q3 Private Endpoint)
//
// RBAC:
//   - Key Vault Administrator → David (objectId)
//   - Key Vault Secrets User → uami.principalId
//
// Secrets que vivirán acá (NO se setean en bicep — se cargan post-deploy):
//   - notion-api-key
//   - openai-api-key
//   - cosmos-connection-string
//   - service-bus-connection-string
//   - mercadopago-access-token (si aplica)
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

@description('Principal ID for Key Vault Secrets User (uami).')
param principalIdReader string

@description('Principal ID for Key Vault Administrator (David).')
param principalIdAdmin string

// TODO 041 — replace with AVM reference + roleAssignments

output resourceId string = ''
output vaultUri string = ''
