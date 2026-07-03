# Azure OpenAI / Foundry — inventario y recurso canónico Umbral Agent Stack

> **Fecha:** 2026-07-02  
> **Estado:** ✅ **`oai-umbral-agents-prod` creado** 2026-07-02 · deployment **`gpt-4.1-mini`** activo  
> **Decisión:** `umbralbim-resource` es del **producto Umbral BIM** (cutover web). **No** usarlo para Rick, Graphify ni piloto UAS.

---

## Inventario actual (subscription Umbral)

| Recurso | RG | Kind | Uso canónico |
|---------|-----|------|--------------|
| `umbralbim-resource` | `rg-dm-8454` | AIServices | **Umbral BIM** (chat web, cutover Azure) |
| `speech-copilot-transcribe` | `rg-umbral-agents-prod` | SpeechServices | STT/TTS Rick voz (LorenzoNeural) |
| `di-umbral-prod` | `rg-umbral-agents-prod` | FormRecognizer | AECO KB PDF/OCR |
| `srch-umbral-kb-prod` | `rg-umbral-agents-prod` | Search | AECO KB index |
| `cursor-api-david` | `rg-openai-cursor` | AIServices | Dev personal Cursor |
| `oai-j2dimqy6` | `rg-visor-ifc-secure` | OpenAI | Visor IFC (otro producto) |
| `n8n-resource-dmm` | `rg-dm-9162` | AIServices | n8n |

**Gap:** en `rg-umbral-agents-prod` **no existe** cuenta OpenAI/Foundry para LLM (Rick runtime, Graphify `--backend azure`, embeddings editorial, Fase 2 gpt-realtime).

---

## Recurso canónico (creado)

| Campo | Valor |
|-------|--------|
| **Nombre** | `oai-umbral-agents-prod` ✅ |
| **RG** | `rg-umbral-agents-prod` |
| **Región** | `eastus2` |
| **Endpoint** | `https://oai-umbral-agents-prod.cognitiveservices.azure.com/` |
| **Deployment piloto Graphify** | `gpt-4.1-mini` (2025-04-14) ✅ |
| **Tags** | `area=agents`, `product=umbral-agent-stack`, `owner=rick` |

### Deployment mínimo post-creación (Graphify F2)

| Deployment | Modelo | Uso |
|------------|--------|-----|
| `gpt-4.1-mini` ✅ | extracción semántica docs Graphify pasada 2 | Piloto Graphify (~USD 10 cap) |

Fase 2 voz realtime (`gpt-realtime`) → deployment aparte, gate David.

---

## Recurso canónico propuesto (referencia — ya creado)

---

## Crear recurso (portal)

Portal **Create Azure AI Foundry** (David debe iniciar sesión):

https://portal.azure.com/#create/Microsoft.CognitiveServicesAIFoundry

Valores en el formulario:

- Resource group: **rg-umbral-agents-prod**
- Region: **East US 2**
- Name: **oai-umbral-agents-prod**
- Pricing tier: **Standard S0**

Keys (recurso creado):

https://portal.azure.com/#@umbralbim.cl/resource/subscriptions/f14f61f0-e692-4fbb-900d-73e55a632374/resourceGroups/rg-umbral-agents-prod/providers/Microsoft.CognitiveServices/accounts/oai-umbral-agents-prod/cskeys

---

## Crear recurso (CLI — Copilot Windows, si David autoriza)

```powershell
az cognitiveservices account create `
  -g rg-umbral-agents-prod `
  -n oai-umbral-agents-prod `
  -l eastus2 `
  --kind AIServices `
  --sku S0 `
  --custom-domain oai-umbral-agents-prod `
  --tags area=agents product=umbral-agent-stack owner=rick

# Verificar
az cognitiveservices account show -g rg-umbral-agents-prod -n oai-umbral-agents-prod `
  --query "{endpoint:properties.endpoint,name:name}" -o json
```

Luego desplegar modelo en Foundry portal o `az cognitiveservices account deployment create` (según quota).

---

## Variables para Graphify F2 (sesión Copilot Windows)

```powershell
$env:AZURE_OPENAI_API_KEY = "<key1 de oai-umbral-agents-prod>"
$env:AZURE_OPENAI_ENDPOINT = "https://oai-umbral-agents-prod.cognitiveservices.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-4.1-mini"
```

**No** commitear keys. **No** usar `umbralbim-resource`.

---

## VPS Rick (runtime)

Hoy Rick en VPS usa paths propios (`KIMI_AZURE_*`, fallbacks vertex/kimi). Alinear `AZURE_OPENAI_*` del gateway a `oai-umbral-agents-prod` es **post-capitalización** (task Rick voz / infra), no bloqueante del piloto Graphify local en Windows.

---

## Referencias repo

- `infra/azure/README.md` — naming, RG, presupuesto Foundry
- `docs/ops/sprint-2026-07-02-prompts-index.md` — preflight Graphify
- `.env.example` — vars estándar UAS
