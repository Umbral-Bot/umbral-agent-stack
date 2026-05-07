// =============================================================================
// service-bus.bicep — Service Bus Standard (mailbox cross-agente)
// =============================================================================
// Sub-task: 2026-05-07-042 (O16.1 agent-specific services)
// AVM ref: br/public:avm/res/service-bus/namespace:0.11.0
// Status: PLACEHOLDER — impl en 042
// =============================================================================
// Params esperados:
//   - name (string): 'sb-umbral-mailbox-${env}'
//   - location (string)
//   - tags (object)
//   - principalIdSender (string)    ← uami
//   - principalIdReceiver (string)  ← uami
//
// Outputs esperados:
//   - resourceId (string)
//   - namespaceEndpoint (string)
//
// Tier:
//   - Standard = topics/subscriptions + sessions + dead-letter
//   - Premium NO necesario para Q2 (volumen bajo)
//
// Topics + subscriptions iniciales (creados como sub-resources):
//   - Topic: 'mailbox'
//     - Subscription: 'codex'
//     - Subscription: 'claude'
//     - Subscription: 'copilot-vps'
//     - Subscription: 'copilot-chat'
//   - Topic: 'eval-events'
//     - Subscription: 'eval-coordinator'
//
// RBAC:
//   - Azure Service Bus Data Sender → uami
//   - Azure Service Bus Data Receiver → uami
//
// Reemplaza (eventualmente) `.agents/mailbox/*.md` filesystem-based.
// Migración progresiva en O17.
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

// TODO 042 — replace with AVM reference at sku=Standard

output resourceId string = ''
output namespaceEndpoint string = ''
