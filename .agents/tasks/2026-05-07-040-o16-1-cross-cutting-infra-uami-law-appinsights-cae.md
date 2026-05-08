---
id: 2026-05-07-040
title: O16.1 sub-task — implement main.bicep + Container Apps Env + Log Analytics + App Insights (cross-cutting infra)
status: open
priority: P1 (deadline duro Sponsorship 2026-06-30)
assigned_to: copilot-chat
created_at: 2026-05-07
created_by: copilot-chat (autonomous mandate from David — limited Codex credits)
parent: 2026-05-07-039 (O16.1 kickoff scaffold, commit e03f9261)
blocks: 041, 042, 043, 044
relates_to: infra/azure/README.md, infra/azure/main.bicep, infra/azure/modules/*
---

# 040 — O16.1 sub-task: cross-cutting infra (UAMI + LAW + AppInsights + Container Apps Env)

## Contexto

Tras 039 (scaffold landed commit `e03f9261`), 040 es el **primer módulo real** — la base cross-cutting que el resto necesita:

- **UAMI** (`uami-umbral-agents-prod`) — provee `principalId` que 041/042 consumen para RBAC.
- **Log Analytics Workspace** — backend de logs para Container Apps + AppInsights.
- **App Insights** — telemetría/traces para agentes.
- **Container Apps Environment** — host efímero de Container Apps Jobs (crawler, ingester, eval).

040 NO crea Container Apps Jobs (las crean los repos por agente vía CI/CD). Solo el ambiente.

## Scope

### 1. Promover stubs a AVM real

| Archivo | AVM module | Versión pinneada |
|---|---|---|
| `modules/managed-identity.bicep` | `br/public:avm/res/managed-identity/user-assigned-identity` | `0.4.0` |
| `modules/log-analytics.bicep` | `br/public:avm/res/operational-insights/workspace` + `br/public:avm/res/insights/component` | `0.7.0` + `0.4.0` |
| `modules/container-apps-env.bicep` | `br/public:avm/res/app/managed-environment` | `0.8.0` |

### 2. Wire modules en `main.bicep`

`targetScope='subscription'`, crea RG, luego despliega los 3 módulos en `scope: rg`.

### 3. RBAC en este sub-task

- Monitoring Metrics Publisher (`3913510d-...`) → uami sobre App Insights.
- (Storage / Cosmos / Search / KV / SB / DI vienen en 041-042.)

### 4. Outputs útiles para 041/042

- `uamiResourceId`, `uamiPrincipalId`, `uamiClientId`
- `logAnalyticsWorkspaceId`, `logAnalyticsCustomerId`
- `appInsightsId`, `appInsightsConnectionString` (via Key Vault en 041, NO output directo)
- `containerAppsEnvId`

### 5. Validación

```powershell
cd infra/azure
./scripts/validate.ps1
./scripts/what-if.ps1   # solo si hay sub Sponsorship logueada
```

NO deploy real (hay 044 para eso).

## Acceptance criteria

- [ ] `az bicep build --file main.bicep` sin errores.
- [ ] `az deployment sub validate` retorna `Succeeded`.
- [ ] Outputs de main.bicep exponen los 7 valores listados arriba.
- [ ] AVM versions pinneadas explícitamente (NO `latest`).
- [ ] Módulos siguientes (041) pueden importar outputs sin tocar más main.

## Out of scope

- Storage / Cosmos / Key Vault (041).
- Service Bus / AI Search / Document Intelligence (042).
- Budget alerts (043).
- Deploy real (044).
- Crear Container Apps Jobs concretos (responsabilidad de cada repo agente).

## F-INC-002 / Operational guards

- F-INC-002 estricto antes de push.
- secret-output-guard #8: NO output directo de connection strings (App Insights connection string queda interno; en 041 se almacena en Key Vault).
- NO touch VPS runtime.
- NO `az deployment sub create` desde 040 (solo validate / what-if).
