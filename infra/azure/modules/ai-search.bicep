// =============================================================================
// ai-search.bicep — AI Search (Basic tier — Opción B conservadora)
// =============================================================================
// Sub-task: 2026-05-07-042 (O16.1 agent-specific services)
// AVM ref: br/public:avm/res/search/search-service:0.7.0
// Status: PLACEHOLDER — impl en 042
// =============================================================================
// Params esperados:
//   - name (string): 'srch-umbral-kb-${env}'
//   - location (string)
//   - tags (object)
//   - principalIdContributor (string)  ← uami para Search Service Contributor
//   - principalIdDataContributor (string)  ← uami para Search Index Data Contributor
//
// Outputs esperados:
//   - resourceId (string)
//   - endpoint (string)
//   - name (string)
//
// Tier:
//   - 'basic' = $75/mes base — 1 partition × 1 replica, 2GB storage, 15 indexes
//   - Promover a 'standard' (S1) cuando KB > 5GB o queries > 60/min sostenido
//
// Settings clave:
//   - replicaCount: 1
//   - partitionCount: 1
//   - hostingMode: 'default'
//   - publicNetworkAccess: 'enabled' (Q3 evaluar Private Endpoint)
//   - authOptions: 'aadOrApiKey' (preferimos AAD via uami)
//   - semanticSearch: 'free' (incluido en Basic)
//
// RBAC:
//   - Search Service Contributor → uami (mgmt: crear/eliminar indexes)
//   - Search Index Data Contributor → uami (data plane: read/write docs)
//
// Indexes esperados (creados por agentes en runtime):
//   - aeco-kb-es-vYYYYMMDD
//   - aeco-kb-en-vYYYYMMDD
//   - aeco-kb-pt-vYYYYMMDD
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

// TODO 042 — replace with AVM reference at sku=basic

output resourceId string = ''
output endpoint string = ''
output serviceName string = name
