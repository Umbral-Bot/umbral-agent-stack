# 051 — O16.2 AgenteUB File Search wiring + smoke (cierre épica)

**Fecha:** 2026-05-08
**Sub-task de:** [`2026-05-07-045-o16-2-kickoff-aeco-kb-pilot.md`](./2026-05-07-045-o16-2-kickoff-aeco-kb-pilot.md)
**Smoke target:** Friday retro 2026-06-26 — bot Umbral en producción cita un párrafo de buildingSMART/IFC con `aeco-kb-es-vYYYYMMDD` visible y URL fuente.
**Owner:** Copilot Chat (autónomo bajo mandato).

## Scope

Cierra O16.2 cableando el index `aeco-kb-es-current` como data source de la **File Search tool** del `AgenteUB` (Foundry project `umbralbim`, RG productivo distinto a `rg-umbral-agents-prod`) + smoke automatizado que consulta el bot vía Responses API y valida que la respuesta cite versión KB + URL fuente.

## Decisiones autónomas (D33-D38)

| ID | Decisión | Default |
|---|---|---|
| D33 | Auth de la connection Foundry → AI Search | UAMI `uami-umbral-agents-prod` con role `Search Index Data Reader` sobre `srch-umbral-kb-prod`. La connection se crea con AAD identity-based (no API key). Q3 upgrade → managed identity nativa del Foundry project. |
| D34 | Wiring path | Mixto: script Python `foundry_connection.py` crea la connection vía REST (Azure ARM API `Microsoft.MachineLearningServices/workspaces/connections`); File Search tool config en el AgenteUB queda **manual en portal Foundry** (documentado en runbook) por estabilidad de la API a 2026-05. |
| D35 | Smoke prompt | "¿Qué dice IFC 4.3 sobre IfcWall según buildingSMART?" → respuesta debe contener (a) substring `aeco-kb-es-v` (version KB visible), (b) ≥1 URL del seed publicado. |
| D36 | Smoke endpoint | Reusar `umbralbim-resource.services.ai.azure.com/.../AgenteUB/protocols/openai/responses` (mismo que `umbral-bot-2` consume en producción). Auth OAuth client_credentials reutiliza secrets ya existentes en Edge Function — el smoke local usa `DefaultAzureCredential` con scope `https://ai.azure.com/.default`. |
| D37 | Cobertura mínima | Smoke pasa si los 2 checks (D35) son verdaderos para el prompt principal. Bot debe responder en español. |
| D38 | Documentación | `runbooks/o16-2-agenteub-filesearch-wiring.md` con steps manuales de portal Foundry (pegar después de live deploy en 051). |

## Deliverables

1. `scripts/aeco-kb/foundry_connection.py` — crea/actualiza connection Foundry → AI Search vía Azure REST (idempotente).
2. `scripts/aeco-kb/smoke_agenteub_kb.py` — smoke automatizado: invoca AgenteUB, valida cita + URL.
3. `runbooks/o16-2-agenteub-filesearch-wiring.md` — pasos manuales File Search en portal Foundry.
4. README scripts/aeco-kb actualizado.

## Pendiente live (post-merge, requiere cuenta Azure activa + AgenteUB con datos)

- [ ] UAMI role `Search Index Data Reader` sobre `srch-umbral-kb-prod` (cross-RG).
- [ ] `python scripts/aeco-kb/foundry_connection.py` → crea connection.
- [ ] Portal Foundry → AgenteUB → Tools → File Search → add data source `aeco-kb-es-current`.
- [ ] `python scripts/aeco-kb/smoke_agenteub_kb.py` → exit 0.
- [ ] Audit `docs/audits/2026-05-08-o16-2-smoke-deploy.md` con outputs.
- [ ] notion-governance: marcar O16.2 como cerrado en plan Q2.

## Definition of done

- [x] Spec 051 escrito.
- [x] Scripts foundry_connection + smoke creados.
- [x] Runbook publicado.
- [x] README actualizado.
- [x] F-INC-002 OK (syntax check).
- [x] PR/commit pushed a main.
- [ ] Smoke live ejecutado y audit publicado (post-merge, separado).

## Constraints

- NO crear Foundry account/project nuevo. REUSAR `umbralbim-resource` productivo.
- NO modificar AgenteUB instructions text (vive en portal Foundry, no en este repo).
- secret-output-guard #8: NO incluir tokens, keys, ni endpoints completos con secrets en commits.
