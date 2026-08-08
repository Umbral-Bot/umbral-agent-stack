# P1 — Higiene VPS (2026-08-07)

> **Pack:** PKG-UAS-P1-VPS-HYGIENE · rama `claude/pkg-uas-p1-vps-hygiene-20260807` ·
> base `fd0c962` (`origin/main` al momento del checkout)
> **Ejecutado por:** Claude, Remote-SSH sobre `/home/rick/umbral-agent-stack` (host `srv1431451`,
> usuario `rick`) — confirmado antes de tocar nada.
> **Estado: FASE 1 (inventario) completa. FASE 2–4 EJECUTADAS** el mismo día bajo
> PKG-UAS-P1-VPS-HYGIENE-EXEC (rama `claude/pkg-uas-p1-vps-hygiene-exec-20260807`, base
> `e07a5c1` = tip de `main` tras mergear este PR de Fase 1). GO citado textual: *"GO VPS
> HYGIENE"* + *"GO A LO MAS RECOMENDABLE E HIGENICO Y ROBUSTO, ANALIZA Y DECIDE"* (David,
> 2026-08-07). Ver §"Fase 2/3 — ejecutado" más abajo para el detalle before/after.

## 0. Contexto que evita duplicar trabajo

El closeout de higiene de hoy (`docs/ops/uas-p1-hygiene-closeout-20260807.md`) cubrió **solo
los clones Windows** (SYNC, Clone A `-copilot`, Clone B `-codex-coordinador`). La fila "P1
(closeout)" de `docs/ops/uas-north-canonical-2026-08-06.md` dice explícitamente: *"VPS higiene
diferida (pedido David: 'por ahora' solo F8A)."* Este pack es esa higiene VPS diferida — sin
solape con lo ya cerrado.

## A. Inventario de clones/worktrees bajo `/home/rick`

Patrones `main-clean` / `.tmp-*` / `dirty*` del enunciado del pack: **0 matches** en este host
(ese naming es específico del setup Windows). Inventario real por `*umbral*`:

### A.1 — El canónico

| Path | Branch | Status | Worktrees registrados | Stashes |
|---|---|---|---|---|
| `/home/rick/umbral-agent-stack` | `claude/pkg-uas-p1-vps-hygiene-20260807` (base `origin/main`) | limpio | 11 (ver A.3) | 25 (ver A.4) |

### A.2 — Clones standalone (`.git` propio, no worktree del canónico)

| Path | Branch | Status | Tamaño | Origen/nota |
|---|---|---|---|---|
| `~/.openclaw/workspace/umbral-agent-stack` | `rick/vps` (sin upstream en origin) | 1 archivo dirty: `openclaw/bin/worker-call` (**solo cambio de modo** 644→755, sin diff de contenido) | 9.4M | Vive dentro del **workspace live de Rick** (`agents.list[main].workspace`). Tip `4b8cfbb` (2026-06-07), rama nunca pusheada. No referenciado por ningún proceso activo (`lsof` vacío). **No tocar sin GO específico** — es zona operativa, no solo residuo. |
| `~/archive/uas/umbral-agent-stack-cand001-apply-20260629-174758` | `main` (stale) | limpio | 33M | **Ya inventariado y gateado** — ver A.5 |
| `~/archive/uas/umbral-agent-stack-cursor` | `rick/supervisor-structured-telemetry` | limpio | 390M | **Ya inventariado y gateado** — ver A.5 |
| `~/archive/uas/umbral-agent-stack.backup-pre-cand001-20260629-174640` | `rick-delivery/editorial-contract-paths` | dirty (untracked: `00_auditoria_schema_rick_cursor.md` + 3 yaml de `examples/pit/`) | 456M | **Ya inventariado y gateado** — ver A.5 |

### A.3 — Worktrees del canónico

| Path | Branch | Status | Proceso activo | Origen |
|---|---|---|---|---|
| `~/.openclaw/workspaces/rick-delivery/umbral-agent-stack-poller-hardening` | `rick-delivery/poller-healthcheck-hardening` | limpio | no | worktree de trabajo activo (nombre indica feature en curso) |
| `~/archive/uas/umbral-agent-stack-{activation-playbook,copilot-cli,editorial,f7-code-gate,f7-policy-gate,postmerge-evidence}` (6) | ramas `rick/copilot-cli-*` fósiles | limpio | no | **Ya inventariados y gateados** — ver A.5 |
| `/tmp/openclaw-oauth-apply-wt` | `rick/openclaw-oauth-apply-20260713` | dirty: 1 archivo (`.agents/tasks/2026-07-12-001-...md`, +33/-10) | no | Commit HEAD **ya mergeado** en `origin/main`; rama borrada de origin. El diff dirty es solo notas de tracking sobre ese task. |
| `/tmp/openclaw-oauth-only-urgent-wt` | `rick/openclaw-oauth-only-urgent-20260713` | dirty: mismo archivo (+30/-8) | no | Idéntico patrón — commit mergeado, rama borrada de origin, dirty = solo notas. |
| `/tmp/rick-hb-20260713-0143/wt-candidate` | detached `0d70b67` | limpio | no | Commit **"fix(notion): dedupe bot poller comments before action log"** (36+146 líneas) — **NO está en `origin/main`**. Es un fix de deduplicación de comentarios distinto al "P2.4 dedupe" que sí vive en main (ese es Shortlist-vs-backlog, no comment-level). Código real, no residuo trivial. |
| `/tmp/rick-hb-20260713-0143/wt-replay-on-origin` | detached `e5d650c` | dirty, staged: `dispatcher/notion_poller.py` + `tests/test_notion_poller.py` | no | Commit base ya mergeado, pero el **staged diff es código nuevo no commiteado**: guarda idempotencia de comentarios bot/echo cuando `created_time == last_ts` para evitar loop infinito de reprocesamiento. Tests incluidos (2 nuevos). Parece un fix real para un bug de loop en el poller, nunca aterrizado. |

### A.4 — Stashes del canónico

25 stashes acumulados (2026-05 a 2026-07). No se abrió ninguno en detalle — fuera del scope
estricto de A (que pide worktrees/clones); quedan listados para que un pack de higiene de
stashes los procese con el mismo criterio que usó el closeout de hoy en los clones Windows
(`drop` solo si contenido confirmado byte-idéntico en `main`).

### A.5 — `~/archive/uas/` ya tiene su propio gate — **no re-clasificar aquí**

`~/archive/uas/WHY.md` documenta que ese directorio fue creado 2026-07-03 bajo gate
**G-WH-VPS-1 Fase B** (autorizado por David), con la regla explícita: *"Borrado definitivo:
SOLO tras gate **G-WH-VPS-2** (≥30 días)."* Hoy (2026-08-07) ya pasaron los 30 días desde la
creación (2026-07-03), pero **G-WH-VPS-2 es un gate nombrado que requiere su propia cita de
David**, no algo que se dispare solo por tiempo transcurrido. La "GO VPS HYGIENE" genérica de
este pack **no** cita G-WH-VPS-2 — así que los 8 ítems de `~/archive/uas/` (3 clones + 6
worktrees registrados, ~964M) quedan **BLOCKED** en este pack, no re-evaluados de cero.

> **Update 2026-08-08:** `~/archive/uas` fue **eliminado definitivamente** bajo gate
> `G-WH-VPS-2` (citado explícitamente por David) en PKG-UAS-P1-VPS-RESIDUALS. Detalle
> completo, re-verificación independiente de las 8 ramas y rescates en
> [uas-p1-vps-residuals-20260808.md](uas-p1-vps-residuals-20260808.md).

## B. Disco

`df -h /`: **96G total, 45G usados, 52G libres (47%)** — sin presión de espacio, esto es
higiene de orden, no rescate de disco lleno.

| Directorio | Tamaño | Nota |
|---|---|---|
| `~/.openclaw/agents` | 9.0G | 8 dirs legítimos (= `agents.list`) pesan la mayoría; resto son ~22 dirs `pit-*` de lanes/judges de torneos, cada uno <1.2M (ver C) |
| `~/.openclaw/npm/projects` | 5.1G | node_modules por proyecto de plugins (codex, etc.) — regenerable en teoría, pero es dependencia de runtime activo, no cache pura |
| `~/.npm` (cache global de npm del usuario) | 6.5G | **cache real, clásico "regenerable obvio"** — candidato limpio para `npm cache clean` |
| `~/.cache` | 1.7G | cache genérica (pip, etc.), no inventariada archivo por archivo |
| `~/archive/uas` | 964M | **DELETED 2026-08-08** bajo `G-WH-VPS-2` — ver A.5 y [uas-p1-vps-residuals-20260808.md](uas-p1-vps-residuals-20260808.md) |
| `~/umbral-agent-stack` | 617M | canónico, KEEP obvio |
| `~/exec-diag-2026-07` | 125M | captura de diagnóstico de julio, ya tiene subcarpeta `archive/` propia (2026-08-02) — no evaluado a fondo si su contenido ya está capturado en `docs/audits/sys-diag-inputs/2026-07-17/`; **DEFER**, no urgente por tamaño |
| `~/rclone`, `~/umbral-pit-vault`, `~/umbral-bot-2`, `~/umbral-obsidian-vault*` | <100M c/u | proyectos separados, fuera del scope de este pack (no son clones de umbral-agent-stack ni residuo de higiene VPS); vistos, no tocados |

## C. OpenClaw

**Gateway:** `openclaw-gateway.service` activo, corriendo desde 2026-08-06 01:15 (~1d17h),
memoria 3.0G/pico 4.5G, sin reinicios inesperados. `openclaw --version` → `2026.7.1-2`.

**`openclaw doctor` (solo lectura, sin `--fix`)** — hallazgos:

1. **P3.2 confirmado, 3/3 puntos exactos:**
   - `plugins.load.paths` tiene 1 entrada redundante apuntando al directorio de plugins
     *bundled* actual de OpenClaw → doctor sugiere quitarla o `doctor --fix`.
   - `plugins.entries.umbral-tournament-github`: plugin stale, no encontrado en disco →
     doctor sugiere removerlo de la config.
   - `gateway.trustedProxies`: confirmado **sin configurar** (`<not set>`) vía lectura directa
     de `openclaw.json` (`gateway` solo tiene `auth`, `http`, `mode`).
2. **999 archivos de transcript huérfanos** en `~/.openclaw/agents/main/sessions` — ya no
   referenciados por `sessions.json`. Doctor puede archivarlos de forma segura (rename a
   `*.deleted.<timestamp>`, no delete).
3. **4/5 sesiones recientes con transcript faltante** — doctor sugiere
   `openclaw sessions cleanup --store .../sessions.json --dry-run --fix-missing` antes de
   `--enforce`.
4. **6 directorios de agente en disco sin entrada en `agents.list`** (ejemplos: `pit-dev-ifc-viewer-judge-1`,
   `pit-dev-ifc-viewer-judge-2`, `pit-dev-ifc-viewer-lane-field-coordination`, +3). Verificado
   por conteo directo: `~/.openclaw/agents` tiene 30 entradas, 8 coinciden con `agents.list`
   (`main`, `rick-orchestrator`, `rick-delivery`, `rick-qa`, `rick-tracker`, `rick-ops`,
   `rick-communication-director`, `rick-linkedin-writer`); el resto son ~22 dirs `pit-*`
   ligados al sistema de torneos — **[[project_pit_tournaments_archived]] sigue en HOLD hasta
   GO de David**, así que no se tocan aunque doctor los marque removibles.
5. **No hay command owner configurado** (`commands.ownerAllowFrom` vacío) — hallazgo de
   seguridad/postura, fuera del alcance de "higiene de residuos" de este pack; se cita para
   que David decida, no se toca.
6. Warnings de `messages.groupChat.visibleReplies` / message tool / Telegram
   first-time-setup — configuración funcional conocida, no residuo.

**Ningún `--fix` se ejecutó.** Todo lo de arriba es de solo lectura.

## D. Crons / timers / procesos

**Crontab de `rick`:** 17 líneas activas + 4 líneas comentadas (`# DISABLED_TANDA_A_2026_07_17`
×3, `# B1-paused 2026-05-24` ×1) — todas apuntando a scripts reales bajo
`umbral-agent-stack/scripts/vps/`. Las líneas comentadas son ruido de bajo riesgo (documentan
una pausa, no ejecutan nada); candidata trivial de limpieza, no urgente.

**systemd `--user` timers:** solo `launchpadlib-cache-clean.timer` (ajeno a Umbral). **Sin
duplicación cron/timer.**

**systemd `--user` units activos relevantes:** `openclaw-gateway`, `openclaw-dispatcher`,
`umbral-worker`, `mission-control` — los 4 `active (running)`, sin flapping visible en el
status leído.

**Procesos:** worker (`:8088`), mission_control (`:8089`), `dispatcher.service`, n8n (proceso
principal + task-runner + 2× `mcp-remote` hacia `dmbutic`/`umbralbim`, consistentes con
[[project_n8n_vps_b1_b3]]), gateway + subprocesos `codex app-server` (uno por sesión activa,
esperado). **Sin procesos zombis ni huérfanos detectados** más allá de lo ya conocido; no se
tocó el zombi `openai:umbral-rick` (prohibido explícitamente por el pack).

## Clasificación

| Ítem | Clase | Razón |
|---|---|---|
| `~/.npm` (cache global, 6.5G) | **DISCARD_SAFE** (candidato, pendiente GO) | cache regenerable clásica |
| Comentarios muertos en crontab (4 líneas) | **DISCARD_SAFE** (candidato, pendiente GO) | no ejecutan, solo ruido documental |
| P3.2 completo (`load.paths`, `umbral-tournament-github`, `trustedProxies`) | **MUTATE_WITH_BACKUP** | `doctor --fix` cubre 2/3; `trustedProxies` es decisión de exposición de red → si implica exponer, **DEFER** por regla del pack; si es solo fijar loopback explícito, mutate trivial |
| 999 transcripts huérfanos (`sessions/main`) | **MUTATE_WITH_BACKUP** | mecanismo oficial de doctor (rename, no delete) — bajo riesgo, reversible |
| 4/5 sesiones con transcript faltante | **DEFER** | requiere `--dry-run` primero para ver impacto real antes de `--enforce` |
| `~/.openclaw/npm/projects` (5.1G) | **DEFER** | parece cache pero es dependencia de runtime activo (codex plugin la usa ahora mismo); no confirmar regenerable sin más evidencia |
| `~/.openclaw/workspace/umbral-agent-stack` (clone standalone, rama `rick/vps` sin upstream) | **DEFER** | vive dentro del workspace operativo de Rick; dirty es solo chmod, pero tocar su rama/git state sin GO específico es zona operativa, no residuo |
| `/tmp/openclaw-oauth-{apply,only-urgent}-wt` (2 worktrees) | **DEFER** | commit ya mergeado + rama ya borrada de origin, pero dirty (notas de task) — regla del pack: dirty = no discard sin listar, ya listado aquí |
| `/tmp/rick-hb-20260713-0143/wt-candidate` (dedupe fix no mergeado) | **DEFER** | código real no presente en `origin/main` — decisión de rescate (cherry-pick) vs descarte le corresponde a David |
| `/tmp/rick-hb-20260713-0143/wt-replay-on-origin` (staged: fix loop bot/echo) | **DEFER** | mismo criterio — parece un bugfix real (evita reprocesar comentarios en loop), nunca aterrizado |
| `~/archive/uas/*` (3 clones + 6 worktrees, ~964M) | **DELETED 2026-08-08** | gate `G-WH-VPS-2` citado en PKG-UAS-P1-VPS-RESIDUALS — ver [uas-p1-vps-residuals-20260808.md](uas-p1-vps-residuals-20260808.md) |
| ~22 dirs `pit-*` huérfanos en `~/.openclaw/agents` (<15M total) | **BLOCKED** | sistema de torneos en HOLD ([[project_pit_tournaments_archived]]) — doctor los marca removibles pero la decisión de producto está pausada |
| No command owner configurado | **DEFER** (fuera de scope) | hallazgo de postura de seguridad, no de residuo — se cita para David, no se ejecuta aquí |
| `~/.openclaw/agents/{main,rick-orchestrator,...}` (8 dirs, 8.9G) | **KEEP** | agentes activos en `agents.list` |
| Canónico `/home/rick/umbral-agent-stack` | **KEEP** | en uso, procesos worker/mission_control corriendo desde ahí |
| Worktree `rick-delivery/umbral-agent-stack-poller-hardening` | **KEEP** | feature en curso, limpio |
| 6 worktrees `rick/copilot-cli-*` dentro de `archive/uas` | **DELETED 2026-08-08** (subsumido en A.5) | removidos junto con el resto de `archive/uas` bajo `G-WH-VPS-2` |
| 25 stashes del canónico | **DEFER** | no abiertos en detalle en este pack; requiere pack de higiene de stashes dedicado |
| `~/rclone`, `~/umbral-pit-vault`, `~/umbral-bot-2`, `~/umbral-obsidian-vault*` | **KEEP** (fuera de scope) | proyectos separados, no residuo de umbral-agent-stack |

## Fase 2/3 — ejecutado (PKG-UAS-P1-VPS-HYGIENE-EXEC, 2026-08-07)

GO citado textual (evidencia en `~/.coord-ag-evidence/uas-p1-vps-hygiene-exec-20260807/AUTHZ.txt`):
*"GO VPS HYGIENE"* + *"GO A LO MAS RECOMENDABLE E HIGENICO Y ROBUSTO, ANALIZA Y DECIDE"*
(David, 2026-08-07). Rama `claude/pkg-uas-p1-vps-hygiene-exec-20260807`, base `e07a5c1`.
Allowlist cerrada — solo lo listado abajo, todo lo demás quedó BLOCKED/DEFER.

### A — DISCARD_SAFE

| Ítem | Antes | Después | Evidencia |
|---|---|---|---|
| Crontab: 4 líneas comentadas muertas (`DISABLED_TANDA_A_2026_07_17` ×3, `B1-paused` ×1) | 18 líneas | 14 líneas activas, diff exacto = solo esas 4 | `crontab.bak` / `crontab.new`, diff limpio (nada más tocado) |
| `~/.npm` cache global | 6.5G | 838M | `npm-cache-before.txt` / `npm-cache-after.txt` |

### B — MUTATE_WITH_BACKUP (OpenClaw)

Backup `openclaw.json` → `openclaw.json.bak` (md5 verificado idéntico antes de editar).

**P3.2 — 2/3 aplicados, 1/3 explícitamente sin tocar:**
- `plugins.load.paths`: entrada redundante → `[]`. **Aplicado.**
- `plugins.entries.umbral-tournament-github`: clave borrada completa. **Aplicado.**
- `gateway.trustedProxies`: **sin tocar**, prohibido explícito del pack (B5).

Método real: `openclaw doctor --fix` (incluso con `--yes` y wrapeado en `script -qfc` para
TTY real) resultó tener un radio de acción mucho mayor al autorizado — llegó a intentar
levantar un servidor MCP externo no relacionado (`mcp-remote https://mcp.magnific.com`) como
parte de un chequeo de bundle, dejando 3 procesos huérfanos que hubo que matar a mano tras
interrumpir el intento. Se abandonó esa vía y se aplicó una **edición JSON quirúrgica**
verificada por round-trip (`json.load`→`json.dump` sin edits daba diff cero contra el
original) — el diff resultante contra el backup son EXACTAMENTE los 2 cambios de arriba,
nada más. El propio gateway confirmó en su log que reconoció los cambios correctos
(`[reload] config change detected; evaluating reload (plugins.load.paths,
plugins.entries.umbral-tournament-github)`) y se reinició limpio solo (SIGUSR1,
`shutdown completed cleanly`, `NRestarts=1`, sin crash-loop) — comportamiento esperado de su
propio hot-reload, no la regla de rollback disparándose. Detalle completo en
`doctor-fix.txt` (evidencia).

**999 transcripts huérfanos — NO ejecutado, DEFER documentado.** Se intentó reconstruir la
lógica de "huérfano" desde `sessions.json` (`usageFamilySessionIds` + `sessionFile`) y dio
**2024** archivos sin referencia, no 999 — una discrepancia de más del doble contra lo que
`doctor` reportó, señal de que la lógica exacta de la herramienta no es replicable a mano de
forma confiable. Renombrar por una lógica propia que diverge tanto viola la regla de "sin
improvisar fuera de lista" del pack. Queda sin ejecutar.

**B6 confirmado cumplido:** no se corrió `sessions cleanup --enforce`; no se tocaron los
dirs `pit-*`; no se tocó `~/.openclaw/workspace/umbral-agent-stack`; no se tocó el zombi
`openai:umbral-rick`; `~/archive/uas/` intacto (gate `G-WH-VPS-2` no citado, no reabierto).

Gateway: **`active (running)`**, `NRestarts=1` (el reload esperado), estable.

### C — `/tmp` worktrees

**C1 — oauth (descartados, no rescatados):** `openclaw-oauth-apply-wt` y
`openclaw-oauth-only-urgent-wt` — confirmado HEAD de ambos como ancestro de `origin/main`
(commits ya mergeados, ramas ya borradas de origin). Dirty = solo notas de tracking sobre un
task (`.agents/tasks/2026-07-12-001-...md`), capturado en evidencia y descartado sin
rescatar (regla del pack: "Dirty = solo notas de task → descartar dirty"). `git worktree
remove --force` ×2 + `git branch -D` de las 2 ramas fósiles locales.

**C2 — hb (rescatados vía PR, luego podados):** `wt-candidate` (commit `0d70b67`,
2026-07-09, "fix(notion): dedupe bot poller comments before action log") y
`wt-replay-on-origin` (staged, sin commit) contenían el **mismo fix exacto** — confirmado
por comparación función por función (`_is_comment_processed`, `_filter_unprocessed_comments`
+ 3 tests idénticos en ambos). Clasificación: `wt-candidate` = **UNIQUE** (no está en
`origin/main`), `wt-replay-on-origin` = **SUBSUMED** por el mismo contenido — un solo rescate
cubre los dos.

Cherry-pick de `0d70b67` sobre `origin/main` actual (rama `claude/rescue-notion-poller-hb-20260713`)
con conflicto de merge por drift del archivo (`dispatcher/notion_poller.py` creció de ~1073 a
1793 líneas desde julio) — resuelto preservando todo el contenido nuevo de `main` e
insertando las 2 funciones + 3 tests del fix en su lugar correspondiente. **222/222 tests de
`test_notion_poller.py` pasan** tras el resolve. Commit `709f211`, push, PR abierto **sin
merge**: **[PR #611](https://github.com/Umbral-Bot/umbral-agent-stack/pull/611)** — el PR
deja explícito que necesita revisión funcional independiente antes de ir a `main` (esto es
higiene de residuos git, no una aprobación de que el fix siga vigente).

Tras la captura + PR: ambos worktrees podados (`git worktree remove --force` ×2). El
directorio padre `/tmp/rick-hb-20260713-0143/` quedó con 13 archivos de notas de
investigación sueltas (no son worktrees git, ~13KB) — **fuera del allowlist C2, no
tocados**, listado guardado en evidencia.

**C3:** worktree `rick-delivery/umbral-agent-stack-poller-hardening` — no tocado, como
exige el pack.

### D — Resultado en disco/estado

| Métrica | Antes (Fase 1) | Después (Fase 2/3) |
|---|---|---|
| `df -h /` uso | 45G/96G (47%) | 40G/96G (42%) |
| `~/.npm` | 6.5G | 838M |
| Crontab líneas | 18 (14 activas + 4 muertas) | 14 (todas activas) |
| Worktrees registrados en canónico | 11 | 8 (−2 oauth, −2 hb, +0 — `archive/uas` intacto) |
| Ramas locales fósiles | — | −2 (`rick/openclaw-oauth-apply-20260713`, `rick/openclaw-oauth-only-urgent-20260713`) |
| `plugins.load.paths` | 1 entrada redundante | `[]` |
| `plugins.entries` | incluía `umbral-tournament-github` (stale) | removida |
| `gateway.trustedProxies` | sin configurar | **sin configurar** (intacto, prohibido tocar) |
| Gateway | active, 1d17h uptime | active, `NRestarts=1` (reload esperado por el propio fix) |

## Gate

**`UAS_P1_VPS_HYGIENE_PASS = PARTIAL`**

Justificación: A y C completos según allowlist; B logra 2/3 de P3.2 (trustedProxies
correctamente intacto por regla dura, no es una falla) pero el archivado de los 999
transcripts huérfanos **no se ejecutó** — la discrepancia 2024 vs 999 en la reconstrucción
manual de la lógica de "huérfano" es evidencia real de que replicarla a mano no es seguro,
así que se dejó sin tocar en vez de arriesgar un rename incorrecto sobre casi 2000 archivos.
Todo lo demás del allowlist se ejecutó con evidencia. `~/archive/uas/`, `trustedProxies`,
zombi `openai:umbral-rick`, dirs `pit-*` y `sessions cleanup --enforce` quedaron intactos
como exige el pack — cero excepciones ahí.

**PRs de este ciclo:**
- [#610](https://github.com/Umbral-Bot/umbral-agent-stack/pull/610) — Fase 1 inventario, **mergeado**.
- [#611](https://github.com/Umbral-Bot/umbral-agent-stack/pull/611) — rescate del fix del poller de Notion, **abierto, sin merge** (requiere revisión funcional aparte).
- Esta rama (`claude/pkg-uas-p1-vps-hygiene-exec-20260807`, acta Fase 2/3) — PR abierto **sin merge**, ver commit de este documento.

**Pendiente de David:**
1. Decidir si el archivado de los 999 transcripts se hace en un pack aparte con más
   visibilidad de la lógica real de `doctor`, o si se acepta dejarlos como están.
2. Revisar y decidir merge de [PR #611](https://github.com/Umbral-Bot/umbral-agent-stack/pull/611) (fix real, no higiene).
3. Mergear el PR de este documento cuando corresponda — sin self-merge.

## Transcripts huérfanos — cierre del residual (PKG-UAS-P1-VPS-TRANSCRIPTS, 2026-08-08)

GO citado: *"go con el siguiente"* (David, 2026-08-08), tras lista residual del orquestador
(1º ítem = transcripts OpenClaw). Evidencia:
`~/.coord-ag-evidence/uas-p1-vps-transcripts-20260808/`. Rama
`claude/pkg-uas-p1-vps-transcripts-20260808`, base `ad71801` (incluye el deploy #611, sin
redeploy).

**F1 — `openclaw doctor` de solo lectura:** conteo actual **1005 orphan transcript files**
en `~/.openclaw/agents/main/sessions` (wording idéntico a ayer, +6 vs los 999 originales —
crecimiento normal de actividad).

**F2 — descubrimiento del CLI oficial:** `openclaw sessions cleanup --dry-run [--agent
<id>|--all-agents] [--json]` es el comando real y acotado (no `doctor --fix`, que sigue
teniendo el problema de radio de acción ya documentado ayer). No interactivo, no toca
plugins/red/config. Detalle completo en `cli-discovery.md` (evidencia).

Dry-run `--agent main --json`:
```json
"unreferencedArtifacts": {
  "scannedFiles": 3294, "removedFiles": 2107,
  "freedBytes": 370093651, "olderThanMs": 2592000000
}
```

**F4 — decisión: NO se ejecuta `--enforce`.** El comando existe y tiene `--dry-run` (vía
"A" en la letra), pero **su comportamiento real falla la condición explícita del pack**
("solo rename/archive, no delete hard"). Verificado con 3 señales independientes:
1. El JSON usa vocabulario `removedFiles`/`freedBytes` — consistente con liberación real
   de disco, no con un rename.
2. `openclaw docs` → la documentación oficial viva
   (`docs.openclaw.ai/reference/session-management-compaction`) dice textual: *"Explicit
   deletion is different: it writes and verifies a compressed transcript archive
   (`*.jsonl.deleted.<timestamp>.zst`...) before removing the deleted session's rows."*
   — es decir, el archivado-por-rename que `doctor` promete pertenece al código de
   **deleción explícita vía API**, no al de **poda automática de artefactos huérfanos**
   (`sessions cleanup`), que la misma doc describe sin ninguna copia recuperable.
3. Los 13 archivos `*.deleted.*` que ya existen en disco pertenecen a ese otro flujo, no
   son evidencia de que esta poda vaya a producir más.

**Conclusión:** el texto de `openclaw doctor` ("archive them safely by renaming") es
impreciso respecto al comportamiento real de la única vía oficial disponible — es delete
permanente sin backup. No existe flag en `sessions cleanup` para forzar rename en vez de
delete. No se ejecutó nada destructivo; ni siquiera se probó en un agente chico como
experimento, para no mutar nada fuera de lo explícitamente autorizado.

**Dimensionamiento completo (solo lectura, `--dry-run --all-agents`)**, para que la
decisión de David sea informada más allá del alcance original de `main`:

| Agente | Escaneados | A remover (delete real) | Bytes |
|---|---:|---:|---:|
| `main` | 3294 | 2107 | 370.1 MB |
| `rick-orchestrator` | 5138 | 4961 | 546.4 MB |
| `rick-ops` | 14139 | 9341 | 977.5 MB |
| `rick-tracker` | 36 | 7 | 70.4 MB |
| `rick-linkedin-writer` | 24 | 6 | 27.6 MB |
| `rick-communication-director` | 25 | 4 | 17.1 MB |
| `rick-delivery` | 29 | 3 | 0.4 MB |
| `rick-qa` | 370 | 3 | 0.4 MB |
| **Total** | **23005** | **16432** | **~2.01 GB** |

Sin presión de disco (42% usado, 57G libres) — nada de esto es urgente por espacio.

**Gate: `UAS_P1_VPS_TRANSCRIPTS_PASS = PARTIAL`.** Fase 1 completa (doctor readonly + CLI
discovery + dry-run de dimensionamiento, todo solo lectura). Se detuvo antes de mutar por
evidencia real de que la única vía oficial es más destructiva de lo que el pack autorizaba
— exactamente el caso "aceptable y preferible a improvisar" que el pack contempla. Gateway
sin tocar (`active`, `NRestarts=1`, sin cambios desde el pack anterior).

**Pendiente de David:** decidir con los números reales de arriba si autoriza el delete
permanente (y con qué alcance — ¿solo `main`, ~370MB? ¿todos los agentes, ~2GB?), sabiendo
que no es reversible y que no hay presión de disco que lo urja.
