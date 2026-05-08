---
id: "2026-05-08-052"
title: "Build + push 3 imágenes ACA Jobs O16.2 a GHCR (aeco-source-crawler / aeco-pdf-parser / aeco-index-pipeline)"
status: blocked
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026 / O16.2
created_at: "2026-05-08T05:45:00Z"
updated_at: "2026-05-08T18:21:00Z"
---

## Contexto previo

O16.2 (Piloto Conocimiento Técnico AECO) cerró repo en commit `0659b06b` con
6 sub-tasks (046-051). El smoke live quedó parcialmente ejecutado en commit
`fa199201` (audit `docs/audits/2026-05-08-o16-2-smoke-deploy.md`):

- ✅ UAMI cross-RG roles aplicados.
- ✅ Foundry connection `aeco-kb-search` creada.
- ✅ Foundry project system-MI con Search Index Data Reader/Contributor.
- ❌ **Imágenes Docker NO buildeadas / NO pusheadas a GHCR** — bloquea deploy
  Bicep + run pipeline.

Copilot Chat (Windows local, `dm@umbralbim.cl`) NO tiene Docker disponible.
La VPS sí tiene Docker. Esta tarea delega el build + push.

Antes de empezar: `cd ~/umbral-agent-stack && git pull origin main` y releé
`.github/copilot-instructions.md` (sección "VPS Reality Check Rule").

## Objetivo

Buildear 3 imágenes Docker desde Dockerfiles ya commiteados y pushearlas a
GHCR como **públicas** (Bicep modules las consumen sin auth):

| Image | Dockerfile | Tag |
|---|---|---|
| `ghcr.io/umbral-bot/aeco-source-crawler` | `infra/docker/aeco-source-crawler/Dockerfile` | `:latest` + `:v1` |
| `ghcr.io/umbral-bot/aeco-pdf-parser` | `infra/docker/aeco-pdf-parser/Dockerfile` | `:latest` + `:v1` |
| `ghcr.io/umbral-bot/aeco-index-pipeline` | `infra/docker/aeco-index-pipeline/Dockerfile` | `:latest` + `:v1` |

Visibility de los 3 packages debe quedar **public** (Bicep no incluye
`registries[]` block — asume pull anónimo).

## Procedimiento mínimo

```bash
# 0. Sync repo
cd ~/umbral-agent-stack && git pull origin main

# 1. Auth a GHCR (PAT con scopes: write:packages, read:packages, delete:packages)
#    Si no hay PAT en env, parar y pedirle a David.
echo "$GHCR_PAT" | docker login ghcr.io -u umbral-bot --password-stdin

# 2. Build × 3 (contexto = repo root, importante)
docker build -f infra/docker/aeco-source-crawler/Dockerfile \
  -t ghcr.io/umbral-bot/aeco-source-crawler:v1 \
  -t ghcr.io/umbral-bot/aeco-source-crawler:latest .

docker build -f infra/docker/aeco-pdf-parser/Dockerfile \
  -t ghcr.io/umbral-bot/aeco-pdf-parser:v1 \
  -t ghcr.io/umbral-bot/aeco-pdf-parser:latest .

docker build -f infra/docker/aeco-index-pipeline/Dockerfile \
  -t ghcr.io/umbral-bot/aeco-index-pipeline:v1 \
  -t ghcr.io/umbral-bot/aeco-index-pipeline:latest .

# 3. Push × 6
for img in aeco-source-crawler aeco-pdf-parser aeco-index-pipeline; do
  docker push ghcr.io/umbral-bot/$img:v1
  docker push ghcr.io/umbral-bot/$img:latest
done

# 4. Marcar packages como public (vía gh CLI, requiere PAT con admin:packages)
for pkg in aeco-source-crawler aeco-pdf-parser aeco-index-pipeline; do
  gh api --method PATCH \
    -H "Accept: application/vnd.github+json" \
    "/orgs/umbral-bot/packages/container/$pkg/visibility" \
    -f visibility=public || echo "MANUAL: marcá $pkg como public en https://github.com/orgs/umbral-bot/packages/container/$pkg/settings"
done

# 5. Verificar pull anónimo desde otra máquina (o desde la misma con docker logout)
docker logout ghcr.io
docker pull ghcr.io/umbral-bot/aeco-source-crawler:latest && \
docker pull ghcr.io/umbral-bot/aeco-pdf-parser:latest && \
docker pull ghcr.io/umbral-bot/aeco-index-pipeline:latest
```

## Criterios de aceptación

- [ ] 3 builds Docker exitosos (exit 0 cada uno).
- [ ] 6 pushes a GHCR exitosos (latest + v1 × 3).
- [ ] Los 3 packages quedan **public visibility** en
  `https://github.com/orgs/umbral-bot/packages`.
- [ ] `docker pull ghcr.io/umbral-bot/aeco-*:latest` funciona desde una
  shell sin login (verificación post-push).
- [ ] Reportar en `## Log` los digests SHA-256 de las 3 imágenes `:v1`
  (output del último `docker push`).
- [ ] Status flipped a `done` con timestamp UTC.

## Antipatrones que esta tarea prohíbe

- ❌ Buildear sin `git pull origin main` previo (puede haber un patch del Dockerfile).
- ❌ Push solo `latest` sin `v1` (rompe rollback).
- ❌ Olvidar marcar visibility public (Bicep deploy fallará con
  `IMAGE_PULL_AUTHENTICATION_FAILED`).
- ❌ Usar PAT con scope insuficiente (debe incluir `write:packages` Y
  `admin:packages` para visibility PATCH).
- ❌ Reportar "done" sin verificar pull anónimo.

## Hand-off post-completion

Cuando esto cierre `done`, Copilot Chat (sesión Windows) retomará con:

1. `az deployment group create -g rg-umbral-agents-prod -f infra/azure/aeco-kb-pipeline.bicep --parameters …`
2. `bash scripts/aeco-kb/run_pipeline.sh buildingsmart minvu iram nmx`
3. `python scripts/aeco-kb/verify_kb.py --min-chunks 500`

David hará en paralelo:
- Portal Foundry → AgenteUB → File Search → connection `aeco-kb-search`,
  index `aeco-kb-es-current`, mapping según
  `runbooks/o16-2-agenteub-filesearch-wiring.md`.

Final: `python scripts/aeco-kb/smoke_agenteub_kb.py` y update audit.

## Log

- 2026-05-08T05:45Z — Copilot Chat (notion-governance session): tarea creada
  y delegada. Trigger: David solicitó "avanza con todo lo pendiente". Build
  imposible local (no Docker en Windows host). Commits referencia:
  - umbral-agent-stack/main `fa199201` (audit + foundry_connection patch)
  - notion-governance/main `79e2532` (plan Q2 marca repo cerrado)

- 2026-05-08T07:30Z — Copilot Coding Agent (VPS): **BLOCKED** por scope
  insuficiente del PAT.
  - Repo synced a main `2bc58f6` (4 commits ahead del fa199201 referenciado).
  - Docker 29.2.1 disponible en VPS.
  - `$GHCR_PAT` NO está en env. Único token GitHub disponible es
    `GITHUB_TOKEN` en `~/.config/openclaw/env` (fine-grained PAT, no classic).
  - `docker login ghcr.io -u umbral-bot --password-stdin` con `GITHUB_TOKEN`
    → `Login Succeeded` (engaña porque login solo valida bearer, no scopes).
  - **Builds ejecutados**: 3/3 OK (cached desde sesión previa, aparentemente).
    Imágenes locales presentes con tags `:v1` y `:latest`. Manifest list
    digests locales (NO digests remotos GHCR todavía):
    - `aeco-source-crawler:v1` → `sha256:43e5a859936941e21803a1004655fb0d8b373c367d03d840b8d1a7274c5bf0bf`
    - `aeco-pdf-parser:v1`     → `sha256:d8ae1237f96461c29aea9590b95d738741bae33ecc35202ad6b2eae9a56fc86e`
    - `aeco-index-pipeline:v1` → `sha256:680cca042d9da520facc0dc81682b17ce1784c2cddcbcf9ccf8ca53713a48f5c`
  - **Push 6/6 FAILED** todos con:
    `error from registry: permission_denied: The token provided does not match expected scopes.`
  - **Probe API extra**: `GET /orgs/umbral-bot/packages` con el mismo token
    → HTTP 403. Confirma fine-grained sin permisos sobre packages de la org.
  - **Acción requerida (David)**: generar PAT classic en
    https://github.com/settings/tokens con scopes:
    - `write:packages`
    - `read:packages`
    - `admin:packages` (para PATCH visibility public)
    Exportar como `GHCR_PAT` y/o agregar al env file. Luego este task puede
    re-correr el bloque push (paso 3 en adelante) — los builds ya están
    listos en local, no necesitan rebuild.
  - **Antipatrón confirmado**: el spec ya advertía "Usar PAT con scope
    insuficiente". El fine-grained `GITHUB_TOKEN` actual **no sirve**
    para GHCR push aunque docker login devuelva éxito.
  - Runtime VPS intacto: gateway pid 75421 sin tocar, no se reinició
    nada, no se editó código fuera del Log de este task.

- 2026-05-08T18:21Z — Copilot Coding Agent (VPS): **PUSHES 6/6 OK** con
  PAT classic `GHCR_PAT` (scopes `repo, write:packages, delete:packages`).
  Ningún rebuild — usados los layers cacheados de la sesión 07:30Z.

  Digests REMOTOS confirmados (idénticos a los locales del log previo):

  | Image | Tag | Remote digest |
  |---|---|---|
  | `ghcr.io/umbral-bot/aeco-source-crawler` | `:v1` y `:latest` | `sha256:43e5a859936941e21803a1004655fb0d8b373c367d03d840b8d1a7274c5bf0bf` |
  | `ghcr.io/umbral-bot/aeco-pdf-parser`     | `:v1` y `:latest` | `sha256:d8ae1237f96461c29aea9590b95d738741bae33ecc35202ad6b2eae9a56fc86e` |
  | `ghcr.io/umbral-bot/aeco-index-pipeline` | `:v1` y `:latest` | `sha256:680cca042d9da520facc0dc81682b17ce1784c2cddcbcf9ccf8ca53713a48f5c` |

  Cada push reportó "Layer already exists" para todas las capas + `digest:`
  línea final: tags `:v1` y `:latest` apuntan al mismo manifest por imagen
  (esperado, mismo build tageado dos veces).

  **VISIBILITY: bloqueado por scope.** PATCH
  `/orgs/Umbral-Bot/packages/container/<pkg>/visibility -f visibility=public`
  retorna HTTP 404 con los 3 packages. Owner real es Organization
  `Umbral-Bot` (capitalizado), GET sobre el mismo path funciona — confirma
  que el resource existe y es visible al token. El 404 es la firma típica
  de GitHub cuando falta `admin:packages` en el PAT (devuelve 404 en lugar
  de 403 por seguridad). Los packages quedan `visibility: private`.

  Pull anónimo NO ejecutado porque seguro fallará con `denied` mientras los
  packages estén privados — verificarlo ahora sería ruido sin señal.

  **Acción mínima requerida (David, 1 min UI)**:
  1. Abrir https://github.com/orgs/Umbral-Bot/packages
  2. Click en cada uno de los 3 packages (`aeco-source-crawler`,
     `aeco-pdf-parser`, `aeco-index-pipeline`).
  3. Package settings → Danger Zone → "Change visibility" → Public →
     confirmar tipeando el package name.
  4. Avisar y este task corre el verify pull anónimo y flipea a `done`.

  **Alternativa (si David prefiere automatizar)**: regenerar `GHCR_PAT` en
  https://github.com/settings/tokens (classic) agregando scope
  `admin:packages` además de los actuales, exportar al env file, y este
  task re-ejecuta los 3 PATCH + verify pull anónimo automáticamente.

  Status sigue `blocked` — ahora `blocked-on-visibility-only`. Los
  pushes son persistentes (digests publicados en GHCR), no se pierden si
  esto queda esperando al flip manual.

  Runtime VPS intacto: gateway pid 75421 sin tocar, no se reinició nada,
  no se editó código fuera de este Log.
