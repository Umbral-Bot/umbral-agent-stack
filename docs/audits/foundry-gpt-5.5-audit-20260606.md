# Foundry audit — `gpt-5.5` para activación en Rick/OpenClaw

- **Fecha:** 2026-06-06
- **Tipo:** Audit read-only (Copilot Windows). Sin writes, sin keys impresas.
- **Objetivo:** Validar el deployment `gpt-5.5` en Foundry para habilitar el alias OpenClaw `azure-openai-responses/gpt-5.5` (deployment directo, NO agente hosted).
- **Skill:** [`.agents/skills/openclaw-foundry-activation/SKILL.md`](../../.agents/skills/openclaw-foundry-activation/SKILL.md)
- **Runbook:** [`docs/runbooks/windows-vps-execution-split.md`](../runbooks/windows-vps-execution-split.md)
- **Superficie ejecutada:** Workstation Windows (Azure CLI autenticado). La activación del alias es **VPS-side** (Copilot-VPS), fuera de alcance de este audit.

## 1. Contexto Azure

| Campo | Valor |
|---|---|
| Subscription name | `Azure subscription 1` |
| Subscription ID | `f14f61f0-e692-4fbb-900d-73e55a632374` |
| Tenant ID | `f67a8c0b-ec74-47cd-836c-355c5a6162d4` |
| Resource group | `rg-openai-cursor` |
| Account (kind=AIServices / Foundry) | `cursor-api-david` |
| Foundry project | `rick-api-david-project` |
| Region | `eastus2` |
| Public network access | `Enabled` |
| Local (API key) auth | **Habilitado** (`disableLocalAuth` = null) |

> Nota: el account `cursor-api-david` es el recurso de Rick/OpenClaw (mismo que aloja `gpt-realtime` referenciado en `.env.example`). NO confundir con `umbralbim-resource` (rg-dm-8454), que pertenece al producto externo umbral-bot.

## 2. Deployment `gpt-5.5`

| Campo | Valor |
|---|---|
| Deployment name | `gpt-5.5` |
| Model name | `gpt-5.5` |
| Model version | `2026-04-24` |
| Provisioning state | **`Succeeded`** |
| SKU | `GlobalStandard` (Estándar global) |
| Capacity | `2517` |
| Responses API support (Microsoft Learn) | ✅ Sí — `gpt-5.5` versión `2026-04-24` listado en modelos soportados por la Responses API |

## 3. Endpoints

| Clase | URL | Uso para el alias |
|---|---|---|
| Account default (cognitiveservices) | `https://cursor-api-david.cognitiveservices.azure.com/` | ❌ NO usar para Responses (host asociado al `FailoverError` `store=false`/`rs_*` documentado en notion-governance policy 05) |
| Azure OpenAI nativo | `https://cursor-api-david.openai.azure.com/` | ✅ **Host correcto** para Responses / Chat Completions |
| Foundry API (services.ai) | `https://cursor-api-david.services.ai.azure.com/` | Inference unificada / agentes |
| Project endpoint | `https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project` | Solo para agente hosted (Rick NO lo usa) |

**Path efectivo del alias OpenClaw `azure-openai-responses`:**
`https://cursor-api-david.openai.azure.com/openai/responses` (o `/openai/v1/responses`).

## 4. API version recomendada

| Superficie | Versión | Estado |
|---|---|---|
| Responses API — next-gen v1 (recomendada) | `/openai/v1/responses?api-version=preview` | Forward path (version-less, features más nuevas) |
| Responses API — dated preview | `2025-04-01-preview` (`/openai/responses`) | **Confirmada en smoke ✓** |
| Chat Completions — GA | `2024-10-21` | GA estable |
| Chat Completions — preview (default del stack) | `2024-12-01-preview` | Default en `.env.example` |

## 5. Auth mode

| Campo | Valor |
|---|---|
| Modo soportado por el recurso | API Key (`api-key` header) **y** Microsoft Entra ID |
| Modo que usa el stack hoy | **API Key** (no `DefaultAzureCredential`) |
| Variable de entorno principal | `AZURE_OPENAI_API_KEY` |
| Variable fallback (agente) | `GPT_RICK_API_KEY` → fallback a `AZURE_OPENAI_API_KEY` |
| Consumidores en el repo | `copilot_agent/agent.py` (BYOK), `dispatcher/model_router.py` (`azure_foundry` → requiere `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY`) |
| OpenClaw (VPS) | Provider `azure-openai-responses` usa `api-key`; el valor vive en `~/.config/openclaw/env` / `gateway.systemd.env` (VPS-side, fuera de este audit) |

## 6. Smoke `gpt-5.5`

- **Método:** `POST https://cursor-api-david.openai.azure.com/openai/responses?api-version=2025-04-01-preview`, body `{ model: "gpt-5.5", input: "...", max_output_tokens: 2000 }`, header `api-key` (no impreso).
- **Resultado:** **PASS** ✅

| Métrica | Valor |
|---|---|
| HTTP | `200` |
| `status` | `completed` |
| `model` devuelto | `gpt-5.5` |
| Response id prefix | `resp_*` |
| Output text | `PASS` |
| Usage | 13 in / 19 out tokens |

> Smoke ejecutado sobre el host nativo `*.openai.azure.com` (el path que usará el alias). Auth por API key validada. Sin secretos en evidencia.

## Recomendación

**¿Listo para el alias OpenClaw `azure-openai-responses/gpt-5.5`?** → **SÍ** (desde la superficie Foundry).

Razones (todas las precondiciones del SKILL cumplidas):
1. Deployment `gpt-5.5` existe y está `Succeeded` (GlobalStandard, capacity 2517 — amplia).
2. Smoke Foundry **PASS** vía Responses API (status `completed`, output correcto).
3. `gpt-5.5` (versión `2026-04-24`) está oficialmente soportado por la Responses API (Microsoft Learn).
4. Host nativo `https://cursor-api-david.openai.azure.com/` disponible — el host correcto para Responses, que evita el `FailoverError` (`store=false`/`rs_*`) observado con el host `cognitiveservices.azure.com`.
5. Auth por API key habilitada y alineada con la variable que el stack ya usa (`AZURE_OPENAI_API_KEY`).

**Condiciones para el paso VPS (Copilot-VPS, requiere autorización explícita de David — NO cubierto aquí):**
- Hacer **OpenClaw audit** primero: leer `~/.openclaw/openclaw.json`, confirmar el schema real del provider `azure-openai-responses` y los modelos existentes (no asumir schema).
- Verificar que el `baseUrl` del provider apunta al host nativo `*.openai.azure.com` (no `cognitiveservices`).
- Confirmar que la API key de `cursor-api-david` está presente en el env de OpenClaw en la VPS.
- Backup de `openclaw.json` → patch SOLO en `.models.providers["azure-openai-responses"].models[]` (agregar `gpt-5.5`) → validar JSON → diff → restart gateway → smoke alias nuevo + alias existente.
- **NO** tocar `agents.list[*].model.primary` ni el default global. **NO** mezclar con Realtime.

## Comandos de evidencia (read-only)

```text
az account show
az cognitiveservices account list
az cognitiveservices account deployment list -n cursor-api-david -g rg-openai-cursor
az cognitiveservices account show -n cursor-api-david -g rg-openai-cursor   # endpoints + auth policy
az rest GET .../accounts/cursor-api-david/projects?api-version=2025-06-01   # project endpoint
POST .../openai/responses?api-version=2025-04-01-preview                     # smoke (api-key no impreso)
```

> Sin keys, tokens ni secretos en este documento ni en la evidencia. Audit puramente read-only: no se modificó ningún recurso Azure, no se editó `openclaw.json`, no se reinició el gateway, no se cambiaron defaults.
