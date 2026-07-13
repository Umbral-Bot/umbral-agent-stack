# MEGAPROMPT — Copilot-VPS · APPLY OpenClaw OAuth discriminado

> **Owner:** `copilot-vps` para OpenClaw/runtime; Copilot Windows para revocar Azure.
>
> **Fuente:** `openclaw-foundry-to-oauth-migration-analysis__2026-07-13__b0004__src-codex.md`
>
> **Matriz:** `data/openclaw-model-migration-matrix-2026-07-13.yaml`
>
> **Estado:** preparado, **NO AUTORIZADO** por la mera existencia de este archivo.

## Objetivo

Convertir OpenClaw desde el provider custom Azure/API-key que hoy se presenta como `openai/*` a la ruta nativa ChatGPT/Codex OAuth, con modelos por rol y crons explícitos. No tocar Worker/editorial/S8 hasta los gates indicados. No reactivar Foundry.

## Autoridad requerida

Antes de cualquier write, David debe dar autorización textual específica para:

1. login OAuth OpenAI en el VPS;
2. backup + patch `~/.openclaw/openclaw.json` y crons;
3. `openclaw doctor --fix` y restart gateway;
4. cleanup de env y rotación/revocación de keys en una fase posterior.

Si falta cualquiera, ejecutar solo T0 read-only y devolver `APPLY_BLOCKED_NO_AUTHORIZATION`.

## Regla de superficie

- **Copilot-VPS:** auth store OpenClaw, JSON, crons, systemd user, smokes y evidencia.
- **Copilot Windows:** Azure/Foundry, revocación/rotación de keys y deployments.
- Copilot-VPS no instala Azure CLI ni modifica recursos Azure.
- El Worker nunca lee/copiará tokens OAuth; la migración Worker va en PR/deploy separado.

## Secret-output guard

- No imprimir stdout crudo de `models status` si contiene perfiles o credenciales truncadas.
- No hacer `cat` de env, JSON auth, SQLite, `models.json` o service environment.
- Registrar solo nombres de variables y conteos `oauth/api_key` extraídos.
- Nunca copiar strings con forma de token, ni siquiera fragmentos abreviados.
- Device code/login se muestra solo en la terminal interactiva de David; no se captura en evidencia.

## CLI canónica del VPS

El binario `openclaw` no está en `PATH` de SSH no interactivo. Usar:

```bash
OPENCLAW_CLI=(
  /usr/bin/node
  /home/rick/.npm-global/lib/node_modules/openclaw/dist/index.js
)
"${OPENCLAW_CLI[@]}" --version
```

No crear symlinks ni editar PATH en esta tarea.

## Stop conditions

STOP inmediato si:

- repo VPS dirty o no sincronizable sin alterar trabajo existente;
- falta autorización explícita;
- gateway no está active antes del cambio;
- no se crea profile OpenAI OAuth usable;
- el catálogo OAuth no expone `openai/gpt-5.6-sol`;
- el candidate JSON conserva endpoint Azure, auth API-key o refs Foundry/Google;
- `config validate` falla;
- un diff incluye secretos;
- restart no está autorizado o gateway no vuelve a active;
- S8 se intenta migrar a Google/OpenAI Images en vez de Magnific;
- se intenta limpiar Azure env del Worker antes de desplegar su cambio de contrato.

## T0 — Preflight repo y runtime (read-only)

```bash
set -euo pipefail
cd ~/umbral-agent-stack
hostname
whoami
date -u +%Y-%m-%dT%H:%M:%SZ
git fetch origin main
git checkout main
git status --short --branch
git log -1 --oneline
test -f docs/audits/MEGAPROMPT-COPILOT-OPENCLAW-OAUTH-MIGRATION-APPLY.md
test -f docs/audits/data/openclaw-model-migration-matrix-2026-07-13.yaml
test -f ~/.openclaw/openclaw.json
systemctl --user is-active openclaw-gateway.service
```

El audit 2026-07-13 encontró el repo VPS dirty y en `29897de3c304`. Si sigue dirty, **no ejecutar** `stash`, `reset`, `checkout --`, `clean` ni `pull`. Devolver:

```text
APPLY_BLOCKED_VPS_REPO_DIRTY
```

Solo tras regularización externa:

```bash
git pull --ff-only origin main
git log -1 --oneline
```

## T1 — Inventario seguro y backups

Requiere autorización de backup/write. Crear evidencia:

```bash
TASK=oauth-migration-20260713
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
EVIDENCE="$HOME/.coord-ag-evidence/$TASK/$STAMP"
mkdir -p "$EVIDENCE"
chmod 700 "$HOME/.coord-ag-evidence/$TASK" "$EVIDENCE"
cp -a ~/.openclaw/openclaw.json "$EVIDENCE/openclaw.json.pre"
"${OPENCLAW_CLI[@]}" cron list --json > "$EVIDENCE/crons.pre.json"
chmod 600 "$EVIDENCE/openclaw.json.pre" "$EVIDENCE/crons.pre.json"
```

No copiar auth SQLite a evidencia general. Si David autoriza backup del auth store, guardarlo `0600` en directorio privado y no adjuntarlo ni commitearlo.

Inventariar solo shape:

- provider ids, hosts y auth mode;
- agent ids/model/thinking;
- allowlist;
- cron id/name/agent/model/thinking;
- nombres de variables LLM, no valores.

## T2 — Login OpenAI OAuth antes del cutover

Requiere interacción de David y no debe capturarse:

```bash
"${OPENCLAW_CLI[@]}" models auth login \
  --provider openai \
  --device-code \
  --profile-id openai:umbral-rick
```

No usar `--force`. No usar `--set-default` todavía.

Verificar sin imprimir credenciales. Ejecutar status desde un script que solo devuelva conteos para provider OpenAI; resultado esperado:

```text
openai oauth>=1 api_key>=0
```

Luego:

```bash
"${OPENCLAW_CLI[@]}" models list --provider openai
```

Gates:

- `openai/gpt-5.6-sol` debe aparecer en el catálogo respaldado por el profile OAuth.
- Elegir `LIGHT_MODEL=openai/gpt-5.4-mini` solo si aparece en ese catálogo. Si no, `LIGHT_MODEL=openai/gpt-5.3-codex`.
- Terra/Luna quedan fuera si no aparecen.

Si Sol no aparece, STOP sin tocar provider/model config:

```text
APPLY_BLOCKED_GPT56_SOL_ENTITLEMENT
```

## T3 — Candidate OpenClaw config y aprobación de diff

No reutilizar `scripts/vps/patch-openclaw-oauth-only.py` sin modificar: el estado live usa un provider Azure llamado `openai`, que ese script no retira.

Crear `openclaw.json.candidate` a partir del backup y aplicar **solo** estas transformaciones:

1. Eliminar `models.providers.azure-openai-responses` si existe.
2. Eliminar `models.providers.openai` **si** su `baseUrl` apunta a Azure o declara `auth: api-key`. La ruta nativa OAuth no necesita ese provider custom.
3. Mantener `plugins.entries.codex.enabled=true`.
4. Añadir `auth.order.openai: ["openai:umbral-rick"]` usando el schema validado por OpenClaw.
5. `agents.defaults.model.primary=openai/gpt-5.5`, fallback `openai/gpt-5.4`.
6. Allowlist base: Sol, 5.5, 5.4, 5.3-codex; añadir mini solo si T2 lo confirmó.
7. Quitar allowlist/refs `azure-openai-responses/*`, `openai-codex/*`, `google/*`, `google-vertex/*`.
8. Aplicar agentes:

| Agent | Primary | Fallbacks | thinkingDefault |
|---|---|---|---|
| `main` | `openai/gpt-5.6-sol` | 5.5, 5.4 | `xhigh` |
| `rick-orchestrator` | `openai/gpt-5.6-sol` | 5.5, 5.4 | `xhigh` |
| `rick-delivery` | `openai/gpt-5.3-codex` | 5.4 | `medium` |
| `rick-qa` | `openai/gpt-5.6-sol` | 5.5, 5.4 | `xhigh` |
| `rick-ops` | `$LIGHT_MODEL` | 5.3-codex | `low` |
| `rick-communication-director` | `openai/gpt-5.6-sol` | 5.5, 5.4 | `xhigh` |
| `rick-linkedin-writer` | `openai/gpt-5.6-sol` | 5.5, 5.4 | `xhigh` |
| `rick-tracker` | `$LIGHT_MODEL` | 5.3-codex | `low` |

Validar el candidate sin hacerlo live. Si la CLI no permite `OPENCLAW_CONFIG_PATH`, validar JSON con Python y schema mediante una copia controlada solo después de autorizar; no adivinar flags.

Antes de aplicar, generar un diff saneado que muestre paths/model ids pero sustituya cualquier `apiKey`, header, token o secret por `[REDACTED]`. David debe aprobar el diff.

## T4 — Aplicar OpenClaw y smokes

Con aprobación explícita del diff:

```bash
cp -a ~/.openclaw/openclaw.json "$EVIDENCE/openclaw.json.pre-apply"
install -m 600 /path/to/openclaw.json.candidate ~/.openclaw/openclaw.json
"${OPENCLAW_CLI[@]}" config validate --json
"${OPENCLAW_CLI[@]}" doctor --fix
systemctl --user restart openclaw-gateway.service
systemctl --user is-active openclaw-gateway.service
```

Verificar:

1. status OpenAI extraído: `oauth>=1`; no API key efectiva para agent turns;
2. no custom provider Azure;
3. no refs Foundry/Google/legacy Codex;
4. smoke `main` Sol, output corto;
5. smoke delivery 5.3-codex;
6. smoke tracker light;
7. runtime mostrado como Codex/OpenAI OAuth.

No imprimir respuesta completa si puede contener contexto; registrar solo PASS, model/runtime y usage agregado.

## T5 — Migrar los seis crons por CLI

No buscar ni editar `~/.openclaw/cron/jobs.json`; no existe en este runtime. Usar IDs live:

```bash
"${OPENCLAW_CLI[@]}" cron edit 6b5dd638-4998-457f-91bf-be4fc8e58a53 \
  --model "$LIGHT_MODEL" --thinking low

"${OPENCLAW_CLI[@]}" cron edit ffde9eab-c89f-4bf7-9d5d-39366ebd0e19 \
  --model openai/gpt-5.3-codex --thinking low

"${OPENCLAW_CLI[@]}" cron edit 978d3d6e-86f9-4447-a624-7ad3fd15bae3 \
  --model openai/gpt-5.5 --thinking medium

"${OPENCLAW_CLI[@]}" cron edit b444bc68-48e3-4406-8997-5854a20771e4 \
  --model "$LIGHT_MODEL" --thinking low

"${OPENCLAW_CLI[@]}" cron edit 31adc1a1-db9c-4722-93fe-7922177bfe16 \
  --model openai/gpt-5.6-sol --thinking xhigh

"${OPENCLAW_CLI[@]}" cron edit 8c06fcf1-4014-401a-a5be-22aeef4c0571 \
  --model openai/gpt-5.5 --thinking high
```

Releer JSON y comparar exactamente los seis. Ejecutar manualmente solo Briefing + un light job si David autorizó el smoke. No disparar todos los jobs productivos.

## T6 — Worker/editorial/S8 (PR y deploy separados)

No ejecutar en el mismo cambio de config OpenClaw.

### Worker/editorial texto

Implementar Opción A de `editorial-worker-oauth-migration-options-2026-07-13.md`:

- provider lógico `openclaw_oauth`;
- model id explícito por task type;
- Worker llama gateway local;
- no lee OAuth store;
- eliminar Foundry/Gemini del routing activo;
- migrar `config/team_workflows.yaml` y `copilot_agent` BYOK o deshabilitarlos;
- reemplazar Gemini grounded por OpenAI web search verificado o Tavily + síntesis OAuth;
- retirar Google TTS y resolver voz en un gate separado;
- migrar guard, contrato y ROLEs atómicamente;
- un post E2E dry-run sin writes Notion/publicación.

### S8

- reemplazar Google image por Magnific-only;
- ratio canónico 4:3;
- selección humana obligatoria;
- no OpenAI Images como sustituto.

### Gaps

- embeddings y Realtime quedan deshabilitados o en proyectos separados;
- `google.audio.generate` queda deshabilitado hasta la decisión de voz;
- no declarar migración completa mientras sigan consumiendo Foundry.

## T7 — Cleanup env, rotación y soak

Solo después de PASS OpenClaw + deploy Worker:

1. Copilot-VPS retira nombres `AZURE_OPENAI_*`/`KIMI_AZURE_*` de gateway/dispatcher/worker según el inventario aprobado.
2. Retira solo credenciales Google de modelos; preserva Calendar/Gmail/Drive/CSE requeridas por otras capacidades.
3. Reinicia cada servicio por separado con autorización y confirma que los nombres retirados ya no aparecen en `/proc/<pid>/environ`.
4. Copilot Windows rota/revoca las keys Azure; Copilot-VPS no hace esa acción.
5. Mantener 24 h de soak con briefing, un job light y una operación editorial dry-run.

Kimi: no retirar hasta inventariar n8n live. Si no hay workflow real, eliminar; si existe, STOP y pedir decisión David sobre la excepción.

## Rollback

### Principio

No reactivar Foundry como rollback automático. Los gates T1/T2 existen para evitar cortar antes de confirmar OAuth.

### Config/crons

Si el gateway falla inmediatamente después de T4 y David autoriza rollback:

```bash
cp -a "$EVIDENCE/openclaw.json.pre-apply" ~/.openclaw/openclaw.json
"${OPENCLAW_CLI[@]}" config validate --json
systemctl --user restart openclaw-gateway.service
systemctl --user is-active openclaw-gateway.service
```

Restaurar crons desde `crons.pre.json` solo con un script revisado que aplique campos por CLI. No copiar el JSON a un path supuesto.

Si las keys Foundry ya fueron revocadas, no restaurar un config que dependa de ellas. Usar un candidate OAuth-safe con `openai/gpt-5.5` y escalar a David; ese estado es contingencia, no PASS final porque `main` debe volver a Sol.

## Evidencia final

Guardar en `$EVIDENCE`:

- identidad, SHAs repo y estado limpio;
- autorización textual de David sin secretos;
- inventario before/after saneado;
- diff saneado;
- validation/doctor result saneado;
- estado de servicios before/after;
- matriz agentes/crons after;
- smokes con solo PASS/model/runtime;
- nombres de env before/after;
- resultado `PASS | PARTIAL | FAIL` y próxima acción.

## PASS final

```text
OPENCLAW_OAUTH_MIGRATION_PASS
openai_oauth=1
openai_api_key_agent_route=0
main=openai/gpt-5.6-sol
agents=8/8
crons=6/6
foundry_refs=0
gemini_active_llm_refs=0
worker_text=openclaw_oauth
stage8=magnific_only
```

Si Worker/S8 todavía no están desplegados, el máximo veredicto es:

```text
OPENCLAW_OAUTH_MIGRATION_PARTIAL | worker=not_migrated | s8=not_migrated
```
