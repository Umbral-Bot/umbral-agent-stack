---
fuente: Codex (clone coordinador umbral-agent-stack)
prompt_origen: Prompt 4 (docs/plans/sys-diag-capture-prompts-2026-07-17.md)
fecha_captura: 2026-07-17 (según David; confirmar al pegar)
superficie: ADRs, deuda técnica, NEVER_SHIPPED, ramas/PRs, Foundry/OAuth
modo: read-only
estado_completitud: COMPLETE (ingerido verbatim por orquestador Cursor desde transcript de-9d13c3, linea 4342)
redacciones_por_ingesta: 0
---

## Salida final de la IA (verbatim)

Auditoría hecha en modo estrictamente read-only.

Snapshot: `origin/main = e90852196b6637dccf45d8718faeab08ffecabbc`, idéntico a GitHub al 2026-07-17 12:17 CLT. No hice `fetch`, checkout, cambios de refs ni ediciones. El working tree preexistente quedó sin cambios.

Aclaraciones:

- Hay **263** refs remotas no mergeadas contra `origin/main`, no ~239.
- Hay **2 PRs abiertos**, no 1: [#541](https://github.com/Umbral-Bot/umbral-agent-stack/pull/541) y [#521](https://github.com/Umbral-Bot/umbral-agent-stack/pull/521).
- Toda referencia `path:línea` siguiente corresponde a `e908521`.

## 1. ADRs

Hay colisiones de numeración: dos ADR-009, dos ADR-010 y dos ADR-011.

| Número | Decisión | ¿El código actual la respeta? | Etiqueta |
|---|---|---|---|
| 001 | Rick/OpenClaw vive en VPS; ejecución VM cuando corresponde. `docs/adr/ADR-001-rick-location.md:12-15` | Sí en lo esencial: gateway systemd en VPS y routing VPS/VM. `openclaw/systemd/openclaw-gateway.service.template:7-18`; `dispatcher/service.py:671-685` | `ACTIVE_HEALTHY` |
| 002 | Notion declarativo + Redis transaccional. `ADR-002:13-22` | Sí: Redis mantiene pending/blocked/state y el Dispatcher refleja estados en Notion. `dispatcher/queue.py:27-37`; `dispatcher/service.py:646-660` | `ACTIVE_HEALTHY` |
| 003 | Niveles Normal/Partial/Limited/Minimal; health 60 s y 3 fallos. `ADR-003:9-30` | Parcial. Enum y bloqueo/requeue existen, pero el servicio usa 10 s/2 fallos y solo transiciona Normal↔Partial; Limited/Minimal no tienen activador. `dispatcher/health.py:20-25,128-149`; `dispatcher/service.py:835-845` | `DRIFT_REPO_VPS` |
| 004 | Auto/Review/Approval; sobre `restrict` requiere aprobación humana. `ADR-004:16-25` | No: `auto_approve_quota: true` permite continuar sobre cuota; contradice incluso el comentario “false default”. `config/quota_policy.yaml:3-6`; `dispatcher/model_router.py:257-280` | `DRIFT_REPO_VPS` |
| 005 | Ghost v1, LinkedIn personal HITL, X manual. `ADR-005:13-34` | Superada por Azure Blob/Function, LinkedIn empresa y update de X automático. `ADR-010-azure-editorial-blog-cms.md:31-49`; `ADR-009-linkedin-company-api.md:16-39`; `ADR-008:7` | `OBSOLETE` |
| 006 | Vertex/Freepik como capa visual primaria. `ADR-006:21-45` | La propia ADR declara ese proveedor superado por Magnific, pero Stage 8 aún llama Google Image directo. `ADR-006:7-11`; `scripts/discovery/stage8_image_generator.py:292-304` | `OBSOLETE` |
| 007 | Notion/Publicaciones como hub editorial y gates exclusivos de David. `ADR-007:13-22,42-47` | Sí en estructura y fail-closed: el handler exige autorización y gate visual. `worker/tasks/editorial_publish.py:5-18` | `ACTIVE_HEALTHY` |
| 008 | Agent Stack core, n8n bordes, Make solo lab/stand-by. `ADR-008:17-19,32-58` | Parcial: no hay workflows n8n versionados y el instalador todavía agenda SIM→Make tres veces al día. `scripts/vps/install-cron.sh:13,70-75` | `DRIFT_REPO_VPS` |
| 009-A | LinkedIn Company Page mediante `/rest/posts`, organización y Telegram final. `ADR-009-linkedin-company-api.md:16-39` | No: no existe `editorial.publish.linkedin_org`; Stage 9c sigue usando `/v2/ugcPosts` y `urn:li:person`. `scripts/discovery/stage9c_linkedin_publish.py:1-20,51-58` | `DRIFT_REPO_VPS` |
| 009-B | Mission Control FastAPI/HTMX read-only en `:8089`. `ADR-009-mission-control-scope.md:24-54` | Mayormente implementado y con unit systemd, pero D6 sigue pendiente: README dice que el middleware `mc:views:*` “se agregará”. Tampoco se autodeploya. `infra/systemd/mission-control.service.template:17-27`; `mission_control/README.md:119-130` | `DRIFT_REPO_VPS` |
| 010-A | Azure Blob + Function como CMS editorial. `ADR-010-azure-editorial-blog-cms.md:31-49` | Código e infra existen, pero los tasks `web.publish/unpublish` no tienen caller de runtime versionado. `worker/tasks/editorial_publish.py:1-21`; `worker/tasks/__init__.py:286-287` | `DRIFT_REPO_VPS` |
| 010-B | Cursor Notion per-page en Redis. `ADR-010-notion-poller-cursor-checkpoint.md:34-48` | Sí, incluyendo TTL, bootstrap, invalidación y métricas. `worker/notion_client.py:508-575,624-707` | `ACTIVE_HEALTHY` |
| 011-A | Criterios duros Agent Stack/n8n/Make. `ADR-011-orquestacion-editorial-criterios-duros.md:27-39` | Misma desviación que ADR-008: n8n sin carga versionada y Make todavía programado por cron. | `DRIFT_REPO_VPS` |
| 011-B | PIT como protocolo hermano de D3, estado en pit-vault. `ADR-011-pit-product-tournament-scope.md:17-38` | PIT y vault existen, pero la ADR sigue Draft y el corte duro de presupuesto continúa como stub. `scripts/pit/pit_tournament_run.py:2-35`; `scripts/pit/pit_runner_core.py:72-80` | `DRIFT_REPO_VPS` |
| 012 | Reemplazar `task_type=testing` por `general`. `ADR-012:49-53` | Sí. `scripts/test_s2_dispatcher.py:40-46`; `worker/models/__init__.py:52-59` | `ACTIVE_HEALTHY` |
| 013 | Stage gate codegen Hostinger. | No contiene una decisión: se declara placeholder y bloqueada por fuente inaccesible. `ADR-013-codegen-backend-stage-gate.md:6-31` | `OBSOLETE` |
| Sin número | Tournament wrapper sobre primitivas OpenClaw, sin reimplementar spawn. `tournament-on-openclaw-primitives.md:12-18` | Sí: skill y runners D3 versionados; la ruta Python paralela no es el camino principal. `openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/SKILL.md`; `scripts/vps/d3.1-tournament-run.sh:6-8` | `ACTIVE_HEALTHY` |

## 2. Deuda técnica relevante

El grep literal no encontró TODO/FIXME/HACK reales en código activo; la deuda está expresada como flags default-off, stubs, ADRs incompletas y paths sin caller.

Esfuerzo: S = pequeño, M = varios archivos/tests, L = cambio transversal/runtime.

| Área | Deuda/evidencia | Riesgo real | Esfuerzo |
|---|---|---|---|
| Dispatcher | `auto_approve_quota: true`. `config/quota_policy.yaml:3-6` | El sistema puede consumir sobre `restrict` sin el gate de David. Alto: gasto/cuota y contradicción contractual. | S |
| Dispatcher/Granola | Clasificación V2 apagada por defecto después de haber escrito `?/?/?`. `dispatcher/notion_poller.py:145-170,677-684` | Seguro contra corrupción, pero la capitalización automática queda detenida hasta proveedor+gate+deploy válido. | M |
| Worker/OAuth | OpenAI/Codex se enruta solo a Azure o `OPENAI_API_KEY`; gateway OAuth no se selecciona. `worker/tasks/llm.py:170-227` | La migración OAuth no puede completarse y retirar Foundry rompería `llm.generate`. | L |
| PIT | Kill switch de presupuesto declara `enforced: false`. `scripts/pit/pit_runner_core.py:72-80`; `pit_tournament_run.py:34-35` | Un torneo real puede superar el techo económico antes de detenerse. | M |
| PIT | Entrega Notion es un stub que deja `notion_page_url=null`. `scripts/pit/pit_deliver_telegram_pack.py:35-37,236-239,448` | Entregas quedan fuera del hub humano/trazabilidad esperada. | M |
| Editorial visual | Stage 8 sigue usando Google directo y carece de multipart >20 MB. `stage8_image_generator.py:297-304,367-372` | Viola Magnific-only; puede fallar por credenciales/política y por assets grandes. | M |
| LinkedIn | Publisher real usa contrato personal legacy `/v2/ugcPosts`. `stage9c_linkedin_publish.py:1-20,51-58` | Si se activa, puede publicar bajo identidad/API equivocada respecto de la decisión Company Page. | M/L |
| Rick mention | Handler v0 reconoce únicamente `/health`. `worker/tasks/rick_orchestrator.py:1-14,34-58` | Las menciones libres reciben “no implementado” aunque la documentación describa un orquestador más capaz. | M |
| Mission Control | D6 carece de middleware de vistas; `/evals` depende de un reporte que ningún cron/CI genera. `mission_control/README.md:112,119-130`; `mission_control/routes/evals.py:12-14` | No se puede aplicar el quality gate ni confiar en la pantalla de evals. | S |
| `copilot_agent` | Autoaprueba toda solicitud de herramientas; errores de shutdown se silencian. `copilot_agent/agent.py:130-133,169-181` | Si se activa como daemon sin endurecimiento, aumenta el blast radius y reduce observabilidad. | S/M |

## 3. Handlers/features sin activación versionada

Criterio: exact-string `git grep` en `e908521`, excluyendo docs/tests/.agents y la propia definición. Esto prueba ausencia de caller **en el repo**, no ausencia absoluta en un VPS/config externo.

| Superficie | Evidencia | Diagnóstico |
|---|---|---|
| Tasks Granola `capitalize_raw`, `create_human_task_from_curated_session`, `update_commercial_project_from_curated_session`, `promote_curated_session`, `capitalize_task_from_raw` | Registrados en `worker/tasks/__init__.py:229-237`; cada nombre tiene solo definición+registry | `NEVER_SHIPPED` como endpoints; parte de la lógica puede usarse internamente |
| `github.orchestrate_tournament` | Registry `worker/tasks/__init__.py:274`; cero caller runtime | `NEVER_SHIPPED`; D3 terminó usando primitivas OpenClaw |
| Tasks Worker `pit.preflight`, `pit.lane_init`, `pit.iteration_close`, `pit.lane_announce` | `worker/tasks/__init__.py:280-283`; los runners llaman `pit_runner_core` directamente | `NEVER_SHIPPED` como API Worker |
| `web.publish_editorial_post` / `web.unpublish_editorial_post` | `worker/tasks/__init__.py:286-287`; cero caller runtime | `NEVER_SHIPPED`; backend construido pero no conectado |
| LinkedIn organización | ADR pide `editorial.publish.linkedin_org`, pero no existe en registry; solo publisher personal legacy | `NEVER_SHIPPED` |
| `copilot_agent` como servicio | Solo ejecución manual `python -m copilot_agent`; `pyproject.toml:69-70` lo empaqueta, sin service/cron/config | `NEVER_SHIPPED` como componente operativo |
| Core eval harness automático | `infra/eval_harness.py:368-402`; no aparece en `.github/workflows` ni crons | `NEVER_SHIPPED` como evaluación recurrente |
| Gpt-Rick Foundry | Docs prometen delegación, pero no hay handler y el único smoke documentado devuelve 403. `docs/43-gpt-rick-agent-azure-foundry.md:4,48-54` | `NEVER_SHIPPED` |
| n8n como borde productivo | ADR-011 reconoce 0 workflows; el árbol actual no contiene exports de workflows | `NEVER_SHIPPED` en configuración versionada; VPS actual no verificado |
| `copilot_cli.run` | Existe y está expuesto, pero `RICK_COPILOT_CLI_ENABLED=false`. `.env.example:216-225`; `config/tool_policy.yaml:37` | `NEVER_SHIPPED` por configuración versionada; pudo habilitarse externamente |

## 4. PRs y ramas

Resultado del cruce:

- `git branch -r --no-merged origin/main`: **263**.
- PRs abiertos: [#541](https://github.com/Umbral-Bot/umbral-agent-stack/pull/541) y [#521](https://github.com/Umbral-Bot/umbral-agent-stack/pull/521).
- En ramas squash-mergeadas, `git cherry` puede seguir mostrando `+`; el PR `MERGED` y el contenido presente en main son la evidencia para `MERGED_REMOTE_ONLY`.

| Rama remota | Contenido | ¿Ya llegó a main? | Etiqueta | Recomendación |
|---|---|---:|---|---|
| `claude/plan-sys-diag-openclaw-worksystem-2026-07-17` | Plan/inventario sys-diag, 653 líneas; tip `8dd4346` | No; PR #541 abierto | `ACTIVE` | `KEEP` |
| `claude/fix-p2a-poller-v2-isolation` | Gate V2 default-off; tip `74a9c22` | Sí, PR #540 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/fix-cap-p1-canonical-identity-safe-update` | Identidad Granola/update seguro; `e7c7066` | Sí, PR #539 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/feat-cap-p1-task-from-raw` | Task raw→Tarea; `d90ba46` | Sí, PR #538 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/feat-cap-p0-verify-append` | Trazabilidad append+verify; `1b013c0` | Sí, PR #537 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/plan-granola-capitalization-hybrid` | Plan híbrido Granola; `a18d5f5` | Sí por squash, PR #536 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/p11b-closeout-audit` | Cierre catch-up Drive; `6153aee` | Sí, PR #535 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/fix-replace-blocks-large-pages` | Fix páginas Notion grandes; `0c7680a` | Sí, PR #534 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/p11b-granola-drive-catchup-sender` | Sender batch Drive; `efd9301` | Sí, PR #533 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/p11b-granola-drive-catchup` | Drive→Notion catch-up; `4adad68` | Sí, PR #532 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/granola-mcp-free-capture` | Capture feeder MCP Basic; `949a853` | Sí, PR #531 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `claude/fix-granola-p1-1-observability` | Freshness/exit-code; `2a939ac` | Sí, PR #530 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `fable/hygiene-h0-h1-close-20260713` | Cierre higiene; `284c299` | Sí, PR #527 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `rescue/coordinador-dirty-2026-07-13` | Contrato human-review + export VS Code; `16219f2` | No; PR #529 cerrado sin merge | `ACTIVE` — respaldo explícito | `KEEP` |
| `rescue/copilot-dirty-2026-07-13` | Quota policy + audit Foundry; `003bafc` | No; PR #528 cerrado sin merge | `ACTIVE` — respaldo explícito | `KEEP` |
| `fable/repo-hygiene-plan-20260713` | Plan higiene repos/clones; `fb533c1` | Sí, PR #526 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `codex/audit-openclaw-foundry-oauth-migration-20260713` | Auditoría OAuth; `9cc200a` | Sí, PR #525 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `codex/docs-mpd2-closeout-b0004` | Cierre MP-D2; `0da5756` | Sí, PR #524 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `codex/p3-editorial-sanitize-b0004` | Gates editoriales/saneamiento; `53a3e40` | Sí por squash, PR #523 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `copilot/fix-pit-dev-quality-gates-20260704` | Billing truth/QA/fulfillment PIT; `3a70689` | Sí, PR #522 | `MERGED_REMOTE_ONLY` | `DELETE_CANDIDATE` |
| `copilot/docs-openclaw-models-hygiene-20260704` *(21.ª; incluida por PR #521)* | Higiene Azure-only per-agent; `7abfaa6` | No; PR abierto y CLEAN | `STALE`: predica Azure-only previo al plan OAuth | `ARCHIVE` o actualizar antes de merge |

Los comentarios de #528/#529 dicen explícitamente que esas dos ramas rescue deben mantenerse como respaldo; no son candidatas a borrado.

## 5. Foundry/OAuth

### Veredicto

**No: el Worker hoy no puede heredar el OAuth OpenAI/Codex del gateway.**

Compartir `~/.config/openclaw/env` no comparte OAuth. OpenClaw guarda los perfiles por agente en `auth-profiles.json`, no en env: `openclaw/workspace-templates/skills/openclaw-gateway/SKILL.md:721-737`.

| Superficie | Estado actual | Qué falta |
|---|---|---|
| Gateway OpenClaw | Tiene soporte de OAuth y ruta `/v1/chat/completions`. La unit carga `~/.config/openclaw/env`. | Login/profile OAuth usable y config sin provider Azure custom; el plan de julio no prueba que APPLY se haya ejecutado. |
| Dispatcher | Providers conocidos: `azure_foundry`, `openclaw_proxy` y Gemini/Claude. `dispatcher/model_router.py:25-35,60-69` | Provider lógico `openclaw_oauth`, modelos explícitos por task type y retiro de defaults Foundry/Gemini. |
| Worker `llm.generate` | Para GPT/Codex exige `AZURE_OPENAI_*` o `OPENAI_API_KEY`. Solo Claude selecciona `openclaw_proxy`. `worker/tasks/llm.py:170-227` | Seleccionar gateway para `openai/*`; reutilizar `_call_openclaw_proxy`; nunca leer/copiar el auth store. |
| `.env.example` | Sigue declarando Foundry como “prioridad máxima” y deployment `gpt-5.3-codex`. `.env.example:54-61` | Marcar Foundry legacy/retirado tras cutover; documentar solo gateway token para texto Worker. |
| Docs 42 | Foundry+API key y model `gpt-5.2-chat`. `docs/42...:31-42,109-130` | Declararla histórica o limitarla a audio/gaps que continúen usando Azure. |
| Docs 43 | Gpt-Rick publicado, pero 403 por permisos y sin handler. `docs/43...:48-54` | Permiso/cliente real o retirar la promesa operativa. |
| Audio/RAG | `azure.audio.generate` y embeddings dependen de Azure key. | OAuth de agent turns no cubre Realtime ni embeddings; requieren decisión separada. |

La especificación de cambios ya existe en `docs/audits/editorial-worker-oauth-migration-options-2026-07-13.md:32-49`. El propio documento figura como “diseño; sin implementación runtime” en líneas 3-5.

## 6. Contradicciones docs ↔ código

| Contradicción | Evidencia |
|---|---|
| ADR-004 exige aprobación; config autoaprueba | `ADR-004:21-25` vs `config/quota_policy.yaml:3-6` |
| ADR-003 dice 60 s/3 fallos; wiring usa 10 s/2 | `ADR-003:21-25` vs `dispatcher/service.py:835-841` |
| Ghost/personal/manual vs Azure/company/X auto | `ADR-005:15-34`; `ADR-010-azure...:31-49`; `ADR-009-linkedin...:16-39`; `ADR-008:7` |
| Worker editorial dice “LinkedIn/X nunca autopublished”, mientras ADR-009 pide Company auto y Stage9c autopublica personal | `worker/tasks/editorial_publish.py:20-21`; `stage9c_linkedin_publish.py:1-20` |
| ADR-006 presenta Vertex/Freepik como decisión aunque su update la declara superada; código conserva Google directo | `ADR-006:7-11,21-45`; `stage8_image_generator.py:297-304` |
| Mission Control D6 aparece aceptado, pero README dice que el contador se agregará después | `ADR-009-mission-control:91-97`; `mission_control/README.md:119-124` |
| Gpt-Rick se anuncia delegable pero el único estado documentado es 403 y no hay handler | `docs/43...:4,48-54`; ausencia en `worker/tasks/__init__.py` |
| ADR-013 está en `docs/adr/` sin decisión | `ADR-013:7,21-31` |
| Numeración ADR no es única | Dos 009, dos 010 y dos 011 en `docs/adr/` |
| Docs/modelos Foundry no coinciden entre sí | Doc 42 usa 5.2; `.env.example` 5.3; código/quotas 5.4. `docs/42...:35-39`; `.env.example:58-61`; `worker/tasks/llm.py:64-71` |

## Top 10 por impacto × facilidad

| # | Hallazgo | Impacto / facilidad | Recomendación |
|---:|---|---|---|
| 1 | Gate de cuota desactivado por `auto_approve_quota: true` | Alto / fácil | `FIX` |
| 2 | Worker no puede usar OAuth del gateway; sigue atado a Foundry/API key | Crítico / difícil | `IMPLEMENT` |
| 3 | Publisher LinkedIn activo apunta a perfil personal y API legacy, no empresa | Alto / fácil de contener | `DISABLE` |
| 4 | Stage 8 contradice Magnific-only y llama Google directo | Alto / fácil de contener | `DISABLE` |
| 5 | Granola V2 está correctamente apagado, pero el trabajo automático queda detenido | Alto / medio | `IMPLEMENT` solo con provider vivo, gate humano y smoke |
| 6 | PIT real no aplica corte duro de presupuesto | Alto / medio | `DISABLE` runs reales hasta enforcement |
| 7 | ADRs duplicadas/obsoletas hacen imposible saber qué contrato manda | Medio-alto / fácil | `FIX` |
| 8 | Mission Control no puede medir D6 y `/evals` no recibe reportes recurrentes | Medio / fácil | `FIX` |
| 9 | 16 de las 20 ramas recientes ya están en main por PR squash | Medio / fácil | `DELETE` candidatas tras última confirmación |
| 10 | Ramas rescue #528/#529 contienen material deliberadamente no mergeado | Alto ante borrado accidental / trivial | `KEEP` |

No se ejecutaron tests porque la tarea fue arqueología read-only; tampoco se modificaron archivos, refs, PRs ni ramas.
