# 35 — APIs de Google Cloud para Rick (SIM / análisis de mercado)

Rick (VPS) puede usar APIs de Google Cloud para el SIM, análisis de mercado y el proyecto embudo. Las credenciales se guardan en `~/.config/openclaw/env` en la VPS; Rick las usa sin exponerlas.

## APIs habilitadas

| API | Uso |
|-----|-----|
| Cloud Natural Language API | Análisis de texto, entidades, sentimiento (posts, noticias). |
| Vertex AI API | Modelos Gemini desde GCP (resúmenes, clustering). |
| BigQuery API | Datos del SIM, agregaciones, consultas. |
| Cloud Storage API | Almacenar JSON, resúmenes, artefactos. |
| Custom Search API (JSON) | Búsqueda web por keyword (Programmable Search). |

## Variable de entorno (VPS)

- **GOOGLE_CSE_API_KEY_RICK_UMBRAL** — API key restringida a las APIs anteriores. Rick la lee desde `~/.config/openclaw/env`.
- Opcional: **GOOGLE_CLOUD_PROJECT_ID** — ID del proyecto GCP (ej. `mi-proyecto-123`) si las llamadas lo requieren.

## Límite de costo

- No superar **255 USD** en uso/créditos de GCP por periodo acordado. Rick debe priorizar uso dentro de ese techo.

## Seguridad

- La key está restringida en GCP (solo las 5 APIs listadas). Opcional: restricción por IP de la VPS.
- Si la key se envió por chat/Telegram, **rotar** cuando termine el setup: en GCP Console crear nueva key, actualizar en `~/.config/openclaw/env`, revocar la anterior.
- No commitear valores reales; `env.template` y este doc solo referencian nombres de variables.

## Proyecto dedicado para Custom Search (opcional)

Si el proyecto principal da 403 con Custom Search JSON API, se puede usar un proyecto solo para esa API:

- **Proyecto:** `rick-cse-umbral` (creado con gcloud: `gcloud projects create rick-cse-umbral`, API habilitada, facturación vinculada).
- **API key:** Crear en ese proyecto (`gcloud services api-keys create --display-name="Rick Custom Search Umbral" --project=rick-cse-umbral`) y poner el valor en `GOOGLE_CSE_API_KEY_RICK_UMBRAL` en `.env` (local) y en `~/.config/openclaw/env` (VPS).

**Nota:** El 403 "This project does not have the access to Custom Search JSON API" puede seguir apareciendo incluso con proyecto nuevo, API habilitada y facturación activa; es un problema conocido (API restringida/deprecada para proyectos nuevos). **Alternativa configurada:** Tavily Search (`TAVILY_API_KEY` + `scripts/web_discovery.py`). Azure Bing no disponible para cuentas nuevas. Ver [docs/36-rick-embudo-capabilities.md](36-rick-embudo-capabilities.md).

## Referencias

- Creación y restricción de API key: Google Cloud Console → APIs y servicios → Credenciales.
- Doc seguridad general: [docs/10-security-notes.md](10-security-notes.md).
