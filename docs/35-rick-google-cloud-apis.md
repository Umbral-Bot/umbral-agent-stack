# 35 — APIs de Google Cloud para Rick (SIM / análisis de mercado)

Rick (VPS) puede usar APIs de Google Cloud para Gemini y servicios GCP del SIM. Las credenciales se guardan en `~/.config/openclaw/env` en la VPS; Rick las usa sin exponerlas.

## APIs habilitadas

| API | Uso |
|-----|-----|
| Cloud Natural Language API | Análisis de texto, entidades, sentimiento (posts, noticias). |
| Vertex AI API | Modelos Gemini desde GCP (resúmenes, clustering). |
| BigQuery API | Datos del SIM, agregaciones, consultas. |
| Cloud Storage API | Almacenar JSON, resúmenes, artefactos. |
| Gemini API (AI Studio) | Llamadas `generativelanguage` para modelos Gemini. |

## Variable de entorno (VPS)

- **GOOGLE_API_KEY** / **GOOGLE_API_KEY_NANO** — keys de Google AI Studio para Gemini.
- **GOOGLE_CLOUD_API_KEY** — key de Google Cloud para Language / BigQuery / Storage / Vertex cuando aplique.
- Opcional: **GOOGLE_CLOUD_PROJECT_RICK_UMBRAL** — ID del proyecto GCP (ej. `mi-proyecto-123`) si las llamadas lo requieren.

Path operativo confirmado:

- `research.web` y `scripts/web_discovery.py` usan **Gemini grounded search** como fallback real cuando Tavily queda sin cuota.
- Este path usa `gemini-2.5-flash` con `tools=[google_search]`.

## Custom Search (legado / experimental)

Google Custom Search **no es el backend operativo del stack**. En este repo no hay evidencia de uso exitoso sostenido y los diagnósticos repetidos muestran `403 This project does not have the access to Custom Search JSON API`.

Variables todavía soportadas para pruebas explícitas:

- **GOOGLE_CSE_API_KEY_RICK_UMBRAL** — key legada para Custom Search.
- **GOOGLE_CSE_CX** — engine ID del Programmable Search Engine.
- Opcional: **WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1** — habilita fallback legado a Google en `scripts/web_discovery.py`.

Ruta recomendada:

- `research.web` y `scripts/web_discovery.py` usan **Tavily** por defecto.
- Si Tavily falla por cuota o no esta configurado, caen a **Gemini grounded search** si `GOOGLE_API_KEY` / `GOOGLE_API_KEY_NANO` estan presentes.
- Custom Search solo debe intentarse con `--allow-google-legacy` o `WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1`.

## Límite de costo

- No superar **255 USD** en uso/créditos de GCP por periodo acordado. Rick debe priorizar uso dentro de ese techo.

## Seguridad

- Restringir cada key a las APIs que realmente usa y, si aplica, por IP de la VPS.
- Si una key se envió por chat/Telegram o quedó en Git, **rotar** cuando termine el setup: crear nueva key, actualizar en `~/.config/openclaw/env`, revocar la anterior.
- No commitear valores reales; `env.template` y este doc solo referencian nombres de variables.

## Proyecto dedicado para Custom Search (solo si insistes con el path legado)

Si quieres seguir intentando con Custom Search JSON API, se puede probar un proyecto dedicado:

- **Proyecto:** `rick-cse-umbral` (creado con gcloud: `gcloud projects create rick-cse-umbral`, API habilitada, facturación vinculada).
- **API key:** Crear en ese proyecto (`gcloud services api-keys create --display-name="Rick Custom Search Umbral" --project=rick-cse-umbral`) y poner el valor en `GOOGLE_CSE_API_KEY_RICK_UMBRAL` en `.env` (local) y en `~/.config/openclaw/env` (VPS).

**Nota:** El 403 "This project does not have the access to Custom Search JSON API" puede seguir apareciendo incluso con proyecto nuevo, API habilitada y facturación activa; es un problema conocido (API restringida/deprecada para proyectos nuevos). **Alternativa operativa:** Gemini grounded search como primario + Tavily como fallback secundario. Azure Bing no disponible para cuentas nuevas. Ver [docs/36-rick-embudo-capabilities.md](36-rick-embudo-capabilities.md).

## Referencias

- Creación y restricción de API key: Google Cloud Console → APIs y servicios → Credenciales.
- Doc seguridad general: [docs/10-security-notes.md](10-security-notes.md).
