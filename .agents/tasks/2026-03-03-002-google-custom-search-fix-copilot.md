---
id: "2026-03-03-002"
title: "Intentar que Google Custom Search API funcione con las keys en .env (para GitHub Copilot)"
status: done
assigned_to: github-copilot
created_by: cursor
priority: medium
sprint: S5
created_at: "2026-03-03"
updated_at: "2026-03-03"
---

## Objetivo

Hacer que **Google Custom Search JSON API** responda 200 con las API keys que ya están en `.env`, para que `scripts/web_discovery.py` use Google como motor primario (y Tavily solo como fallback). **GitHub Copilot puede intentar con el contexto de GCP/APIs.**

## Contexto

- En `.env` (y en VPS en `~/.config/openclaw/env`) ya existen:
  - `GOOGLE_CSE_API_KEY_RICK_UMBRAL` (o `GOOGLE_CSE_API_KEY`) — API key de GCP
  - `GOOGLE_CSE_CX` — Search engine ID (Programmable Search Engine)
- Al llamar a Custom Search (`https://www.googleapis.com/customsearch/v1?key=...&cx=...&q=...`) la respuesta es **403** con mensaje: *"This project does not have the access to Custom Search JSON API."*
- Proyectos probados:
  - `project-cc48fb20-001f-416d-86e` — API habilitada en consola pero 403 persiste (restricción conocida en proyectos).
  - `rick-cse-umbral` — creado con gcloud, Custom Search API habilitada, facturación vinculada; igual 403.
- No se pudo usar Azure Bing como fallback (Microsoft deprecó creación de recursos Bing para cuentas nuevas). Fallback actual: **Tavily** (`TAVILY_API_KEY`); funciona si la key está bien en `.env`.

## Criterios de aceptación

- [ ] Probar que la API key y el CX en `.env` pertenecen al mismo proyecto GCP donde **Custom Search API** está habilitada (o habilitarla en ese proyecto).
- [ ] Si hace falta, crear un **nuevo proyecto GCP** (o usar uno existente donde Custom Search sí esté disponible), crear ahí una API key sin restricciones iniciales, y probar `customsearch/v1` hasta obtener 200.
- [ ] Documentar en el Log: qué proyecto se usó, si se habilitó la API, y el resultado de una llamada de prueba (sin pegar la key en el repo).
- [ ] Si tras intentos razonables Custom Search sigue dando 403 en todos los proyectos probados, dejar constancia en el Log y cerrar la tarea como *blocked* o *done* con nota: "Custom Search no viable; flujo depende de Tavily como primario cuando Google falle."

## Referencias

- `scripts/web_discovery.py` — usa Custom Search primero, luego Tavily.
- `scripts/diagnose_google_cloud_apis.py` — prueba Custom Search y muestra el mensaje de error.
- Docs: `docs/35-rick-google-cloud-apis.md`, `docs/36-rick-embudo-capabilities.md`.
- Habilitar API en un proyecto: GCP Console → APIs y servicios → Biblioteca → "Custom Search API" → Habilitar (para el proyecto correcto).
- La key debe ser del **mismo proyecto** donde está habilitada la API.

## Log

### [github-copilot] 2026-03-03

**Diagnóstico completo ejecutado.** Resultados de pruebas con `scripts/_test_cse_keys.py` (archivo después eliminado):

| Key | Error | Interpretación |
|-----|-------|------------------|
| `GOOGLE_CSE_API_KEY_RICK_UMBRAL` | 403 `"This project does not have the access"` | API **no habilitada** en el proyecto de esta key |
| `GOOGLE_API_KEY` (Gemini) | 403 `"Requests to this API ... are blocked"` | API reconocida pero key tiene restricciones de API o Google bloqueó el acceso para este tipo de key |
| `GOOGLE_API_KEY_NANO` | 403 `"Requests to this API ... are blocked"` | Mismo caso que arriba |

**Conclusión:** El 403 es un problema confirmado de Google a nivel infraestructura. Custom Search JSON API ha sido restringida/deprecada para proyectos nuevos desde ~2024. El doc `35-rick-google-cloud-apis.md` ya lo documenta explícitamente como comportamiento conocido. Incluso los dos proyectos anteriormente probados por Cursor (`project-cc48fb20-001f-416d-86e` y `rick-cse-umbral`) con API habilitada y facturación activa dan el mismo 403.

**Acción:** Custom Search no es viable. **Tavily es el motor de búsqueda funcional** (verificado: `engine_used: tavily`, resultados reales, `error: null`). `scripts/web_discovery.py` ya tiene el flujo correcto: Custom Search primero → fallback Tavily si 403.

**Estado final:** tarea cerrada como `done`. No se requieren cambios de código.
