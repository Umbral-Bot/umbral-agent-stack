# Audit — Azure AI Foundry capacity + OpenClaw sync (post-MP1)

- **Fecha:** 2026-07-04
- **Superficie:** Copilot Windows (Azure CLI, read-only + smokes con api-key en memoria)
- **Cuenta Azure:** dm@umbralbim.cl — subscription `Azure subscription 1` (`f14f61f0-…2374`)
- **Contexto:** MP1 aplicado en VPS (`OPENCLAW_AZURE_ONLY=YES`): primary `azure/gpt-5.5`, fallback único `azure/gpt-5.4`. Evidencia VPS: `~/.coord-ag-evidence/openclaw-azure-only-policy-2026-07-04.md`.
- **Sin secretos:** ninguna key impresa ni almacenada en este documento.

## Resultado

```
AZURE_FOUNDRY_AUDIT=OK | gpt-5.5=deployed | capacity=ok | openclaw_sync_plan=docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md#handoff-copilot-vps
```

Azure/Foundry está sano. **Todos** los hallazgos MP1 ("deployments rotos") son problemas de configuración/auth del lado OpenClaw, no de Azure.

## 1. Recurso e infraestructura

| Ítem | Valor |
|---|---|
| Resource group | `rg-openai-cursor` (eastus) |
| Account | `cursor-api-david` — kind `AIServices`, SKU `S0`, región **eastus2** |
| Endpoint inference (usado por VPS) | `https://cursor-api-david.openai.azure.com/openai/v1` ✅ live (smoke PASS) |
| Endpoint alterno mismo account | `https://cursor-api-david.cognitiveservices.azure.com/` (audio/realtime scripts) |
| Endpoint Foundry project (Gpt-Rick app) | `https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project/...` (Responses/Activity Protocol — superficie separada, ver `openclaw/workspace-templates/TOOLS.md`) |
| Auth | api-key (`AZURE_OPENAI_*` / GPT_RICK en env VPS — valores no impresos) |

Otros accounts del stack con deployments GPT-5.x (comparten cuota regional): `umbralbim-resource` (rg-dm-8454), `n8n-resource-dmm` (rg-dm-9162), `oai-umbral-agents-prod` (rg-umbral-agents-prod, sin gpt-5.x).

## 2. Tabla de deployments — `cursor-api-david`

| Deployment | Model (version) | SKU / capacity | Rate limits (por 60 s) | Región | Estado Azure | Smoke 2026-07-04 | ¿En openclaw.json (post-MP1)? |
|---|---|---|---|---|---|---|---|
| **gpt-5.5** | gpt-5.5 (2026-04-24) | GlobalStandard / **2 517** | 2 517 req · 2 517 000 tok | eastus2 | Succeeded | ✅ PASS `/responses` → `AZURE_PONG` | ✅ **primary** — mantener |
| **gpt-5.4** | gpt-5.4 (2026-03-05) | GlobalStandard / **5 000** | 50 000 req · 5 000 000 tok | eastus2 | Succeeded | ✅ PASS `/responses` → `AZURE_PONG` | ✅ **fallback único** — mantener |
| **gpt-5.4-pro** | gpt-5.4-pro (2026-03-05) | GlobalStandard / 800 | 800 req · 800 000 tok | eastus2 | Succeeded | ✅ PASS `/responses` · ❌ `/chat/completions` → "operation unsupported" (esperado) | ⚠️ retirar del catálogo OpenClaw (ver hallazgo A) |
| gpt-4.1 | gpt-4.1 (2025-04-14) | GlobalStandard / 50 | — | eastus2 | Succeeded | ✅ PASS `/chat/completions` con api-key | ❌ retirar (hallazgo B) |
| gpt-5.2-chat | gpt-chat-latest (2026-05-05) | GlobalStandard / 150 | — | eastus2 | Succeeded | ✅ PASS `/chat/completions` con api-key | ❌ retirar (hallazgo B) |
| Kimi-K2.5 | Kimi-K2.5 v1 (MoonshotAI) | GlobalStandard / 50 | — | eastus2 | Succeeded | ✅ PASS vía `services.ai.azure.com/models/chat/completions` | ❌ retirar (hallazgo B) |
| gpt-5.3-codex | gpt-5.3-codex (2026-02-24) | GlobalStandard / 5 000 | — | eastus2 | Succeeded | no probado (fuera de cadenas MP1) | no — disponible por api-key si se necesitara |
| Otros (o3 10 000 · o3-pro 1 600 · codex-mini 10 000 · DeepSeek-V3.2 500 · gpt-audio-1.5 15 000 · gpt-realtime 10 · gpt-image-15 60 · sora-2 10 · text-embedding-3-small/large · whisper) | — | GlobalStandard/Standard | — | eastus2 | Succeeded | n/a | no aplican a cadenas de chat OpenClaw |

## 3. Capacidad y throttling (429)

**Métricas `AzureOpenAIRequests` últimos 7 días (2026-06-27 → 07-04):**

| Métrica | Valor |
|---|---|
| Total requests | 2 043 — **100 % HTTP 200, cero 429, cero 5xx** |
| Por deployment | gpt-5.5: 2 009 · gpt-5.4: 30 · gpt-5.2-chat: 4 |
| Pico implícito | ≈ 300 req/día ≪ 2 517 RPM de gpt-5.5 |

**Cuota regional GlobalStandard eastus2 (K-TPM asignados / límite):**

| Familia | Usado | Límite | Desglose asignación |
|---|---|---|---|
| gpt-5.5 | 17 393 | 30 000 | cursor-api-david 2 517 + umbralbim-resource 2 270 + n8n-resource-dmm 12 606 → **headroom libre 12 607** |
| gpt-5.4 | 7 500 | 30 000 | cursor-api-david 5 000 + umbralbim-resource 2 500 → headroom 22 500 |
| gpt-5.4-pro | 1 200 | 4 800 | cursor-api-david 800 + umbralbim-resource 400 |
| gpt-4.1 (Std) | según portal | — | uso actual nulo en cadenas |

**Veredicto capacidad: OK — no se requiere bump.** Uso real está ~3 órdenes de magnitud por debajo del límite y no hubo un solo 429 en la semana. Si a futuro aparecen 429 sostenidos: Foundry portal → Deployments → `gpt-5.5` → Edit → subir capacity (hay 12 607 K-TPM libres en la región; operación online, sin downtime, reversible).

## 4. Hallazgos MP1 resueltos

### A. `gpt-5.4-pro` re-ruteado a Codex OAuth (400) — CAUSA RAÍZ ENCONTRADA
El deployment existe y está sano, pero sus capabilities son `chatCompletion: false, responses: true` → **solo acepta Responses API**. Verificado en vivo: `/openai/v1/responses` PASS, `/openai/v1/chat/completions` responde "The requested operation is unsupported". Si OpenClaw registra el alias por la ruta chat/completions, el 400 es determinista y el runtime cae a Codex OAuth.
**Decisión recomendada:** retirarlo del catálogo OpenClaw (la política MP1 define fallback único `gpt-5.4`, que tiene 6× su capacidad). El deployment puede quedar en Azure (PAYG, costo cero sin uso); re-agregarlo solo si el provider de OpenClaw invoca Responses API nativamente.

### B. "Saved login expired" en gpt-5.2-chat / Kimi-K2.5 / gpt-4.1 — NO es Azure
Los tres deployments existen (`Succeeded`) y los tres **pasan smoke con la api-key vigente** del account. El error "saved login expired" proviene de perfiles auth OAuth/sesión del lado OpenClaw, no de Foundry.
**Decisión recomendada:** limpiarlos de providers en `openclaw.json` (coherente con MP1 azure-only). No se requiere re-auth ni re-deploy en Azure. Decommission en Azure es opcional (uso semanal: 4/0/0 requests) y queda a criterio de David — no bloquea nada.

### C. Endpoint live confirmado
`https://cursor-api-david.openai.azure.com/openai/v1` operativo (smokes gpt-5.5/gpt-5.4/gpt-5.4-pro vía `/responses`). Coincide con `AZURE_OPENAI_*`/GPT_RICK en env VPS.

### D. Aliases residuales `models.json` (VPS-side)
`gpt→openai/gpt-5.4` y `gemini-flash→google/…` en `~/.openclaw/agents/main/agent/models.json` no son verificables desde Windows → incluidos en el handoff para Copilot-VPS (borrar o re-apuntar a `azure/*`).

## 5. Cross-check repo

| Archivo | Estado |
|---|---|
| `config/editorial-model.yaml` | ✅ consistente con MP1: `azure-openai-responses/gpt-5.5` requerido + fallback `azure-openai-responses/gpt-5.4`, silent-fallback prohibidos. Sin cambios. |
| `openclaw/workspace-templates/TOOLS.md` | ✅ URLs Responses/Activity apuntan al project endpoint `services.ai.azure.com/.../Gpt-Rick` (superficie Foundry app, distinta del inference endpoint). Vigente. Sin cambios. |
| `docs/15-model-quota-policy.md` | ⚠️ drift: la nota de estado 2026-03-08 describía gpt-4.1/gpt-5.2-chat/Kimi como los modelos Azure activos. **Actualizado** en este audit con nota de estado 2026-07-04 (MP1). |

<a id="handoff-copilot-vps"></a>
## 6. Handoff → Copilot-VPS (MP2, requiere autorización de David para writes/restart)

**Contexto:** Azure sano; todo el trabajo restante es runtime OpenClaw. Backup + diff + smoke obligatorios según skill `openclaw-vps-operator`.

1. **Backup:** `cp -a ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-$(date +%F-%H%M)`.
2. **Mantener (cadena válida azure, ya aplicada en MP1):**
   - `azure/gpt-5.5` — primary (deployment `gpt-5.5`, 2 517 K-TPM, Responses+Chat OK).
   - `azure/gpt-5.4` — fallback único (deployment `gpt-5.4`, 5 000 K-TPM, Responses+Chat OK).
3. **Eliminar de `openclaw.json` (providers/catálogo):**
   - `gpt-5.4-pro` (Responses-only en Azure; 400 por chat/completions → re-ruteo Codex OAuth).
   - `gpt-5.2-chat`, `kimi-k2.5`, `gpt-4.1` (perfiles auth OAuth muertos en OpenClaw; en Azure funcionan por api-key pero están fuera de política MP1).
   - Cualquier residuo `openai/*` y `google/*` en cadenas.
4. **Limpiar `~/.openclaw/agents/main/agent/models.json`:** borrar aliases `gpt→openai/gpt-5.4` y `gemini-flash→google/…`, o re-apuntarlos a `azure/gpt-5.4` si algún flujo los referencia.
5. **Validar JSON + diff**, luego (con autorización) `systemctl --user restart openclaw-gateway`.
6. **Smoke:** alias primary y fallback (`AZURE_PONG`), + `openclaw models status`. Reportar PASS/PARTIAL/FAIL y evidencia en `~/.coord-ag-evidence/`.
7. **Rollback documentado:** `cp -a <backup> ~/.openclaw/openclaw.json && systemctl --user restart openclaw-gateway`.
8. **No requerido:** bump de TPM en Foundry (cero 429/7d). Si aparecieran 429 sostenidos, avisar a Copilot Windows → subir capacity de `gpt-5.5` en portal (headroom regional 12 607 K-TPM).

## Comandos ejecutados (reproducibilidad, read-only salvo smokes POST)

```
az account show
az cognitiveservices account list
az group list
az cognitiveservices account deployment list -g rg-openai-cursor -n cursor-api-david
az cognitiveservices account deployment show ... (gpt-5.5 / gpt-5.4 / gpt-5.4-pro)
az cognitiveservices usage list -l eastus2
az monitor metrics list --metric AzureOpenAIRequests (split StatusCode / ModelDeploymentName, 7d)
az cognitiveservices account keys list  # key solo en memoria del shell para smokes
POST {endpoint}/openai/v1/responses (gpt-5.5, gpt-5.4, gpt-5.4-pro) → AZURE_PONG
POST {endpoint}/openai/v1/chat/completions (gpt-4.1, gpt-5.2-chat, gpt-5.4-pro=fail esperado)
POST https://cursor-api-david.services.ai.azure.com/models/chat/completions (Kimi-K2.5)
```
