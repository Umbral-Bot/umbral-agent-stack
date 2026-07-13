# Auditoría Foundry → OpenAI OAuth — OpenClaw, Worker y editorial

- **Fecha:** 2026-07-13
- **Corrida:** `b0004`
- **Autor:** Codex
- **Branch:** `codex/audit-openclaw-foundry-oauth-migration-20260713`
- **Baseline repo:** `origin/main` @ `e5d650c5`
- **VPS auditada:** `srv1431451`, usuario `rick`, 2026-07-13T15:03Z
- **Modo:** repo + VPS read-only; no patches, reinicios, deploys, writes Notion ni smokes de generación

> Convención de evidencia: **[Repo]** es configuración o código versionado; **[VPS live]** es lectura saneada del runtime; **[Inferencia]** es una conclusión derivada y se marca como tal. No se copiaron valores de keys o tokens.

## 1. Resumen ejecutivo y veredicto recomendado

El plan de migración está listo, pero el runtime **todavía no está en OAuth**. El cambio urgente del 12 de julio migró los nombres visibles a `openai/*`, pero el VPS conserva un provider `models.providers.openai` con endpoint Azure, `auth: api-key` y credenciales literales. `openclaw models status --probe-provider openai` informó `oauth=0`, `api_key=1`. Por lo tanto, `openai/gpt-*` hoy es una etiqueta sobre Foundry, no prueba de ChatGPT/Codex OAuth.

Recomendación:

1. Migrar OpenClaw a la ruta nativa Codex OAuth: login `openai` por device code, retirar los providers custom Azure que sombrean la ruta nativa, usar solo refs canónicas `openai/*` y verificar `oauth=1` antes de cambiar agentes o crons.
2. Mantener `main` en `openai/gpt-5.6-sol` solo si el catálogo **OAuth** de la cuenta lo expone. El catálogo actual está autenticado por API key y no demuestra entitlement OAuth.
3. Aplicar matriz por rol: Sol para razonamiento/editorial pesado; GPT-5.3 Codex o el mini OAuth realmente expuesto para operaciones ligeras; GPT-5.5 como fallback pesado.
4. Migrar texto Worker/editorial mediante el gateway local OpenClaw. El Worker no debe leer el SQLite ni copiar tokens OAuth.
5. Retirar Google/Gemini del routing activo. S8 debe dejar `google.image.generate` y pasar a Magnific-only.
6. Tratar embeddings RAG y Realtime de voz como gaps sin equivalente OAuth 1:1; pausarlos o rediseñarlos en gates separados.

**Veredicto recomendado:** `MIGRATION_PLAN_READY | openclaw=oauth_discriminated | worker=needs_contract_change | gemini=removed | s8=magnific_only`

La aplicación queda cerrada por dos gates técnicos previos: `openai OAuth profile usable` y `gpt-5.6-sol visible en catálogo OAuth`. No son bloqueantes para este plan documental.

## 2. Inventario Foundry por superficie

### 2.1 OpenClaw histórico y agentes

**[VPS live]** Los backups `openclaw.json.bak*` reconstruyen el estado Foundry sin leer secretos. El provider histórico usó `api: openai-responses`, `auth: api-key`, host `cursor-api-david.openai.azure.com/openai/v1`, `contextWindow=400000` y `maxTokens=16384` para GPT-5.4/5.5. El backup de catálogo también contenía GPT-4.1, GPT-5.2 Chat, Kimi K2.5 y GPT-5.4 Pro.

| surface | id | foundry_ref | foundry_config | role_need | volume | oauth_target | equivalence | notes |
|---|---|---|---|---|---|---|---|---|
| openclaw agent | `main` | `azure-openai-responses/gpt-5.5` | `xhigh`; fb 5.4, Kimi, 5.2-chat, OpenAI 5.4 | flagship / decisión final | medio | `openai/gpt-5.6-sol` | upgrade | Fijo por David; gate de entitlement |
| openclaw agent | `rick-orchestrator` | `azure-openai-responses/gpt-5.5` | `xhigh`; fb 5.4/5.2-chat | planning heavy | medio | `openai/gpt-5.6-sol` | upgrade | Fallback 5.5 → 5.4 |
| openclaw agent | `rick-delivery` | `azure-openai-responses/gpt-5.5` | `xhigh`; antes 5.4 + 5.2-chat | coding acotado | medio | `openai/gpt-5.3-codex` | downgrade intencional | Mantiene capacidad de código con menor coste |
| openclaw agent | `rick-qa` | `azure-openai-responses/gpt-5.5` | `xhigh`; fb 5.4 | QA editorial / razonamiento | medio | `openai/gpt-5.6-sol` | upgrade | Puede usar 5.5 para QA no editorial mediante override explícito |
| openclaw agent | `rick-ops` | `azure-openai-responses/gpt-5.5` | `xhigh`; fb 5.4/5.2-chat | ops-light | alto | mini OAuth visible; si no, `openai/gpt-5.3-codex` | downgrade intencional | No usar Sol como default de seguimiento |
| openclaw agent | `rick-communication-director` | `azure-openai-responses/gpt-5.5` | `xhigh`; fb 5.4 | voz / escritura heavy | bajo-medio | `openai/gpt-5.6-sol` | upgrade | Contrato editorial debe migrar junto |
| openclaw agent | `rick-linkedin-writer` | `azure-openai-responses/gpt-5.5` | S6/S7 `xhigh` | escritura heavy | medio | `openai/gpt-5.6-sol` | upgrade | Mantener gate humano |
| openclaw agent | `rick-tracker` | `azure-openai-responses/gpt-5.5` | `medium`; antes fb Gemini Flash + 5.4 | tracking / clasificación | alto | mini OAuth visible; si no, `openai/gpt-5.3-codex` | downgrade intencional | `thinking=low`; no Gemini |

### 2.2 Catálogo Foundry histórico

| Modelo/deployment | Evidencia | Config observada | Migración |
|---|---|---|---|
| `gpt-5.5` | [Repo] audit 2026-06-06 + [VPS] backups | versión `2026-04-24`, GlobalStandard, capacity 2517, reasoning, 400k/16k | heavy → `openai/gpt-5.6-sol`; fallback `openai/gpt-5.5` |
| `gpt-5.4-pro` | [VPS] backup catálogo | reasoning, 400k/16k | `openai/gpt-5.6-sol` |
| `gpt-5.4` | [Repo/VPS] | reasoning, 400k/16k | `openai/gpt-5.5` o conservar `openai/gpt-5.4` como segundo fallback |
| `gpt-5.2-chat` | [Repo/VPS] | no reasoning, 400k/65,536 | `openai/gpt-5.5` |
| `gpt-4.1` | [VPS] backup catálogo | no reasoning, 128k/32,768 | mini OAuth o `openai/gpt-5.3-codex`; no equivalencia exacta necesaria |
| `kimi-k2.5` | [Repo/VPS] | no reasoning, 200k/8,192; API-only documentado | retirar de agentes; conservar solo si se demuestra workflow n8n vivo y David lo ratifica |

### 2.3 Crons live

**[VPS live]** OpenClaw 2026.6.10 almacena seis jobs accesibles por `openclaw cron list --json`; el path solicitado `~/.openclaw/cron/jobs.json` no existe. Solo `Briefing matutino` tiene `payload.model`. Los otros cinco heredan el modelo del agente, por lo que cuatro jobs asignados a `main` heredan hoy el tier más caro.

| job | agent | override live | necesidad | target propuesto |
|---|---|---|---|---|
| Seguimiento cada 30 min — Proyecto embudo/Drive | `rick-ops` | ninguno | tracking alto volumen | mini OAuth visible; fallback `openai/gpt-5.3-codex`, `low` |
| SIM — recolección señales (cada 6h) | `main` | ninguno | extracción ligera | `openai/gpt-5.3-codex`, `low` |
| SIM — discovery web por keywords (cada 12h) | `main` | ninguno | síntesis/research | `openai/gpt-5.5`, `medium` |
| SIM — Google Trends RSS (cada 12h) | `main` | ninguno | clasificación ligera | mini OAuth visible; fallback `openai/gpt-5.3-codex`, `low` |
| Investigación Profunda Mercado AECO (Tavily) - 2 días | `main` | ninguno; schedule real 12h | research heavy | `openai/gpt-5.6-sol`, `xhigh` |
| Briefing matutino | `rick-orchestrator` | `azure-openai-responses/gpt-5.5` | digest de un turno | `openai/gpt-5.5`, `high` |

El briefing está fuera del allowlist live y es el caso directo que explica el error de modelo en Telegram. Debe migrarse mediante `openclaw cron edit <id> --model ...`, no editando un archivo inexistente.

### 2.4 Worker, Dispatcher y superficies auxiliares

| surface/id | foundry_ref/config | role_need | oauth_target | equivalence / acción |
|---|---|---|---|---|
| Dispatcher `coding`, `general`, `ms_stack` | preferred `azure_foundry` → `gpt-5.4` | texto/código | provider nuevo `openclaw_oauth` → `openai/gpt-5.3-codex` o 5.5 por task | cambio de contrato |
| Dispatcher `writing` | fallback `azure_foundry` | escritura | `openclaw_oauth` → 5.6 Sol/5.5 | cambio de contrato |
| Dispatcher `research`, `critical`, `light` | Foundry en fallback; Gemini primario en research/light | mixto | eliminar Gemini; targets por rol/volumen | cambio de policy obligatorio |
| Worker `llm.generate` | aliases `azure_foundry→gpt-5.4`, `azure_gpt_41`, `azure_gpt_52`, `kimi_azure` | texto | gateway local OpenClaw con `openai/*` | no hay OAuth directo en handler actual |
| Worker tournament | default `models=[azure_foundry]` | batch/competencia | target explícito por lane; no default Foundry | cambio de default |
| Worker `rag.query` answer | default `model=azure_foundry` | síntesis RAG | gateway local 5.5/5.3 | texto migrable |
| Worker RAG embeddings | `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, default `text-embedding-3-large` | embeddings | **sin equivalente OAuth 1:1** | pausar vector/hybrid o diseñar proveedor separado |
| Worker `azure.audio.generate` | `gpt-realtime`, API `2025-04-01-preview`, key Azure | Realtime/TTS | **sin equivalente OAuth 1:1** | OAuth Codex no autentica Realtime público; gate separado |
| `copilot_agent` BYOK | `AZURE_OPENAI_*`, default `gpt-5.4` | agente publicado / texto | gateway OpenClaw o deprecar BYOK | el cliente actual no soporta OAuth |
| `config/team_workflows.yaml` | team `data` declara `gemini-2.5-flash` | trabajo ligero | mini OAuth visible; fallback 5.3-codex | cambio de workflow |
| Worker `research.web` backend | Gemini 2.5 Flash + Google Search grounded | discovery/research | OpenClaw/OpenAI web search o Tavily + 5.5 | retirar llamada Gemini directa; validar herramientas |
| Worker `google.audio.generate` | `gemini-2.5-flash-preview-tts` | TTS | proveedor de voz aprobado en gate separado | no usar Google directo; no asumir OAuth TTS |
| n8n/Kimi | doc `docs/kimi-recurso-n8n.md`; env activo, sin workflow versionado encontrado | automatización legacy | retirar si no hay workflow vivo; excepción solo con ratificación | decisión requerida antes de borrar env |
| LiteLLM | placeholder Google/OpenAI, no activo probado | proxy aspiracional | no usar como atajo de esta migración | fuera de camino crítico |

### 2.5 Scripts y templates capaces de reinyectar el estado legacy

| Path | Ref/función legacy | Tratamiento |
|---|---|---|
| `scripts/ops/patch-openclaw-voice-fallbacks.py` | añade 5.4/5.2/Kimi Foundry y Vertex | deprecar o reescribir antes de cualquier uso |
| `scripts/vps/patch-openclaw-gpt55-xhigh.py` | promueve todos los agentes a Foundry 5.5 | conservar solo como histórico con warning o archivar |
| `scripts/vps/patch-openclaw-oauth-only.py` | usa refs `openai-codex/*` y no elimina el provider Azure renombrado `openai` | reemplazar antes de APPLY |
| `openclaw/workspace-templates/skills/openclaw-gateway/SKILL.md` | exige Foundry 5.5/5.4 y permite Gemini | migrar junto al contrato editorial |
| `openclaw/workspace-templates/skills/llm-generate/SKILL.md` | defaults/aliases Foundry y Gemini | migrar al provider lógico gateway OAuth |
| `openclaw/workspace-templates/skills/rag-knowledge/SKILL.md` y `tournament/SKILL.md` | defaults `azure_foundry` | alinear con los gaps/defaults nuevos |
| `openclaw/workspace-templates/TOOLS.md` y `provider-status/SKILL.md` | documentan Azure/Google como rutas activas | actualizar después del deploy |

El checklist de refs cubre configuración/código/templates activos y backups live. Los documentos históricos que narran activaciones Foundry se conservan como evidencia y no son targets de reemplazo textual masivo.

## 3. Estado VPS live vs repo: drift

| Hallazgo | Repo | VPS live | Conclusión |
|---|---|---|---|
| Provider OpenAI | script urgente elimina `azure-openai-responses` | provider `openai` custom apunta a Azure y usa API key | migración nominal, no OAuth |
| Auth OpenAI | docs esperan OAuth | `oauth=0`, `api_key=1`; sin `auth.order.openai` | gate T1 fallido |
| Modelos agentes | script usa refs legacy `openai-codex/*` para varios agentes | refs ya son `openai/*` | doctor o cambio posterior reescribió slugs, no credencial |
| Rick main | requerido `openai/gpt-5.6-sol` | primary correcto por nombre | entitlement no comprobado |
| Provider block | repo urgente solo elimina provider Foundry por nombre | provider Azure fue renombrado a `openai` | el script actual no basta para la fase APPLY |
| Editorial | contrato exige Foundry 5.5 | agentes ya muestran `openai/*` | guard fallará o el pipeline queda incoherente |
| Cron store | prompt suponía `cron/jobs.json` | archivo ausente; CLI devuelve 6 jobs | usar CLI, no path fijo |
| Briefing | no cubierto por script | override Foundry stale | migración incompleta |
| Env | script pide comentar Azure/Kimi | procesos gateway, dispatcher y worker conservan nombres Azure/Kimi activos | retiro incompleto; reinicios no hicieron limpieza efectiva |
| Repo VPS | origin/main Windows `e5d650c5` | VPS `29897de3c304` y dirty | APPLY debe hacer STOP hasta resolver repo dirty |

**[VPS live]** El provider y su `models.json` contienen material de key literal. Este informe registra solo `literal_present`; no copia ningún fragmento. La fase APPLY debe retirar ese material y coordinar revocación/rotación fuera del repo.

## 4. Configuración Foundry en particular

- **Deployment y recurso [Repo]:** `cursor-api-david`, RG `rg-openai-cursor`, `eastus2`; `gpt-5.5` Succeeded, versión `2026-04-24`, GlobalStandard capacity 2517. El audit es de 2026-06-06; no se consultó Azure Portal en esta corrida. **CONFIDENCE: medium** para el estado actual del deployment.
- **Endpoints [Repo/VPS]:** el alias histórico usó el host nativo `cursor-api-david.openai.azure.com`. Los procesos Worker/Dispatcher todavía exponen `AZURE_OPENAI_ENDPOINT` hacia `cursor-api-david.cognitiveservices.azure.com`.
- **Auth [VPS]:** API key, no OAuth. Hay variables `AZURE_OPENAI_*` y `KIMI_AZURE_*` activas en procesos gateway, dispatcher y worker.
- **Provider histórico [VPS backup]:** `azure-openai-responses`, `api=openai-responses`, `auth=api-key`; modelos GPT-4.1, GPT-5.2 Chat, Kimi K2.5, GPT-5.4, GPT-5.5 y GPT-5.4 Pro.
- **Thinking [Repo/VPS backup]:** defaults y todos los agentes `xhigh`, excepto `rick-tracker=medium`.
- **Fallbacks [VPS backup]:** 5.4, 5.2-chat, Kimi y refs OpenAI; tracker añadió Gemini Flash.
- **Allowlist [VPS live]:** solo `openai/gpt-5.6-sol`, `openai/gpt-5.5`, `openai/gpt-5.4`, `openai/gpt-5.3-codex`. El briefing aún pide `azure-openai-responses/gpt-5.5`.
- **Fuente faltante [Repo]:** `docs/audits/rick-openclaw-technical-debt-2026-07-05.md` no existe en `origin/main`, historial local ni VPS. No se afirma una serie 429 específica sin esa evidencia.

## 5. Catálogo OAuth disponible y límites de la evidencia

**[VPS live]** `openclaw models list` reconoce:

- configurados: `openai/gpt-5.6-sol`, `openai/gpt-5.5`, `openai/gpt-5.4`, `openai/gpt-5.3-codex`;
- conocidos por el catálogo key-backed: `openai/gpt-5.4-mini`, `openai/gpt-5.4-nano`, `openai/o3-mini`, `openai/o4-mini` y otros.

Esto **no** confirma que mini/nano estén disponibles por OAuth: el status efectivo es API key. La selección light debe quedar condicional al resultado de `models auth login --provider openai --device-code` seguido por `models list --provider openai` y `models status --probe --probe-provider openai`.

Documentación oficial consultada:

- [OpenClaw — OpenAI provider](https://docs.openclaw.ai/providers/openai): `openai/*` es la ruta canónica; `openai-codex/*` es legacy; OAuth y API key son auth distintas bajo el mismo prefix.
- [OpenClaw — Doctor](https://docs.openclaw.ai/gateway/doctor): `doctor --fix` reescribe refs legacy y limpia pins, pero un endpoint custom no es elegible para selección implícita del runtime Codex.
- [OpenClaw — Agent runtimes](https://docs.openclaw.ai/concepts/agent-runtimes): la ruta OAuth normal usa refs `openai/*` con runtime Codex.
- [OpenAI — preview GPT-5.6](https://openai.com/index/previewing-gpt-5-6-sol/): Sol=flagship, Terra=balanced, Luna=fast/affordable; al 2026-06-26 el acceso era preview limitada.

La propia documentación de OpenClaw exige consultar el catálogo de la cuenta. Sol aparece por nombre en el VPS, pero no hubo login OAuth ni smoke de generación en esta corrida.

## 6. Matriz rol → `openai/*`

| Tier | Roles | Primary | Thinking | Fallbacks | Gate |
|---|---|---|---|---|---|
| flagship | `main`, orchestrator, communication-director, linkedin-writer, QA editorial | `openai/gpt-5.6-sol` | `xhigh` | 5.5 → 5.4 | Sol visible en catálogo OAuth |
| heavy estable | briefing, research normal, QA no editorial | `openai/gpt-5.5` | high/xhigh | 5.4 | OAuth profile usable |
| coding acotado | delivery, scripts, reparación | `openai/gpt-5.3-codex` | medium/high | 5.4 | OAuth profile usable |
| light alto volumen | ops, tracker, signal/RSS | mini OAuth expuesto | low | 5.3-codex | no asumir mini antes del probe |

No se propone Terra/Luna en el patch inicial porque no aparecen en el catálogo live actual. Podrán sustituir 5.5/mini cuando el catálogo OAuth los exponga y exista un soak separado.

## 7. Gemini: eliminación y sustitutos

**[Repo]** Gemini sigue activo en `config/quota_policy.yaml`, `config/team_workflows.yaml`, `worker/tasks/llm.py`, `worker/research_backends.py`, `worker/tasks/google_audio.py`, `worker/tasks/google_image.py`, `infra/docker/litellm_config.yaml`, templates OpenClaw, el fallback histórico del tracker y S8. **[VPS live]** el gateway aún recibe variables Google y el catálogo lista modelos Gemini.

Plan:

1. Quitar Gemini de rutas activas `research`, `light` y fallbacks.
2. Reemplazar tracking/clasificación por mini OAuth realmente visible; fallback `openai/gpt-5.3-codex`.
3. Reemplazar research por 5.5 o Sol según profundidad.
4. Reemplazar el backend grounded Gemini por OpenAI web search vía OpenClaw cuando el runtime/herramientas lo soporten, o Tavily + síntesis OAuth. No cambiar retrieval por un modelo sin herramienta.
5. Retirar Google TTS del plan activo y elegir el proveedor de voz en un gate separado; no asumir que el OAuth de agent turns cubre audio.
6. Retirar refs Google del allowlist y de agentes/crons tras confirmar que no hay otra capacidad no-LLM compartiendo esas variables. No borrar credenciales Calendar/Gmail/Drive: no son modelos.
7. Separar `GOOGLE_*` de productividad de `GOOGLE_API_KEY`/Vertex de LLM para evitar un borrado indiscriminado.

## 8. Magnific-only para imágenes

**[Repo]** `scripts/discovery/stage8_image_generator.py` contradice la política actual: llama directamente `worker.tasks.google_image.handle_google_image_generate`, modelo default `gemini-3-pro-image-preview`, ratio 3:2 y coste estático Gemini. La documentación de producción ya declara Magnific como proveedor visual primario y ratio canónico 4:3.

Acción propuesta:

- S8 debe llamar un handler explícito `editorial.magnific_generate` o el broker Rick/Magnific aprobado.
- Eliminar el import/call a `worker.tasks.google_image` del camino editorial.
- Mantener gates: texto aprobado → N alternativas Magnific → selección humana → autorización de publicación.
- Guardar `provider=magnific`, creation id, URL exportable, ratio 4:3 y coste/créditos; nunca un link UI.
- No sustituir Google por OpenAI Images: aunque OpenClaw documenta imágenes con OAuth, la regla de David para S8 es **Magnific-only**.

## 9. Worker/editorial: contrato y opciones A/B

**Opción A — recomendada:** Worker → gateway local OpenClaw → runtime Codex OAuth.

- Reutiliza `/v1/chat/completions` y `OPENCLAW_GATEWAY_TOKEN`.
- Añade un provider de router `openclaw_oauth` y mapea task types a refs `openai/*`.
- Cambia `_detect_provider` para que OpenAI seleccionado por el Dispatcher no caiga en `_call_azure_foundry` ni requiera `OPENAI_API_KEY`.
- El gateway, no el Worker, posee OAuth y su refresh lifecycle.
- Requiere un post E2E dry-run y observabilidad de modelo/auth efectivo.

**Opción B — no recomendada en esta fase:** OAuth directo dentro del Worker.

- El código actual solo sabe API key para `_call_openai` y Foundry.
- Leer `openclaw-agent.sqlite` acoplaría el Worker a storage privado y filtraría tokens.
- Implementar un cliente Codex app-server completo duplica el runtime de OpenClaw.
- Solo reconsiderar si OpenClaw publica un SDK/servicio estable de token delegation.

`config/editorial-model.yaml`, el guard, ROLE.md y el contrato deben cambiar atómicamente. S6 y S7.5 ya usan `openclaw/main`; S7 y S9 son determinísticos en código y no necesitan modelo. La prueba necesaria es un post E2E dry-run que demuestre `provider=openai`, `oauth=1`, modelo esperado y cero writes de publicación.

Detalle ampliado: [`editorial-worker-oauth-migration-options-2026-07-13.md`](./editorial-worker-oauth-migration-options-2026-07-13.md).

## 10. Coste cualitativo Foundry vs OAuth

| Factor | Foundry API key | ChatGPT/Codex OAuth | Magnific |
|---|---|---|---|
| Unidad | requests/tokens y capacidad Azure | límites/credits del plan Codex; no equivale a API gratis ilimitada | créditos de generación |
| Control | quota_policy local + Azure | perfil OAuth, límites de workspace, tier de modelo | balance y gate por asset |
| Heavy | GPT-5.5/5.4 con coste Azure | Sol consume más allowance; 5.5 reduce riesgo/coste | no aplica texto |
| Light | Gemini Flash/Kimi/5.2 | mini OAuth si existe; si no 5.3-codex | no aplica |
| Riesgo | 429/capacity/key lifecycle | preview entitlement, rate limits del plan, refresh OAuth | saldo insuficiente |

OpenAI publica precios API relativos de Sol/Terra/Luna, pero esos precios no deben trasladarse directamente al consumo OAuth. Se usa solo la relación cualitativa: Sol > Terra > Luna en coste y capacidad.

## 11. Riesgos y mitigaciones

| Riesgo | Severidad | Mitigación |
|---|---|---|
| refs `openai/*` siguen en Azure API key | crítica | retirar provider custom Azure; verificar `oauth=1 api_key=0` antes de smoke |
| Sol es preview / entitlement desconocido | alta | gate catálogo OAuth; no fallback silencioso para `main` |
| provider custom `openai` sombrea runtime Codex | crítica | eliminar bloque custom cuando host/auth prueben Azure; mantener plugin Codex |
| briefing stale fuera de allowlist | alta | `cron edit --model openai/gpt-5.5`; smoke manual del job |
| crons `main` heredan Sol sin discriminación | media-alta | overrides explícitos por job |
| contratos editoriales siguen Foundry | alta | cambiar YAML, guard, docs y ROLEs en un PR atómico |
| Worker no soporta OAuth | crítica | Opción A gateway proxy; no copiar tokens |
| S8 sigue Google directo | crítica de política | reemplazo Magnific-only antes de activar S8 |
| research/team workflows/Google TTS siguen en Gemini | alta | migrar o deshabilitar cada handler; preservar solo Google de productividad |
| embeddings/Realtime sin OAuth 1:1 | alta | pausar o separar proyectos; no fingir equivalencia |
| env Azure/Kimi sigue en procesos | alta | limpiar EnvironmentFiles + daemon-reload/restart autorizado + verificar nombres |
| key literal persiste en JSON/models store | crítica de seguridad | retirar, rotar/revocar y verificar ausencia sin imprimir valor |
| repo VPS dirty y desalineado | alta operativa | STOP en preflight; no stash/reset automático |
| doc técnica 2026-07-05 faltante | media de evidencia | no citar 429 no demostrados; recuperar fuente si se necesita |

## 12. Secuencia de aplicación T0–T7

- **T0 — Gate humano y repo:** aprobación textual; VPS identity; repo limpio/sincronizado; backups planeados.
- **T1 — OAuth antes del cutover:** login OpenAI por device code; verificar profile usable y catálogo OAuth. Si Sol no aparece, STOP y consultar a David.
- **T2 — Patch OpenClaw propuesto:** remover providers Azure por semántica, no solo por nombre; refs/allowlist/agents/thinking discriminados; validar una copia.
- **T3 — Cutover y service:** backup, patch, `config validate`, `doctor --fix`, restart autorizado, status `oauth=1`.
- **T4 — Crons:** aplicar overrides explícitos a los seis jobs; smoke briefing y un job light.
- **T5 — Repo Worker/editorial:** PR separado para policy/router/guard/ROLEs; tests unitarios y dry-run E2E.
- **T6 — Imagen:** reemplazar S8 por Magnific-only; prueba con asset no publicable y gate humano.
- **T7 — Retiro y soak:** quitar Azure/Google LLM/Kimi no usado de env y procesos, rotar keys, observar 24 h, cerrar evidencia.

El prompt ejecutable para Copilot-VPS está en [`MEGAPROMPT-COPILOT-OPENCLAW-OAUTH-MIGRATION-APPLY.md`](./MEGAPROMPT-COPILOT-OPENCLAW-OAUTH-MIGRATION-APPLY.md).

## 13. Criterios PASS y rollback

### PASS OpenClaw

- `models status` muestra provider OpenAI con al menos un profile `oauth=1` y sin API key efectiva para los agent turns objetivo.
- No existen providers custom con endpoint Azure ni refs `azure-openai-responses/*` en config, allowlist, agentes, crons o session pins.
- `main.primary=openai/gpt-5.6-sol`; smoke demuestra runtime Codex OAuth. Si no hay entitlement, no se declara PASS.
- Los siete agentes restantes y seis crons coinciden con la matriz.
- Briefing ejecuta una vez sin `model not allowed`.

### PASS Worker/editorial

- `config/quota_policy.yaml` no enruta texto a Foundry/Gemini.
- `llm.generate`, S6 y S7.5 registran `openai/*` vía gateway OAuth.
- Guard editorial exige el target nuevo y falla explícitamente ante cualquier modelo distinto.
- S8 no importa ni invoca Google; Magnific es el único provider editorial.
- RAG embeddings y Realtime están migrados en gates propios o explícitamente deshabilitados; no quedan fallbacks ocultos.

### Rollback

Rollback de la fase APPLY restaura `openclaw.json`, cron definitions y auth-order desde backups, valida JSON y reinicia solo con autorización. No restaura ni reactiva Foundry como estado deseado: si el cutover OAuth falla antes de T3, no se aplica; si falla después de retirar una key, se escala a David en vez de recrear secretos. El rollback detallado vive en el megaprompt APPLY.

## 14. Evidencia y archivos fuente

Repo principal:

- `docs/audits/openclaw-gpt-5.5-promotion-20260607.md`
- `docs/audits/openclaw-oauth-only-revert-2026-07-12.md`
- `docs/openclaw-config-reference-2026-03.json5`
- `config/editorial-model.yaml`
- `scripts/editorial/editorial_model_guard.py`
- `config/quota_policy.yaml`
- `dispatcher/model_router.py`, `dispatcher/service.py`
- `worker/tasks/llm.py`, `worker/tasks/rag.py`, `worker/rag/indexer.py`, `worker/tasks/azure_audio.py`
- `copilot_agent/agent.py`, `config/team_workflows.yaml`, `worker/research_backends.py`, `worker/tasks/google_audio.py`, `worker/tasks/google_image.py`
- `scripts/discovery/stage6_llm_combinator.py`, `stage7_5_copy_writer.py`, `stage8_image_generator.py`, `stage9_linkedin_draft.py`
- `scripts/vps/patch-openclaw-gpt55-xhigh.py`, `patch-openclaw-oauth-only.py`
- `openclaw/workspace-agent-overrides/*/ROLE.md`
- `.env.example`, `infra/docker/litellm_config.yaml`, `docs/kimi-recurso-n8n.md`

VPS read-only:

- `~/.openclaw/openclaw.json` y backups, resumidos sin secretos;
- auth/status vía OpenClaw 2026.6.10;
- crons vía CLI JSON;
- nombres de variables en entornos de procesos, sin valores;
- estado systemd gateway/dispatcher/worker.

## 15. Decisiones diferidas que no bloquean el plan

1. Si el catálogo OAuth no expone Sol, David debe elegir entre esperar acceso o aceptar temporalmente 5.5 para `main`; el plan no toma esa decisión por él.
2. Confirmar si existe un workflow n8n vivo que dependa de Kimi. El documento de intención y una env activa no prueban uso productivo.
3. Elegir estrategia de embeddings y Realtime fuera de OAuth; ambos requieren un contrato distinto al de agent turns.

`MIGRATION_PLAN_READY | openclaw=oauth_discriminated | worker=needs_contract_change | gemini=removed | s8=magnific_only`
