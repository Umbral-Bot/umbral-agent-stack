---
id: 2026-05-07-042
title: O16.1 sub-task 042 — agent-specific services (Service Bus + AI Search + Document Intelligence)
status: in-progress
created: 2026-05-07
assigned_to: copilot-chat
parent: 2026-05-07-039
depends_on: 2026-05-07-041  # commit 32a92b36 (Storage + Cosmos + KV)
blocks: [2026-05-07-043, 2026-05-07-044]
---

# 042 — Agent-specific services (Service Bus + AI Search + Document Intelligence)

## Objetivo

Promover a REAL los módulos de servicios específicos por agente:

- **service-bus.bicep** → Namespace `Standard` + topics `mailbox` (4 subs: codex/claude/copilot-vps/copilot-chat) + `eval-events` (1 sub: eval-coordinator). RBAC `Service Bus Data Sender` + `Receiver` → UAMI.
- **ai-search.bicep** → Service `basic` tier ($75/mes base, 2GB, 15 indexes, semantic free), `aadOrApiKey` (AAD-first via UAMI). RBAC `Search Service Contributor` + `Search Index Data Contributor` → UAMI.
- **document-intelligence.bicep** → CognitiveServices `kind=FormRecognizer` `S0`, `customSubDomainName=name`, `disableLocalAuth=true` (AAD-only). RBAC `Cognitive Services User` → UAMI.
- **main.bicep** → wire 3 módulos + 3 outputs cada uno.

## Decisiones

- **Direct ARM** (consistente con 040/041).
- **Service Bus Standard** (no Premium) — Sponsorship volumen bajo. Topics + sessions + dead-letter incluidos.
- **AI Search Basic** — locked en plan Q2 ($75/mes base). Promover a S1 solo si KB >5GB.
- **DI S0** — F0 free no sirve (limita 500 págs/mes). `disableLocalAuth=true` fuerza AAD via UAMI (no api-key).
- Topics/subs creados como sub-resources (no en runtime). Cada agente consume su propia subscription.
- Indexes de AI Search NO se crean en bicep — los crean los agentes en runtime (`aeco-kb-es-vYYYYMMDD`).

## RBAC matrix (esta task)

| Resource | Role | Built-in ID | Principal |
|---|---|---|---|
| Service Bus namespace | Azure Service Bus Data Sender | `69a216fc-b8fb-44d8-bc22-1f3c2cd27a39` | UAMI |
| Service Bus namespace | Azure Service Bus Data Receiver | `4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0` | UAMI |
| AI Search service | Search Service Contributor (mgmt) | `7ca78c08-252a-4471-8644-bb5ff32d4ba0` | UAMI |
| AI Search service | Search Index Data Contributor | `8ebe5a00-799e-43f5-93ac-243d3dce84a7` | UAMI |
| Document Intelligence | Cognitive Services User | `a97b65f3-24c7-4388-baec-2e87135dc908` | UAMI |

## Acceptance

- `az bicep build main.bicep` clean (warnings 043 esperadas: `alertEmail`/`totalMonthlyBudgetUsd`).
- NO deploy real.

## Guardrails

- F-INC-002 estricto pre-push.
- secret-output-guard: ningún connection string outputea (DI/Search no tienen — usan AAD).
- NO touch openclaw / VPS / runtime.

## Next

- 043 — Budget alerts (consume `alertEmail` + `totalMonthlyBudgetUsd` reservados desde 039 — cierra warnings).
- 044 — Smoke deploy real (`az deployment sub create`).
