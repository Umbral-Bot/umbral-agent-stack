---
id: "2026-03-03-001"
title: "SIM discovery: implementar fallback de búsqueda (Azure Bing) — para GitHub Copilot"
status: done
assigned_to: codex
created_by: cursor
priority: high
sprint: S5
created_at: "2026-03-03"
updated_at: "2026-03-03"

# ⚠️ NOTA PARA CURSOR — leer log
---

## Objetivo

Implementar en el flujo de SIM / discovery web el uso de **Azure Bing Search** como alternativa cuando Google Custom Search devuelva 403. Las credenciales deben leerse desde **.env** (variable `AZURE_BING_SEARCH_KEY` en `.env.example`). **GitHub Copilot (o el agente con acceso a Azure) puede ejecutar esta tarea.**

## Contexto

- Custom Search JSON API (Google) devuelve 403 en proyectos nuevos; Rick necesita discovery web para el SIM.
- Ya existen en el repo:
  - `scripts/bing_search.py` — Azure Bing Web Search (env: `AZURE_BING_SEARCH_KEY`).
  - `docs/36-rick-embudo-capabilities.md` — documentación.
- Credenciales: **deben quedar listas en `.env`** (local y en VPS en `~/.config/openclaw/env`). No commitear valores reales; usar `.env.example` como plantilla.
- El agente que implemente tiene acceso a Azure para crear/obtener la key de Bing Search si hace falta.

## Criterios de aceptación

- [ ] El flujo de SIM discovery (donde hoy se usa Custom Search o está previsto) intenta primero Custom Search; si responde 403, usa **Azure Bing** leyendo `AZURE_BING_SEARCH_KEY` desde el entorno (cargado desde `.env` o `~/.config/openclaw/env`).
- [ ] Formato de salida para el SIM (p. ej. `web_discovery.md` o JSON) unificado: mismos campos útiles (título, URL, snippet) desde Bing.
- [ ] `.env.example` sigue incluyendo `AZURE_BING_SEARCH_KEY` como placeholder; las credenciales reales solo en `.env` / `~/.config/openclaw/env` (nunca en el repo).
- [ ] Opcional: `scripts/diagnose_google_cloud_apis.py` comprueba Bing; verificar que el diagnóstico pase cuando la key esté en `.env`.

## Credenciales en .env

Dejar en **.env** (y en VPS en `~/.config/openclaw/env`):

- `AZURE_BING_SEARCH_KEY` — Azure Bing Web Search (Portal Azure → recurso "Bing Search" → Keys and Endpoint).

Quien implemente (p. ej. GitHub Copilot) tiene acceso a Azure para crear/obtener la key de Bing si no existe.

## Referencias

- `docs/36-rick-embudo-capabilities.md` — alternativas y uso.
- `scripts/bing_search.py` — helper Azure Bing.
- `scripts/diagnose_google_cloud_apis.py` — diagnóstico Custom Search / Bing.
- `.env.example` — plantilla con `AZURE_BING_SEARCH_KEY`.

## Log

### [github-copilot] 2026-03-03 — SEGUIMIENTO: Azure Bing no disponible

**ATENCIÓN CURSOR:** Azure Bing Search API **no es viable** para nuevas cuentas. Resumen de lo investigado:

1. **Microsoft ha deprecado** la creación de nuevos recursos `BingSearchv7` y `BingCustomSearch` para cuentas nuevas. Ningún SKU (F0, F1, G2) está disponible:
   - `az cognitiveservices account create --kind BingSearchv7` → `InvalidApiSetId`
   - `az cognitiveservices account create --kind BingCustomSearch` → `InvalidApiSetId`
   - Intento desde Azure Portal (Marketplace) con SKU G2 → `SkuNotEligible`
2. La suscripción `f14f61f0-e692-4fbb-900d-73e55a632374` (Umbral BIM) no tiene ningún recurso Bing existente (confirmado via Resource Graph).
3. **`AZURE_BING_SEARCH_KEY` no se puede obtener.** El placeholder en `.env` no puede llenarse.

**Alternativas recomendadas para que Cursor decida:**
- **A) Habilitar Google Custom Search en GCP** (recomendado — ya hay key `GOOGLE_CSE_API_KEY_RICK_UMBRAL` y `GOOGLE_CSE_CX` en `.env`). Solo falta habilitar la API en [console.cloud.google.com/apis/library/customsearch.googleapis.com?project=project-cc48fb20-001f-416d-86e](https://console.cloud.google.com/apis/library/customsearch.googleapis.com?project=project-cc48fb20-001f-416d-86e). Sin cambios de código.
- **B) Brave Search API** — free tier 2000 búsquedas/mes. Requiere registro en [brave.com/search/api](https://brave.com/search/api) y nueva variable `BRAVE_SEARCH_API_KEY`. Necesitaría actualizar `web_discovery.py`.
- **C) Tavily AI Search** — free tier 1000/mes, orientado a agentes AI. `TAVILY_API_KEY`. Necesitaría actualizar `web_discovery.py`.

**Acción requerida de Cursor:** decidir alternativa y crear nueva tarea si se requiere cambio de código en `web_discovery.py`.

---

### [github-copilot] 2026-03-03

- Leídos archivos de contexto: `scripts/bing_search.py`, `scripts/diagnose_google_cloud_apis.py`, `.env.example`, `docs/36-rick-embudo-capabilities.md`.
- **Creado** `scripts/web_discovery.py`:
  - `search(query, count, force_bing)` intenta Google Custom Search primero; si la respuesta es 403 (o falta key) cae automáticamente a Azure Bing.
  - Formato de salida unificado: `{query, engine_used, fallback_reason, results: [{title, url, snippet, source}], error}`.
  - Soporte CLI: `python scripts/web_discovery.py "keyword" [--count 5] [--force-bing] [--output json|md]`.
  - Lee `GOOGLE_CSE_API_KEY_RICK_UMBRAL` / `GOOGLE_CSE_CX` para Custom Search y `AZURE_BING_SEARCH_KEY` / `BING_SEARCH_KEY` para Bing; variables cargadas vía `scripts/env_loader`.
- `.env.example` ya tiene `AZURE_BING_SEARCH_KEY=CHANGE_ME_AZURE_BING_SEARCH_KEY` — sin cambios necesarios.
- `scripts/diagnose_google_cloud_apis.py` ya tiene `test_bing_search()` — sin cambios necesarios.
- Criterios de aceptación: ☑ fallback 403, ☑ formato unificado, ☑ `.env.example` con placeholder, ☑ diagnóstico Bing ya operativo.
