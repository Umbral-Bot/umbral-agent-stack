# Inventario FINAL — diagnóstico total OpenClaw/Umbral × work system (2026-07-17)

Estado: **FINAL** (consolidación Prompt 9 file-based). Sucede a `sys-diag-openclaw-inventory-draft-2026-07-17.md`.
Gate: `SYS_DIAG_FINAL_READY`. Único pendiente no bloqueante: `ui-evidence` (`UI_EVIDENCE_PENDING`).
Insumos: 8 devoluciones multi-IA + captura n8n, en `docs/audits/sys-diag-inputs/2026-07-17/` (manifest+SHA-256 validado fail-closed: **10/10 MATCH**), cruzados contra el draft VPS/repo y el contrato gov.

**Dos ejes en todo hallazgo (nunca colapsados):** `runtime_status` ∈ {HEALTHY, DEGRADED, BROKEN, UNKNOWN} · `work_value` ∈ {KEEP, FIX, DISABLE, DELETE, IMPLEMENT, DEFER, UNKNOWN}. Cada afirmación marca EVIDENCIA vs INFERENCIA y fuente. Regla aplicada: toda etiqueta `HEALTHY`/`ACTIVE_HEALTHY` emitida sin ver triggers/ejecuciones se degradó a `UNKNOWN`.

---

## 1. Resumen ejecutivo — lo que cambió tras la consolidación

1. **DOS instancias n8n, no una** (hallazgo estructural, EVIDENCIA cruzada 01+07+10). La instancia **VPS** está ociosa (7 workflows inactivos, 0 ejecuciones — capturado). Pero las tarjetas de aprobación del "KB Pipeline" en Teams enlazan a **`http://localhost:5680`**: hay un **n8n LOCAL en la máquina de David** que sí ejecuta (flujo Speckle→n8n→Sheets/Teams con señal real el 17-jul). Esto reconcilia la contradicción "n8n vivo vs 7 workflows muertos": son instancias distintas. El trabajo real de automatización de David vive en su PC, con dependencia frágil (si el equipo está apagado, las aprobaciones quedan colgadas) y sin TLS.

2. **El gateway NO está "sano" — está DEGRADED en su capa de modelos** (EVIDENCIA VPS, lector 6, nuevo respecto al draft). Servicio/transporte HEALTHY (token, loopback, Telegram), pero 6 de 8 agentes degradados: `gpt-5.6-sol` falla por requerir un Codex más nuevo (1.744 líneas/48h), `gpt-5.3-codex` no soportado con la cuenta ChatGPT (416 líneas), 6.722 "WebSocket closed before connect", 192 "embedded agent failed". El draft lo pintó verde de más.

3. **Tres urgencias de seguridad confirmadas** (sin valores reproducidos): (a) **password en texto plano** en `C:\Users\david\vm_script.ps1` (~5 meses, script que hace Invoke-Command a la VM Hyper-V "OpenClaw"); (b) **fingerprint parcial de credencial Google Vertex** filtrado por `openclaw models status` (bug de salida del CLI); (c) **`/health` sin auth** publicando el catálogo interno en Notion. Patrón sistémico: dos secretos en texto plano en el PC de David (vm_script.ps1 + env.rick).

4. **`llm.generate` 100% FAIL cuantificado y con límite nuevo a la decisión**: 272 líneas "GOOGLE_API_KEY no configurada" en 48h (EVIDENCIA VPS). Codex añade el límite material (lector 4): la ruta OAuth Rick+Luna **solo cubre texto GPT/Codex** y **requiere implementar el provider `openclaw_oauth`** (trabajo L, hoy solo especificado en doc, sin implementar); **audio (`azure.audio.generate`) y embeddings/RAG seguirán dependiendo de key Azure** → retirar Foundry por completo rompería esas superficies.

5. **Gate de cuota anulado** (EVIDENCIA repo, lector 4, nuevo): `auto_approve_quota: true` en `config/quota_policy.yaml` permite consumir sobre nivel `restrict` **sin aprobación humana**, contra ADR-004 y contra el comentario "false default" del propio archivo. Riesgo directo de gasto no autorizado, fácil de arreglar.

6. **Runtime ≠ HEAD por servicio** (EVIDENCIA VPS, lector 6, nuevo): dispatcher y mission-control corren procesos del 3-jul con el ejecutable Python marcado `deleted` — **no cargaron el HEAD actual** pese a que el repo está en main limpio. No existe paso "restart tras merge" en el ritmo de deploy.

7. **Los paneles NEVER_SHIPPED tienen un matiz sin resolver** (contradicción Notion↔VPS): el draft los marcó NEVER_SHIPPED por `Permission denied`; Notion muestra Dashboard Rick y panel OpenClaw actualizados por cron **hasta el 2026-07-14** y luego detenidos. Algo los escribió hasta esa fecha. **UNRESOLVED** — degradados a UNKNOWN hasta verificar qué proceso los escribía.

8. **Deuda de gobernanza de agentes = la brecha estructural mayor** (Perplexity + todo el resto). No existe registro único de agentes con dueño/propósito/estado. Síntomas convergentes: 9 asistentes Notion (solo 2 verificados), copilot_agent/mcp_server huérfanos, improvement supervisor design_only, "Arquitecto de Workspace" archivado nunca activado, SIM sin dueño, crons never-shipped, 3 skills solo-live. El benchmark 2026 nombra "agentes sin registro/owner" como antipatrón #1.

9. **Cifras en conflicto, ninguna elegida por intuición**: ramas sin merge **236 / 239 / 263** según método y momento (todos coinciden en ~89-90%, >230); PRs abiertos **2** (gana la cifra reciente: #521 preexistente + #541 autogenerado por este diagnóstico); `tasks_in_memory` **445 vs 1000** (buffer variable en el tiempo, no constante). Ver ledger §5.

10. **El sistema de trabajo real de David está mapeado** (01+07): agenda fuera de Outlook (en Notion), 6 flujos de email manuales, 8 compromisos abiertos con fecha, 4 familias de trabajo repetitivo automatizable, y preferencias operativas registradas. Ver §6.

---

## 2. Scorecard benchmark 2026 (rúbrica Perplexity, 10 controles)

Puntuación de los hallazgos del stack contra el checklist de estado del arte (EVIDENCIA externa citada; el mapeo al stack es INFERENCIA).

| # | Control | Estado | Evidencia |
|---|---------|--------|-----------|
| 1 | Registro único de agentes (owner/propósito/estado) | **FAIL** | sin registro; huérfanos, never-shipped, 9 asistentes Notion opacos |
| 2 | Identidad y permisos por agente, sin credenciales compartidas | **PARTIAL** | env.rick + vm_script.ps1 con secretos sin atribución; la ruta OAuth Rick+Luna va en la dirección correcta |
| 3 | Contratos de superficie (schemas/MCP/Agent Cards) | **PARTIAL** | drift de skills = superficies sin contrato versionado; worker con handlers sin caller |
| 4 | Human-in-the-loop real | **PASS parcial** | poller solo-Control-Room con gate humano; gates de David en editorial/publicación |
| 5 | Kill-switch y budget-switch | **PARTIAL** | flag V2 fail-closed OK; PERO `auto_approve_quota:true` anula el gate de cuota; PIT sin budget enforcement |
| 6 | Auditoría y observabilidad | **PARTIAL** | ops_log existe; triage v0 publica telemetría cruda en superficie de usuario; métricas sin semántica (445 vs 118) |
| 7 | Higiene de créditos Notion AI | **UNKNOWN** | 0 visibilidad de consumo; aplicabilidad depende del plan (DEFER) |
| 8 | Poller resiliente (cursor + checkpoint semántico + dedupe + backoff) | **PARTIAL** | cursor ADR-010 OK, dedupe OK; falta verificar backoff Retry-After y checkpoint semántico |
| 9 | Gateway endurecido | **PARTIAL→FAIL** | loopback+token OK; PERO fingerprint Vertex por CLI, tailscale serve no documentado, allowedOrigins sin verificar |
| 10 | Defensa prompt-injection multicanal | **UNKNOWN** | sin evidencia de provenance tags/scanners para tool outputs |

**Lectura**: la arquitectura (gateway + workers + supervisor humano) **coincide** con el patrón recomendado 2026; el déficit es de **disciplina de control** (registro, contratos, auditoría, budget), no de diseño.

---

## 3. Inventario final por dominio

Notación: `rt` = runtime_status, `wv` = work_value. `[E]` evidencia, `[I]` inferencia. Fuente entre paréntesis.

### 3.1 Gateway OpenClaw y modelos
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| Servicio/transporte gateway (token, loopback, Telegram, 8 agentes) | HEALTHY | KEEP | [E] VPS L6: systemd running, /health 200 | alta |
| Capa de modelos: 6/8 agentes degradados (gpt-5.6-sol y gpt-5.3-codex fallan) | **DEGRADED** | FIX | [E] VPS L6: 1.744+416 líneas error/48h, 6.722 WS closes | alta |
| Fingerprint parcial Vertex filtrado por `openclaw models status` | DEGRADED | FIX (rotar+parchear) | [E] VPS L6, sin valor | alta → **SEG §7** |
| tailscale serve publica gateway en tailnet (config dice off) | DEGRADED | FIX | [E] draft; [I] L2 benchmark #9 exige documentarlo | media (no revalidado por L6) |
| Versión 2026.6.10 vs 2026.7.1; plugin path redundante; bootstrap ABSENT ×8 | DEGRADED | FIX/UNKNOWN | [E] VPS L6 | alta / bootstrap UNKNOWN |
| 6 procesos codex app-server ~1GB; 6.722 WS closes de cliente no identificado | DEGRADED | FIX | [E] VPS L6 | media (origen UNKNOWN) |
| Credenciales anthropic/google/vertex huérfanas en auth store | UNKNOWN | DEFER | [E] draft+L6, sin smoke | media |
| APPLY del plan OAuth de julio en el gateway | UNKNOWN | — | [E] L4: "el plan no prueba que APPLY corrió" | — |

### 3.2 Worker, dispatcher, mission-control, poller
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| Worker /health, 118 handlers | HEALTHY | KEEP | [E] VPS L6: curl directo | alta |
| `llm.generate` 100% FAIL (GOOGLE_API_KEY ausente; Azure/OpenAI ausentes) | BROKEN | FIX vía P2b | [E] VPS L6: 272 líneas/48h; [E] repo L4: llm.py:170-227 | alta |
| Ruta OAuth Rick+Luna: solo texto; audio/embeddings siguen con key Azure | — | IMPLEMENT (`openclaw_oauth`) | [E] repo L4 §5; spec existe sin implementar | alta |
| `notion.add_comment` 400 (>2000 chars) flujo 06:00 | DEGRADED | FIX (chunkear) | [E] draft | alta |
| `research.web` OK vía azure_foundry | HEALTHY | KEEP | [E] draft ops_log; [E] L4/L5 backend Azure existe | alta |
| Poller daemon V2 OFF (flag ausente en env del proceso) | HEALTHY | KEEP | [E] VPS L6: PID 3016854 post-HEAD; flag ausente | alta |
| Poller: 36 fallas reales/48h (18 tracebacks + 10 iter abortadas + 8) tras filtrar firmas | DEGRADED | FIX | [E] VPS L6 (auto-corrección: 500 líneas limpias ≠ 48h) | alta |
| Log poller 102 MB sin rotación + handler duplicado | DEGRADED | FIX | [E] VPS L6 + draft | alta |
| dispatcher + mission-control corren Python "deleted" del 3-jul (no cargaron HEAD) | DEGRADED | FIX (restart + política) | [E] VPS L6: PIDs 1769618/1769623 | alta |
| Gate de cuota anulado: `auto_approve_quota: true` (contra ADR-004) | DEGRADED | FIX | [E] repo L4: quota_policy.yaml:3-6 | alta → **SEG §7** |
| Triage v0 @Rick publica JSON /health crudo en Control Room | DEGRADED | FIX (reply humano) | [E] repo draft §4 | alta |
| Gap anti-loop: replies sin prefijo "Rick:" | UNKNOWN (latente) | FIX | [E] repo draft | media |

### 3.3 SIM / crons VPS
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| SIM Daily (research+report) — hackathon marzo, sin dueño/lector | HEALTHY (corre) / DEGRADED (LLM) | **DISABLE** | [E] draft §3 + L6: corre 08:00/08:30 | alta |
| sim-to-make 3×/día — falla por `MAKE_WEBHOOK_SIM_URL` ausente | BROKEN | DISABLE | [E] draft (contenido log); L6 lo vio HEALTHY solo por mtime | alta (draft gana) |
| dashboard-rick + openclaw-panel — cron dispara, efecto no se materializa | BROKEN/UNKNOWN | FIX o DISABLE | [E] draft (Permission denied) vs [E] Notion (updates hasta 07-14) → **UNRESOLVED §5** | media |
| e2e-validation 06:00 — 11/15 PASS, 4 FAIL (arrastra llm.generate) | DEGRADED | FIX vía P2b | [E] draft | alta |
| supervisor/health-check/quota-guard/daily-digest/notion-curate/granola-gap-check | HEALTHY | KEEP | [E] draft+L6 | alta (mtime; contenido parcial) |
| discovery-publish (comentado desde mayo) | — | DEFER→DELETE | [E] draft+L6 | alta |

### 3.4 n8n (DOS instancias)
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| **n8n VPS**: 7 workflows TODOS inactivos, 0 ejecuciones, 2 creds SMTP | HEALTHY (servicio) / — (workflows) | DISABLE workflows / KEEP servicio | [E] captura 10-n8n sqlite ro | alta |
| **n8n LOCAL (localhost:5680)**: Speckle→Sheets/Teams activo hoy; KB Pipeline | DEGRADED (dep. PC encendido, sin TLS) | FIX | [E] cruce 01+07 (señal 17-jul en 2 fuentes) | alta (existencia) / media (salud) |
| Bind VPS `*:5680` filtrado por firewall externo; tailnet no probado | — | KEEP (verificar tailnet) | [E] test externo timeout | alta / tailnet UNKNOWN |

### 3.5 Notion (workspace de David)
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| 9 asistentes custom (Analista, Claudio activos; 5 no abiertos; Arquitecto archivado) | UNKNOWN | KEEP/triage | [E] L3: Notion no expone triggers/modelo/ejecución | alta (existencia) / baja (salud) |
| Transcripciones Granola 133 filas, editada hoy; Registro de Tareas 33 filas | HEALTHY | KEEP | [E] L3 timestamps | alta |
| Publicaciones: deuda de schema desde 2026-04-22 (18 props extra, Proyecto=texto) | DEGRADED | FIX | [E] L3 | alta |
| Bandeja revisión Rick estancada (nada desde 2026-03-17) | DEGRADED | DISABLE/archivar | [E] L3 | alta |
| Bandeja Puente: items "Instrucción Notion:[n/n]" varados desde mayo | DEGRADED | FIX (limpiar) | [E] L3 | alta |
| DB Tareas—UAS (eventos worker) sin filas desde 2026-05-19 | DEGRADED | UNKNOWN | [E] L3: worker vivo pero dejó de escribir ahí | alta |
| Control Room NO localizable por búsqueda de Notion AI | UNKNOWN | FIX (documentar URL) | [E] L3: superficie del único poller activo | media |
| Triplicidad DBs de proyectos (Umbral / técnicos-Rick / Asesorías) + duplicados de instrucciones | DEGRADED | FIX/DELETE | [E] L3 | alta |
| Créditos Notion AI: 0 visibilidad de consumo | UNKNOWN | DEFER | [E] L3 | — |

### 3.6 Repo: ADRs, publicación, PIT, OAuth (Codex L4)
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| Colisiones de numeración ADR (2×009, 2×010, 2×011; 013 placeholder) | — | FIX | [E] repo L4 | alta |
| stage9c LinkedIn: publica personal legacy `/v2/ugcPosts` vs ADR-009-A (Company) | BROKEN | **DISABLE** | [E] repo L4: riesgo identidad equivocada | alta → **SEG §7** |
| stage8 imagen: Google Image directo pese a ADR-006 (Magnific) | DEGRADED | DISABLE | [E] repo L4 | alta |
| PIT sin corte duro de presupuesto (`enforced:false`); entrega Notion stub | DEGRADED | DISABLE runs reales | [E] repo L4 | alta → **SEG §7** |
| ADR-003 health drift (código 10s/2 fallos vs ADR 60s/3, sin Limited/Minimal) | DEGRADED | FIX | [E] repo L4 | alta |
| Worker no hereda OAuth del gateway (perfiles en auth-profiles.json, no env) | BROKEN | IMPLEMENT | [E] repo L4 §5 | alta |
| Editorial exige azure-openai-responses vs matriz lo prohíbe | DEGRADED | FIX | [E] draft+L4 | alta |
| No hay TODO/FIXME literales; deuda = flags off/stubs/ADRs incompletas | — | — | [E] repo L4 | alta |

### 3.7 Higiene git/clones/ramas (S14 ampliado)
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| ~236-239 ramas remotas sin merge (~89%); método sin fetch no autoritativo | — | FIX (conteo canónico + barrida) | [E] draft 239 / L4 263 / L5 236 | media (ver §5) |
| 2 PRs abiertos: #521 (deuda real, ~13d) + #541 (autogenerado por este diag) | — | PR: resolver #521 | [E] L4/L5 | alta |
| 16 de 21 ramas recientes = MERGED_REMOTE_ONLY (squash) | — | DELETE_CANDIDATE | [E] repo L4 | alta |
| Ramas rescue #528/#529 = respaldo explícito | — | **DO_NOT_TOUCH** | [E] repo L4 (comentarios PR) | alta |
| notion-governance DIRTY (contrato sin commitear) | — | DO_NOT_TOUCH hasta P4 | [E] draft S14 | alta |
| codex-coordinador DIRTY (8+9) + 200 detrás | — | DO_NOT_TOUCH → rescatar | [E] draft S14 (L4 no revalidó, ver §5) | media |
| Clones/worktrees VPS dirty: 2 OAuth /tmp, wt-replay (notion_poller.py mod.), backup 29 untracked | — | DO_NOT_TOUCH (gate 30d) | [E] VPS L6 | alta |
| ~10 residuos `.tmp-*`, `_wt*` (1 stub roto), clones STALE | — | DELETE_CANDIDATE (fase H) | [E] draft+L1 | media |
| `.audit-clones-temp.json` sin trackear = residuo de auditoría de clones | UNKNOWN | ARCHIVE/verificar | [E] L5 | alta |

### 3.8 Entorno local de David (Cursor L1, GitHub/Windows L5)
| Hallazgo | rt | wv | Evidencia | Confianza |
|---|---|---|---|---|
| Hook Cursor `protect-canonical.py` fail-closed roto (`MainThreadShellExec not initialized`) — cegó su propia auditoría | BROKEN | FIX | [E] L1 (causa de PARTIAL) | alta |
| vm_script.ps1: password en texto plano (~5 meses), Invoke-Command a VM Hyper-V "OpenClaw" | — | FIX urgente | [E] L5, sin valor | alta → **SEG §7** |
| 3 tareas Windows ligadas a clon `umbral-agent-stack-codex`: GranolaVmRawIntakeStartup FALLÓ (cód 1, 2026-07-15); UmbralWorkerPrimary OK | DEGRADED | FIX | [E] L5 | alta |
| Worker primario y intake Granola arrancan por login de Windows, no como servicio | — | KEEP (documentar) | [E] L5 | alta |
| Workflow GitHub Actions "Tests" DUPLICADO en umbral-agent-stack | DEGRADED | FIX | [E] L5 | alta |
| Azure: 7 resource groups; rg-nonprod MEZCLADO con proyecto "Consultor" | HEALTHY/DEGRADED | FIX (separar RG) | [E] L5 | alta |
| Regla global plugin netlify-skills-router inyectada en todos los roots (destino Azure) | DEGRADED | FIX | [E] L1 | alta |
| Kit `_audit-2026-07` con `token-map.csv` no abierto (posible sensible) | UNKNOWN | revisar (David) | [E] L5 | media → **SEG §7** |
| Repo fantasma Umbral-Bot/umbral-bot-copilot → 404 (config local apunta ahí) | BROKEN | FIX (limpiar ref) | [E] L5 | alta |
| VM "OpenClaw" es Hyper-V LOCAL, no Azure | — | KEEP | [E] L5 | alta |

### 3.9 Superficies nunca-desplegadas / huérfanas (consolidado)
copilot_agent + mcp_server (ORPHAN abril) · improvement supervisor docs/70-77 (design_only) · "Arquitecto de Workspace" Notion (archivado, nunca activó) · Gpt-Rick Foundry (403, sin handler) · Linear (congelado marzo) · Make/PAD (restos S5-S7) · Power Automate S4 (OBSOLETE con errores, potencialmente aún habilitado). **wv común**: DEFER (decisión de retiro) salvo copilot_agent/mcp_server (DELETE/attic) y Power Automate S4 (DISABLE explícito por seguridad).

---

## 4. (reservado — ver §3, inventario por dominio)

## 5. Contradiction ledger

| # | Afirmación A | Afirmación B | Explicación | Veredicto |
|---|---|---|---|---|
| 1 | Ramas sin merge: draft **239** | L4 **263** / L5 **236** | Métodos distintos (git local sin fetch vs clones bare temporales) y momentos distintos | **UNRESOLVED** en cifra exacta; orden de magnitud ~89-90% (>230) es lo accionable. Conteo canónico = `fetch --prune` + API GitHub |
| 2 | draft: **1** PR abierto (#521) | L4/L5: **2** (#521 + #541) | #541 es autogenerado por este diagnóstico, posterior al draft | **Gana B**: 2 abiertos; deuda real = #521 |
| 3 | draft: /health **445** (buffer) | L6: **1000** | Mismo campo, momentos distintos; 1000 = tope del buffer | **Gana B para el instante**; citar como variable en el tiempo, no constante. 118 handlers = constante |
| 4 | draft: gateway **sano** | L6: gateway **DEGRADED** (6/8 agentes, modelos rotos) | "Sano" solo aplica a transporte/servicio | **Gana B** (más granular): servicio HEALTHY + modelos DEGRADED |
| 5 | draft: dashboard-rick/openclaw-panel **NEVER_SHIPPED** (perm denied) | L3 (Notion): actualizados por cron **hasta 07-14** | Algo escribió los paneles hasta el 14; el draft ve el cron nuevo fallando | **UNRESOLVED**: ambos a UNKNOWN; verificar qué proceso escribía y por qué cesó |
| 6 | draft: n8n vivo pero 7 workflows muertos | 01/07: n8n con actividad real hoy | **Dos instancias distintas**: VPS ociosa + local:5680 activa | **Ambas ganan** en su ámbito; reconciliado (§1.1) |
| 7 | draft: skills drift 42 vs 86, 3 solo-live | L6: 10 solo-live / 49 solo-repo / 27 difieren = 86 | Granularidad: draft cuenta directorios, L6 cuenta entradas diff (incluye desktop.ini) | **UNRESOLVED**: re-contar con métrica única antes de sync; drift grande confirmado por ambos |
| 8 | L5: stack "100% Azure" | draft: routing LLM por OAuth ChatGPT, perfiles Google/Vertex | L5 infirió desde infra cloud (7 RGs Azure); sin ver runtime del worker | **Gana draft**: infra visible 100% Azure, routing LLM NO |
| 9 | draft: codex-coordinador 200 detrás | L4: "origin/main idéntico a GitHub, sin fetch" | Distinto clone o distinto momento; sin fetch no comparable | **UNRESOLVED**: verificar en qué clone corrió cada captura |
| 10 | L6: sim-to-make/dashboard-rick ACTIVE_HEALTHY | draft: rotos | L6 miró solo mtime del log; un cron que falla también actualiza mtime | **Gana draft** (contenido > mtime); regla: no etiquetar HEALTHY por mtime |
| 11 | L2/L4: decisión "no restaurar key" viable | L4 §5: audio/embeddings siguen con key Azure | La política cubre texto; audio/RAG requieren decisión aparte | **Refinado**: mantener OAuth para texto, explicitar excepción audio/RAG; llm.generate seguirá FAIL hasta implementar `openclaw_oauth` |
| 12 | Varias IAs: etiquetas ACTIVE_HEALTHY | Sin ver triggers/ejecuciones | Notion AI, Cursor (tool-blocked), extensiones por correlación | **Regla aplicada**: todas degradadas a UNKNOWN salvo evidencia de ejecución |

---

## 6. Mapa del sistema de trabajo real de David

**Fuentes**: 01 (ChatGPT/Gmail/memoria), 07 (M365/Graph), 03 (Cursor), reglas del repo.

**Dónde vive el trabajo:**
- **Agenda real fuera de Outlook** [E]: calendario M365 casi vacío (6 eventos en 4 semanas, docencia 0h visible pese a cohorte activa) → vive en Notion/Google. Única cadencia en Outlook: reunión semanal "Copilot/Agente" con Daniel Muñoz (WSP).
- **Canales operativos**: Teams TED›Automatizaciones y TED›General; Master AEC 4.0 V2 (cohorte vigente: Rhino Inside, MCP Rhino, n8n).
- **Automatización propia en su PC** [E]: n8n local (localhost:5680) — flujo Speckle→Sheets/Teams y KB Pipeline (monitor semanal de docs oficiales con aprobación humana).

**Trabajo manual repetitivo (candidatos a agente, EVIDENCIA Gmail):**
1. Nómina del workshop n8n (78 notificaciones Luma/4 semanas → traslado manual + correos).
2. Onboarding docente: accesos de estudiantes (92 notificaciones Canvas/18 semanas, respuestas manuales sobre Teams/SharePoint/Speckle/licencias).
3. Seguimientos de compromisos/pagos/cotizaciones (redactados uno por uno; 8 compromisos abiertos con fecha).
4. Producción docente (transcripciones→PPT→README→prompts→ejercicios, hecho a mano en Drive).

**Preferencias operativas registradas** [E, memoria ChatGPT]:
- Español siempre; tratar como "David"; formal en lo profesional, casual en lo cotidiano.
- Correo: saludo breve → contexto mínimo → punto → acción → cierre "Quedo atento"/"Saludos"; texto listo para copiar.
- Decisiones: opciones claras + **recomendación explícita**; evitar "copiloto" como marca; preferir "agentes IA"/"asistentes especializados".
- Docencia: martes y jueves 12:00–15:00 Chile; no esperar respuestas fuera del horario de la contraparte.
- Documentos: revisión iterativa (versión → validación real → ajuste → consolidación).
- Orquestación (repo): Cursor lead, un agente a la vez, coordinación por archivos `.agents/`, dry-run default, repo=intent/VPS=reality; Copilot = Merge Master; **residuo legacy "Lovable coordinador" sin limpiar**.

**Gates humanos vivos**: publicación editorial, capitalización Granola (click por fila), merges a main, deploys/restarts, cuota>restrict (hoy anulado por el bug §3.2), fases destructivas.

**Compromiso técnico cruzado**: ticket de soporte Microsoft por **bloqueo de facturación de GitHub Copilot** (abierto 03-jul) — toca el ecosistema del stack.

---

## 7. Urgencias de seguridad (tratadas aparte, SIN valores)

| # | Hallazgo | Acción propuesta (requiere GO; NO ejecutada) |
|---|---|---|
| S-1 | **Password en texto plano** en `C:\Users\david\vm_script.ps1` (~5 meses) | Rotar la credencial de la VM, migrar a Credential Manager/DPAPI/Key Vault, borrar del script. **Decisión de David** (rotación = acción prohibida para el agente). |
| S-2 | **Fingerprint parcial Google Vertex** filtrado por `openclaw models status` | Rotar el perfil Vertex; reportar/parchear el bug de salida del CLI (secret-output-guard). |
| S-3 | **`/health` sin auth** publica catálogo interno del Worker en Control Room (triage v0) | Reply sanitario resumido (`Worker OK · 118 handlers · LLM degradado`), sin listado ni telemetría. |
| S-4 | `auto_approve_quota: true` — gasto sobre `restrict` sin aprobación | Poner en `false` (restaura gate humano ADR-004). |
| S-5 | stage9c publicaría LinkedIn bajo identidad personal legacy | DISABLE hasta alinear con ADR-009-A (Company). |
| S-6 | PIT sin corte duro de presupuesto (`enforced:false`) | Bloquear runs reales hasta enforcement. |
| S-7 | `token-map.csv` en `_audit-2026-07` (no abierto; posible sensible) | Revisión manual de David antes de cualquier ingesta. |
| S-8 | env.rick (45 claves en texto plano, local, no-git) | Mover fuera del repo, verificar rotación, borrar. |
| S-9 | n8n local expone aprobaciones vía `http://localhost:5680` sin TLS | Si se expone, solo por túnel autenticado (cruza con tailscale serve). |
| — | **Contexto externo** (Perplexity, fuentes 2° marcadas): CVEs OpenClaw 2026 y crecimiento de instancias expuestas | Verificar versión desplegada contra advisories antes de cualquier exposición; hoy el gateway NO es público (verificado). |

Ninguna de estas acciones fue ejecutada. Ningún valor de secreto fue leído ni reproducido.

---

## 8. Roadmap priorizado (paquetes pequeños y reversibles)

Cada paquete ≤1 sesión, con gate humano. **Nada implementado aquí.**

**Tanda A — Quick wins reversibles (bajo riesgo, alto alivio):**
- A1. Apagar SIM (2 crons) + sim-to-make (1 cron). [DISABLE, XS]
- A2. `auto_approve_quota → false`. [FIX, XS] — cierra S-4.
- A3. Reply sanitario del triage v0 + prefijo "Rick:" en replies. [FIX, S] — cierra S-3 + gap anti-loop.
- A4. Rotación de logs (poller 102 MB, supervisor, ops_log) + quitar handler duplicado. [FIX, S]
- A5. Actualizar cabecera runbook poller + runbook mailbox→.agents/tasks. [FIX, XS]
- A6. `chmod +x` dashboard-rick/openclaw-panel — **después** de resolver la contradicción §5 (qué escribía hasta 07-14). [FIX, XS, condicionado]

**Tanda B — Seguridad (requiere decisiones de David):**
- B1. Rotar credencial VM + migrar vm_script.ps1 a vault. [S-1]
- B2. Rotar perfil Vertex + parchear CLI. [S-2]
- B3. Mover/borrar env.rick; revisar token-map.csv. [S-7, S-8]
- B4. DISABLE stage9c y stage8 hasta alinear ADRs. [S-5]

**Tanda C — Destrabar el multiplicador LLM:**
- C1. Implementar provider `openclaw_oauth` (spec ya escrita) — destraba llm.generate para texto, triage LLM (task 033), smart replies, E2E. [IMPLEMENT, L] — **explicitar que audio/RAG siguen con key Azure**.
- C2. Restart de dispatcher + mission-control + política "restart tras merge". [FIX, S] — cierra el drift runtime≠HEAD.

**Tanda D — Higiene estructural:**
- D1. Conteo canónico de ramas (`fetch --prune` + API) → barrida guiada por lotes; preservar rescue #528/#529. [FIX, M]
- D2. Re-medir skills drift con métrica única → política de sync repo→workspace (capitalizar `windows` y `umbral-worker` antes). [FIX, M]
- D3. Renumerar colisiones ADR; marcar 005/006/013 obsoletas. [FIX, S]
- D4. Limpieza Notion: bandejas estancadas, items varados, duplicados de instrucciones, triplicidad de DBs de proyectos, deuda de schema Publicaciones. [FIX, M]
- D5. Separar RG "Consultor" de rg-nonprod; resolver workflow Tests duplicado; limpiar ref repo 404. [FIX, S]

**Tanda E — Nuevas capacidades alineadas al work system (no por moda):**
- E1. **Registro único de agentes** (owner/propósito/plataforma/trigger/coste/estado) — resuelve huérfanos, never-shipped, asistentes Notion y SIM de una vez. Es la brecha #1 del benchmark. [IMPLEMENT, M]
- E2. Agente de operación del workshop n8n (nómina Luma→acceso→correo). [IMPLEMENT, M]
- E3. Agente de onboarding docente (Canvas→accesos por plataforma→respuestas). [IMPLEMENT, M]
- E4. Agente de compromisos/seguimientos (extraer promesas de correos→próxima acción). [IMPLEMENT, M]
- E5. Estado central en Notion para lo que hoy muere en Teams (n8n escribe items con estado; Teams solo notifica; elimina dependencia de localhost:5680). [IMPLEMENT, M]

**Anti-recomendaciones (qué NO hacer):**
- NO restaurar GOOGLE_API_KEY como atajo (decisión = OAuth; y no cubriría el problema de identidad compartida del benchmark).
- NO reactivar V2 classify antes de C1 + GO.
- NO sync masivo de skills sin re-conteo y sin capitalizar `windows`/`umbral-worker`.
- NO mergear codex-coordinador tal cual (CONFLICT_RISK, 200 detrás) — rescatar dirty primero.
- NO tocar notion-governance dirty ni ramas rescue #528/#529.
- NO apagar Azure Foundry por completo (rompe audio/RAG y editorial).
- NO borrar ramas/clones por antigüedad sola — cruzar con `[UI_EVIDENCE_PENDING]` y confirmar MERGED_REMOTE_ONLY.

---

## 9. Decisiones que requieren GO humano de David

1. **Seguridad (urgente)**: rotar credencial VM (S-1) y perfil Vertex (S-2); ambas son acciones prohibidas para el agente. Definir vault.
2. **SIM**: confirmar DISABLE definitivo o rediseño semanal con dueño.
3. **Ruta LLM**: aprobar implementación de `openclaw_oauth` (C1) y confirmar que audio/RAG conservan key Azure.
4. **Paneles 07-14**: decidir investigación de qué proceso los escribía antes de tocar los crons (A6).
5. **Higiene git**: autorizar barrida de ramas y triage de clones dirty (D1); qué se archiva/borra es decisión por lote.
6. **notion-governance P4**: sigue diferido por David; el contrato dirty permanece DO_NOT_TOUCH hasta entonces.
7. **Nuevas capacidades E2-E5**: cuáles priorizar según carga real (docencia vs comercial).
8. **Bloqueo facturación Copilot**: seguimiento del ticket Microsoft (fuera del stack, pero lo condiciona).

---

## 10. UNKNOWNs abiertos y checks posteriores (read-only)

- Qué instancia n8n ejecuta qué, y salud real del KB Pipeline (¿aprobaciones colgadas?) → inspección del n8n local:5680.
- Qué proceso escribía Dashboard Rick/panel OpenClaw hasta 07-14 y por qué cesó → logs VPS + config cron.
- Conteo canónico de ramas (fetch+API) y en qué clone corrió cada captura de codex-coordinador.
- Re-conteo de skills drift con métrica única.
- Backoff Retry-After y checkpoint semántico del poller (benchmark #8) → lectura de código/runtime.
- allowedOrigins y checks de identidad del Control UI (benchmark #9).
- Uso real de familias windows/gui/browser/figma/github/rag (REGISTERED_ONLY vs usadas) → ops_log ≥7 días.
- Mapeo clone↔hilo → **`[UI_EVIDENCE_PENDING]`** (pantallazos de David; `ui-evidence-claude-cursor-threads.md`).
- Créditos Notion AI (0 visibilidad); plan del workspace.
- Bug del hook `protect-canonical.py` → arreglar y re-correr la auditoría Cursor completa.
- Origen de 6.722 WS closes; 2 procesos Node root no atribuidos; superficie que sirve Redis.

---

## 11. Gates

- `SYS_DIAG_PLAN_READY` ✅ · `SYS_DIAG_CAPTURE_READY` ✅ · `SYS_DIAG_DOCS_PR_READY` ✅ · `SYS_DIAG_INPUTS_STAGED` ✅ (validado fail-closed 10/10).
- **`SYS_DIAG_FINAL_READY`** ✅ con este documento: inventario final (dos ejes), contradiction ledger (12), mapa del work system, roadmap por paquetes, lista de GOs, urgencias de seguridad. Pendiente no bloqueante: `UI_EVIDENCE_PENDING`.
- **No se implementó, desplegó, limpió, borró rama, exportó workflow ni rotó secreto.** Próximo paso = GO de David por tanda.
