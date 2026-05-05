# 2026-05-05-002 — Auditoría runtime de los 8 subagents vs modelo organizacional Rick

- **Created**: 2026-05-05
- **Assigned to**: copilot-vps (acceso SSH real a VPS Hostinger)
- **Status**: ready
- **Priority**: P1 (bloquea Ola 1 del modelo organizacional)
- **Depends on**: ninguna
- **Blocks**: Ola 1 fundamentos (re-prompt de Rick + archivar/promover subagents).

## Contexto

El doc `notion-governance/docs/architecture/15-rick-organizational-model.md` (commit `7a11af7` en `main` de `notion-governance`) define un modelo de Rick CEO + 6 gerencias. La §5 hace un mapeo **conceptual** de los 8 subagents existentes en `~/.openclaw/agents/` contra ese modelo, asumiendo que la mayoría son placeholders sin contenido. Antes de archivar o promover nada, hay que **verificar runtime** qué tiene cada uno realmente.

## Hipótesis a verificar

Según §5 del doc:

| Subagent | Hipótesis | Acción propuesta si se confirma |
|---|---|---|
| `rick-orchestrator` | Vacío / redundante con `main`. | Archivar. |
| `rick-delivery` | Concepto ambiguo, sin uso. | Archivar o reconvertir. |
| `rick-qa` | No tiene contenido de gerencia, sí podría tener lógica QA. | Reconvertir a skill `qa-runner`. |
| `rick-tracker` | Trackea experiencia, no es gerencia. | Reconvertir a skill `experience-tracker` dentro de Mejora Continua. |
| `rick-ops` | Health/ops, no es gerencia. | Reconvertir a skills (`ops-runner`, `health-checker`) dentro de Desarrollo. |
| `rick-communication-director` | Semilla válida de gerencia. | Promover a Gerencia de Comunicación. |
| `rick-linkedin-writer` | Skill puntual mal envuelto en agent. | Reconvertir a skill `linkedin-writer` dentro de Marketing. |
| `improvement-supervisor` | Semilla válida de gerencia. | Promover a Gerencia de Mejora Continua. |

## Qué hay que hacer (en VPS)

Para **cada uno** de los 8 directorios bajo `~/.openclaw/agents/`:

```bash
ssh rick@<vps>
cd ~/.openclaw/agents/<agent_id>
ls -la                          # estructura completa
ls -la agent/ 2>/dev/null       # subdir agent si existe
find . -type f -name "*.md" -exec wc -l {} \;   # docs
find . -type f -name "*.json" -exec ls -la {} \;
find . -type f -name "*.yaml" -o -name "*.yml" 2>/dev/null
# Buscar prompt real:
cat agent/*.md 2>/dev/null | head -200
cat *.md 2>/dev/null | head -200
# Buscar config:
cat agent/auth.json 2>/dev/null | jq '.'
# Buscar referencias en openclaw.json:
jq --arg id "<agent_id>" '.agents[] | select(.id == $id)' ~/.openclaw/openclaw.json
```

Y también:

1. **Uso histórico**: revisar logs/sessions/trajectories de últimos 30 días buscando si **alguno** de estos 8 fue invocado:

   ```bash
   sudo journalctl -u openclaw-gateway --since '30 days ago' | grep -iE "(rick-orchestrator|rick-delivery|rick-qa|rick-tracker|rick-ops|rick-communication-director|rick-linkedin-writer|improvement-supervisor)"
   # Sessions JSONL:
   find ~/.openclaw/sessions -name "*.jsonl" -mtime -30 | xargs grep -lE "<agent_id>" 2>/dev/null
   # Trajectories:
   find ~/.openclaw/trajectories -name "*.json" -mtime -30 | xargs grep -lE "<agent_id>" 2>/dev/null
   ```

2. **Referencias entre subagents**: `grep -r "<agent_id>" ~/.openclaw/agents/` (qué agente menciona a otro).

## Output esperado (entregable)

Append al final de **este mismo archivo** una sección `## Resultado auditoría 2026-05-05`, con una tabla por agente:

| Agent ID | ¿Tiene system prompt real? (path + first 5 lines) | ¿Tiene skills propias? | ¿Tiene config no-default? | Invocaciones últimos 30d | Recomendación final | Justificación |

Y al final de la tabla, **clasificación final**:

- **Archivar inmediatamente** (mover a `~/.openclaw/agents/_archive/`): lista.
- **Promover a Gerencia** (mantener + completar charter después): lista.
- **Reconvertir a skill** (extraer lógica útil + borrar agent): lista, indicando skill destino y gerencia destino.
- **Caso ambiguo / requiere decisión humana**: lista con recomendación opcional.

## Reglas operativas

1. **NO modificar nada** en esta task. Es read-only audit. Cualquier cambio (archivar, mover, borrar) viene en task posterior con aprobación de David.
2. **NO inventar uso** si los logs no lo muestran. "0 invocaciones" es resultado válido.
3. **Respetar memoria cross-repo**: este archivo se commitea a `umbral-agent-stack/main` para que Copilot Chat lo vea de vuelta.
4. **Push obligatorio** cuando termines: `git add` + commit + `git push origin main`.
5. **Si encontrás secretos** en algún archivo de agent → reportar **path + tipo de secreto**, NUNCA pegar el valor en el output.

## Referencias

- Doc del modelo: `notion-governance/docs/architecture/15-rick-organizational-model.md` (commit `7a11af7`).
- Task que originó esto: `2026-05-05-001-copilot-vps-telegram-bot-bind-o15.md` (HOLD por falta de prefix routing en OC 5.3-1).
- Baseline OpenClaw: `2026.5.3-1 (2eae30e)`, `~/.openclaw/openclaw.json` md5 `44be041f8650197b6e00c35034d96282`.

## Resultado auditoría 2026-05-05

**Ejecutado por:** copilot-vps (sesión Copilot Chat con SSH/local en VPS Hostinger)
**Fecha:** 2026-05-05
**Modo:** read-only (no se modificó ningún archivo de runtime).
**Baseline OpenClaw:** `~/.openclaw/openclaw.json` registra los 9 agentes (incluye `main`). Versión gateway en logs: `v2026.3.2`.

### Hallazgo central — la hipótesis de §5 está parcialmente equivocada

La §5 del modelo organizacional asumía que la mayoría de los 8 subagents son "placeholders sin contenido". **La realidad runtime contradice esa suposición en 7 de 8 casos.** El verdadero "placeholder" runtime es `improvement-supervisor`. Los demás tienen `IDENTITY.md`, `SOUL.md`, `AGENTS.md` y/o `ROLE.md` reales y, en varios casos, carteras grandes de skills propias.

**Importante sobre la estructura real:** El "system prompt" de cada agent NO vive en `~/.openclaw/agents/<id>/`. Esa ruta solo contiene `sessions/` (jsonl de runtime) y, opcionalmente, `agent/` con `auth-profiles.json` / `models.json` / `auth-state.json`. **El charter real de cada agent vive en `~/.openclaw/workspaces/<id>/`** (junto al symlink `umbral-agent-stack` y al directorio `skills/`). Esto se cargó vía la convención OpenClaw `AGENTS.md` + `IDENTITY.md` + `SOUL.md` + `ROLE.md` + `TOOLS.md` que el gateway lee del workspace en cada sesión.

### Tabla por agente

| Agent ID | ¿Tiene system prompt real? (path + first 5 lines) | ¿Tiene skills propias? | ¿Tiene config no-default? | Invocaciones últimos 30d (sessions live + journal mentions) | Recomendación final | Justificación |
|---|---|---|---|---|---|---|
| `rick-orchestrator` | **Sí, sustancial.** `~/.openclaw/workspaces/rick-orchestrator/` contiene `AGENTS.md` (17 KB), `SOUL.md` (12 KB, 13 reglas operativas: gobernanza de proyectos, handoffs, integración de subagentes, prohibición push a main, etc.), `IDENTITY.md`, `ROLE.md` ausente pero `SKILL.md` (8.6 KB) presente. Primeras líneas IDENTITY: `# Rick Orchestrator / Mision: descomponer pedidos, decidir estrategia y delegar a delivery, qa, tracker u ops.` | **Sí, 26 skills** (agent-handoff-governance, linear-*, gmail, google-calendar, granola-pipeline, editorial-*, n8n-editorial-orchestrator, etc.) | Sí: `subagents.allowAgents = [rick-delivery, rick-qa, rick-tracker, rick-ops]`; tools.profile=`coding` + 60 alsoAllow extras. Modelo: `azure-openai-responses/gpt-5.4`. | **51 sessions live + 7 menciones en journalctl.** Es el agent con más uso real. | **Promover a Gerencia (de Orquestación / CEO-aux) — NO archivar.** El doc §5 dice "vacío / redundante con main" — es **falso**. Es el meta-orquestador real con 13 reglas operativas, 26 skills propias y allowAgents activo. | El charter es enorme y diferenciado de `main` (incluye reglas específicas de delegación, gobernanza de Linear projects, integración de sessions_spawn). Re-prompt OK, pero no archivar. |
| `rick-delivery` | **Sí, real pero corto.** `workspaces/rick-delivery/AGENTS.md` (565 B), `IDENTITY.md` ("ejecutar entregables y producir artefactos concretos"), `SOUL.md` con guardrails ejecución 2026-03-09 ("Primero ejecuta, luego reporta"), `TOOLS.md` (7.2 KB compartido). | **Sí, 29 skills** (la mayor cartera) — competitive-funnel-benchmark, document-generation, editorial-*, figma, gmail, google-calendar, granola-pipeline, linear, etc. | Modelo: gpt-5.4; tools.profile=coding + 56 alsoAllow. Sin allowAgents (no spawnea subagentes). | **1 session live + 1 mención en journal** (la sesión es de 2026-03-09, agent vivo pero usado raramente directo; rick-orchestrator delega a él vía sus propias 51 sesiones). | **Reconvertir a "Gerencia de Delivery" o mantener como agent-de-equipo dentro de Desarrollo.** NO archivar. | Tiene la mayor cartera de skills (29). Es el ejecutor real cuando orchestrator delega. Si el modelo organizacional separa CEO+6 gerencias, este encaja como Gerencia de Desarrollo/Delivery. La hipótesis "ambiguo, sin uso" es **falsa**: tiene contenido, tiene skills, tiene rol diferenciado de orchestrator. |
| `rick-qa` | **Sí, real.** `workspaces/rick-qa/AGENTS.md` (571 B): "revisar calidad, consistencia, riesgos y criterios de aceptacion". `IDENTITY.md`, `SOUL.md` con guardrails idénticos a delivery, `TOOLS.md` (7.2 KB). | **Sí, 18 skills** (linear-project-auditor, linear-delivery-traceability, linear-issue-triage, n8n-editorial-orchestrator, llm-generate, etc.) | Modelo: gpt-5.4; profile=coding + 40 alsoAllow. | **1 session live + 5 menciones en journal.** | **Mantener como agent QA dedicado, NO reconvertir a skill.** | La hipótesis "no tiene contenido de gerencia, sí podría tener lógica QA → reconvertir a skill `qa-runner`" subestima la realidad: 18 skills propias, charter con guardrails y rol claro citado por orchestrator e improvement-supervisor. Reconvertir a skill **perdería** las 18 skills y la separación de modelo/tools. Mantener como agent dentro de la gerencia que David elija (Mejora Continua o Desarrollo). |
| `rick-tracker` | **Sí, real.** `workspaces/rick-tracker/AGENTS.md` (583 B), `IDENTITY.md` ("dar trazabilidad a tareas, incidencias, estatus y seguimiento operativo"), `SOUL.md`, `TOOLS.md`. | **Sí, 20 skills** (editorial-source-curation, editorial-voice-profile, gmail, google-calendar, linear, linear-delivery-traceability, etc.) | Modelo distinto al resto: **`google-vertex/gemini-3.1-pro-preview`** (único agent en Vertex). profile=coding + 56 alsoAllow. | **3 sessions live + 3 menciones en journal.** | **Caso ambiguo / requiere decisión humana.** Recomendación opcional: reconvertir el rol "trazabilidad operativa" a un sub-rol dentro de Mejora Continua, pero el agent tiene 20 skills útiles que valen reasignar más que tirar. | El doc §5 lo lee como "trackea experiencia, no es gerencia → skill". Tiene punto: el rol es horizontal (no es una gerencia). Pero tiene 20 skills y modelo Vertex único — convertirlo a skill `experience-tracker` requiere reubicar esas skills a otra parte. Decisión humana. |
| `rick-ops` | **Sí, real.** `workspaces/rick-ops/AGENTS.md` (586 B), `IDENTITY.md` ("operar el gateway, VPS, workers, observabilidad y automatizaciones del sistema"), `SOUL.md`, `TOOLS.md`, además directorios propios `notes/` y `runbooks/` (modificados 2026-05-04 y 2026-05-05 — uso activo). | **Sí, 19 skills** (browser-automation-vm, n8n-editorial-orchestrator, linear-*, llm-generate, etc.) | Modelo gpt-5.4; profile=coding + 74 alsoAllow (la cartera de tools más amplia después de `main`). | **50 sessions live + 10 menciones en journal.** Segundo agent más usado (después de orchestrator). | **Mantener como agent operativo (Gerencia de Operaciones / Plataforma) — NO reconvertir a skill.** | La hipótesis "Health/ops, no es gerencia → reconvertir a skills" es **falsa para los hechos runtime**: 50 sesiones reales, runbooks vivos en `workspaces/rick-ops/runbooks/`, 19 skills, tool surface más amplia. Es uno de los dos agentes que realmente trabaja. Convertirlo a skill rompería el ciclo operativo. |
| `rick-communication-director` | **Sí, real.** `workspaces/rick-communication-director/AGENTS.md` (821 B con calibración obligatoria), `IDENTITY.md` ("revisar si el copy publico suena a David y proponer variantes controladas"), `SOUL.md` corto y específico ("voz de David, AEC/BIM"), `USER.md`, `HEARTBEAT.md`. | **Sí, 1 skill** clave: `director-comunicacion-umbral` (con `CALIBRATION.md` + `SKILL.md`). | Modelo gpt-5.4 con fallbacks; profile=coding pero **solo 7 alsoAllow** (cartera estrechamente alineada al rol editorial). | **1 session live + 28 menciones en journal** (mención más alta de todo el set — el agent es invocado vía handoff desde rick-linkedin-writer). | **Promover a Gerencia de Comunicación / Marketing (semilla válida) — confirmado.** | Coincide con la hipótesis §5. Charter limpio, skill diferenciada, tool-surface mínima coherente. La cantidad de menciones en journal (28) sugiere que `rick-linkedin-writer` lo invoca como handoff obligatorio (declarado en su propio AGENTS.md). |
| `rick-linkedin-writer` | **Sí, muy real.** `workspaces/rick-linkedin-writer/ROLE.md` (4.2 KB con purpose, responsibilities, boundaries, anti-slop blacklist, acceptance criteria, handoff obligatorio a `rick-communication-director`). `AGENTS.md` (1.1 KB) con lectura obligatoria de 4 archivos antes de generar drafts. | **Sí, 1 skill:** `linkedin-post-writer` (con `LINKEDIN_WRITING_RULES.md` + `CALIBRATION.md` + `SKILL.md`). | Modelo gpt-5.4 con fallbacks; profile=coding pero **solo 3 alsoAllow** (la cartera más estrecha — coherente con scope puntual). | **2 sessions live + 5 menciones en journal.** | **Caso ambiguo: skill bien envuelta. Recomendación opcional: mantener como agent dedicado, NO reconvertir a skill.** | El doc §5 dice "skill puntual mal envuelto en agent → reconvertir". Argumento en contra: el agent tiene boundaries explícitos, handoff obligatorio formalizado, anti-slop blacklist y un `ROLE.md` de 4 KB — eso es más que una skill, es un rol con contrato. Reconvertir a skill perdería el handoff cross-agent. **Decisión humana.** Si se reconvierte, debe migrar simultáneamente el handoff a `rick-communication-director` a un mecanismo intra-skill. |
| `improvement-supervisor` | **Charter sí, runtime no.** `workspaces/improvement-supervisor/ROLE.md` (21 KB — el más grande), declara explícitamente **"design-only. Not active. Not registered."** y dice que `OpenClaw registration → absent`. **PERO sí está registrado en `~/.openclaw/openclaw.json`** con `agentDir: ~/.openclaw/agents/improvement-supervisor/agent` (path **no existe en disco**). No tiene `IDENTITY.md/SOUL.md/AGENTS.md` propios. | **No, 0 skills** en `workspaces/improvement-supervisor/skills/` (directorio inexistente). | Registro mínimo en openclaw.json (solo id, name, model, workspace, agentDir roto). Sin tools.alsoAllow. | **1 session live (creada hoy 2026-05-05 02:48 UTC, posiblemente test) + 0 menciones en journal.** | **Caso ambiguo / requiere decisión humana.** Recomendación opcional: **alinear repo↔runtime** — o (a) borrar el registro de openclaw.json y mantener `ROLE.md` como design-only, o (b) completar `IDENTITY.md`/`SOUL.md`/skills si Mejora Continua va a activarse en Ola 1. | **Divergencia repo↔VPS detectada.** El propio `ROLE.md` afirma que el agent NO está registrado, pero sí lo está (con `agentDir` apuntando a path inexistente). Esto es exactamente la regla "VPS Reality Check" del repo: la intención del repo (ROLE.md design-only) contradice el runtime (entrada en openclaw.json). El doc §5 dice "promover a Gerencia de Mejora Continua" — antes de promover, **resolver la divergencia** y decidir si se activa o se borra el registro huérfano. |

### Clasificación final

#### Archivar inmediatamente (mover a `~/.openclaw/agents/_archive/`)
**Ninguno.** Ningún subagent califica como "vacío sin contenido" según evidencia runtime. La hipótesis §5 de archivar `rick-orchestrator` y `rick-delivery` es **falsa**.

#### Promover a Gerencia (mantener + completar charter después)
1. **`rick-orchestrator`** → Gerencia de Orquestación / función CEO-auxiliar (es el meta-orquestador real, 51 sesiones, 26 skills, 13 reglas operativas).
2. **`rick-communication-director`** → Gerencia de Comunicación (semilla limpia, charter coherente, 28 menciones en journal vía handoff).
3. **`rick-ops`** → Gerencia de Operaciones / Plataforma (50 sesiones, 19 skills, runbooks vivos).
4. **`rick-delivery`** → Gerencia de Desarrollo / Delivery (29 skills, ejecutor real cuando orchestrator delega).

#### Reconvertir a skill (extraer lógica útil + borrar agent)
**Ninguno como obligatorio.** Reconvertir cualquier agent con ≥18 skills propias destruiría más valor del que rescata. La hipótesis §5 sobreestima cuánto se puede comprimir un agent en un skill.

#### Casos ambiguos / requieren decisión humana
1. **`rick-qa`** — El doc §5 dice "reconvertir a skill `qa-runner`". Mi recomendación: **mantenerlo como agent**, agruparlo bajo Mejora Continua o Desarrollo. 18 skills + rol claro lo justifican. Si David igual quiere comprimir, hay que migrar las 18 skills a otra ubicación primero.
2. **`rick-tracker`** — Único agent con modelo Vertex (gemini-3.1-pro-preview), 20 skills, rol horizontal (trazabilidad). El doc §5 dice "reconvertir a skill `experience-tracker` dentro de Mejora Continua". Razonable, pero requiere reubicar 20 skills y decidir si el cambio de provider (Vertex → Azure) es aceptable.
3. **`rick-linkedin-writer`** — El doc §5 dice "reconvertir a skill `linkedin-writer`". Tiene handoff cross-agent formalizado y `ROLE.md` de 4 KB con boundaries. Reconvertir requiere reformular el handoff a `rick-communication-director`.
4. **`improvement-supervisor`** — **Divergencia repo↔VPS bloqueante.** ROLE.md (21 KB) dice "no registrado"; openclaw.json sí lo tiene registrado con `agentDir` roto. **Antes de promover a Gerencia de Mejora Continua, hay que decidir:** (a) borrar el registro huérfano y mantener design-only, o (b) crear `agentDir` real con `IDENTITY.md`/`SOUL.md`/skills y activar siguiendo `docs/77-improvement-supervisor-phase6-activation-plan.md`.

### Otros hallazgos relevantes

- **Modelo asignado por agent (de openclaw.json):** 7 agents usan `azure-openai-responses/gpt-5.4`; **`rick-tracker` es el único en `google-vertex/gemini-3.1-pro-preview`**. Si el modelo organizacional asume homogeneidad de provider, esto es una excepción a documentar.
- **Tool surfaces (alsoAllow count):** main=79, rick-ops=74, rick-orchestrator=60, rick-delivery=56, rick-tracker=56, rick-qa=40, rick-communication-director=7, rick-linkedin-writer=3, improvement-supervisor=0. Los dos editoriales tienen surfaces estrechas y coherentes; ops/delivery/tracker/qa tienen surfaces amplias casi indistinguibles entre sí (potencial área de simplificación, no de archivado).
- **`subagents.allowAgents`:** solo `main` y `rick-orchestrator` tienen permiso de spawn. Los demás son leaves del grafo. Coherente.
- **Cross-references en charters:**
  - `rick-orchestrator/SKILL.md` enumera explícitamente las skills clave de cada subagent (mapa real de delegación).
  - `improvement-supervisor/ROLE.md` referencia a `rick-orchestrator`, `rick-delivery`, `rick-qa` como receptores de redirects.
  - `rick-linkedin-writer/AGENTS.md` y `ROLE.md` formalizan handoff a `rick-communication-director` (explica los 28 hits en journal de comm-director).
  - `rick-communication-director`, `rick-delivery`, `rick-ops`, `rick-qa`, `rick-tracker` no se referencian entre sí en sus charters.

### Secretos detectados (NO se pegan valores)

Cinco agents tienen `auth-profiles.json` y/o `auth-state.json` con tokens reales en disco (modo 0700, accesible solo a `rick`):

| Path | Tipo de secreto |
|---|---|
| `~/.openclaw/agents/rick-delivery/agent/auth-profiles.json` | OAuth/API tokens para `anthropic:manual`, `google-vertex:default` (refresh+access), `google:default` (key), `openai-codex:default` (key). |
| `~/.openclaw/agents/rick-qa/agent/auth-profiles.json` | Mismo set de proveedores que rick-delivery. |
| `~/.openclaw/agents/rick-tracker/agent/auth-profiles.json` + `auth-state.json` | Tokens runtime cacheados. |
| `~/.openclaw/agents/rick-communication-director/agent/models.json` | Solo config de providers (sin tokens en este archivo, pero el agent usa los del store global vía gateway). |
| `~/.openclaw/agents/rick-linkedin-writer/agent/models.json` | Igual al anterior. |

**Acción recomendada (no ejecutada en esta task read-only):** si en task posterior se decide archivar/reconvertir alguno de los 4 agents con `auth-profiles.json` (delivery, qa, tracker), **rotar tokens y borrar el JSON antes de mover el directorio a `_archive/`**, no solo `mv`. Los archivos están en 0700 pero se duplicarían.

### Cierre

- La task se ejecutó en modo read-only. **No se modificó ningún archivo runtime.** Solo se hizo `git pull` en el repo y append a este propio archivo.
- Recomendación general para Ola 1: **el doc `15-rick-organizational-model.md` §5 debe revisarse antes de archivar nada.** Su mapeo conceptual subestima sistemáticamente lo que ya existe runtime. Sugerencia concreta: re-escribir §5 con esta tabla como base y dejar §5-original como "hipótesis pre-auditoría".
- Bloqueante para Ola 1 (re-prompt + archivar): la divergencia `improvement-supervisor` repo↔VPS debe resolverse primero (decidir activar o borrar registro huérfano).

