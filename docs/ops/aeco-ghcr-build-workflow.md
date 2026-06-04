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

## Notas

- Este workflow reemplaza el build local cuando no hay Docker/WSL/Podman.
- No usa `GHCR_PAT` local: GitHub Actions publica con `GITHUB_TOKEN` y
  `packages: write`.
- Si GHCR rechaza el push por permisos de package, el fix es de permisos de
  paquete/org en GitHub, no de codigo del pipeline.
