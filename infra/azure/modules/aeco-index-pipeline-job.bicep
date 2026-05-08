// =============================================================================
// aeco-index-pipeline-job.bicep — O16.2/049 Container Apps Job (manual trigger)
// =============================================================================
// Sub-task: 2026-05-08-049
// Status: REAL (direct ARM resource)
// =============================================================================
// Job que ejecuta version-detector o index-publisher según el primer arg.
// Default: publisher.
//
// Identity: UAMI uami-umbral-agents-prod.
// Roles requeridos:
//   - Storage Blob Data Contributor (storage) ✅ asignado en O16.1
//   - Search Index Data Contributor + Search Service Contributor ✅ O16.1
//   - Cognitive Services OpenAI User en umbralbim-resource ⚠️ pending (cablear en 050 deploy real)
// =============================================================================

@description('Job name.')
param name string = 'aeco-index-pipeline'

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Container Apps Environment resource ID.')
param environmentId string

@description('UAMI resource ID.')
param userAssignedIdentityId string

@description('UAMI client ID.')
param userAssignedIdentityClientId string

@description('Storage account name.')
param storageAccountName string

@description('AI Search service name.')
param searchServiceName string

@description('Foundry endpoint para embeddings cross-RG.')
param embeddingEndpoint string = 'https://umbralbim-resource.openai.azure.com'

@description('Embedding deployment name.')
param embeddingDeployment string = 'text-embedding-3-small'

@description('Container image.')
param image string = 'ghcr.io/umbral-bot/aeco-index-pipeline:latest'

@description('GHCR PAT (classic) con scope read:packages — para pull de imagen privada.')
@secure()
param ghcrPat string

@description('Replica timeout (publisher con embeddings + uploads cabe en 60 min para 500 chunks).')
@minValue(60)
@maxValue(7200)
param replicaTimeoutSeconds int = 3600

@description('Retry limit.')
@minValue(0)
@maxValue(5)
param replicaRetryLimit int = 1

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
      secrets: [
        { name: 'ghcr-pat', value: ghcrPat }
      ]
      registries: [
        {
          server: 'ghcr.io'
          username: 'umbral-bot'
          passwordSecretRef: 'ghcr-pat'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'pipeline'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
            { name: 'STORAGE_ACCOUNT', value: storageAccountName }
            { name: 'CONTAINER', value: 'crudos' }
            { name: 'SEARCH_SERVICE', value: searchServiceName }
            { name: 'ALIAS_NAME', value: 'aeco-kb-es-current' }
            { name: 'EMBEDDING_ENDPOINT', value: embeddingEndpoint }
            { name: 'EMBEDDING_DEPLOYMENT', value: embeddingDeployment }
            // Override per-invocation: SOURCE_TYPE (detect) o SOURCE_TYPES (publish)
            // CMD args via az containerapp job start --args 'detect --source-type X' o 'publish --source-types X Y'
          ]
        }
      ]
    }
  }
}

output resourceId string = job.id
output name string = job.name
