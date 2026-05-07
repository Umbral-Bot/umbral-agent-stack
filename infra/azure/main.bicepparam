using 'main.bicep'

// =============================================================================
// main.bicepparam — params para deploy (1 environment por archivo si necesitás)
// =============================================================================
// Subscription ID NO se commitea — se setea al deploy via:
//   az deployment sub create --location eastus2 \
//     --template-file main.bicep \
//     --parameters main.bicepparam
// =============================================================================

param environment = 'prod'
param location = 'eastus2'
param alertEmail = 'alertas@umbralbim.cl'
param totalMonthlyBudgetUsd = 7206
param tags = {
  owner: 'david-moreira'
  project: 'umbral-agents'
  costCenter: 'sponsorship-2026'
  environment: 'prod'
  managedBy: 'bicep'
}
