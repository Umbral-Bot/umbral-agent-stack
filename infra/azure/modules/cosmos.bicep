// =============================================================================
// cosmos.bicep — Cosmos DB NoSQL (Serverless)
// =============================================================================
// Sub-task: 2026-05-07-041 (O16.1 data plane)
// AVM ref: br/public:avm/res/document-db/database-account:0.10.0
// Status: PLACEHOLDER — impl en 041
// =============================================================================
// Params esperados:
//   - name (string): 'cosmos-umbral-ops-${env}'
//   - location (string)
//   - tags (object)
//   - principalIdDataContributor (string)  ← uami
//
// Outputs esperados:
//   - resourceId (string)
//   - endpoint (string)
//   - databaseName (string)
//
// Capabilities:
//   - 'EnableServerless'      — pay-per-RU, sin baseline
//   - 'EnableNoSQLVectorSearch' — para memoria vectorial
//
// Database + containers iniciales (definidos en sub-resources):
//   - DB: 'umbral-ops'
//   - Containers: 'agent-memory' (pk: /agentId), 'leads' (pk: /companyId),
//     'eval-results' (pk: /agentId), 'mailbox-messages' (pk: /threadId)
//
// RBAC (data plane — usa SQL Role Definitions de Cosmos):
//   - Built-in role 'Cosmos DB Built-in Data Contributor' (00000000-...-002)
//     → uami.principalId
// =============================================================================

@description('Cosmos DB account name.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID for Cosmos DB Built-in Data Contributor.')
param principalIdDataContributor string

// TODO 041 — replace with AVM reference

output resourceId string = ''
output endpoint string = ''
output databaseName string = 'umbral-ops'
