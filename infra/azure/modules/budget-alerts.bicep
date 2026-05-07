// =============================================================================
// budget-alerts.bicep — Consumption Budgets (per-service + total)
// =============================================================================
// Sub-task: 2026-05-07-043 (O16.1 cost hardening)
// AVM ref: br/public:avm/res/consumption/budget:0.4.0
// Scope: subscription (budgets son sub-scope, no RG-scope para Sponsorship)
// Status: PLACEHOLDER — impl en 043
// =============================================================================
// Params esperados:
//   - alertEmail (string): 'alertas@umbralbim.cl'
//   - totalMonthlyBudgetUsd (int): 7206
//   - resourceGroupName (string): 'rg-umbral-agents-prod'
//
// Budgets a crear (Opción B conservadora):
//
// | Budget name                  | Amount/mo | Filter (resourceGroup tag) |
// |------------------------------|-----------|----------------------------|
// | umbral-foundry               | $3500     | resource type Microsoft.CognitiveServices |
// | umbral-ai-search             | $300      | resource type Microsoft.Search |
// | umbral-cosmos                | $200      | resource type Microsoft.DocumentDB |
// | umbral-container-apps        | $700      | resource type Microsoft.App |
// | umbral-storage               | $300      | resource type Microsoft.Storage |
// | umbral-document-intelligence | $400      | resource type Microsoft.CognitiveServices kind=FormRecognizer |
// | umbral-service-bus           | $200      | resource type Microsoft.ServiceBus |
// | umbral-app-insights          | $300      | resource type Microsoft.Insights / OperationalInsights |
// | umbral-key-vault             | $50       | resource type Microsoft.KeyVault |
// | umbral-total-monthly         | $7206     | resourceGroup = rg-umbral-agents-prod |
//
// Thresholds (cada budget): 50% / 80% / 100% → email a alertEmail
//
// Hard stop: NO automático. Runbook manual `docs/runbooks/azure-budget-exceeded.md`
// (a crear en task 043) con pasos:
//   1. Revisar Cost Management por tag resource type
//   2. Identificar resource leakeando
//   3. Pausar Container Apps Job o reducir SKU
//   4. Si imposible: `az group delete --name rg-umbral-agents-prod` (nuke)
// =============================================================================

targetScope = 'subscription'

@description('Email recipient for all budget alerts.')
param alertEmail string

@description('Total monthly budget in USD.')
param totalMonthlyBudgetUsd int

@description('Resource group name to scope total budget.')
param resourceGroupName string

// TODO 043 — replace with AVM reference repeated per budget line above

// Outputs (placeholder)
output budgetIds array = []
