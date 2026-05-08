// =============================================================================
// service-bus.bicep — Service Bus Standard (mailbox cross-agente)
// =============================================================================
// Sub-task: 2026-05-07-042 (O16.1 agent-specific services)
// Status: REAL (direct ARM resources)
// =============================================================================
// Standard tier (topics + subs + sessions + dead-letter). Premium NO en Q2.
// 2 topics: 'mailbox' (4 subs por agente) + 'eval-events' (1 sub).
// RBAC Data Sender + Data Receiver → UAMI.
// =============================================================================

@description('Service Bus namespace name.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID for Service Bus Data Sender.')
param principalIdSender string

@description('Principal ID for Service Bus Data Receiver.')
param principalIdReceiver string

resource sb 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource topicMailbox 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  parent: sb
  name: 'mailbox'
  properties: {
    maxSizeInMegabytes: 1024
    defaultMessageTimeToLive: 'P14D'
    enableBatchedOperations: true
    supportOrdering: true
    requiresDuplicateDetection: false
  }
}

var mailboxSubs = [
  'codex'
  'claude'
  'copilot-vps'
  'copilot-chat'
]

resource mailboxSubscriptions 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = [for s in mailboxSubs: {
  parent: topicMailbox
  name: s
  properties: {
    deadLetteringOnMessageExpiration: true
    maxDeliveryCount: 10
    defaultMessageTimeToLive: 'P14D'
    requiresSession: false
    enableBatchedOperations: true
  }
}]

resource topicEval 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  parent: sb
  name: 'eval-events'
  properties: {
    maxSizeInMegabytes: 1024
    defaultMessageTimeToLive: 'P14D'
    enableBatchedOperations: true
  }
}

resource evalSub 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  parent: topicEval
  name: 'eval-coordinator'
  properties: {
    deadLetteringOnMessageExpiration: true
    maxDeliveryCount: 10
    defaultMessageTimeToLive: 'P14D'
    enableBatchedOperations: true
  }
}

// RBAC: Service Bus Data Sender → UAMI (69a216fc-b8fb-44d8-bc22-1f3c2cd27a39)
var sbDataSenderRoleId = '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39'

resource sbSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: sb
  name: guid(sb.id, principalIdSender, sbDataSenderRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', sbDataSenderRoleId)
    principalId: principalIdSender
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Service Bus Data Receiver → UAMI (4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0)
var sbDataReceiverRoleId = '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0'

resource sbReceiver 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: sb
  name: guid(sb.id, principalIdReceiver, sbDataReceiverRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', sbDataReceiverRoleId)
    principalId: principalIdReceiver
    principalType: 'ServicePrincipal'
  }
}

output resourceId string = sb.id
output name string = sb.name
output namespaceEndpoint string = 'https://${sb.name}.servicebus.windows.net/'
