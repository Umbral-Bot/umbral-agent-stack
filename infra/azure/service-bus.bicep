// infra/azure/service-bus.bicep
// Service Bus Standard namespace + 2 queues: lead-enrichment, kb-refresh.
// Standard required for topic/subscription headroom (vs Basic which is queues-only).

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

var nsName = 'sb-umbral-o16-${env}-${uniqueString(resourceGroup().id)}'

resource ns 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: substring(nsName, 0, min(50, length(nsName)))
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    disableLocalAuth: true // managed identity only
    publicNetworkAccess: 'Enabled' // dev default; prod private endpoint
    minimumTlsVersion: '1.2'
  }
}

var queueNames = [
  'lead-enrichment'
  'kb-refresh'
]

resource queues 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = [for q in queueNames: {
  parent: ns
  name: q
  properties: {
    lockDuration: 'PT1M'
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    requiresSession: false
    deadLetteringOnMessageExpiration: true
    maxDeliveryCount: 5
    enablePartitioning: false
    enableBatchedOperations: true
  }
}]

output namespaceName string = ns.name
output namespaceId string = ns.id
