# P1 — Higiene VPS (2026-08-07)

> **Pack:** PKG-UAS-P1-VPS-HYGIENE · rama `claude/pkg-uas-p1-vps-hygiene-20260807` ·
> base `fd0c962` (`origin/main` al momento del checkout)
> **Ejecutado por:** Claude, Remote-SSH sobre `/home/rick/umbral-agent-stack` (host `srv1431451`,
> usuario `rick`) — confirmado antes de tocar nada.
> **Estado: FASE 1 (inventario) completa. FASE 2–4 NO ejecutadas — sin cita explícita de
> "GO VPS HYGIENE" en esta conversación.** Este documento es el inventario + clasificación que
> el pack pide como insumo previo al GO, no un cierre.

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

## B. Disco

`df -h /`: **96G total, 45G usados, 52G libres (47%)** — sin presión de espacio, esto es
higiene de orden, no rescate de disco lleno.

| Directorio | Tamaño | Nota |
|---|---|---|
| `~/.openclaw/agents` | 9.0G | 8 dirs legítimos (= `agents.list`) pesan la mayoría; resto son ~22 dirs `pit-*` de lanes/judges de torneos, cada uno <1.2M (ver C) |
| `~/.openclaw/npm/projects` | 5.1G | node_modules por proyecto de plugins (codex, etc.) — regenerable en teoría, pero es dependencia de runtime activo, no cache pura |
| `~/.npm` (cache global de npm del usuario) | 6.5G | **cache real, clásico "regenerable obvio"** — candidato limpio para `npm cache clean` |
| `~/.cache` | 1.7G | cache genérica (pip, etc.), no inventariada archivo por archivo |
| `~/archive/uas` | 964M | **BLOCKED** — ver A.5 |
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
| `~/archive/uas/*` (3 clones + 6 worktrees, ~964M) | **BLOCKED** | gate propio `G-WH-VPS-2` no citado en este GO — ver A.5 |
| ~22 dirs `pit-*` huérfanos en `~/.openclaw/agents` (<15M total) | **BLOCKED** | sistema de torneos en HOLD ([[project_pit_tournaments_archived]]) — doctor los marca removibles pero la decisión de producto está pausada |
| No command owner configurado | **DEFER** (fuera de scope) | hallazgo de postura de seguridad, no de residuo — se cita para David, no se ejecuta aquí |
| `~/.openclaw/agents/{main,rick-orchestrator,...}` (8 dirs, 8.9G) | **KEEP** | agentes activos en `agents.list` |
| Canónico `/home/rick/umbral-agent-stack` | **KEEP** | en uso, procesos worker/mission_control corriendo desde ahí |
| Worktree `rick-delivery/umbral-agent-stack-poller-hardening` | **KEEP** | feature en curso, limpio |
| 6 worktrees `rick/copilot-cli-*` dentro de `archive/uas` | **BLOCKED** (subsumido en A.5) | ya gateados |
| 25 stashes del canónico | **DEFER** | no abiertos en detalle en este pack; requiere pack de higiene de stashes dedicado |
| `~/rclone`, `~/umbral-pit-vault`, `~/umbral-bot-2`, `~/umbral-obsidian-vault*` | **KEEP** (fuera de scope) | proyectos separados, no residuo de umbral-agent-stack |

## Gate

**`UAS_P1_VPS_HYGIENE_PASS = PARTIAL`**

Fase 1 (inventario, solo lectura) — **completa**, evidencia en este documento. Fase 2
(discard safe), Fase 3 (mutate OpenClaw) y Fase 4 (repo runtime) — **no ejecutadas**: esta
conversación no contiene la cita explícita "GO VPS HYGIENE" que el pack exige antes de mutar
o borrar nada. Nada fue borrado, movido, ni reiniciado. `openclaw doctor` corrió sin `--fix`.

**Pendiente de David, con la lista de arriba como insumo:**
1. Confirmar GO explícito para ejecutar los `DISCARD_SAFE` (cache npm, comentarios de
   crontab) y los `MUTATE_WITH_BACKUP` (P3.2 vía `doctor --fix` + backup previo de
   `openclaw.json`; archivado de los 999 transcripts).
2. Decidir rescate vs descarte de los 2 worktrees `/tmp/rick-hb-20260713-0143/*` (código no
   mergeado, parece bugfix real del poller de Notion).
3. Si corresponde citar gate `G-WH-VPS-2` para `~/archive/uas/`, hacerlo en un pack aparte —
   no se re-abre aquí.
4. `trustedProxies`: aclarar si "configurar" significa fijar loopback explícito (mutate
   trivial) o exponer a una red — en ese caso, DEFER por regla dura del pack.

No hubo `git push` de esta rama todavía — se hace junto con este commit, sin abrir PR hasta
que el gate sea `Y` o David indique lo contrario.
