# Runbook — O16.2/051 AgenteUB File Search wiring

**Owner:** David Moreira (operación) + Copilot Chat (scripts).
**Smoke target:** Friday retro 2026-06-26.

## Pre-requisitos

- Pipeline 050 ejecutado, `aeco-kb-es-current` apunta a un index con ≥500 chunks.
- `python scripts/aeco-kb/verify_kb.py --min-chunks 500` → exit 0.
- `az login` con cuenta que tenga RBAC sobre `umbralbim-resource` (Foundry) y `srch-umbral-kb-prod`.

## Paso 1 — Asignar role a la UAMI sobre AI Search (cross-RG)

```bash
UAMI_PRINCIPAL_ID=$(az identity show -g rg-umbral-agents-prod -n uami-umbral-agents-prod --query principalId -o tsv)
SEARCH_ID=$(az search service show -g rg-umbral-agents-prod -n srch-umbral-kb-prod --query id -o tsv)

az role assignment create \
  --assignee-object-id "$UAMI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Search Index Data Reader" \
  --scope "$SEARCH_ID"
```

> Foundry necesita además `Cognitive Services OpenAI User` sobre `umbralbim-resource` (ya pendiente desde 049 para embeddings — cablear acá si todavía no se hizo).

## Paso 2 — Crear connection Foundry → AI Search (script idempotente)

```bash
python scripts/aeco-kb/foundry_connection.py \
  --foundry-sub <FOUNDRY_SUB_ID> \
  --foundry-rg <FOUNDRY_RG> \
  --foundry-workspace umbralbim
```

> El script crea/actualiza `connections/aeco-kb-search` con `category=CognitiveSearch`, `authType=AAD`, target `https://srch-umbral-kb-prod.search.windows.net`.

## Paso 3 — Configurar File Search tool del AgenteUB (manual, portal Foundry)

1. Portal Foundry → project `umbralbim` → Agents → `AgenteUB`.
2. Tools → File Search → **+ Add data source**.
3. Source type: **Azure AI Search**.
4. Connection: seleccionar `aeco-kb-search` (creada en Paso 2).
5. Index: `aeco-kb-es-current` (alias).
6. Field mapping:
   - Content field: `content`
   - Vector field: `content_vector`
   - Title field: `doc_title`
   - URL field: `source_url`
   - Filepath / id field: `chunk_id`
   - Metadata fields: `version`, `valid_from`, `jurisdiction`, `source_type`, `doc_type`
7. Embedding model: `text-embedding-3-small` (deployment ya existente).
8. Save. Esperar status `Ready`.

## Paso 4 — Smoke automatizado

```bash
python scripts/aeco-kb/smoke_agenteub_kb.py
```

Pass = exit 0 + log `SMOKE PASS`. Validaciones:
- Substring `aeco-kb-es-vYYYYMMDD` presente en respuesta.
- ≥1 URL HTTP/HTTPS citada.

## Paso 5 — Audit + cierre

1. Crear `docs/audits/2026-05-08-o16-2-smoke-deploy.md` con:
   - Timestamp.
   - Index activo (`get_active_index`).
   - Doc count + cobertura por jurisdicción (`verify_kb.py` output).
   - Texto de respuesta del bot al prompt smoke.
   - Versión KB citada + URL.
2. notion-governance: marcar O16.2 cerrado en plan Q2-2026.
3. Friday retro 2026-06-26: incluir captura del smoke pass.

## Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| Smoke falla con `missing KB version tag` | AgenteUB no cita el campo `version` en respuestas | Editar instructions en portal Foundry: "cuando uses File Search, citá siempre `version` + `source_url` del chunk". |
| `403 Forbidden` en File Search | UAMI sin role `Search Index Data Reader` | Re-aplicar Paso 1. |
| Connection no aparece en File Search | Foundry portal no refrescó | Recargar página o cerrar/reabrir portal. |
| Bot responde "no tengo información" | Index vacío o alias apunta a index incorrecto | `verify_kb.py` para validar; `index_publisher.py` para republicar. |
