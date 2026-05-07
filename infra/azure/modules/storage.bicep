// =============================================================================
// storage.bicep — Storage Account (Hot tier, Blob)
// =============================================================================
// Sub-task: 2026-05-07-041 (O16.1 data plane)
// AVM ref: br/public:avm/res/storage/storage-account:0.14.0
// Status: PLACEHOLDER — impl en 041
// =============================================================================
// Params esperados:
//   - name (string): 'stumbralagents${env}' (≤24, lowercase, sin guiones)
//   - location (string)
//   - tags (object)
//   - principalIdContributor (string)  ← uami para Storage Blob Data Contributor
//
// Outputs esperados:
//   - resourceId (string)
//   - blobEndpoint (string)
//
// Containers iniciales (creados por module o por crawler en runtime):
//   - 'crudos'           — PDFs/HTML/JSON sin procesar
//   - 'datasets-curados' — JSONL para File Search
//   - 'eval-results'     — outputs de eval pipelines
//
// RBAC:
//   - Storage Blob Data Contributor → uami.principalId
//
// Settings clave:
//   - allowBlobPublicAccess: false
//   - supportsHttpsTrafficOnly: true
//   - minimumTlsVersion: 'TLS1_2'
//   - accessTier: 'Hot'
//   - sku: 'Standard_LRS' (Sponsorship; promover a ZRS si hace falta)
// =============================================================================

@description('Storage account name (≤24 chars, lowercase, no hyphens).')
@maxLength(24)
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID of the user-assigned MI for Storage Blob Data Contributor role.')
param principalIdContributor string

// TODO 041 — replace with AVM reference + roleAssignments

// Outputs (placeholder)
output resourceId string = ''
output blobEndpoint string = ''
