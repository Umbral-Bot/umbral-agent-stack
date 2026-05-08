// =============================================================================
// aeco-source-crawler-job.bicep — O16.2/048 Container Apps Job (manual trigger)
// =============================================================================
// Sub-task: 2026-05-08-048
// Status: REAL (direct ARM resource)
// =============================================================================
// Job manualmente invocable que descarga PDFs desde seeds estáticos por
// source_type, dedupe SHA-256, persiste en crudos/aeco/raw/{source}/.
//
// Identity: UAMI uami-umbral-agents-prod (Storage Blob Data Contributor en O16.1).
// Image: ghcr.io/umbral-bot/aeco-source-crawler:latest.
// Cron diario 03:00 UTC: cableado en 050 (Q2 manual).
// =============================================================================

@description('Job name.')
param name string = 'aeco-source-crawler'

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Container Apps Environment resource ID.')
param environmentId string

@description('UAMI resource ID.')
param userAssignedIdentityId string

@description('UAMI client ID — inyectado como AZURE_CLIENT_ID.')
param userAssignedIdentityClientId string

@description('Storage account name.')
param storageAccountName string

@description('Container image.')
param image string = 'ghcr.io/umbral-bot/aeco-source-crawler:latest'

@description('GHCR PAT (classic) con scope read:packages — para pull de imagen privada.')
@secure()
param ghcrPat string

@description('Replica timeout (crawler con rate-limit 1 req/s + ≤100 docs cabe en 30 min).')
@minValue(60)
@maxValue(7200)
param replicaTimeoutSeconds int = 1800

@description('Retry limit (HTTP 429 / 5xx ya retry-eados internamente; 1 retry de Job para crash transitorio).')
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
          name: 'crawler'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
            { name: 'STORAGE_ACCOUNT', value: storageAccountName }
            { name: 'CONTAINER', value: 'crudos' }
            // Override per-invocation: SOURCE_TYPE, MAX_DOCS
          ]
        }
      ]
    }
  }
}

output resourceId string = job.id
output name string = job.name
