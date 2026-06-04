# Core-first next prompts (2026-06-03)

Prompt pack para continuar el plan core-first sin depender de memoria del hilo.

Estado de base:

- PR activo: https://github.com/Umbral-Bot/umbral-agent-stack/pull/449
- Branch: `codex/core-first-stabilization`
- No mergear ni cerrar PRs stale sin autorizacion explicita de David.
- No publicar LinkedIn sin HITL estricto.

## Donde estan los prompts

Usar este archivo como fuente activa:

- `docs/ops/core-first-next-prompts-2026-06-03.md` (este pack).

Archivos de apoyo:

- `docs/ops/copilot-handoff-prompts.md`: historico. La seccion D6.1d quedo superada por este pack porque no contempla rebuild/push de imagenes tras PR #449.
- `scripts/aeco-kb/README.md`: runbook tecnico actualizado para crawler/parser/publisher/verify.
- `mission_control/README.md`: endpoints y deploy read-only.
- `infra/systemd/mission-control.service.template`: unit systemd user para VPS.

## Orden minimo

1. David/Cursor revisa y mergea PR #449 si lo aprueba.
2. Builder con Docker reconstruye y pushea las 3 imagenes AECO KB desde `main`.
3. Copilot Windows/Azure-auth actualiza ACA Jobs al tag nuevo y ejecuta D6.1e.
4. Copilot-VPS despliega Mission Control read-only.
5. Tracker cleanup: inventariar stale PRs; cerrar solo con autorizacion.
6. D3.5 tournament rerun solo si David autoriza costo/tiempo.
7. Cursor/editorial Wave 2 con LinkedIn HITL estricto.

---

## PROMPT 0 - David/Cursor: revisar y mergear PR #449

Pegar en Cursor o usar manualmente como checklist:

```text
Sos Cursor lead. Revisar PR #449 sin merge automatico.

PR: https://github.com/Umbral-Bot/umbral-agent-stack/pull/449

Objetivo:
- Confirmar que el PR implementa core-first stabilization:
  - hermeticidad tests/e2e env load
  - OAuth LinkedIn portable Windows/POSIX
  - dependency floor updates
  - D6.1e AECO KB source repair
  - Mission Control read-only gates/risks/tournaments
  - tournament PR_URL protocol
  - prompts de continuidad core-first

Checks antes de merge:
- CI verde o equivalente local documentado.
- No hay `.env` ni secretos versionados.
- No hay launcher de torneos en Mission Control v1.
- No hay autopublicacion LinkedIn.
- `docs/ops/core-first-next-prompts-2026-06-03.md` existe y marca D6.1d historico como superado.

Si apruebo merge:
- Mergear PR #449 a `main`.
- No cerrar PRs #442/#443.
- Responder con commit merge y confirmar que D6.1e puede pasar a Builder GHCR.

Si no apruebo:
- Dejar comentario con bloqueadores concretos.
```

Acceptance:

- `main` contiene los cambios de PR #449, o hay blockers concretos.
- Si se mergea, el siguiente prompt es `PROMPT 1`.

---

## PROMPT 1 - Builder GHCR: rebuild/push imagenes AECO KB

Usar en una superficie con Docker y GHCR PAT. La VPS sirve si tiene Docker y `GHCR_PAT`.
No requiere Azure CLI.

Si la workstation no tiene Docker/WSL/Podman o falta `GHCR_PAT`, usar el
fallback CI documentado en `docs/ops/aeco-ghcr-build-workflow.md`:

```powershell
cd C:\GitHub\umbral-agent-stack
git checkout main
git pull --ff-only origin main
$sha = git rev-parse --short=8 HEAD
$tag = "core-first-$sha"
gh workflow run "AECO KB GHCR Images" --repo Umbral-Bot/umbral-agent-stack --ref main -f tag=$tag
$run = gh run list --repo Umbral-Bot/umbral-agent-stack --workflow "AECO KB GHCR Images" --limit 1 --json databaseId --jq ".[0].databaseId"
gh run watch $run --repo Umbral-Bot/umbral-agent-stack --exit-status
gh run view $run --repo Umbral-Bot/umbral-agent-stack --json conclusion,url,headSha,displayTitle
```

Acceptance del fallback:

- Workflow `AECO KB GHCR Images` termina `success`.
- El summary lista digest para source crawler, pdf parser e index pipeline.
- El tag reportado se pasa a `PROMPT 2`.

```text
Sos Copilot Builder. Rebuild/push de imagenes AECO KB post PR #449.
Responder en espanol. NO imprimir secretos. NO tocar Azure. NO reiniciar gateway/worker.

Contexto:
- PR #449 ya debe estar mergeado en `main`.
- D6.1e no puede correr con imagenes viejas porque los cambios de seeds/crawler/parser/publisher viven dentro de las imagenes.
- Necesitamos 3 imagenes nuevas con tag inmutable `core-first-<shortsha>`.

Preflight:
cd ~/umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git status --short --branch
git log -1 --oneline

# STOP si dirty o si main no contiene el pack:
test -f docs/ops/core-first-next-prompts-2026-06-03.md || { echo "MISSING_PROMPT_PACK"; exit 2; }
grep -q "preflight-only" scripts/aeco-kb/source_crawler.py || { echo "MISSING_D61E_SOURCE_REPAIR"; exit 2; }

# Docker/GHCR:
docker version
test -n "$GHCR_PAT" || { echo "BLOCKED: GHCR_PAT missing"; exit 2; }
echo "$GHCR_PAT" | docker login ghcr.io -u umbral-bot --password-stdin >/dev/null

SHA=$(git rev-parse --short HEAD)
TAG="core-first-$SHA"
echo "tag=$TAG"

docker build -f infra/docker/aeco-source-crawler/Dockerfile \
  -t ghcr.io/umbral-bot/aeco-source-crawler:$TAG \
  -t ghcr.io/umbral-bot/aeco-source-crawler:latest .

docker build -f infra/docker/aeco-pdf-parser/Dockerfile \
  -t ghcr.io/umbral-bot/aeco-pdf-parser:$TAG \
  -t ghcr.io/umbral-bot/aeco-pdf-parser:latest .

docker build -f infra/docker/aeco-index-pipeline/Dockerfile \
  -t ghcr.io/umbral-bot/aeco-index-pipeline:$TAG \
  -t ghcr.io/umbral-bot/aeco-index-pipeline:latest .

for img in aeco-source-crawler aeco-pdf-parser aeco-index-pipeline; do
  docker push ghcr.io/umbral-bot/$img:$TAG
  docker push ghcr.io/umbral-bot/$img:latest
  docker image inspect ghcr.io/umbral-bot/$img:$TAG --format '{{json .RepoDigests}}'
done

docker logout ghcr.io >/dev/null || true

Final obligatorio:
- VEREDICTO: D61E_IMAGES_PUSHED_OK o D61E_IMAGES_PUSH_BLOCKED
- tag usado: core-first-<shortsha>
- digest/RepoDigest de cada imagen si hubo push OK
- confirmar que no se toco Azure ni runtime
```

Acceptance:

- 3 imagenes publicadas con el mismo tag `core-first-<shortsha>`.
- El runner Windows/Azure recibe el tag exacto.

---

## PROMPT 2 - Copilot Windows/Azure-auth: D6.1e update jobs + run + verify

Usar solo despues de `PROMPT 1`. Reemplazar `<TAG_DE_PROMPT_1>`.

```text
Sos Copilot Windows con Azure auth. Ejecutar D6.1e source repair/run/verify para AECO KB.
Responder en espanol. NO imprimir secretos. NO ocultar 400/errores Azure Search.

Tag de imagenes GHCR validado por Builder: `<TAG_DE_PROMPT_1>`

Objetivo:
- Actualizar ACA jobs a las imagenes post PR #449.
- Ejecutar buildingSMART end-to-end:
  crawler -> parser -> publisher -> verify.
- Acceptance: raw/parsed no vacio, index `aeco-kb-es-vYYYYMMDD`, alias `aeco-kb-es-current`, min 150 chunks, jurisdiccion `intl`.

Preflight repo:
cd C:\GitHub\umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git status --short --branch
git log -1 --oneline

# STOP si main no contiene PR #449:
if (-not (Test-Path docs\ops\core-first-next-prompts-2026-06-03.md)) { throw "MISSING_PROMPT_PACK" }
if (-not (Select-String -Path scripts\aeco-kb\source_crawler.py -Pattern "preflight-only" -Quiet)) { throw "MISSING_PREFLIGHT_ONLY" }
if (-not (Select-String -Path scripts\aeco-kb\pdf_parser.py -Pattern "aeco/raw/{source_type}" -Quiet)) { throw "MISSING_RAW_ENUMERATION" }
if (-not (Select-String -Path scripts\aeco-kb\verify_kb.py -Pattern "aliases" -Quiet)) { throw "MISSING_ALIAS_FALLBACK" }

python -m pip install -e ".[aeco-kb]"
python scripts/aeco-kb/source_crawler.py --source-type buildingsmart --preflight-only
# STOP si no son 4/4 OK o si aparece 404.

Azure preflight:
$rg = "rg-umbral-agents-prod"
az account show --query "{tenant:tenantId,subscription:id,user:user.name}" -o json
az containerapp job list -g $rg --query "[?starts_with(name, 'aeco-')].{name:name,state:properties.provisioningState,image:properties.template.containers[0].image}" -o table

# Confirmar que az soporta --image para job update; si no, STOP y reportar.
if (-not (az containerapp job update -h | Select-String -SimpleMatch "--image")) { throw "AZ_CLI_JOB_UPDATE_IMAGE_UNSUPPORTED" }

Update imagenes:
$tag = "<TAG_DE_PROMPT_1>"
$images = @{
  "aeco-source-crawler" = "ghcr.io/umbral-bot/aeco-source-crawler:$tag"
  "aeco-pdf-parser" = "ghcr.io/umbral-bot/aeco-pdf-parser:$tag"
  "aeco-index-pipeline" = "ghcr.io/umbral-bot/aeco-index-pipeline:$tag"
}

foreach ($job in $images.Keys) {
  $image = $images[$job]
  az containerapp job show --name $job --resource-group $rg --query name -o tsv
  if ($LASTEXITCODE -ne 0) { throw "BLOCKED: missing ACA job $job" }
  az containerapp job update --name $job --resource-group $rg --image $image
  if ($LASTEXITCODE -ne 0) { throw "BLOCKED: image update failed for $job" }
}

az containerapp job list -g $rg --query "[?starts_with(name, 'aeco-')].{name:name,image:properties.template.containers[0].image}" -o table
# STOP si cualquiera de los 3 jobs no apunta a $tag.

Helper run/wait:
function Start-AcaJobAndWait {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string[]]$JobArgs
  )
  Write-Host "START $Name $($JobArgs -join ' ')"
  $execName = az containerapp job start --name $Name --resource-group $rg --args @JobArgs --query name -o tsv
  if ($LASTEXITCODE -ne 0 -or -not $execName) { throw "start failed: $Name" }
  for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep -Seconds 20
    $status = az containerapp job execution show --name $Name --resource-group $rg --job-execution-name $execName --query properties.status -o tsv 2>$null
    Write-Host "$Name/$execName status=$status"
    if ($status -in @("Succeeded","Failed","Canceled")) {
      if ($status -ne "Succeeded") { throw "$Name execution $execName ended $status" }
      return $execName
    }
  }
  throw "$Name execution timed out: $execName"
}

Run pipeline buildingSMART:
$execs = @()
$execs += Start-AcaJobAndWait -Name "aeco-source-crawler" -JobArgs @("--source-type","buildingsmart","--max-docs","4")
$execs += Start-AcaJobAndWait -Name "aeco-pdf-parser" -JobArgs @("--source-type","buildingsmart")
$execs += Start-AcaJobAndWait -Name "aeco-index-pipeline" -JobArgs @("publish","--source-types","buildingsmart")
$execs | ConvertTo-Json

Verify:
python scripts/aeco-kb/verify_kb.py --min-chunks 150 --jurisdictions intl

Evidence:
az search alias show --service-name srch-umbral-kb-prod --resource-group $rg --alias-name aeco-kb-es-current -o json
az search index list --service-name srch-umbral-kb-prod --resource-group $rg --query "[?starts_with(name, 'aeco-kb-es-v')].name" -o table

Final obligatorio:
- VEREDICTO: D61_AECO_KB_RUN_VERIFY_OK o D61_AECO_KB_RUN_VERIFY_BLOCKED
- tag de imagen usado
- executions ACA
- doc/chunk count de verify
- alias target
- si falla: primer error real, no resumen ambiguo
```

Acceptance:

- Preflight seeds buildingSMART pasa sin 404.
- Los 3 ACA jobs ejecutan con tag nuevo.
- `verify_kb.py --min-chunks 150 --jurisdictions intl` pasa.

---

## PROMPT 3 - Copilot-VPS: Mission Control read-only deploy

Usar despues de merge de PR #449. No depende de D6.1e.

```text
Sos Copilot-VPS. Desplegar Mission Control v1 read-only en VPS puerto 8089.
Responder en espanol. NO imprimir tokens. NO reiniciar gateway salvo que sea estrictamente necesario y autorizado. NO ejecutar torneos. NO agregar boton run tournament.

Preflight repo:
cd ~/umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git status --short --branch
git log -1 --oneline
test -f mission_control/README.md || { echo "MISSING_MISSION_CONTROL"; exit 2; }
test -f infra/systemd/mission-control.service.template || { echo "MISSING_SERVICE_TEMPLATE"; exit 2; }
grep -q "/gates" mission_control/README.md || { echo "MISSING_GATES_DOC"; exit 2; }
grep -q "/risks" mission_control/README.md || { echo "MISSING_RISKS_DOC"; exit 2; }

Install/check:
source .venv/bin/activate
python -m pip install -e .
python -m pytest tests/mission_control -q

Env/token:
mkdir -p ~/.config/openclaw
touch ~/.config/openclaw/env
chmod 600 ~/.config/openclaw/env
if ! grep -q '^MISSION_CONTROL_TOKEN=' ~/.config/openclaw/env; then
  TOKEN=$(openssl rand -hex 32)
  printf '\nMISSION_CONTROL_TOKEN=%s\n' "$TOKEN" >> ~/.config/openclaw/env
  unset TOKEN
fi
grep -q '^REDIS_URL=' ~/.config/openclaw/env || printf '\nREDIS_URL=redis://localhost:6379/0\n' >> ~/.config/openclaw/env
# NO cat del env file.

Systemd:
mkdir -p ~/.config/systemd/user
cp infra/systemd/mission-control.service.template ~/.config/systemd/user/mission-control.service
systemctl --user daemon-reload
systemctl --user enable --now mission-control
sleep 3
systemctl --user is-active mission-control
journalctl --user -u mission-control -n 80 --no-pager

Health:
curl -fsS http://127.0.0.1:8089/health
curl -fsS http://127.0.0.1:8088/health
curl -fsS http://127.0.0.1:18789/health
systemctl --user is-active openclaw-gateway openclaw-dispatcher umbral-worker

Bearer smoke without printing token:
set -a
. ~/.config/openclaw/env
set +a
curl -fsS -H "Authorization: Bearer $MISSION_CONTROL_TOKEN" http://127.0.0.1:8089/gates >/tmp/mc-gates.json
curl -fsS -H "Authorization: Bearer $MISSION_CONTROL_TOKEN" http://127.0.0.1:8089/risks >/tmp/mc-risks.json
python3 - <<'PY'
import json
for p in ["/tmp/mc-gates.json", "/tmp/mc-risks.json"]:
    data = json.load(open(p))
    print(p, type(data).__name__, "ok")
PY

Final obligatorio:
- VEREDICTO: MISSION_CONTROL_READONLY_DEPLOY_OK o MISSION_CONTROL_READONLY_BLOCKED
- HEAD short
- systemctl active states
- health :18789/:8088/:8089
- confirmar: sin launcher de torneos, sin token impreso
```

Acceptance:

- `mission-control` activo en systemd user.
- `/health`, `/gates`, `/risks` responden.
- Gateway/dispatcher/worker siguen activos.

---

## PROMPT 4 - Tracker cleanup read-only: stale PRs y board drift

No cerrar nada salvo que David escriba explicitamente `autorizo cerrar PR #442 y #443`.

```text
Sos Codex/Copilot tracker. Hacer inventario read-only de deuda operativa post core-first.
Responder en espanol. NO cerrar PRs. NO merge. NO editar main.

Repo:
cd C:\GitHub\umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git log -1 --oneline

Inventario GitHub:
gh pr view 442 --repo Umbral-Bot/umbral-agent-stack --json number,title,state,url,headRefName,baseRefName,mergeable,updatedAt
gh pr view 443 --repo Umbral-Bot/umbral-agent-stack --json number,title,state,url,headRefName,baseRefName,mergeable,updatedAt
gh pr list --repo Umbral-Bot/umbral-agent-stack --state open --json number,title,url,headRefName,baseRefName,updatedAt

Inventario repo:
Select-String -Path .agents\board.md -Pattern "D6.1d|D6.1e|442|443|stale|Mission Control|LinkedIn|HITL"
Select-String -Path docs\ops\*.md -Pattern "D6.1d|D6.1e|442|443|stale"

Salida:
- Tabla PR | estado | razon para cerrar/mantener | accion recomendada.
- Lista de docs/board lines que apuntan a prompts obsoletos.
- Propuesta de patch docs-only si hace falta.

Final:
- VEREDICTO: TRACKER_CLEANUP_INVENTORY_READY
- Si David autoriza luego, preparar prompt separado para cerrar PRs stale.
```

Acceptance:

- Inventario claro.
- Cero cambios destructivos.

---

## PROMPT 5 - D3.5 clean tournament rerun opcional

Usar solo si David autoriza costo/tiempo:

```text
autorizo D3.5 clean tournament rerun

Sos Copilot-VPS. Ejecutar D3.5 como torneo limpio desde main standalone.
Responder en espanol. NO nested rick-orchestrator. NO merge winner. NO salvage como exito.

Success definition:
- 2 lanes terminan con branch push + gh pr create.
- Cada lane emite linea literal PR_URL=https://github.com/Umbral-Bot/umbral-agent-stack/pull/<n>.
- Judge compara PRs y recomienda winner.
- Merge winner solo si David lo autoriza despues.

Preflight:
cd ~/umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git status --short --branch
git log -1 --oneline
grep -q "PR_URL=https://..." docs/79-tournament-protocol-openclaw-native.md || { echo "MISSING_PR_URL_PROTOCOL"; exit 2; }

Evidencia:
EV=~/.coord-ag-evidence/D3.5
mkdir -p "$EV"
date -Iseconds | tee "$EV/run-start.txt"
git log -1 --oneline | tee -a "$EV/run-start.txt"

Run:
# Usar el skill/protocolo vigente de torneo desde main.
# Issue/lane exactos los define David antes de ejecutar.
# Si una lane no entrega PR_URL, veredicto PARTIAL, no OK.

Final veredictos:
- D35_CLEAN_TOURNAMENT_OK: solo con 2 PR URLs + judge.
- D35_CLEAN_TOURNAMENT_PARTIAL: spawn o trabajo real, pero faltan PR URLs.
- D35_CLEAN_TOURNAMENT_BLOCKED: no arranca o falla preflight.

NO merge. NO cerrar PRs stale.
```

Acceptance:

- El torneo limpio no se confunde con salvage.
- PR URLs obligatorias.

---

## PROMPT 6 - Cursor/editorial Wave 2 + LinkedIn HITL

Esto es roadmap/decision work, no publicacion.

```text
Sos Cursor lead. Planificar Wave 2 editorial y LinkedIn v1 con HITL estricto.
Responder en espanol. NO publicar. NO programar publicaciones. NO dejar autopublicacion activa.

Inputs canonicos:
- Core-first plan de David.
- ADR-017 modelo Areas -> Gerencias -> Agentes -> Subagentes.
- Runbooks/editorial docs actuales del repo.
- PR #449 / main post-merge.

Decisiones a cerrar:
- Canal vs formato.
- S6 canonico.
- content hash/idempotencia.
- SQLite hardening.
- observabilidad.
- source-use policy.
- LinkedIn token lifecycle antes de vencimiento/reauth.

HITL LinkedIn obligatorio:
- Rick puede generar copy, metadata, payload y asset.
- David debe marcar `aprobado_contenido=true`.
- David debe marcar `autorizar_publicacion=true`.
- La publicacion requiere accion explicita de David.

Roadmap:
- Ghost: primer canal plenamente automatizable.
- X: manual/asistido v1.
- Visuales tecnicos: Mermaid/screenshots primero; AI concept/hero solo cuando aporte.
- Vertex/Freepik API-first; no automatizar UIs de terceros.

Output:
- Plan Wave 2 con owners y gates.
- Que queda en Notion HITL vs repo source of truth.
- Riesgos ToS/reputacion.
- Prompts de ejecucion separados para implementation PRs.

Final:
- VEREDICTO: EDITORIAL_WAVE2_PLAN_READY
- No publicar nada.
```

Acceptance:

- La salida puede convertirse en tareas sin mezclar LinkedIn, Mission Control y torneos.
- HITL queda como gate no negociable.

---

## Handoff format recomendado

Para cualquier delegacion que salga de este pack, registrar:

```md
## Handoff
- tipo: issue | subagent | update
- solicitante original: David
- owner del handoff:
- caso padre / proyecto: Core-first Umbral Agent Stack
- motivo del handoff:
- problema a resolver:
- contexto minimo suficiente:
  - estado actual:
  - intento previo:
  - restricciones / riesgos:
  - links fuente:
- entregable esperado:
- criterio de aceptacion:
- eta:
- checkpoint si no hay eta cerrada:
- registro:
  - linear:
  - notion:
- plan de retorno al solicitante:
- condicion exacta de cierre:
```
