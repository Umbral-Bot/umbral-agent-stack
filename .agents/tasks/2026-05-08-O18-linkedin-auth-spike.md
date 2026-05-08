# Task O18 — Spike LinkedIn auth lifecycle (validar config/auth_lifecycle.example.yaml)

**Owner**: Copilot VPS
**Tipo**: spike de validación documental + gap report.
**Branch**: `copilot-vps/o18-linkedin-auth-spike`
**Base**: `main`.
**Plan ref**: O18 del plan Q2-2026.

## Contexto

`config/auth_lifecycle.example.yaml` declara block `linkedin:` con expectativas
de OAuth client + refresh token + scopes. Antes de implementar el LinkedIn
auto-poster (componente del Sistema Editorial Rick), validar que el bloque
LinkedIn coincide con la documentación oficial actual de Microsoft/LinkedIn.

## Doc fuente primaria

- https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens
- Doc complementaria: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow

## Tareas

### Task 1 — Fetch + parse de la doc oficial

Bajar contenido (curl o `mcp_microsoft-doc_microsoft_docs_fetch` desde tu
herramienta MCP) de los 2 URLs y extraer:
- Lifetime exacto de access_token (segundos).
- Lifetime exacto de refresh_token (días/segundos).
- Scopes requeridos para "publishing posts" (UGC API + posts API).
- Endpoints OAuth (authorize, token, refresh).
- Whether refresh_token rotates on use (yes/no).
- Whether app needs LinkedIn Marketing Developer Platform approval para
  scopes de publishing.

### Task 2 — Auditar bloque actual

Leer `config/auth_lifecycle.example.yaml` sección `linkedin:` y comparar
campo por campo con lo extraído en Task 1. Diff esperado en columnas:
| campo | doc oficial | yaml actual | gap |

### Task 3 — Auditar handlers existentes

`grep -r "linkedin" worker/ dispatcher/ identity/` para ver qué hay hoy.
Reportar:
- Handlers existentes (probablemente solo placeholder).
- Imports de SDK LinkedIn (probablemente 0).
- Refs a env vars `LINKEDIN_*`.
- Si existe doc previo en `docs/` sobre integración LinkedIn.

### Task 4 — Gap report

Path: `docs/spikes/O18-linkedin-auth-gap-report.md`.

Estructura:
- **Summary**: 1 párrafo, ¿el yaml actual sirve o necesita rework?
- **Doc oficial extracted facts** (Task 1).
- **YAML diff table** (Task 2).
- **Runtime state**: handlers + env vars + docs (Task 3).
- **Recommendations** ordenadas por prioridad:
  1. Cambios mínimos al yaml (campos faltantes, tipos incorrectos).
  2. Pre-requisitos antes de implementar el auto-poster (app approval,
     scopes, etc.).
  3. Estimación de esfuerzo para implementar handler `linkedin.post_share`
     (S/M/L).
- **Open questions**: lo que la doc no aclara y requiere prueba en sandbox.

## Reglas duras

- 0 implementación, solo doc + audit.
- 0 escrituras a `config/auth_lifecycle.example.yaml` (eso viene en task
  posterior si el gap lo justifica).
- 0 llamadas a LinkedIn API (no hay token todavía).
- Branch `copilot-vps/o18-linkedin-auth-spike` desde `main`.
- PR base = `main`.

## Aceptación

- PR abierto con el gap report.
- Tabla diff completa.
- Recomendaciones accionables.
- Owner (David) revisa y aprueba o pide ajustes; spike NO se cierra hasta
  que David confirma alineamiento con la realidad de su LinkedIn Developer
  app.
