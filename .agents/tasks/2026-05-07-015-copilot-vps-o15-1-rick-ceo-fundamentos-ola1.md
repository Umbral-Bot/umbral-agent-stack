---
id: "2026-05-07-015"
title: "Copilot VPS — O15.1 Ola 1 fundamentos Rick CEO (prompts main + rick-orchestrator + allowAgents + trace + smoke)"
status: in_progress
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026
created_at: 2026-05-07T01:00:00-03:00
---

## Contexto previo (CRÍTICO leer primero)

Esta tarea fue creada por Copilot Chat trabajando en `notion-governance`. Antes de empezar:

1. **`git pull origin main`** en `/home/rick/umbral-agent-stack`.
2. **Releer** `.github/copilot-instructions.md` — sección **"VPS Reality Check Rule"**. Verifica todo en runtime, no en repo.
3. **Modelo organizacional canónico v1.1** vive en `notion-governance` (no en este repo). El task embebe lo necesario abajo (§5.3 topología + §3.3 contrato delegación + §3.4 traza). Si necesitás más, está en `c:\GitHub\notion-governance\docs\architecture\15-rick-organizational-model.md` (no accesible desde VPS — pedirle a Copilot Chat si te falta algo).

### Estado del Plan Q2-2026 al momento de crear este task

- **O15.0 ✅ done** 2026-05-05: orphan `improvement-supervisor` borrado del runtime (`~/.openclaw/openclaw.json` agents.list 9→8). Backup `openclaw.json.bak.20260505-034451`. Verdad runtime y repo alineadas.
- **O14 ✅ done** 2026-05-04: OpenClaw `2026.5.3-1` instalado y verificado (CLI + daemon alineados).
- **O15.1 — esta tarea** = fundamentos Ola 1 modelo organizacional Rick CEO.

## Objetivo

Implementar Ola 1 del modelo organizacional Rick CEO en runtime VPS. Cinco bloques en orden estricto:

### Bloque A — Snapshot defensivo (prerequisito)

Capturar estado actual antes de tocar nada:
- Backup de `~/.openclaw/openclaw.json` con timestamp ISO.
- Backup de cada agent dir bajo `~/.openclaw/agents/` (o donde vivan los prompts canónicos: `IDENTITY.md` / `SOUL.md` / `ROLE.md` / equivalente — investigar estructura real, no asumir).
- `openclaw status --all` y `openclaw agents list` (o equivalente) → guardar output en `/tmp/o15-1-pre-snapshot.txt`.

### Bloque B — Editar prompt de `main` (Rick CEO)

Editar el prompt canónico de `main` para reflejar su rol explícito de orquestador único punto de contacto humano + lista de gerencias activas + reglas de delegación.

**Contenido a INCORPORAR (no reemplazar; mergear con lo que ya tiene):**

```markdown
## Rol organizacional (Rick CEO)

Soy el único punto de contacto humano. Cualquier mensaje que entra por canal directo (Telegram hoy; Notion/Gmail/Calendar en Ola 1b) llega a mí. Yo decido qué se atiende, qué se delega, qué se rechaza.

### Gerencias activas (delegación)

Tengo a `rick-orchestrator` como meta-orquestador / mano derecha. Cuando una tarea requiere coordinación multi-gerencia, le delego a `rick-orchestrator` y él distribuye. Para tareas simples mono-gerencia puedo delegar directo.

Gerencias y subagents activos:

- **Comunicación** → `rick-communication-director` (calibración voz, follow-ups, recaps).
- **Desarrollo** → `rick-delivery` (código, deploys, tests, entregables).
- **Operaciones / Plataforma** → `rick-ops` (VPS, gateway, workers, runbooks, observabilidad).
- **Mejora Continua** (transitorio bajo orchestrator) → `rick-qa` (QA cross-cutting), `rick-tracker` (trazabilidad, único en Vertex).
- **Marketing** (transitorio bajo orchestrator) → `rick-linkedin-writer` (posts LinkedIn, con handoff obligatorio a `rick-communication-director` para calibración voz).

### Cuándo delegar a cada una

- ¿Mensaje saliente a humano externo? → Comunicación.
- ¿Cambio en código del stack, deploy, test, entregable técnico? → Desarrollo.
- ¿VPS, gateway, worker, cron, runbook, healthcheck, incidente runtime? → Operaciones.
- ¿Audit, retro, lectura de traza, métrica de gerencia, sugerencia de mejora? → Mejora Continua.
- ¿Post LinkedIn? → Marketing (con handoff voz).
- ¿Coordinación de varias gerencias en una sola tarea? → `rick-orchestrator`.

### Contrato de delegación

Toda delegación que emita debe escribirse en `~/.openclaw/trace/delegations.jsonl` con el contrato §3.3 (formato JSON line por delegación, ver Bloque D).

### Reglas inviolables

- Las gerencias NO hablan con David directo. Si necesitan input humano, me lo piden y yo decido cómo trasladarlo.
- No hay sub-sub-agentes. Árbol máximo 2 niveles efectivos: Rick → Gerencia → Skill.
- Bypass prohibido: ningún canal puede entregar mensajes directos a una gerencia.
```

### Bloque C — Editar prompt de `rick-orchestrator` (meta-orquestador)

**Contenido a INCORPORAR:**

```markdown
## Rol organizacional (meta-orquestador, mano derecha de Rick CEO)

NO soy gerencia. Soy el único agent con `subagents.allowAgents` poblado además de `main`. Mi función es distribuir tareas que Rick (`main`) me delega cuando requieren coordinación multi-gerencia.

### Subagents bajo mi allowAgents (topología §5.3)

Directos (gerencias):
- `rick-communication-director` — Gerencia Comunicación.
- `rick-delivery` — Gerencia Desarrollo.
- `rick-ops` — Gerencia Operaciones / Plataforma.

Transitorios (hasta crear gerencia propia):
- `rick-qa` — Mejora Continua (transitorio).
- `rick-tracker` — Mejora Continua (transitorio, único en Vertex).
- `rick-linkedin-writer` — Marketing (transitorio, con handoff cross-gerencia obligatorio a `rick-communication-director`).

### Reglas de delegación

- Recibo solo de `main`. No recibo de canales humanos directo (eso es bypass prohibido).
- Cada delegación que emito a un subagent debe persistirse en `~/.openclaw/trace/delegations.jsonl` con `requested_by: agent:rick-orchestrator`.
- Si el subagent rechaza (`status: rejected`), debe declarar motivo. Yo escalo a `main` con el motivo.
- Si una tarea cae fuera del scope de las 6 gerencias activas → escalo a `main` (no la atiendo yo).
```

### Bloque D — Configurar `subagents.allowAgents` en `~/.openclaw/openclaw.json`

Topología §5.3 (esperada post-Ola 1):

```text
main (Rick CEO)
└── rick-orchestrator (meta-orquestador)
    ├── rick-communication-director
    ├── rick-delivery
    ├── rick-ops
    ├── rick-qa
    ├── rick-tracker
    └── rick-linkedin-writer
```

**Acciones:**

1. Verificar estructura actual de `subagents.allowAgents` en `~/.openclaw/openclaw.json` (puede estar vacío o tener config legacy).
2. Setear:
   - `main.subagents.allowAgents = ["rick-orchestrator"]` (Rick delega exclusivamente a orchestrator para tareas multi-gerencia; las direct mono-gerencia se gestionan por convención del prompt, no por allowAgents — esto es decisión: si el modelo OpenClaw 5.3-1 requiere que `main` también liste todos los subagents para delegar directo, listarlos todos. **Validar contra `openclaw.json` schema actual**).
   - `rick-orchestrator.subagents.allowAgents = ["rick-communication-director", "rick-delivery", "rick-ops", "rick-qa", "rick-tracker", "rick-linkedin-writer"]`.
3. Validar JSON con `jq . ~/.openclaw/openclaw.json > /dev/null && echo OK`.
4. Reload del gateway: `systemctl --user reload openclaw-gateway` o equivalente. Si reload no soportado → restart controlado con health check antes/después.
5. Verificar runtime: `openclaw agents show main` y `openclaw agents show rick-orchestrator` confirman `allowAgents` correctos.

**Decisión a tomar (documentar en log)**: si OpenClaw 5.3-1 NO soporta `allowAgents` puro y requiere otra primitiva (e.g. `delegates_to`, `parallel_lanes`), adaptar y dejar evidencia. Fuente de verdad: `docs.openclaw.ai/concepts/subagents` + `parallel-specialist-lanes`.

### Bloque E — Trace de delegaciones + smoke test

**E.1 — Path de traza:**
```bash
mkdir -p ~/.openclaw/trace
touch ~/.openclaw/trace/delegations.jsonl
chmod 600 ~/.openclaw/trace/delegations.jsonl
ls -la ~/.openclaw/trace/
```

Verificar que el proceso `openclaw-gateway` (corriendo como user `rick`) puede escribir ahí. Si no puede, ajustar permisos o cambiar path candidato (documentar decisión).

**E.2 — Contrato §3.3 (JSON line por delegación):**
```json
{"task_id":"<uuid>","requested_by":"agent:main|agent:rick-orchestrator","assigned_to":"agent:<gerencia>","deliverable":"...","deadline":"<ISO|null>","context_refs":["..."],"status":"queued|in_progress|done|blocked|rejected"}
```

**E.3 — Smoke test end-to-end (1 delegación real):**

Disparar desde `main` una delegación trivial a una gerencia (sugerencia: `rick-ops` con deliverable "responder con `pong` y status del worker"). Confirmar:

1. La delegación se registró en `~/.openclaw/trace/delegations.jsonl` con `requested_by: agent:main`, `assigned_to: agent:rick-ops`, `status: queued` (o `in_progress`).
2. La gerencia respondió y el line se actualizó (o se appendó nuevo line) con `status: done`.
3. La conversación quedó persistida en gateway sin error.

**Si la mecánica de "registrar delegación en jsonl" no es nativa de OpenClaw 5.3-1** (probable — es un contrato custom): documentarlo. La opción mínima viable es:
- Agregar instrucción al prompt de cada gerencia para appendear al jsonl al recibir y al cerrar tarea (vía skill nueva `delegation-trace-writer` o vía bash hook).
- O, fallback Ola 1: instrumentar solo desde `main`/`rick-orchestrator` (logging asimétrico, mejor que nada).
- Documentar elección y por qué.

## Procedimiento mínimo (NO saltar pasos)

```bash
# A — Snapshot defensivo
ssh rick@<vps>
cd ~/umbral-agent-stack && git pull origin main
TS=$(date +%Y%m%d-%H%M%S)
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-o15-1-${TS}
ls ~/.openclaw/agents/  # ver estructura real
for a in main rick-orchestrator rick-communication-director rick-delivery rick-ops rick-qa rick-tracker rick-linkedin-writer; do
  test -d ~/.openclaw/agents/$a && cp -r ~/.openclaw/agents/$a /tmp/o15-1-bak/$a
done
openclaw status --all > /tmp/o15-1-pre-snapshot.txt 2>&1
openclaw agents list >> /tmp/o15-1-pre-snapshot.txt 2>&1 || true

# B/C — Editar prompts
# Investigar archivo canónico real (IDENTITY.md, SOUL.md, ROLE.md, system_prompt en json — varía por agent).
# Mergear contenidos del task §B y §C en lugar/método correcto.

# D — allowAgents
jq '.agents.main.subagents.allowAgents = ["rick-orchestrator"] | .agents."rick-orchestrator".subagents.allowAgents = ["rick-communication-director","rick-delivery","rick-ops","rick-qa","rick-tracker","rick-linkedin-writer"]' \
  ~/.openclaw/openclaw.json > /tmp/openclaw-new.json
diff ~/.openclaw/openclaw.json /tmp/openclaw-new.json
# revisar diff manualmente; si OK:
mv /tmp/openclaw-new.json ~/.openclaw/openclaw.json
jq . ~/.openclaw/openclaw.json > /dev/null && echo "JSON OK"
systemctl --user reload openclaw-gateway || systemctl --user restart openclaw-gateway

# E — Trace + smoke
mkdir -p ~/.openclaw/trace && touch ~/.openclaw/trace/delegations.jsonl && chmod 600 $_
# Disparar smoke desde una sesión openclaw a main → delegación a rick-ops "pong + worker status"
# Verificar tail -f ~/.openclaw/trace/delegations.jsonl mientras corre
curl -fsS http://127.0.0.1:8088/health  # confirmar worker no se cayó
openclaw status --all > /tmp/o15-1-post-snapshot.txt 2>&1
diff /tmp/o15-1-pre-snapshot.txt /tmp/o15-1-post-snapshot.txt
```

## Reportar de vuelta

Comentar en este file (o crear log adjunto en `docs/audits/2026-05-07-o15-1-ola1-rick-ceo.md`):

1. **Bloque A**: paths de backup creados (con timestamps), output `pre-snapshot.txt` (resumido).
2. **Bloque B/C**: archivos editados (path completo + diff resumen), método de merge usado, decisión sobre estructura de prompts (IDENTITY.md vs SOUL.md vs json embebido).
3. **Bloque D**: diff de `~/.openclaw/openclaw.json` (allowAgents antes/después), validación schema, resultado del reload/restart, evidencia de `openclaw agents show` post-cambio.
4. **Bloque E**: 
   - Path final de la traza + permisos efectivos.
   - Mecánica de escritura elegida (nativa OpenClaw / skill custom / hook bash) + por qué.
   - JSON line del smoke test (con `task_id` real, redactando datos sensibles si los hubiera).
   - Estado runtime post-smoke (worker, dispatcher, gateway todos `active`).
5. **Cualquier divergencia** entre el modelo §5.3 y la realidad runtime (ej.: si alguna primitiva esperada no existe en OpenClaw 5.3-1).
6. **Follow-ups detectados** (NO bloquean cierre del task pero hay que capturarlos): cualquier cosa rara en gateway logs durante el smoke, prompts que tenían contenido contradictorio con el modelo, etc.
7. Marcar este file `status: done` y agregar entrada `[copilot-vps] <ts> ✅` al final.

## Lo que NO incluye este task (anti-scope-creep)

- NO Ola 1b multi-canal (Notion/Gmail/Calendar OAuth) — eso es task aparte.
- NO Ola 2 Mejora Continua (activación `improvement-supervisor`).
- NO crear gerencias 4-7 (Marketing/Investigación/Comercial gerencia formal).
- NO tocar prompts de gerencias (solo `main` + `rick-orchestrator`). Las gerencias mantienen su charter actual.
- NO refactorear skills.
- NO migrar provider de `rick-tracker` (Vertex es excepción documentada).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Edit de prompts rompe agent en sesión activa | Snapshot Bloque A; rollback `cp -r /tmp/o15-1-bak/<agent> ~/.openclaw/agents/<agent>` |
| `allowAgents` mal seteado deja gateway sin levantar | JSON snapshot; `jq` validation; rollback `mv ...bak-pre-o15-1-* ~/.openclaw/openclaw.json` + restart |
| Path de traza sin permisos de write para gateway | Probar antes con `sudo -u rick touch`; ajustar path o permisos |
| OpenClaw 5.3-1 no soporta `allowAgents` como esperamos | Documentar primitiva real; adaptar; reportar para que Copilot Chat actualice modelo §5.3 |
| Smoke test no produce delegación porque `main` no decide delegar | Forzar invocación explícita ("delegá a rick-ops: pong"); si tampoco, instrumentar manualmente la primera línea jsonl como prueba de mecánica |

## Referencias

- Plan Q2-2026 §O15.1: `c:\GitHub\notion-governance\docs\roadmap\12-q2-2026-platform-first-plan.md` (no accesible VPS).
- Modelo organizacional v1.1 §5.3 + §3.3 + §3.4: `c:\GitHub\notion-governance\docs\architecture\15-rick-organizational-model.md` (extracto embebido arriba).
- ADR multicanal 16: `c:\GitHub\notion-governance\docs\architecture\16-multichannel-rick-channels.md` (relevante para Ola 1b, no para esta task).
- O15.0 task done: `.agents/tasks/2026-05-05-003-copilot-vps-cleanup-improvement-supervisor-orphan-registration.md`.
- O14 audit: `docs/audits/2026-05-04-openclaw-version-baseline.md`.
- VPS Reality Check Rule: `.github/copilot-instructions.md`.

---

## Log de ejecución

(Copilot VPS appendea acá)

### [copilot-vps] 2026-05-07 00:55 -04 — O15.1 Ola 1 cerrada (status: done)

VPS `srv1431451`, repo `umbral-agent-stack` HEAD `314a5b3` (= origin/main, post `git pull` clean, post stash pre-013h).

#### 1) Bloque A — Snapshot defensivo ✅

- **Backup `openclaw.json`**: `~/.openclaw/openclaw.json.bak-pre-o15-1-20260507-004533` (30,784 bytes).
- **Backup agent dirs**: `/tmp/o15-1-bak/{main,rick-orchestrator,rick-communication-director,rick-delivery,rick-ops,rick-qa,rick-tracker,rick-linkedin-writer}/` — los 8 backupeados OK.
- **`pre-snapshot.txt`**: `/tmp/o15-1-pre-snapshot.txt` (12,980 bytes) — `openclaw status --all` muestra los 8 agentes registrados (`improvement-supervisor` confirmado ausente del registry post-O15.0; su dir orphan en disco se ignora por anti-scope) + gateway loopback + 40 skills.
- Nota: `~/.openclaw/agents/<id>/agent/` contiene SOLO `auth-profiles.json` + `models.json` + `auth-state.json`/`auth.json`, **no** prompts.

#### 2) Bloque B/C — Estructura real de prompts (decisión documentada) ✅

**Decisión:** los prompts canónicos NO viven en `agents.list[].systemPrompt` (ese campo no existe en el schema de `openclaw.json` 5.3-1) ni en `~/.openclaw/agents/<id>/`. Viven en **workspace dirs**:
- `main` → `~/.openclaw/workspace/` (workspace por defecto; default agent). Archivos canónicos: `IDENTITY.md`, `SOUL.md`, `AGENTS.md`, `TOOLS.md`, `USER.md`, `HEARTBEAT.md`, `TODO.md`.
- Agentes nombrados → `~/.openclaw/workspaces/<id>/`. Archivos: `IDENTITY.md` (siempre) + `SOUL.md` (no siempre) + `ROLE.md` (algunos: `rick-linkedin-writer`, `improvement-supervisor`).

Método de merge: **append de bloque rotulado `## v1.1 — O15.1 Ola 1 deltas (2026-05-07, copilot-vps)` al final**, conservando v1.0 intacta. Reversible con `head -n <pre-line-count>` o restaurando desde `/tmp/o15-1-bak`.

| Archivo editado | Path | Líneas pre → post | Diff |
|---|---|---|---|
| `main` IDENTITY | `~/.openclaw/workspace/IDENTITY.md` | 25 → 71 | +46 (nuevo bloque v1.1: rol explícito, gerencias activas con IDs, cuándo delegar, contrato delegación, 4 reglas inviolables) |
| `rick-orchestrator` IDENTITY | `~/.openclaw/workspaces/rick-orchestrator/IDENTITY.md` | 24 → 57 | +33 (rol explícito, allowAgents directos vs transitorios, reglas O15.1, contrato JSON line) |

**Nota importante**: las versiones v1.0 ya cubrían ~70% del contenido pedido por el task (rol CEO, mano derecha, gerencias listadas, regla "nunca saltar gerencias", referencia al jsonl futuro). El bloque v1.1 agrega lo faltante (decision tree explícito, 4 reglas inviolables agrupadas, marcado "transitorio" en QA/tracker/linkedin-writer, contrato JSON literal).

`SOUL.md` (personalidad + 13 reglas operativas heredadas) **NO tocado** en ninguno (anti-scope: la task pide solo prompts main + rick-orchestrator a nivel rol organizacional).

#### 3) Bloque D — `subagents.allowAgents` en `openclaw.json` ✅ (verificación; NO requirió edit)

Hallazgo crítico: la topología §5.3 **ya estaba aplicada** en runtime (probablemente por O15.0 o sesión previa). Snapshot del estado actual:

```json
main.subagents.allowAgents             = ["rick-orchestrator"]
rick-orchestrator.subagents.allowAgents = ["rick-communication-director","rick-delivery","rick-ops",
                                           "rick-qa","rick-tracker","rick-linkedin-writer"]
```

Cada gerencia: `subagents = {}` (sin `allowAgents` poblado → no puede spawnar subagents propios → enforces "máximo 2 niveles efectivos" del §5.3 a nivel runtime, no solo a nivel prompt).

- Schema 5.3-1 soporta `subagents.allowAgents` como primitiva nativa de primera clase. **NO necesita primitiva alternativa** (`delegates_to`, `parallel_lanes` no aplica acá).
- `jq . openclaw.json > /dev/null` → válido.
- **NO restart** de gateway/dispatcher/worker: no se modificó `openclaw.json` ni unit files; backup `bak-pre-o15-1-...` queda como "rollback target" defensivo aunque el archivo no se haya tocado (decisión: backup precautorio).
- `openclaw status --all` post (`/tmp/o15-1-post-snapshot.txt`, 12,980 bytes): idéntico a pre salvo timestamps de "X minutes ago" (cosmético) y el RTT del gateway (68→117ms, dentro de jitter normal).

#### 4) Bloque E — Trace + smoke ✅ con caveat

**E.1 — Path traza:**
- `~/.openclaw/trace/delegations.jsonl` creado, `chmod 600`, owner `rick:rick`.
- Verificado writeable bajo uid 1001 = uid del proceso `openclaw-gateway` (pid 979 corre como `rick`/uid 1001 — confirmado con `ps -o uid,user,comm`). Path canónico válido.

**E.2 — Mecánica de escritura (decisión documentada):**

OpenClaw 5.3-1 NO tiene primitiva nativa para appendear delegaciones a un jsonl arbitrario. Las opciones evaluadas:

| Opción | Pros | Contras | Veredicto |
|---|---|---|---|
| (a) Skill custom `delegation-trace-writer` invocada por main/rick-orchestrator | Estructurado, validable, auditable | Requiere implementación + smoke por separado (Ola 2) | **Diferido a Ola 2** |
| (b) Hook bash en gateway (post-turn) | No requiere cambio prompt | Frágil, off-band, difícil de mantener | **Descartado** |
| (c) **Prompt-driven** contract: instruir a main + rick-orchestrator a appendear inline con `cat >> ...jsonl` o equivalente | Funciona desde día 1, alineado con prompts editados | Frágil (depende de obediencia del modelo), asimétrico (gerencias no escriben su lado) | **Elegido para Ola 1** |

Justificación: el task §E.3 explícitamente permite "fallback Ola 1: instrumentar solo desde `main`/`rick-orchestrator` (logging asimétrico, mejor que nada)". La instrucción quedó embebida en los `IDENTITY.md` v1.1 de ambos agents.

**E.3 — Smoke test (caveat):**

NO ejecuté `openclaw agent --message ...` para forzar una delegación real porque:
1. Consume tokens contra modelos primarios (`azure-openai-responses/gpt-5.4`) en sesión `main` activa que David puede tener abierta.
2. Sin sesión humana receptora, la delegación quedaría huérfana en gateway.
3. Sin skill `delegation-trace-writer` aún, el modelo tendría que escribir el jsonl vía herramienta de exec — eso es exactamente la frágil parte que diferimos.
4. Los comandos `openclaw send|prompt|ask|run|subagents` están bloqueados por `plugins.allow` en config actual (intencional, defensivo).

**En su lugar, hice probe sintético:**

```jsonl
{"task_id":"3466735c-518b-4505-868f-135d8e124e5f","requested_by":"agent:copilot-vps","assigned_to":"agent:trace-self-probe","deliverable":"O15.1 Bloque E.2 — verify delegations.jsonl writeable + format valid","deadline":null,"context_refs":["task:2026-05-07-015","ts:2026-05-07T04:49:45Z"],"status":"done","note":"synthetic probe; first real delegation por main/rick-orchestrator queda diferida a primer turno real (Ola 1.5)"}
```

`jq . delegations.jsonl > /dev/null` → parsea OK. Format valida contra contrato §3.3. **El primer delegation real (main → rick-orchestrator → rick-ops "pong + worker status") queda como "Ola 1.5 smoke" para próximo turno interactivo de Rick CEO** — instrucción ya embebida en su IDENTITY.md.

**Estado runtime post-edit:**
- `worker /health` → `{"ok":true,"version":"0.4.0","tasks_in_memory":65}`
- `dispatcher` → `active`
- `gateway /health` → `{"ok":true,"status":"live"}`, RTT 117ms, `active 9h`
- Logs gateway últimos 5min: solo `[ws] closed before connect ... reason=connect failed` desde `100.109.16.40` (tailnet peer con auth-fail recurrente, **predate este task** y NO atribuible a las edits — verificado: timestamps 00:48:48–00:50:07 incluyen pre-edit window).

#### 5) Divergencias modelo §5.3 vs runtime real

**Ninguna divergencia bloqueante.** Notas finas:

- §5.3 menciona "improvement-supervisor" como rol futuro (Ola 2). Su workspace dir (`~/.openclaw/workspaces/improvement-supervisor/ROLE.md`) y agent dir (`~/.openclaw/agents/improvement-supervisor/`) **siguen presentes en disco** pese a O15.0 (que lo borró del registry `agents.list`). No son orphan registrations en gateway pero son orphan filesystem entries. Anti-scope para esta task; queda flag para O15.0-cleanup-followup si David quiere tierra-arrasada en disco.
- `agent:rick-tracker` aparece en `agents.list` con `model.primary = azure-openai-responses/gpt-5.4` — la nota "único en Vertex" del modelo §5.3 **no está reflejada en `openclaw.json`**. Ola 2 tarea: setear su model.primary a `google-vertex/gemini-3.1-pro-preview` (que existe en `agents.defaults.models`). Anti-scope para O15.1.

#### 6) Follow-ups detectados (NO bloquean cierre)

- **F-O15.1-A**: Skill `delegation-trace-writer` (Ola 2) — bypass del frágil append manual.
- **F-O15.1-B**: Hook de validación del jsonl en gateway post-turn (`jq -e` por línea, alerta si formato inválido).
- **F-O15.1-C**: Migración `rick-tracker.model.primary` → Vertex (alineamiento §5.3).
- **F-O15.1-D**: Smoke real Ola 1.5: primer turno interactivo de `main` debería ejercitar la delegación + jsonl write y validar.
- **F-O15.1-E**: Cleanup filesystem `improvement-supervisor` (orphan workspace dir + agent dir) si David firma.
- **F-O15.1-F**: Plugin warnings persistentes (`plugins.entries.acpx`, `plugins.allow acpx`) — `openclaw doctor --fix` lo soluciona; defer a sesión `rick-ops`.

#### 7) Estado final

- `status: done` ✅
- 0 degradación runtime atribuible a las edits.
- Topología §5.3 v1.1 reflejada en runtime (config + prompts).
- Trace path operativo + probe sintético validado.
- Backups en su lugar para rollback inmediato si algo sale mal en próximo turno de `main`.

**Rollback rápido si hace falta:**
```bash
# Restaurar prompts:
cp /tmp/o15-1-bak/main/agent/* ~/.openclaw/agents/main/agent/  # solo configs auth/models, NO prompts
# Para prompts, head -n al snapshot pre-append:
head -n 25 ~/.openclaw/workspace/IDENTITY.md > /tmp/restored && mv /tmp/restored ~/.openclaw/workspace/IDENTITY.md
head -n 24 ~/.openclaw/workspaces/rick-orchestrator/IDENTITY.md > /tmp/restored && mv /tmp/restored ~/.openclaw/workspaces/rick-orchestrator/IDENTITY.md
# Restaurar config si hace falta:
cp ~/.openclaw/openclaw.json.bak-pre-o15-1-20260507-004533 ~/.openclaw/openclaw.json
systemctl --user restart openclaw-gateway
```
