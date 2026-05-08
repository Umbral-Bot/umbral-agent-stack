// =============================================================================
// aeco-pdf-parser-job.bicep — O16.2/047 Container Apps Job (manual trigger)
// =============================================================================
// Sub-task: 2026-05-07-047
// Status: REAL (direct ARM resource)
// =============================================================================
// Job manualmente invocable (`az containerapp job start`) que parsea 1 PDF de
// `crudos/aeco/raw/...` con DI prebuilt-layout y escribe chunks a
// `crudos/aeco/parsed/...`. Trigger Event Grid → SB → KEDA se cablea en 050.
//
// Identity: UAMI `uami-umbral-agents-prod` (RBAC ya asignado en O16.1:
//   - Cognitive Services User → di-umbral-prod
//   - Storage Blob Data Contributor → stumbralagentsprod
// ).
//
// Image: ghcr.io/umbral-bot/aeco-pdf-parser:latest (público GHCR — Q3 migrar a ACR).
// =============================================================================

@description('Job name.')
param name string = 'aeco-pdf-parser'

@description('Azure region (debe coincidir con el Container Apps Environment).')
param location string

@description('Tags.')
param tags object = {}

@description('Container Apps Environment resource ID.')
param environmentId string

@description('UAMI resource ID (uami-umbral-agents-prod).')
param userAssignedIdentityId string

@description('UAMI client ID — inyectado al container como AZURE_CLIENT_ID.')
param userAssignedIdentityClientId string

@description('Document Intelligence endpoint (https://di-umbral-prod.cognitiveservices.azure.com/).')
param diEndpoint string

@description('Storage account name (stumbralagentsprod).')
param storageAccountName string

@description('Container image (override en CI/CD para pin de tag inmutable).')
param image string = 'ghcr.io/umbral-bot/aeco-pdf-parser:latest'

@description('Replica timeout en segundos (PDFs grandes pueden tomar 5-10 min).')
@minValue(60)
@maxValue(3600)
param replicaTimeoutSeconds int = 1800

@description('Replica retry limit (DI puede dar 429 transitorios).')
@minValue(0)
@maxValue(10)
param replicaRetryLimit int = 2

resource job 'Microsoft.App/jobs@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    environmentId: environmentId
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: replicaTimeoutSeconds
      replicaRetryLimit: replicaRetryLimit
      manualTriggerConfig: {
        replicaCompletionCount: 1
        parallelism: 1
      }
    }
    template: {
      containers: [
        {
          name: 'pdf-parser'
          image: image
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
            { name: 'DI_ENDPOINT', value: diEndpoint }
            { name: 'STORAGE_ACCOUNT', value: storageAccountName }
            { name: 'INPUT_CONTAINER', value: 'crudos' }
            { name: 'OUTPUT_CONTAINER', value: 'crudos' }
            // Override per-invocation con `az containerapp job start --env-vars ...`:
            //   INPUT_BLOB_PATH, SOURCE_TYPE, JURISDICTION, DOC_TYPE, VERSION, LANG, SOURCE_URL, VALID_FROM
          ]
        }
      ]
    }
  }
}

output resourceId string = job.id
output name string = job.name
