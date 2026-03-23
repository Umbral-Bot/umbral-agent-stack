# GitLab Sandbox Mirror

## Objetivo

Usar GitLab como **mirror/sandbox opcional** del repo, sin mover el seguimiento principal fuera de:

- **GitHub** para código, PRs y Actions
- **Linear** para issues
- **Notion / OpenClaw** para operación

La idea es tener un segundo hogar para el código:

- backup operativo
- pruebas de flujo en GitLab
- sandbox para explorar CI/MR sin tocar el modelo principal

## Decisión operativa

**GitHub sigue siendo la fuente canónica.**

GitLab queda solo como:

- mirror del branch `main`
- espejo de tags
- sandbox opcional para revisar el repo desde otra plataforma

**No** usar GitLab como tracker principal mientras el proyecto ya dependa de:

- GitHub PRs
- Linear
- Notion
- `.agents/`

Eso evita abrir una cuarta fuente de verdad.

## Por qué este diseño

En este repo conviene **empujar desde GitHub hacia GitLab**, no al revés.

Razones:

- GitHub ya es el origen canónico del código.
- Queremos que GitLab Free sea espejo/sandbox, no el centro del flujo.
- El repo ya tiene CI y coordinación montadas alrededor de GitHub.

Por eso el repo incluye un workflow de GitHub Actions:

- [`.github/workflows/gitlab-mirror.yml`](../.github/workflows/gitlab-mirror.yml)

Ese workflow:

- corre en pushes a `main`
- replica tags
- hace un sync diario de respaldo
- también puede ejecutarse manualmente con `workflow_dispatch`

## Setup mínimo

### 1. Crear proyecto vacío en GitLab

Crear un proyecto privado, por ejemplo:

- `umbral-agent-stack-sandbox`

Recomendado:

- visibility: `Private`
- no importar desde GitHub
- no usarlo como issue tracker principal

### 2. Crear token de GitLab para push

Usar un **Personal Access Token** de GitLab con capacidad de escritura de repo.

El caso más simple para este mirror es un token con alcance:

- `write_repository`

Si luego quisieras automatizar más cosas desde GitLab, puedes ampliar scopes, pero para este mirror no hace falta.

### 3. Crear secret en GitHub

En el repo de GitHub, crear este secret de Actions:

- `GITLAB_MIRROR_PUSH_URL`

Formato:

```text
https://oauth2:<GITLAB_TOKEN>@gitlab.com/<namespace>/umbral-agent-stack-sandbox.git
```

Ejemplo:

```text
https://oauth2:glpat-xxxxxxxxxxxxxxxxxxxx@gitlab.com/umbral-bot/umbral-agent-stack-sandbox.git
```

## Activación

Con el secret creado, el workflow se activa solo:

- push a `main`
- push de tags
- corrida diaria
- corrida manual

Si el secret no existe, el workflow queda en **skip limpio** y no rompe CI.

## Verificación

### Opción 1. Manual desde GitHub Actions

Ejecutar:

- `GitLab Sandbox Mirror`

Luego comprobar en GitLab que aparezcan:

- branch `main`
- tags del repo

### Opción 2. Verificación local

Desde un clon local:

```bash
git fetch origin
git ls-remote https://gitlab.com/<namespace>/umbral-agent-stack-sandbox.git
```

## Gobernanza

Para que este diseño no genere caos:

- GitHub sigue siendo el origen canónico
- Linear sigue siendo el tracker real
- Notion/OpenClaw siguen siendo la capa operativa
- GitLab no se usa para abrir issues paralelas del mismo trabajo

Recomendación fuerte:

- no trabajar features directamente en GitLab
- no hacer merge requests en GitLab como flujo principal
- no convertir GitLab en una segunda bitácora operativa

## Recovery / re-sync

Si alguna vez necesitas forzar el espejo manualmente desde un clon local:

```bash
git fetch --force --prune origin
git remote add gitlab https://oauth2:<TOKEN>@gitlab.com/<namespace>/umbral-agent-stack-sandbox.git
git push --force gitlab refs/remotes/origin/main:refs/heads/main
git push --force --tags gitlab
```

## Límites y tradeoffs

- Esto no reemplaza GitHub Actions, Linear ni Notion.
- El mirror está pensado para `main` + tags, no para duplicar la coordinación multiagente.
- Si en el futuro quisieras usar GitLab como plataforma principal, eso ya sería una migración real y habría que rediseñar el flujo.

## Estado en este repo

Repo-side ya quedó listo:

- workflow de mirror creado
- documentación de setup añadida
- README enlazado

Lo único pendiente para activarlo de verdad es humano:

1. crear el proyecto en GitLab
2. generar el token
3. cargar `GITLAB_MIRROR_PUSH_URL` en GitHub Secrets
