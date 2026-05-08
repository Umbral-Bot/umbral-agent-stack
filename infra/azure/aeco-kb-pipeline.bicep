// =============================================================================
// aeco-kb-pipeline.bicep — O16.2/050 umbrella del pipeline AECO KB
// =============================================================================
// Sub-task: 2026-05-08-050
// Status: REAL (referencia los 3 módulos jobs de 047/048/049)
// =============================================================================
// Despliega los 3 ACA Jobs del pipeline AECO KB, cada uno con manualTrigger.
// El orquestador secuencial vive en scripts/aeco-kb/run_pipeline.sh (Q2).
// Q3 upgrade → Service Bus chained / KEDA event-driven.
//
// Uso:
//   az deployment group create -g rg-umbral-agents-prod \
//     -f infra/azure/aeco-kb-pipeline.bicep \
//     -p location=eastus2 \
//     -p environmentId=<cae-id> \
//     -p userAssignedIdentityId=<uami-id> \
//     -p userAssignedIdentityClientId=<uami-client-id> \
//     -p storageAccountName=stumbralagentsprod \
//     -p searchServiceName=srch-umbral-kb-prod \
//     -p diEndpoint=https://di-umbral-prod.cognitiveservices.azure.com/
// =============================================================================

@description('Azure region.')
param location string

@description('Resource tags.')
param tags object = {}

@description('Container Apps Environment resource ID.')
param environmentId string

@description('UAMI resource ID.')
param userAssignedIdentityId string

@description('UAMI client ID.')
param userAssignedIdentityClientId string

@description('Storage account name (raw + parsed + index manifests).')
param storageAccountName string

@description('AI Search service name.')
param searchServiceName string

@description('Document Intelligence endpoint.')
param diEndpoint string

@description('Foundry endpoint para embeddings (cross-RG).')
param embeddingEndpoint string = 'https://umbralbim-resource.openai.azure.com'

@description('Embedding deployment name.')
param embeddingDeployment string = 'text-embedding-3-small'

@description('GHCR PAT (classic) con scope read:packages — pull de imágenes privadas.')
@secure()
param ghcrPat string

module sourceCrawler 'modules/aeco-source-crawler-job.bicep' = {
  name: 'aeco-source-crawler-job'
  params: {
    location: location
    tags: tags
    environmentId: environmentId
    userAssignedIdentityId: userAssignedIdentityId
    userAssignedIdentityClientId: userAssignedIdentityClientId
    storageAccountName: storageAccountName
    ghcrPat: ghcrPat
  }
}

module pdfParser 'modules/aeco-pdf-parser-job.bicep' = {
  name: 'aeco-pdf-parser-job'
  params: {
    location: location
    tags: tags
    environmentId: environmentId
    userAssignedIdentityId: userAssignedIdentityId
    userAssignedIdentityClientId: userAssignedIdentityClientId
    diEndpoint: diEndpoint
    storageAccountName: storageAccountName
    ghcrPat: ghcrPat
  }
}

module indexPipeline 'modules/aeco-index-pipeline-job.bicep' = {
  name: 'aeco-index-pipeline-job'
  params: {
    location: location
    tags: tags
    environmentId: environmentId
    userAssignedIdentityId: userAssignedIdentityId
    userAssignedIdentityClientId: userAssignedIdentityClientId
    storageAccountName: storageAccountName
    searchServiceName: searchServiceName
    embeddingEndpoint: embeddingEndpoint
    embeddingDeployment: embeddingDeployment
    ghcrPat: ghcrPat
  }
}

output crawlerJobName string = sourceCrawler.outputs.name
output parserJobName string = pdfParser.outputs.name
output publisherJobName string = indexPipeline.outputs.name
