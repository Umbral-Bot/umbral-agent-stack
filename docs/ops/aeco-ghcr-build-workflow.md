# AECO KB GHCR build workflow

Manual workflow para construir y publicar las 3 imagenes de Container Apps Jobs
del pipeline AECO KB cuando la workstation no tiene Docker local.

Workflow:

- `.github/workflows/aeco-ghcr-images.yml`
- permisos: `contents: read`, `packages: write`
- registry: `ghcr.io/umbral-bot`
- imagenes:
  - `aeco-source-crawler`
  - `aeco-pdf-parser`
  - `aeco-index-pipeline`

## Uso

Desde `main`:

```powershell
$sha = git rev-parse --short=8 HEAD
$tag = "core-first-$sha"
gh workflow run "AECO KB GHCR Images" --repo Umbral-Bot/umbral-agent-stack --ref main -f tag=$tag
gh run list --repo Umbral-Bot/umbral-agent-stack --workflow "AECO KB GHCR Images" --limit 1
```

Esperar el run:

```powershell
$run = gh run list --repo Umbral-Bot/umbral-agent-stack --workflow "AECO KB GHCR Images" --limit 1 --json databaseId --jq ".[0].databaseId"
gh run watch $run --repo Umbral-Bot/umbral-agent-stack --exit-status
gh run view $run --repo Umbral-Bot/umbral-agent-stack --json conclusion,url,headSha,displayTitle
```

## Acceptance

- El run termina `success`.
- El summary del run lista el tag y los digests de las 3 imagenes.
- El tag inmutable tiene formato `core-first-<shortsha>`.
- `latest` se actualiza junto con el tag inmutable.
- El siguiente paso usa ese tag en ACA Jobs antes de correr D6.1e.

## GHCR auth

El workflow requiere una de estas dos condiciones:

1. Repo secret `GHCR_PAT` con un classic PAT que tenga `read:packages` y
   `write:packages` sobre los packages de `Umbral-Bot`.
2. Los package settings de GHCR conceden write access a
   `Umbral-Bot/umbral-agent-stack`, y el run se dispara con
   `allow_github_token=true`.

Sin una de esas condiciones, el workflow falla antes de construir imagenes para
evitar gastar tiempo en builds que terminan en `403 Forbidden`.

### Prompt GHCR auth fix

```text
Sos David/GitHub admin. Desbloquear push GHCR para AECO KB images.

Contexto:
- Repo: Umbral-Bot/umbral-agent-stack
- Workflow: AECO KB GHCR Images
- Tracking issue: https://github.com/Umbral-Bot/umbral-agent-stack/issues/452
- Run fallido: https://github.com/Umbral-Bot/umbral-agent-stack/actions/runs/26923231791
- Error real: GHCR 403 al pushear ghcr.io/umbral-bot/aeco-source-crawler:core-first-24e070d7
- Tokens disponibles en Codex no tienen read:packages; repo secret GHCR_PAT no existe.

Opcion A recomendada:
1. Crear classic PAT con scopes `read:packages` y `write:packages`.
2. Guardarlo como repo secret `GHCR_PAT` en Umbral-Bot/umbral-agent-stack.
3. Avisar para rerun del workflow con tag `core-first-24e070d7`.

Opcion B:
1. En GitHub Packages, abrir cada package:
   - aeco-source-crawler
   - aeco-pdf-parser
   - aeco-index-pipeline
2. Package settings -> Manage Actions access.
3. Dar write access a `Umbral-Bot/umbral-agent-stack`.
4. Rerun con `allow_github_token=true`.

No imprimir PAT en chats ni logs.
```

## Notas

- Este workflow reemplaza el build local cuando no hay Docker/WSL/Podman.
- No usa `GHCR_PAT` local: GitHub Actions publica con `GITHUB_TOKEN` y
  `packages: write` solo si el package concede acceso al repo; si no, usa
  repo secret `GHCR_PAT`.
- Si GHCR rechaza el push por permisos de package, el fix es de permisos de
  paquete/org en GitHub, no de codigo del pipeline.
