# Inventario draft — diagnóstico total OpenClaw/Umbral × work system (2026-07-17)

Estado: **DRAFT** — evidencia propia VPS+repo completa; queda abierto hasta integrar las respuestas multi-IA (ver `docs/plans/sys-diag-capture-prompts-2026-07-17.md`).
Gate: `SYS_DIAG_CAPTURE_READY` (este doc + prompts listos).
Método: captura read-only por SSH (`vps-umbral`, srv1431451, user rick, 2026-07-17 ~14:00-14:45 UTC) + lectura de `C:\GitHub\umbral-agent-stack` (main @ e9085219) + `C:\GitHub\notion-governance`. **Nada fue modificado, reiniciado ni deployado.** Etiquetas de evidencia: `[VPS]` observado por SSH, `[repo]` inferido de código/docs, `[gov]` contrato notion-governance.

## 1. Resumen ejecutivo

1. **El núcleo del stack está sano** `[VPS]`: gateway OpenClaw 2026.6.10 (uptime 4d, auth token, loopback), worker v0.4.0 con 118 tasks, dispatcher, mission-control, poller (PID 3016854, V2 classify OFF confirmado — flag ausente en el env del proceso), Redis docker, repo desplegado limpio en main @ e908521.
2. **SIM Daily Report identificado**: artefacto del hackathon 2026-03-04 (Codex, task 010). Dos crons 3×/día; la mitad LLM falla al 100% desde que el Worker no tiene `GOOGLE_API_KEY`; keywords fosilizadas de marzo; nadie consume el output. Veredicto **ACTIVE_NOISY → DISABLE** (§3).
3. **Triage v0 @Rick documentado**: **ACTIVE_DEGRADED** — responde, pero postea JSON de telemetría interna en Control Room (viola regla 3 de gobernanza) y tiene un gap anti-loop conocido (§4).
4. **Causa raíz transversal**: Worker sin proveedor LLM vivo mata `llm.generate`, `composite.research`, resumen SIM, smart replies question/task y 4 checks del E2E — mientras `research.web` sí funciona vía `azure_foundry` `[VPS]`. Un solo fix (decisión P2b: ruta Rick+Luna, no restaurar GOOGLE_API_KEY) destraba todo o justifica apagar los consumidores.
5. **Dos crons nunca corrieron ni una vez** `[VPS]`: dashboard-rick (hourly) y openclaw-panel (cada 6h) fallan con `Permission denied` desde su instalación (script sin `+x` y cron sin prefijo `bash`). **NEVER_SHIPPED** con fix trivial.
6. **Drift masivo de skills** `[VPS]`: workspace vivo 42 skills vs 86 en template; 19 stale; 47 nunca deployadas; 3 viven SOLO en producción sin versionar (incl. **umbral-worker**, central al stack); la skill `windows` fue editada en producción y un re-sync ciego la pisaría. AGENTS/TOOLS/SOUL del workspace también stale.
7. **n8n SÍ está corriendo** `[VPS]` (systemd user, desde 2026-06-23) pero el repo tiene **cero** workflows exportados — lo que corra ahí es irrecuperable desde git. UNKNOWN qué hace → prompt 10 pasa a ser necesario.
8. **Sorpresas de superficie**: `tailscale serve` publica el gateway en el tailnet mientras OpenClaw reporta exposición OFF; 6 procesos `codex app-server` acumulados (~1GB RAM); rsshub docker sin consumidor conocido; log del poller de 101MB sin rotación y con handler duplicado.
9. **Gobernanza**: contrato V2 claro (runtime-bridge v2.0), pero el working tree de notion-governance está DIRTY en rama de trabajo y los cambios de contrato más recientes (actor notion_poller, QW-2) existen solo sin commitear. Política formal de créditos Notion AI: no existe como policy (gap).
10. **Cementerio identificado**: improvement supervisor (docs/70-77) NEVER_SHIPPED; copilot_agent + mcp_server ORPHAN; Linear congelado desde marzo; Make/PAD restos de S5-S7; sim-to-make falla 3×/día hace 24+ días por env ausente.
11. **Reconciliación del reply de Rick resuelta** `[VPS]`+`[repo]`: `tasks_in_memory=445` y "118 tasks" NO se contradicen — son métricas distintas del mismo `/health` (445 = registros de ejecuciones recientes en memoria en ese momento; 118 = handlers registrados). Ver §4-bis.
12. **Deuda git masiva** `[local]`: 30+ clones/worktrees Umbral en `C:\GitHub`, **239 ramas remotas sin merge** en umbral-agent-stack con **1 solo PR abierto** (#521, stale desde 04-jul), 2 clones DIRTY_HIGH_RISK (codex-coordinador: dirty + 200 detrás de main; notion-governance-cursor: 12 tracked + 130 untracked sin upstream) y ~10 residuos `.tmp-*` de auditorías/deploys previos. Ver §S14. Mapeo clone↔hilo: `[UI_EVIDENCE_PENDING]`.

## 2. Inventario por superficie

### S1 — Gateway OpenClaw `[VPS]`
| Ítem | Etiqueta | Evidencia/Detalle | Rec |
|---|---|---|---|
| openclaw-gateway.service | ACTIVE_HEALTHY | v2026.6.10, PID 2526932, uptime ~4d, /health 200, loopback 18789, auth token | KEEP |
| Telegram (único canal) | ACTIVE_HEALTHY | allowlist DM+grupos = solo 1813248373 (David) | KEEP |
| 8 agentes / routing modelos | ACTIVE_HEALTHY | todo OpenAI vía OAuth codex (quota 85% restante); fallbacks definidos; 7/8 activos <1h | KEEP |
| rick-linkedin-writer | OBSOLETE | 1 sesión histórica, inactivo 18d | DEFER (David confirma; si no, DISABLE) |
| Credenciales anthropic/google/vertex en auth store | ORPHAN | definidas y sin ningún modelo que las use; `models status` imprime fragmentos parciales de tokens (higiene) | DEFER (retirar/rotar si solo-OpenAI es permanente) |
| `tailscale serve` → gateway en tailnet | DRIFT_REPO_VPS | status dice "exposure off" pero serve activo publica :18789 en tailnet (privado, 3 nodos; token auth sigue aplicando) | FIX (David decide: documentar o apagar serve) |
| plugins.load.paths warning | ACTIVE_NOISY | warning en cada comando CLI, sin impacto funcional | FIX en ventana (doctor --fix) |
| Versión vs npm | COST_RISK | 2026.6.10 instalada vs 2026.7.1 disponible | DEFER (upgrade con smoke) |
| 6× codex app-server acumulados | ACTIVE_NOISY / COST_RISK | ~1GB RSS total; 4 pares desde Jul-13; mapeo a sesiones vivas UNKNOWN | FIX (auditar y reciclar en restart planificado) |
| "Bootstrap file ABSENT" ×8 agentes | UNKNOWN | reportado por status; implicación no confirmada | DEFER (verificar con doc oficial) |

### S2 — Workspace/skills drift `[VPS]`
| Ítem | Etiqueta | Detalle | Rec |
|---|---|---|---|
| Conteo global | DRIFT_REPO_VPS | live 42 skills vs template 86; ~20 idénticas, 19 difieren, 3 solo-live, 47 solo-template | FIX (definir política de sync o lista selectiva documentada) |
| AGENTS.md / TOOLS.md / SOUL.md live | DRIFT_REPO_VPS | los 3 stale vs template (template más nuevo); HEARTBEAT sincronizado | FIX (re-deploy con revisión de delta) |
| 19 skills stale en live | DRIFT_REPO_VPS | muestreo: 6/7 template-más-nuevo (agent-handoff-governance 823 líneas de diff) | FIX (re-sync tras revisar `windows`) |
| Skill `windows` | DRIFT_REPO_VPS (inverso) | editada EN producción después del último sync (366 líneas); un re-sync ciego la pisa | FIX (capitalizar al repo ANTES de cualquier sync) |
| Skill `umbral-worker` (solo-live) | ORPHAN | puente a la Worker API, central al stack, sin versionar | FIX (capitalizar al repo — prioritario) |
| `granola-meeting-capitalization` (solo-live) vs `granola-pipeline` (solo-template) | DUPLICATE / ORPHAN | par nunca reconciliado; coincide con pendiente P3 del plan híbrido | FIX (decidir canónica bajo plan híbrido) |
| `google-agenda-readiness` (solo-live) | ORPHAN | gate de readiness agenda Google, sin versionar | FIX o DELETE tras confirmación |
| 47 skills solo-template | NEVER_SHIPPED | BIM/AEC, Power Platform, media, integraciones; el agente vivo no las tiene | DEFER (triage explícito: deployar las útiles, resto = biblioteca) |
| desktop.ini ×6 + dir auto-anidado | OBSOLETE | residuo de copia manual Windows→VPS | DELETE en mantenimiento |

### S3 — Crons, daemons, watchdogs `[VPS]`
| Cron/daemon | Etiqueta | Detalle | Rec |
|---|---|---|---|
| supervisor.sh */5 | ACTIVE_HEALTHY | Redis/Worker/Dispatcher OK, sin restarts; log 1.4MB sin rotación | KEEP (+rotación) |
| health-check.sh */30 | ACTIVE_HEALTHY | verde; PERO reporta dispatcher como process_only cuando la unit systemd existe | KEEP + FIX detección |
| notion-poller-cron */5 (watchdog) | ACTIVE_HEALTHY | 2 relanzamientos en 24 días (el de hoy = deploy P2a) | KEEP |
| scheduled-tasks * * * * * | ACTIVE_HEALTHY | 5429 líneas "blocked" históricas sin timestamp; hoy corre (repo en main) | KEEP + timestamp en log |
| quota-guard */15 | ACTIVE_HEALTHY | corriendo sin errores | KEEP |
| daily-digest 22:00 | ACTIVE_HEALTHY | exit 0, comentario Notion OK | KEEP |
| notion-curate 05:20 | ACTIVE_HEALTHY | contadores en 0, estable | KEEP |
| granola-gap-check 08:00 | ACTIVE_HEALTHY | funciona; reporta 2 issues de datos reales (missing_granola_document_id) | KEEP + resolver los 2 issues |
| openclaw-runtime-snapshot 20 */6 | ACTIVE_HEALTHY | artefactos regenerados hoy 06:20 | KEEP |
| e2e-validation 06:00 | ACTIVE_DEGRADED | 11/15 PASS, 4 FAIL (llm.generate, composite.research, R8 coding/research), 5 SKIP por env | FIX vía P2b o recortar suite |
| ooda-report lunes 07:00 | ACTIVE_DEGRADED | saltó el 13-jul (repo no estaba en main); próximo lunes debería correr | KEEP + verificar 20-jul |
| sim-daily 8,14,20 | ACTIVE_NOISY | ver §3 | DISABLE |
| sim-report 8:30,14:30,20:30 | ACTIVE_NOISY | ver §3 | DISABLE |
| sim-to-make 9,15,21 | OBSOLETE / NEVER_SHIPPED | falla idéntico 3×/día ≥24 días: `MAKE_WEBHOOK_SIM_URL not set` | DISABLE (comentar línea) |
| dashboard-rick hourly | NEVER_SHIPPED | JAMÁS corrió: script sin +x y cron sin `bash` → Permission denied cada hora | FIX trivial (chmod +x) |
| openclaw-panel 0 */6 | NEVER_SHIPPED | mismo bug; 4 fallos silenciosos/día desde instalación | FIX trivial |
| discovery-publish (comentado) | OBSOLETE | pausado "B1-paused 2026-05-24", 8 semanas sin dueño | DEFER 30 días → DELETE línea |
| n8n.service (systemd user) | ACTIVE_HEALTHY / UNKNOWN | corre desde 2026-06-23 (npm nativo); workflows internos NO auditados; repo tiene 0 workflows exportados | KEEP provisional + auditar (prompt 10) + exportar workflows al repo |
| rsshub (docker) | UNKNOWN | up 3 semanas en :1200; ningún consumidor identificado | verificar consumidor; si nadie → DISABLE |
| redis.service not-found | OBSOLETE | referencia muerta; el runtime real es docker umbral-redis | limpiar referencia |
| Recursos host | ACTIVE_HEALTHY | disco 38%, load 0.73, RAM 5GB libres, uptime 24d | KEEP |

### S4 — Worker FastAPI `[VPS]`
118 tasks registradas: notion 15, windows 12, linear 11, granola 9, gui 7, browser 6, client 6, n8n 5, figma 5, github 5, tournament_lane 5, google 4, rag 4, pit 4, document 3, system 2, google_drive 2, gmail 2, web 2, +1 c/u (ping, research, llm, composite, make, azure, tournament, copilot_cli, rick).

| Ítem | Etiqueta | Detalle | Rec |
|---|---|---|---|
| Worker /health + supervisión | ACTIVE_HEALTHY | v0.4.0, PID 2972295, loopback 8088; 18791 NO escucha (no es puerto vigente) | KEEP + documentar 18791 |
| `llm.generate` | ACTIVE_DEGRADED | 100% FAIL: default `gemini-2.5-pro` exige exactamente `GOOGLE_API_KEY` (llm.py:279); rutas Claude (UMBRAL_DISABLE_CLAUDE) y OpenAI/Azure también muertas en Worker; arrastra composite.research | FIX vía decisión P2b (ruta Rick+Luna) o apagar consumidores |
| `research.web` | ACTIVE_HEALTHY | corre vía `azure_foundry` según ops_log (resuelve el UNKNOWN del repo: no es Gemini-NANO/Tavily hoy) | KEEP |
| `notion.add_comment` (caller 06:00) | ACTIVE_DEGRADED | Notion 400: comentario de 2161 chars > límite 2000; el contenido se pierde; sim-report sí chunkea — el bug es de otro caller | FIX (chunkear ≤2000) |
| familia granola.* | ACTIVE_HEALTHY | P1 `capitalize_task_from_raw` ejecutada hoy dry-run y real, sin fallos | KEEP |
| ops_log central | ACTIVE_HEALTHY / ACTIVE_NOISY | ~/.config/umbral/ops_log.jsonl, 85k líneas; poller domina 84% de eventos recientes | KEEP + rotar (script existe) |
| Env Worker/gateway (solo nombres) | ACTIVE_HEALTHY | PRESENTES: NOTION_API_KEY+~15 NOTION_*_ID, LINEAR_API_KEY, REDIS_URL, WORKER_URL, GITHUB_TOKEN, TAVILY, HOSTINGER, X_*. AUSENTES: GOOGLE_API_KEY, ANTHROPIC, OPENAI, NOTION_POLLER_ENABLE_V2_CLASSIFY. AZURE/KIMI comentados | KEEP (coincide con gobernanza) |

### S5 — Poller / Control Room / triage `[VPS]`+`[repo]` → detalle en §4
| Ítem | Etiqueta | Detalle | Rec |
|---|---|---|---|
| Daemon poller | ACTIVE_HEALTHY | PID 3016854 desde 09:35 (post-deploy P2a), ciclo ~60s, dedup OK, V2 flag ausente en env del proceso = OFF | KEEP |
| Log poller /tmp | ACTIVE_NOISY | 101MB sin rotación + cada línea DUPLICADA (doble handler) + httpx INFO | FIX (rotación, handler, log level) |
| Cursors Redis | ACTIVE_HEALTHY | last_ts, 12× notion:poll:cursor:* (TTL 30d — pueden ser resabios de alcance previo), processed_comment TTL 24h; 0 claves granola/sim | KEEP + verificar alcance real de scan |
| Runbook poller (cabecera) | DRIFT_REPO_VPS | dice "poller PAUSADO, P2a NO desplegado" cuando la realidad es deployado+reactivado | FIX (actualizar cabecera) |
| Fan-out review targets | COST_RISK | hasta ~70 req/min sostenidos contra Notion API (~3 rps promedio); sin backoff 429 explícito en poller | KEEP con vigilancia |

### S7 — SIM / research / editorial / tournament / PIT / Granola
Ver §3 (SIM). Resto:
| Ítem | Etiqueta | Detalle | Rec |
|---|---|---|---|
| Editorial pipeline | ACTIVE_HEALTHY `[repo]` | superficie más viva: 17 specs, gates endurecidos (PR #523, jul-12), gold set | KEEP; resolver conflicto Azure (abajo) |
| Azure Foundry (provider) | ACTIVE_DEGRADED `[repo]` | conflicto vivo: editorial-model.yaml EXIGE azure-openai-responses/gpt-5.5 mientras la matriz de migración 2026-07-13 lo declara prefijo prohibido-objetivo; y `[VPS]` research.web corre por azure_foundry hoy | FIX (completar migración OAuth o actualizar contrato editorial ANTES de apagar Foundry) |
| Tournament/PIT | ACTIVE_DEGRADED `[repo]` | ejecución real vía PIT; 2 torneos v1 en vault; 3 blockers (roster, per-lane model, budget); docs/69 superseded por docs/79 | FIX blockers; marcar docs/69 superseded |
| mission_control | ACTIVE_HEALTHY `[VPS]` | corre como systemd user (:8089, read-only) — resuelve el UNKNOWN del repo; hospeda juez PIT | KEEP + documentar deploy |
| Improvement supervisor (docs/70-77) | NEVER_SHIPPED `[repo]` | design_only explícito; nada lo carga; 0 commits desde 2026-04-20 | DEFER (retomar Phase 6 o marcar design-archive) |
| evals/ | ACTIVE_HEALTHY `[repo]` | almacén de calibraciones del pipeline editorial | KEEP |

### S10-S12 — Leftovers `[repo]`
| Ítem | Etiqueta | Detalle | Rec |
|---|---|---|---|
| copilot_agent/ (Phase 4) | ORPHAN | sin refs de runtime; 0 commits desde abril | DELETE/attic + pyproject + test |
| mcp_server/ (Phase 3) | ORPHAN | único consumidor = copilot_agent; sin deploy refs | DEFER/DELETE junto a copilot_agent |
| Programa Copilot CLI F1-F8 | ACTIVE_DEGRADED | vive como lane PIT (#483); F8 (ejecución real) nunca activada, gates en false | KEEP task; decidir cierre o archivo del roadmap F8 |
| Azure audio / Gpt-Rick (docs/42-43) | OBSOLETE | Gpt-Rick murió en 403 (marzo); azure_audio task sin toques desde marzo; voz Rick siguió otro camino | DEFER (confirmar uso en VPS; si no, marcar históricos) |
| n8n (código repo) | OBSOLETE `[repo]` / ACTIVE `[VPS]` | cliente+tasks de marzo, env comentado, 0 workflows en repo — PERO la instancia VPS corre | FIX: exportar workflows de la instancia al repo; luego decidir |
| Make / Power Automate | OBSOLETE | docs de marzo; PAD allowlist en tool_policy sin flujos definidos; sim-to-make roto | DELETE refs env template; DEFER limpieza PAD |
| mailbox legacy | OBSOLETE | 0 código; `.agents/mailbox/` NO existe pero un runbook ordena usarlo | FIX runbook (apuntar a .agents/tasks/) |
| .agents/ board | ACTIVE_HEALTHY | en uso (última asignación hace 3d); 280 tasks sin archivar, .bak sueltos | KEEP + higiene menor |
| Linear | OBSOLETE | integración completa congelada desde 2026-03-23; modelo Linear-first desplazado por Notion+board; webhook en VPS UNKNOWN | DISABLE (confirmar webhook sin tráfico; marcar docs/34/67 superseded) |
| Archivos raíz (update.zip, vm_net.tmp, worker_err/out.txt, vps_pub_key.txt) | OBSOLETE | residuos bootstrap feb-mar, ninguno en git | DELETE (fase H higiene) |
| env.rick (raíz, no commiteado) | SECURITY_RISK | env real con 45 claves pobladas, fechado 2026-03-23, gitignored; riesgo local (copias accidentales); hubo incidente de creds en mayo | FIX (mover fuera del repo, verificar rotación, borrar) |
| `C:\Granola\*.log` literales en repo VPS | ORPHAN `[VPS]` | 2 archivos con nombre Windows literal en ~/umbral-agent-stack, sin escrituras desde Jul-4 | DELETE |

### S13 — Sistema de trabajo de David (síntesis `[repo]`+`[gov]`)
- **Ritmos**: los documentados son del stack (crons diario/semanal/mensual, OODA lunes, digest 22:00); los ritmos personales de David NO están en repos → gap que cierran los prompts 1/2/7.
- **Superficies canónicas**: Control Room = SOLO comunicación (SOUL R15); Registro de Tareas 517bfeb9 (única escritura del motor P1); Transcripciones Granola; Proyectos técnicos - Rick d4098fa4 (único writer real del capitalizador — NO Asesorías); Bandeja revisión Rick; board .agents/; Telegram; Drive PIT. DB Entregables ELIMINADA; "Registro de Sesiones" = deleted_legacy (404 esperado); "Esquemas mínimos V1" archivado.
- **Gates humanos**: GO explícito para writes live nuevos, deploys/restarts, keys LLM, fases destructivas H3-H5, merges a main (nunca desde VPS), cuota>restrict, capitalización por click (`Procesar con agente=true`).
- **Orquestación**: Cursor lead, un agente a la vez, coordinación por archivos .agents/, prompts en español pegados por David en tandas, dry-run default + piloto chico, repo=intent / VPS=reality.
- **Créditos**: Notion AI ~300/mes (7 corridas del Transcriptor agotaron saldo una vez); presupuesto ≤20-30 corridas manuales, NUNCA batch/triggers; cuota OAuth Codex = operativa de Rick, prohibida para batch; camino LLM futuro aprobado = Rick+GPT-5.6 Luna vía OAuth, NO restaurar GOOGLE_API_KEY.
- **Gobernanza — gaps detectados** `[gov]`: sin regla literal anti-"acuses vacíos"; sin policy formal de créditos; binding Entregables inline (P2.4) sin fecha; "Mi Perfil" placeholder; "Desarrollos y Cambios de Sistema" NEVER_SHIPPED; y **el working tree está DIRTY** en `claude/feat-notion-capitalizacion-v21-pilot` con el registro del actor notion_poller/QW-2/data_source_id SOLO sin commitear → riesgo de perder el contrato mismo (no tocar hasta P4, que David difirió).

### S14 — Higiene de repos, clones y ramas (`C:\GitHub`) `[local, git/gh read-only, 2026-07-17 ~11:15 ET]`

**Nada fue borrado, stasheado, reseteado ni cerrado.** Sub-taxonomía: ACTIVE | STALE | MERGED_REMOTE_ONLY | ORPHAN_LOCAL | DIRTY_HIGH_RISK | CONFLICT_RISK | UNKNOWN. Correspondencia clone↔hilo inferida del sufijo del nombre; sin pantallazos de hilos Claude Code/Cursor/Codex la correspondencia exacta queda `[UI_EVIDENCE_PENDING]` — no se inventó ninguna.

**Cifras globales umbral-agent-stack** (clone principal): 232 ramas locales (114 no mergeadas a origin/main, 118 mergeadas), **239 ramas remotas no mergeadas**, **1 solo PR abierto** (#521 `copilot/docs-openclaw-models-hygiene-20260704`, sin actividad desde 04-jul → STALE). notion-governance: 2 PRs abiertos stale de mayo (#6 megadiagnóstico, #3 policy force-push — este último documenta un incidente de force-push previo, señal de CONFLICT_RISK cultural).

#### Familia umbral-agent-stack
| Clone | Rama | Estado git | Etiqueta | Propietario probable | Rec |
|---|---|---|---|---|---|
| umbral-agent-stack | claude/plan-sys-diag… (esta rama) | limpio; 1 untracked: `.audit-clones-temp.json` | ACTIVE | Cursor lead / Claude Code | KEEP; el .json es evidencia de auditoría previa no gitignored → COMMIT_SEPARATELY o ARCHIVE |
| umbral-agent-stack-codex-coordinador | codex/editorial-linkedin-smoke-rescue | **8 tracked + 9 untracked dirty; 200 detrás**; último commit 2026-05-30 | **DIRTY_HIGH_RISK** + STALE | hilo Codex coordinador `[UI_EVIDENCE_PENDING]` | DO_NOT_TOUCH → revisar contenido; si hay trabajo real → COMMIT_SEPARATELY; merge a estas alturas = CONFLICT_RISK |
| umbral-agent-stack-copilot | main | 1 tracked + 2 untracked dirty; 6 detrás; último 2026-07-04 | ACTIVE (dirty en main) | Copilot VPS handoffs | COMMIT_SEPARATELY el delta o descartar con revisión; no trabajar dirty sobre main |
| umbral-agent-stack-b0004 | codex/docs-mpd2-closeout-b0004 | limpio, **sin upstream**; último 2026-07-12 | MERGED_REMOTE_ONLY probable (MP-D2 cerrado vía PR #523) | hilo Codex b0004 | verificar y ARCHIVE/DELETE_CANDIDATE si ya está en main |
| umbral-agent-stack-b0004-oauth (worktree) | codex/audit-openclaw-foundry-oauth-migration-20260713 | limpio, sync | MERGED_REMOTE_ONLY probable (matriz migración ya en main) | hilo Codex OAuth | verificar y ARCHIVE |
| umbral-agent-stack-claude | claude/feat-pit-2b-spawn | limpio, **sin upstream**; último 2026-06-10 | ORPHAN_LOCAL / UNKNOWN (¿PIT-2b llegó a main vía #517?) | hilo Claude PIT | verificar; si mergeado → DELETE_CANDIDATE |
| umbral-agent-stack-codex | codex/granola-raw-intake-batch | limpio, sync; último 2026-04-13 | STALE / MERGED_REMOTE_ONLY probable | hilo Codex granola (histórico) | ARCHIVE |
| umbral-agent-stack-antigravity | antigravity/001-rick-recommendations | limpio; último 2026-03-09 | STALE | Antigravity IDE | ARCHIVE / DELETE_CANDIDATE |
| Worktrees Cursor (`~/.cursor/worktrees/umbral-agent-stack/{reo,wah,weo}`) | detached @ bce0754c ×3 | limpios | ORPHAN_LOCAL probable (agentes background Cursor) | Cursor | IGNORE; limpiar con `git worktree prune` en higiene futura |
| `.tmp-gd52-adr-scopes` (worktree) | copilot/docs-gd52-adr-scopes | divergido (-158/+1) según `.audit-clones-temp.json` | STALE / ORPHAN_LOCAL | hilo Copilot docs | revisar → ARCHIVE/DELETE_CANDIDATE |

#### Familia notion-governance
| Clone | Rama | Estado git | Etiqueta | Rec |
|---|---|---|---|---|
| notion-governance | claude/feat-notion-capitalizacion-v21-pilot | **7 tracked + 7 untracked dirty** (contrato runtime-bridge, registro notion_poller, QW-2, D-19/P10-SEC63 SOLO acá) | **DIRTY_HIGH_RISK** — trabajo real, NO basura | **DO_NOT_TOUCH** hasta P4 (gated por David); COMMIT_SEPARATELY es el destino final |
| notion-governance-cursor | cursor/b2b-root-move | **12 tracked + 130 untracked, sin upstream**; último 2026-03-30 | DIRTY_HIGH_RISK + STALE; contenido UNKNOWN (¿trabajo o basura?) | DO_NOT_TOUCH → triage de contenido antes de cualquier decisión |
| notion-governance-antigravity | antigravity/notion-live-audit-2026-03-27 | limpio; último 2026-04-07 | STALE | ARCHIVE |
| notion-governance-rick-v1-draft | cursor/rick-runtime-v1-draft | limpio; último 2026-03-31 | STALE | ARCHIVE |
| notion-governance-temp | main @ f04829d (2026-03-31) | limpio | ORPHAN_LOCAL (snapshot "temp") | DELETE_CANDIDATE (previa confirmación) |
| notion-governance-main.bundle | — (archivo bundle) | — | ORPHAN_LOCAL | ARCHIVE o DELETE_CANDIDATE |

#### Residuos y contenedores
| Ítem | Qué es | Etiqueta | Rec |
|---|---|---|---|
| `.tmp-*` (≥10: cvia3-deploy, gd52-adr-scopes, b2-closeout, coord-ag, nga-megadiag, o16-2-047, 411-*.py/md, scan-result.json…) | clones/worktrees/archivos temporales de deploys y auditorías previas (p.ej. `.tmp-cvia3-deploy` = clone main 217 detrás) | ORPHAN_LOCAL | revisar lista completa → DELETE_CANDIDATE en fase H de higiene; NO borrado ahora |
| `.audit-clones-temp.json` (untracked en raíz del stack) | salida de una auditoría de clones previa (otro hilo) — evidencia útil para S14, no gitignored | UNKNOWN (dueño) | COMMIT_SEPARATELY como dato de auditoría o ARCHIVE; `[UI_EVIDENCE_PENDING]` hilo de origen |
| `_wt/` (b3-pr441-*, fase-a-deploy/rollback), `_wt-editorial-baseline`, `_wt-l9-wire`, `_wt-protocol`, `_wt-q-3` | contenedores de worktrees viejos sin `.git` raíz; `_wt-claude-qa-preview` es un **stub roto** (apunta a metadata inexistente de umbral-bot-claude) | ORPHAN_LOCAL | revisar → DELETE_CANDIDATE; el stub roto es DELETE_CANDIDATE claro |
| `copilot-worktrees/`, `_archive/`, `_sandbox/`, `cursor-codex-bridge/` | contenedores de worktrees Copilot, archivo histórico, sandbox, y una extensión VSIX bridge | UNKNOWN / STALE | inventario fino en fase de higiene; IGNORE por ahora |
| Familia umbral-bot-* (9 clones: copilot con **509 ramas locales** y 1 detrás; codex 37 ramas; cursor dirty 3+109 untracked; cursor-k 127 detrás; pr448-deploy en detached HEAD; 4 worktrees rotos umbral-azure-*/qa-baseline/release-note) | **producto Umbral Bot** — fuera del alcance funcional de este sys-diag, inventariado por visibilidad | UNKNOWN (scope aparte) | replicar este mismo ejercicio S14 en un diagnóstico propio de Umbral Bot |
| umbral-ai-registry-backup | main, snapshot diario automático (hoy 03:02) | ACTIVE | KEEP |
| umbral-skills-registry | feat/config-governance-d0, 5 tracked dirty, **último commit hoy 11:11** | ACTIVE (otro hilo trabajando AHORA) | DO_NOT_TOUCH |
| umbral-agent-forge, umbral-advisory, umbral-lab, umbral-marketing, umbral-bim, acc-copilot-aec40, mp-bim-radar | repos satélite limpios, actividad baja/histórica | STALE / IGNORE | IGNORE en este diagnóstico |

**Lectura para el work system:** la política "feature branch → PR → merge por David" se cumple en el repo principal, pero el ciclo **no cierra**: las ramas no se borran tras merge (239 remotas vivas), los clones por-agente no se retiran al terminar su hilo, y no existe registro clone↔hilo↔estado. Trabajo real en riesgo hoy: notion-governance (contrato sin commitear) y codex-coordinador (dirty + 200 detrás). Los prompts 3/4/5/6 cruzan esto con lo que cada IA ve.

## 3. Caso SIM Daily Report (criterio DONE)

- **Qué es**: "Sistema de Inteligencia de Mercado" — demo del hackathon 2026-03-04 (Codex, `.agents/tasks/2026-03-04-010`). `sim_daily_research.py` encola 6× `research.web` (keywords fijas de marzo: "embudo ventas…", "tendencias BIM 2026…") + 1× `llm.generate`; `sim_daily_report.py` cuenta OK/FAIL en ops_log y postea comentario (+subpágina si >1900 chars) en Control Room.
- **Qué lo genera**: crons `sim-daily-cron.sh` (8,14,20 UTC) y `sim-report-cron.sh` (:30) — ambos confirmados en crontab `[VPS]`; sim-daily fue instalado a mano (no está en install-cron.sh).
- **Por qué llm.generate 0/5 FAIL**: encola sin `model` → default `gemini-2.5-pro` → `_call_gemini` exige exactamente `GOOGLE_API_KEY` (llm.py:279), ausente en el Worker; Claude bloqueado (`UMBRAL_DISABLE_CLAUDE`), OpenAI/Azure sin keys en Worker. `research.web` 13/13 OK porque corre por `azure_foundry` `[VPS ops_log]`. El "0/5" además **mezcla fuentes**: el filtro cuenta cualquier research.web/llm.generate de la ventana (incluye E2E de las 06:00) — atribución engañosa.
- **Por qué nadie lo vio fallar**: el dispatcher silencia deliberadamente la escalación de fuentes sim_daily/sim_report/cron a Linear (anti-spam correcto) → el único síntoma era el propio comentario que David terminó sin reconocer.
- **Costo**: ~18 búsquedas/día (~540/mes) contra la cuota del provider de research; llm.generate fallido = US$0 (aborta pre-request). Costo dominante: **atencional** — 3 comentarios + 1 subpágina/día de ruido en la superficie canónica de más señal.
- **Veredicto**: **ACTIVE_NOISY** (secundaria ACTIVE_DEGRADED) → **DISABLE** (comentar ambas líneas de crontab + quitar de install-cron.sh para que no se reinstale). Si David quiere inteligencia de mercado real: rediseñar como ritual semanal con dueño, keywords vivas y post solo-con-señal. *Acción NO ejecutada en este paquete (requiere cambio de estado en VPS → GO de David).*

## 4. Caso triage v0 @Rick (criterio DONE)

- **Flujo** `[repo]`: comentario en Control Room → poller detecta `@rick` (autor debe estar en allowlist `DAVID_NOTION_USER_ID`) → encola `rick.orchestrator.triage` → handler v0 SIN LLM (worker/tasks/rick_orchestrator.py:28-135): si contiene `/health` postea el JSON crudo del Worker; cualquier otro texto → "Comando no reconocido en triage v0" con eco + referencias internas.
- **Conflicto de gobernanza**: el reply expone `tasks_registered` completo, `ts`, `version` — telemetría interna en Notion, contra reglas 1/3/6 de `notion-governance-runtime` → etiqueta **ACTIVE_DEGRADED** (responde; contenido no-útil) + ACTIVE_NOISY el reply.
- **Aislamiento P2a**: correcto y testeado — el flag OFF apaga SOLO el scan V2 classify; mentions y review targets siguen. `[VPS]` confirma flag ausente en el env del proceso.
- **Gap anti-loop**: los replies del triage NO llevan prefijo "Rick:"; si el author-guard (capa 1) cae, re-entran al pipeline. Hoy inofensivo (sin @rick no re-dispara; smart-reply degrada a silencio sin LLM), pero con proveedor LLM restaurado sería riesgo real. Fix barato identificado (prefijar "Rick:").
- **Camino a LLM real** = task 033 diferida + P2b (proveedor Rick+Luna) + salida gobernanza-compliant (español, sin telemetría) → **NEVER_SHIPPED** hoy; IMPLEMENT detrás de P2b.
- **smart_reply**: question/task degradan a **silencio deliberado** sin LLM (correcto: "silence beats a false promise"); solo `instruction` opera (upsert_task + handoff). ACTIVE_DEGRADED aceptado hasta P2b.

### §4-bis. Comentario de Rick observado por David — reconciliación 445 vs 118 (criterio DONE)

David observó un reply de Rick a `/health` publicado en Control Room con `ok=true`, `tasks_in_memory=445` y la lista completa de tasks registradas truncada por Notion (familias notion/windows/linear/research/llm/n8n/azure/figma/document/…).

**Reconciliación — RESUELTA con evidencia de código + runtime; ninguna cifra es "la equivocada":**
- `worker/app.py:489-497` `[repo]`: `/health` devuelve DOS métricas distintas: `tasks_registered = list(TASK_HANDLERS.keys())` (los **tipos de handler registrados**) y `tasks_in_memory = len(_task_store)`.
- `worker/app.py:128-138` `[repo]`: `_task_store` es un `OrderedDict` acotado de **resultados de ejecuciones recientes** ("In-memory task store (bounded, most recent 1000)", `MAX_TASK_HISTORY = 1000`, con evicción FIFO).
- Verificación en vivo 2026-07-17 ~14:54 UTC `[VPS]`: `curl /health` → `len(tasks_registered) = 118`, `tasks_in_memory = 1000`, version 0.4.0, mismo worker PID 2972295 (arrancado hoy 02:02).
- **Conclusión**: 118 = handlers registrados (lo que reporté como "118 tasks"); 445 = cuántos **registros de ejecución** había en memoria en el momento del reply de Rick; creció hasta el tope de 1000 durante el día (el poller solo genera ~337 ejecuciones `notion.poll_comments` por media hora, lo que explica la velocidad). No hay discrepancia: son métricas de ejes distintos (catálogo vs historial). El número 445 NO significa "445 tasks disponibles".
- Corolario de diseño: `tasks_in_memory` es telemetría de buffer interno **sin ningún valor para David** — mostrarla en Notion solo genera confusión (exactamente la que generó).

**Cuestionamiento del reply (integrado al veredicto del triage):**
- Publicar el registro interno completo en Control Room = **ACTIVE_NOISY** + **riesgo de exposición de información** (secundaria SECURITY_RISK): `/health` no requiere autenticación (`worker/app.py:491` "no requiere autenticación") y su volcado en Notion revela el catálogo completo de capacidades internas del Worker en una superficie compartida. Sin credenciales expuestas, pero es inventario interno fuera de su superficie.
- **Una task registrada NO prueba nada más que el import del handler**: ni que esté activa, ni que tenga credenciales, ni que funcione, ni que se haya usado alguna vez.
- Triage v0 además **ignora instrucciones libres**: cualquier texto que no sea `/health` recibe "Comando no reconocido" con eco — no hay interpretación.

**Clasificación de las 118 tasks registradas por familia (evidencia disponible; el resto UNKNOWN):**
| Familia (n) | Clasificación | Evidencia |
|---|---|---|
| notion (15) | ACTIVE_HEALTHY (poll/read/write en uso hoy) — salvo add_comment caller 06:00 ACTIVE_DEGRADED | ops_log + journalctl `[VPS]` |
| granola (9) | ACTIVE_HEALTHY (P1 ejecutada hoy dry-run y real) | ops_log `[VPS]` |
| research (1) + web (2) | ACTIVE_HEALTHY (azure_foundry) | ops_log `[VPS]` |
| llm (1) + composite (1) | MISSING_CREDENTIAL / ACTIVE_DEGRADED (100% FAIL) | journalctl `[VPS]` |
| rick (1) | ACTIVE_DEGRADED (triage v0, este caso) | ops_log `[VPS]` |
| linear (11) | REGISTERED_ONLY probable (integración congelada desde 2026-03-23; tráfico webhook UNKNOWN) | `[repo]` |
| n8n (5) | REGISTERED_ONLY / UNKNOWN (env N8N_* comentado en template; instancia viva aparte) | `[repo]` |
| windows (12) + gui (7) + browser (6) | REGISTERED_ONLY / UNKNOWN (dependen de la VM opcional; uso reciente no observado en ops_log) | `[VPS]` parcial |
| make (1) | MISSING_CREDENTIAL (MAKE_WEBHOOK_SIM_URL ausente; falla 3×/día) | `[VPS]` |
| azure (1, audio) | OBSOLETE probable / UNKNOWN (sin toques desde marzo; voz Rick fue por otro camino) | `[repo]` |
| copilot_cli (1) | REGISTERED_ONLY (gates RICK_COPILOT_CLI_* en false en template; estado VPS UNKNOWN) | `[repo]` |
| tournament_lane (5) + tournament (1) + pit (4) | ACTIVE_DEGRADED (PIT vivo con 3 blockers) | `[repo]` |
| google (4) + gmail (2) + google_drive (2) | MISSING_CREDENTIAL probable (OAuth Google comentado "oauth-apply-disabled") | `[VPS]` env nombres |
| figma (5), github (5), rag (4), document (3), client (6), system (2), ping (1) | UNKNOWN / REGISTERED_ONLY — sin señal en la ventana observada | — |

**Oportunidad futura (NO implementada en este paquete):** reply sanitario resumido en español, sin listado interno — p.ej. `Worker OK · 118 handlers · LLM degradado (sin proveedor) · última tarea hace 2 min`. Es el mismo FIX del triage v0 ya priorizado en la matriz (§5); queda detrás del GO de David.

## 5. Matriz de consolidación (D) — top hallazgos priorizados

| Fuente | Hallazgo | Etiqueta | Impacto work system | Rec | Esfuerzo | Dependencias | Riesgo |
|---|---|---|---|---|---|---|---|
| VPS+repo | SIM Daily Report 3×/día sin dueño ni lector | ACTIVE_NOISY | contamina Control Room (superficie de máxima señal) | DISABLE | XS | GO David (cambio estado VPS) | nulo (reversible) |
| VPS | sim-to-make falla 3×/día ≥24d | OBSOLETE | ruido en logs; cron quemado | DISABLE | XS | GO David | nulo |
| VPS | dashboard-rick + openclaw-panel jamás corrieron (perm denied) | NEVER_SHIPPED | David cree tener dashboard horario y no existe | FIX | XS | GO David (chmod) | nulo |
| repo+gov | Triage v0 postea telemetría en Notion | ACTIVE_DEGRADED | viola gobernanza; erosiona confianza en Rick | FIX (reply humano) | S | ninguna (código) | bajo |
| repo | Gap anti-loop replies sin "Rick:" | SECURITY_RISK (latente) | loop potencial al restaurar LLM | FIX | XS | antes de P2b | bajo |
| VPS+repo | Worker sin proveedor LLM (llm.generate 100% FAIL) | ACTIVE_DEGRADED | mata SIM/E2E/smart-reply/composite | FIX vía P2b (Rick+Luna) | M | decisión David P2b | medio |
| VPS | Drift skills 42/86 + 3 orphans solo-live (umbral-worker) | DRIFT_REPO_VPS | producción corre contratos stale; skill clave sin backup | FIX (capitalizar orphans → política sync) | M | revisar `windows` primero | medio |
| VPS | tailscale serve publica gateway (config dice off) | DRIFT_REPO_VPS | superficie no documentada | FIX (decidir+documentar) | XS | David decide | bajo |
| VPS | n8n activo con workflows solo-en-instancia | UNKNOWN / COST_RISK | automatización fuera de control de versión | FIX (exportar al repo) + prompt 10 | S | acceso n8n UI | medio |
| VPS | Log poller 101MB + handler duplicado | ACTIVE_NOISY | riesgo disco; ahoga señal de ops_log | FIX | S | ninguna | bajo |
| VPS | 6× codex app-server ~1GB | ACTIVE_NOISY | RAM; señal de fuga de sesiones | FIX (restart planificado) | XS | ventana mantenimiento | bajo |
| repo | notion.add_comment 400 (>2000 chars) flujo 06:00 | ACTIVE_DEGRADED | contenido se pierde en silencio | FIX (chunkear) | XS | ninguna | bajo |
| gov | Working tree notion-governance DIRTY con contrato sin commitear | DRIFT_REPO_VPS | el contrato mismo en riesgo de pérdida | FIX (P4, gated por David) | S | GO David (P4 diferido) | alto si se pierde |
| repo | Editorial exige azure-openai-responses vs matriz lo prohíbe | ACTIVE_DEGRADED | conflicto contrato/migración; bloquea apagar Foundry | FIX (decidir contrato) | S | decisión migración OAuth | medio |
| repo | Linear congelado desde marzo | OBSOLETE | modelo Linear-first ya desplazado; docs engañosos | DISABLE + marcar docs superseded | S | confirmar webhook VPS | bajo |
| repo | Improvement supervisor design_only (docs/70-77) | NEVER_SHIPPED | 8 docs sugieren un supervisor que no existe | DEFER (archivar o retomar) | S | decisión David | bajo |
| repo | copilot_agent + mcp_server huérfanos | ORPHAN | peso muerto en árbol y packaging | DELETE/attic | S | ninguna | bajo |
| repo | env.rick con secretos (local, no git) | SECURITY_RISK | secretos en texto plano copiables | FIX (mover+verificar rotación+borrar) | S | David (posible rotación) | medio |
| VPS | Runbook poller cabecera stale | DRIFT_REPO_VPS | induce a re-ejecutar reactivación | FIX docs | XS | ninguna | bajo |
| VPS | rsshub sin consumidor conocido | UNKNOWN | recursos (chromium) sin propósito claro | verificar → DISABLE si nadie | XS | inventario n8n/editorial | bajo |
| VPS | rick-linkedin-writer inactivo 18d | OBSOLETE | agente definido sin uso | DEFER (David) | XS | David confirma | nulo |
| VPS | Credenciales anthropic/google/vertex huérfanas en auth store | ORPHAN | superficie de credencial innecesaria | DEFER (retirar/rotar) | XS | política solo-OpenAI | bajo |
| VPS | Granola gap-check: 2 issues de datos | ACTIVE_HEALTHY (señal) | 2 raws con missing_granola_document_id | FIX datos | XS | ninguna | bajo |
| repo | Mailbox: runbook ordena usar dir inexistente | OBSOLETE | confunde a agentes nuevos | FIX runbook | XS | ninguna | nulo |
| local | 239 ramas remotas sin merge + 1 PR abierto stale (#521) | STALE (deuda git) | el ciclo branch→PR→merge no cierra; imposible saber qué está vivo | FIX (política de cierre de ramas + barrida guiada) | M | cruce prompts 4/5 + [UI_EVIDENCE_PENDING] | medio |
| local | codex-coordinador dirty (8+9) y 200 detrás de main | DIRTY_HIGH_RISK | trabajo de mayo potencialmente perdible; merge hoy = conflicto seguro | DO_NOT_TOUCH → triage de contenido | S | David/hilo Codex | alto si se pisa |
| local | notion-governance-cursor: 12 tracked + 130 untracked sin upstream | DIRTY_HIGH_RISK | contenido sin clasificar (¿trabajo o basura?) desde marzo | DO_NOT_TOUCH → triage | S | David | medio |
| local | ~10 residuos `.tmp-*` + `_wt*` stubs (1 roto) + clones STALE (antigravity, temp, rick-v1-draft…) | ORPHAN_LOCAL | ruido cognitivo y disco; riesgo de trabajar en el clone equivocado | DELETE_CANDIDATE (fase H, con GO) | S | confirmación por ítem | bajo |
| VPS+repo | Reply /health publica catálogo interno completo (445/118 confusión incluida) | ACTIVE_NOISY (sec. SECURITY_RISK exposición) | confundió a David; expone inventario interno en superficie compartida | FIX (reply sanitario resumido — mismo fix triage v0) | S | GO David | bajo |

## 6. Oportunidades (E)

**Quick wins (≤1 día, reversibles, casi todos requieren GO por tocar estado VPS):**
1. Apagar SIM (2 líneas de cron) + sim-to-make (1 línea) → Control Room limpio de un día para otro.
2. `chmod +x` dashboard-rick/openclaw-panel → dos superficies que David "ya tiene" empiezan a existir.
3. Prefijo "Rick:" en replies del triage (1 línea de código, pre-requisito de P2b).
4. Chunkeo ≤2000 en el caller de add_comment de las 06:00.
5. Rotación de logs (poller 101MB, supervisor, ops_log — script ya existe) + quitar handler duplicado.
6. Actualizar cabecera del runbook poller + runbook mailbox→.agents/tasks.
7. Borrar residuos: `C:\Granola\*.log` (VPS), desktop.ini ×6, update.zip/vm_net.tmp/worker_*.txt (local).

**Apalancamiento del stack existente:**
- **P2b Rick+Luna** es el multiplicador: un solo proveedor LLM vivo rehabilita triage inteligente (task 033), smart replies, E2E completo y (si se quiere) un SIM rediseñado. Todo lo demás ya está construido.
- Skill "Rick orquesta" + capitalizar `umbral-worker` al repo: el puente Worker ya existe en producción, solo hay que versionarlo.
- Triage v0 → reply humano en español (sin esperar P2b): el canal ya funciona, solo cambia el formato del mensaje.
- mission_control ya corre en VPS: documentar el deploy y usarlo como panel en vez de crear otro.

**Retiros de ruido:**
- SIM completo (o rediseño semanal con dueño), sim-to-make, discovery-publish (decidir en 30 días), rick-linkedin-writer, credenciales huérfanas del auth store, Linear (marcar superseded), Make/PAD refs, docs/69 y docs/70-77 como archivo de diseño.

**Implementaciones nuevas alineadas al work system (no por moda):**
- Política de sync de skills repo→workspace (deploy explícito con lista, no copia manual).
- Export automático de workflows n8n al repo (cron semanal `n8n export`) — cierra el hueco de irrecuperabilidad.
- "Automation registry": una tabla única (repo) de toda automatización periódica con dueño + lector + criterio de retiro — la lección SIM es que **toda automatización sin lector humano se apaga sola o se apaga a tiempo**.
- Policy formal de créditos Notion AI en notion-governance (hoy solo comentario en registry).

**Higiene git (nueva, tras S14 — nada ejecutado):**
- Barrida guiada de ramas: script read-only que liste las 239 remotas sin merge con último commit/autor → David decide por lotes (la mayoría serán MERGED_REMOTE_ONLY o muertas).
- Rescate priorizado de los 2 DIRTY_HIGH_RISK (notion-governance vía P4 gated; codex-coordinador con triage de su diff antes de que main se aleje más).
- Registro clone↔hilo↔estado (una tabla en `.agents/`) para que cada clone tenga dueño y fecha de retiro — el equivalente git del "automation registry".
- Al cerrar un hilo de agente: regla de cierre = commit/PR o descarte explícito + retiro del clone (hoy no existe y por eso hay 30+ clones).

**Qué NO hacer (anti-recomendaciones):**
- NO borrar/stashear/resetear ningún clone ni rama durante el diagnóstico (incluye `.tmp-*`): primero cruce con prompts 3/4/5/6 y pantallazos de hilos (`[UI_EVIDENCE_PENDING]`).
- NO mergear codex-coordinador tal cual (200 detrás = CONFLICT_RISK); triage de contenido primero.
- NO restaurar `GOOGLE_API_KEY` para "arreglar rápido" llm.generate (decisión vigente: ruta OAuth Rick+Luna).
- NO reactivar `NOTION_POLLER_ENABLE_V2_CLASSIFY` antes de P2b + GO.
- NO re-sync masivo de skills sin revisar antes el diff de `windows` (se pierde trabajo hecho en producción).
- NO ejecutar agentes Notion en batch para "auditar más rápido" (créditos).
- NO mergear el working tree sucio de notion-governance fuera del P4 gated.
- NO apagar Azure Foundry hasta resolver el contrato editorial que lo exige.

## 7. UNKNOWNs que cierran las rondas multi-IA

| UNKNOWN | Lo cierra |
|---|---|
| Workflows activos dentro de n8n | Prompt 10 (o inspección UI por David) |
| Agentes Notion custom, triggers, créditos consumidos | Prompt 2 (Notion AI) |
| Ritmos personales/calendario de David | Prompts 1 y 7 |
| Automatizaciones mencionadas solo en ChatGPT/memoria | Prompt 1 |
| Extensiones/Actions/tareas programadas Windows | Prompt 5 |
| Estado Cursor multi-root, clones duplicados locales | Prompt 3 |
| Ramas/PRs abandonados, deuda ADR | Prompt 4 |
| Validación independiente de esta captura VPS | Prompt 6 |
| "Bootstrap file ABSENT" ×8; mapeo codex app-servers a sesiones; consumidor rsshub; webhook Linear con tráfico | Prompt 6 + mantenimiento |
| Alcance real del scan del poller (12 cursors vs "solo Control Room") | Prompt 6 (config del daemon) |
| Mapeo clone↔hilo Claude Code/Cursor/Codex (S14) — `[UI_EVIDENCE_PENDING]` | Pantallazos de hilos de David + prompts 3/4/5 |
| Contenido real de los DIRTY (codex-coordinador 8+9; nga-cursor 12+130) — ¿trabajo o basura? | Triage manual guiado (fase posterior, con GO) |
| ¿MERGED_REMOTE_ONLY? de b0004/b0004-oauth/claude-pit2b/codex-granola | Prompt 4 (Codex cruza contra main) |
| Uso reciente real de familias windows/gui/browser/figma/github/rag (REGISTERED_ONLY vs usadas) | Check posterior: ops_log ventana ≥7 días (read-only) |

## 8. Gates

- `SYS_DIAG_PLAN_READY` — cumplido (plan commiteado).
- `SYS_DIAG_CAPTURE_READY` — **cumplido con este doc**: inventario propio con evidencia y taxonomía + 10 prompts listos + S14 higiene git + reconciliación 445/118. Siguiente paquete: consolidación cuando David devuelva las respuestas multi-IA (prompt 9), cruzando contra el inventario git/gh de S14.
- `SYS_DIAG_DOCS_PR_READY` — PR solo-docs abierto a main (3 archivos, sin fixes/deploy), base de la consolidación futura. Sin merge hasta GO de David.
