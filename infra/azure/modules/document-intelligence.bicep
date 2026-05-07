// =============================================================================
// document-intelligence.bicep — Document Intelligence (Form Recognizer S0)
// =============================================================================
// Sub-task: 2026-05-07-042 (O16.1 agent-specific services)
// AVM ref: br/public:avm/res/cognitive-services/account:0.10.0
// Status: PLACEHOLDER — impl en 042
// =============================================================================
// Params esperados:
//   - name (string): 'di-umbral-${env}'
//   - location (string)  ← validar disponibilidad en eastus2
//   - tags (object)
//   - principalIdReader (string)  ← uami para Cognitive Services User
//
// Outputs esperados:
//   - resourceId (string)
//   - endpoint (string)
//
// Kind: 'FormRecognizer' (Document Intelligence v4)
// SKU: 'S0' (pay-per-page; F0 free tier limita 500 págs/mes y NO sirve para producción)
//
// Modelos a usar (built-in, no custom Q2):
//   - prebuilt-layout (PDFs estructurados)
//   - prebuilt-read (OCR puro)
//   - prebuilt-document (key-value generic)
//
// Custom models llegan en Q3 si datasets justifican.
//
// RBAC:
//   - Cognitive Services User → uami.principalId
//
// Settings clave:
//   - publicNetworkAccess: 'Enabled' (Q3 evaluar Private Endpoint)
//   - disableLocalAuth: true (forzar AAD via uami)
//   - customSubDomainName: name (requerido para AAD)
// =============================================================================

@description('Document Intelligence account name.')
param name string

@description('Azure region (validar disponibilidad — eastus2 OK).')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID for Cognitive Services User.')
param principalIdReader string

// TODO 042 — replace with AVM reference at kind=FormRecognizer, sku=S0

output resourceId string = ''
output endpoint string = ''
