# Plan de higiene de repos — Windows + política VPS

> **Fecha:** 2026-07-13 · **Sprint:** b0004 · **Fuente:** Fable (Claude Code) ·
> **Modo:** READ-ONLY + planificación documental — **cero borrados ejecutados en esta corrida**
>
> **Veredicto:** `REPO_HYGIENE_PLAN_READY | phases=7 | destructive_pending_approval`
>
> Inventario machine-readable: [`docs/audits/data/repo-hygiene-inventory-2026-07-13.yaml`](data/repo-hygiene-inventory-2026-07-13.yaml)
> Tareas: [`2026-07-13-001` H0](../../.agents/tasks/2026-07-13-001-fable-repo-hygiene-h0-worktree-prune.md) ·
> [`2026-07-13-002` H1 borrador](../../.agents/tasks/2026-07-13-002-fable-repo-hygiene-h1-dirty-rescue.md)

## 0. Método y confianza

Inventario git determinista (canónico + 15 checkouts del audit Cursor) + workflow
de 22 agentes: 10 analistas por checkout, 1 analista de política VPS, 1 juez de
triage de ramas, y **10 verificadores adversariales independientes** que
intentaron refutar cada recomendación `REMOVE`/`ARCHIVE`. Resultado: 9
recomendaciones confirmadas, **1 refutada y corregida** (coordinador — §3.1).
Todos los conteos citados aquí fueron re-verificados al menos dos veces.

## 1. Continuidad — este plan NO parte de cero

| Hito previo | Estado |
|---|---|
| **G-WH-1** (modelo canónico Windows, Pass 9) | ✅ Firmado por David 2026-07-03 |
| **Pass 8** rescates de clones obsoletos | ✅ Ejecutado (PRs #496–#500) |
| **Fase A Windows** (archivar clones → `_archive\uas`) | ✅ Ejecutada (PRs #506/#507): 15 dirs archivados; codex reclasificado KEEP (padre git del coordinador) |
| **Fase B VPS** (home = 1 checkout canónico) | ✅ Ejecutada (PR #505) |
| **G-WH-2** (borrado físico `_archive`, ventana 30 días) | ⏳ ~2026-08-02 |
| **Desenredo codex→coordinador** | ⏳ Declarado en cierre Fase A — se resuelve en H4 |

Este plan es la **segunda pasada**: limpia lo que escapó del censo de julio-02
(los checkouts `.tmp-*` con prefijo oculto, el trío de worktrees Cursor, los
worktrees b0004 post-merge), captura los únicos genuinos que quedan, y formaliza
la política VPS que la Fase B dejó implícita.

## 2. Estado verificado 2026-07-13 (correcciones al contexto del GO)

| Métrica | Contexto GO | **Verificado** |
|---|---|---|
| Checkouts vivos | 15 | **15** ✅ (+ hallazgo: ~16 worktrees CLI Codex en `~/.codex/worktrees/*`, fuera del censo) |
| Worktrees prunable | 11 | **12** (dry-run; match 1:1 con los archivados de Fase A) |
| Ramas locales | 216 | **216** ✅ (118 merged en origin/main · 98 no · **81 con commits sin respaldo remoto**) |
| Ramas remotas | 252 | **252** ✅ (27 merged · 223 no · 5 `rescue/*` protegidas) |
| Canónico "+15 vs origin rama" | ahead 15 | rama **ya mergeada** vía PR #525 — el "+15" era contra un upstream obsoleto; 0 commits en riesgo |
| Clones dirty | copilot, coordinador | ✅ + trío Cursor reo/wah/weo (dirty idéntico triplicado) |
| Stashes | — | **15** en 4 repos (canónico 5 · codex 4 · copilot 4 · claude 2), 3 de ellos **únicos-valiosos** |

## 3. Hallazgos clave

### 3.1 Material ÚNICO en riesgo real (nada de esto existe en ningún remote)

| # | Qué | Dónde | Riesgo |
|---|---|---|---|
| 1 | Rama `backup/local-untracked-2026-04-29` @ 684b2758 — 22 archivos, +1216 líneas (.claude/ agents+hooks+skills, scripts prueba Azure audio/Foundry) | clone **copilot** | **ALTO** — único punto de existencia; primera acción de H2 |
| 2 | `docs/ops/editorial-publicaciones-human-review-contract.md` **de 174 líneas** (main solo tiene 38; 129 líneas solo aquí) | **coordinador** (untracked) | ALTO — el análisis inicial lo marcó "redundante" con el diff invertido; **refutado por el verificador adversarial** y corregido |
| 3 | Stash canónico `stash@{0}` (de HOY): backlog P2 «Migración RAG: Azure Cognitive Search → pgvector» (~USD 73/mes) | canónico | MEDIO — solo vive en el stash |
| 4 | Stash claude `stash@{0}`: megaprompt editorial blog Azure (163 líneas) | clone claude | MEDIO |
| 5 | Stash copilot `stash@{0}`: tabla «Cola de torneos (David — no perder)» | clone copilot | MEDIO |
| 6 | Dirty copilot: bloque quota-policy «post-MP1 OPENCLAW_AZURE_ONLY» + audit `azure-foundry-capacity-...-2026-07-04.md` (121 líneas) | clone copilot | MEDIO — candidatos directos a PR docs |
| 7 | `scripts/export-vscode-config.ps1` (251 líneas) + `.env` ignorado con 4 claves `AZURE_OPENAI_*` que no están en ningún otro .env | coordinador | MEDIO — el `.env` se destruiría con un `worktree remove --force` |
| 8 | Ramas RESCUE_HIGH: `antigravity/sync-uncommitted-changes` (equipo codegen completo, 1154 líneas), `rick/editorial-linkedin-writer-flow` (LINKEDIN_WRITING_RULES 1626 líneas), `codex/wip-granola-v2-snapshot-2026-04-30` | canónico | MEDIO — features no absorbidas por main |

### 3.2 Lo que parecía riesgo y NO lo es (verificado)

- **Los 8 M del coordinador** (calibraciones editoriales): diff byte-idéntico al
  stash compartido `S2-RESCUE-01` y contenido ya en main (CAL-008/009/010,
  «rescate coordinador 2026-05-30»). El rescate del Pass 8 sí ocurrió.
- **El trío Cursor reo/wah/weo**: dirty byte-idéntico entre los 3 y 100%
  superseded por main (verificación a nivel de blob, incluidas las 18 entradas
  de update.zip). Aplicar su diff de quota-policy sería *regresión*.
- **`pr-313-recover` / `pr-315-recover`** (ahead ~1060): contenido byte-idéntico
  re-aterrizado en main tras el force-push de mayo; el ahead es historia pre-rewrite.
- **`rick/vps` local Windows** (1 commit): patch-id ya presente en
  `origin/rick/vps@56820573` — respaldado en remoto.
- **b0004 y b0004-oauth**: sus commits son patch-idénticos a `ac16876b` (#524) y
  `2f797091` (#525) respectivamente. El worktree b0004-oauth quedó mergeado HOY.

### 3.3 Estructura descubierta

- **El clone codex es padre git de 26 worktrees**: coordinador + pit-v2-contract
  (prunable) + ~16 worktrees del CLI de Codex (`~/.codex/worktrees/*`) + 1 en
  Temp. Borrar codex rompe todo eso → el "desenredo" de Fase A es más grande de
  lo declarado y queda anclado en H4.
- Los 3 clones `.tmp-*` y el worktree `.tmp-gd52-adr-scopes` **escaparon del
  censo de Fase A** (prefijo oculto). Los 4 están verificados sin material único.

## 4. Matriz de decisión H0–H6

> H0 es la única fase ejecutable sin gate. **H1+ requieren GO explícito de David.**
> Toda fase con `destructive: true` exige checklist §4.1 por objeto, ejecutado
> el mismo día de la acción (los veredictos de hoy caducan si algo cambia).

| Fase | Objetivo | Comandos clave | Prerequisitos | Rollback | Owner | destructive |
|---|---|---|---|---|---|---|
| **H0** | Prune de 12+1 metadatos de worktrees huérfanos (restos Fase A) | `git worktree prune -v` en canónico y en clone codex | dry-run == lista esperada (ya verificado) | `git worktree add` re-crea (ramas siguen vivas) | **Fable** | **false** |
| **H1** | Rescate dirty + stashes: capturar los 8 únicos de §3.1 (items 2–7) a `_archive\uas\rescue-2026-07-13\` + MANIFEST; `.env` coordinador preservado fuera de git | `git diff >`, `Copy-Item`, `git stash show -p`, `git show stash@{N}^3` | GO David; zona de rescate creada; regla .env (nunca commitear) | n/a — solo copia | **Copilot Windows** | **false** |
| **H2** | Respaldo de ramas con commits únicos: (1º) push `backup/local-untracked-2026-04-29` desde copilot como `rescue/copilot-local-untracked-2026-04-29`; push de las 3 RESCUE_HIGH como `rescue/*`; diff-review de las 6 MEDIUM; `git bundle` masivo de las 72 LOW como seguro barato | `git push origin <rama>:rescue/<rama>-2026-07`, `git bundle create` | GO David (push = superficie externa); H1 done | borrar ramas rescue pusheadas; bundles se borran | **Copilot Windows** | **false** (crea, no borra) |
| **H3** | Delete de ramas locales del canónico: 117 merged (lista datada) + 72 LOW-superseded (post-bundle H2) + 17 no-merged-pushed opcionales → objetivo ≤ 30 locales | `git branch -d` (merged) / `git branch -D` con evidencia patch-id (squash) | GO David; H2 done (bundle existente); NUNCA tocar `rick/vps`, las HIGH/MEDIUM sin decisión, ni `fable/*` activas | bundle H2 + reflog 90d + refs remotas | **Copilot Windows** | **true** |
| **H4** | Remoción de checkouts verificados: trío Cursor (post H1-U3), `.tmp-cvia3-deploy`, `.tmp-o16-2-047`, `.tmp-uas-feat-vps-policy`, `.tmp-gd52-adr-scopes`, `umbral-agent-stack-b0004`, `umbral-agent-stack-b0004-oauth` (post-confirmación sesión) + **desenredo codex↔coordinador** (opciones abajo) | `git worktree remove` (path EXACTO, jamás glob — b0004 vs b0004-oauth comparten prefijo) / `Remove-Item` para clones standalone | GO David; checklist §4.1 por objeto el mismo día; H1 done | re-clone / `git worktree add`; los archivados de Fase A siguen intactos hasta G-WH-2 | **Copilot Windows** | **true** |
| **H5** | Limpieza de ramas remotas: 27 merged con checklist PR (excluir `rescue/*`); las 223 no-merged SOLO inventario por lotes con dueño por prefijo — sin delete masivo | `git push origin --delete <rama>` una a una tras checklist | GO David POR LOTE; checklist: PR merged verificado + no `rescue/*` + no `rick/vps` + patch-id en main | restaurar desde reflog remoto/GitHub durante ventana, o desde bundles H2 | **David + Copilot Windows** | **true** (remoto) |
| **H6** | Política VPS formal (§6): checkout canónico main-limpio ff-only + worktree-only para APPLY + cerrar gaps del gate + fix docs | PR de docs + patch a 6 wrappers cron sin gate + alerta de gate bloqueado | Firma David de reglas §7; espejo VPS de H1 (rescate del dirty actual de la VPS) antes de normalizar | los cambios de política son PRs reversibles | **Copilot VPS + David** | **mixto** (normalizar el checkout VPS implica limpiar dirty → gate) |

### 4.1 Checklist obligatorio pre-REMOVE (endurecido por los verificadores)

Por cada checkout a borrar, el mismo día de la ejecución:

1. `git rev-list --count --all --not --remotes` == 0 (todas las refs, no solo HEAD).
2. `git stash list` vacío o stashes ya rescatados.
3. `git status --porcelain -uall` vacío **y** `--ignored=matching` revisado
   (los `.env` locales son invisibles para porcelain — lección del coordinador).
4. `git worktree list`: ni padre de worktrees vivos, ni hijo de un padre a borrar.
5. Sin `.gitmodules`.
6. `git fsck --unreachable` + reflog revisados (lección de `.tmp-cvia3`: había
   2 commits solo-reflog; resultaron pushed, pero la metodología debe cubrirlos).
7. Ningún proceso con handle/cwd dentro de la ruta (`fsmonitor--daemon stop` si aplica).
8. Path exacto en el comando — nunca globs por prefijo.

### 4.2 Desenredo codex↔coordinador (decisión David en H4)

| Opción | Qué se hace | Pros | Contras |
|---|---|---|---|
| **A (recomendada)** | Coordinador se promueve a clone independiente (clone nuevo + checkout main + migrar el dirty ya rescatado en H1); codex queda solo como padre de los worktrees `.codex/*` hasta que el CLI los suelte | Respeta G-WH-1 (coordinador = canónico Codex); mínima disrupción | codex sigue vivo un tiempo (2 dirs familia codex) |
| B | Aceptar veredicto de datos: remover coordinador (post-H1) y usar codex como clone Codex (checkout main) | 1 solo dir familia codex ya | Contradice G-WH-1 firmado; codex arrastra 25 ramas viejas |
| C | Remover ambos post-rescates y clonar codex limpio | Estado más limpio | Rompe los ~16 worktrees CLI `.codex/*`; más trabajo |

## 5. Ramas

### 5.1 Locales merged (delete H3) — 118, muestra de las más recientes

Lista completa datada generada en el inventario de esta corrida; las 50 más
antiguas son de marzo (rondas R16–R23 cerradas). Muestra del extremo reciente:
`codex/aeco-*` (jun-03), `codex/core-first-*` (jun-03), `claude/feat-tournament-v11-hardening`
(jun-09), `umbralbim-didactic-fortnight` (jun-22), `cursor/cand001-blog-v31-sensitivity-fix`
(jun-29), `cursor/rick-voice-capitalize-mvp` (jul-13, mergeada #525). Se excluyen
`main` y la rama de este plan.

### 5.2 Locales con commits sin respaldo — 81, triage verificado

| Bucket | Nº | Acción |
|---|---|---|
| **RESCUE_HIGH** | 3 | H2: push como `rescue/*` — `antigravity/sync-uncommitted-changes` (codegen team), `rick/editorial-linkedin-writer-flow` (reglas LinkedIn 1626 líneas), `codex/wip-granola-v2-snapshot-2026-04-30` |
| **RESCUE_MEDIUM** | 6 | H2: diff-review antes de decidir — `feat/ux1-noise-reduction`, `audit-2026-03-quick-wins`, `codex/notion-v2-drift-cleanup`, `rick/vps`, `copilot/feat-o8a-granola-length-instrumentation`, `copilot/fix-notion-poll-comments-timeout` |
| **RESCUE_LOW (superseded)** | 72 | H2: bundle de seguro → H3: delete. Verificación por familias: squash-merges confirmados por PR (#200 #296 #444 #448 #458–465 #488 #490 #492 #523 #524), integraciones R14–R16, 13 clónicas test-coverage sobre granola V1 deprecado, lanes efímeras de torneo, y las 2 `pr-*-recover` re-aterrizadas byte-idéntico |

**Fuera del canónico** (ampliación H2): `backup/local-untracked-2026-04-29`
(copilot, riesgo ALTO) y `codex/f8g-pin-gpt55-high-effort` (handoff largo 317
líneas; main tiene consolidado de 78).

### 5.3 Remotas — resumen (H5, sin deletes sin checklist)

27 merged (deletables con checklist) · 223 no-merged por prefijo:
rick 59 · codex 40 · cursor 30 · feat 26 · copilot 25 · copilot-vps 9 ·
tournament 6 · **rescue 5 (intocables)** · resto 23.
`origin/rick/vps` protegida (deuda VPS-P1-3: 141 commits sin auditar).

## 6. Política VPS (H6) — propuesta sobre lo que YA existe

**Lo que ya está en main y funciona:** checkout canónico `~/umbral-agent-stack`
en main ff-only (Fase B); gate bloqueante `scripts/vps/ensure-main-for-run.sh`
(PR #423) cableado en 10 wrappers cron + supervisor + full-stack-up; guardrails
`github.*` del Worker; skill `openclaw-vps-operator` §5 (edición vía clone
temporal `/tmp/<task>-clean` o worktree autorizado).

**Los gaps que explican el estado actual** (VPS dirty + detrás ⇒ los crons
gated se están saltando **en silencio** ahora mismo):

1. 6 crons sin gate: `health-check`, `notion-curate`, `openclaw-runtime-snapshot`,
   `dashboard-rick`, `openclaw-panel`, `granola-gap-check`.
2. El gate no alerta cuando bloquea (solo `/tmp/ensure_main_for_run.log`) y no
   hay runbook «qué hacer cuando el gate bloquea».
3. La política worktree-para-APPLY es advisory (skill), no norma: la propia task
   `2026-07-12-001` instruye `git pull origin main` directo sin check de dirty;
   el APPLY OAuth usó worktree por improvisación, no por procedimiento.
4. Docs contradictorios: `docs/62` L435 niega la existencia del gate (nota stale
   pre-#423) y §7.1 pide vivir en `rick/vps` contra el modelo main-pinned;
   `docs/66` L181 enlaza a un doc inexistente.
5. El hook local `block-deployed-repo-writes.sh` no está versionado.

**Propuesta H6 (para firma):**

- **P-V1** — El canónico VPS se declara **solo-runtime**: main limpio, ff-only.
  *Dirty tracked en el canónico = incidente* → alerta Notion/Telegram vía el
  supervisor, no solo log.
- **P-V2** — **Todo APPLY** (patches, migraciones, edición de config del repo)
  se ejecuta en **worktree/clone temporal** `/tmp/<task>-<fecha>` con TTL y
  cleanup registrado en la task. El template de tasks VPS reemplaza
  `cd ~/umbral-agent-stack && git pull` por el patrón worktree-APPLY.
- **P-V3** — Extender el gate a los 6 crons faltantes + modo alerta.
- **P-V4** — Normalización one-shot del estado actual: espejo VPS de H1
  (rescatar el dirty actual del canónico VPS con MANIFEST) → `git checkout main
  && git pull --ff-only`. Con gate de David (es la única sub-fase destructiva).
- **P-V5** — Fix de docs: actualizar `docs/62` (L435 + §7.1), reparar link de
  `docs/66`, versionar el hook (o su instalador).
- Fuera de alcance: `~/.openclaw` (no se toca) y auditoría de
  `origin/rick/vps` (141 commits — deuda VPS-P1-3, task futura).

## 7. Reglas de oro (para firma de David)

1. **Un solo hub Windows:** `C:\GitHub\umbral-agent-stack`. Todo lo demás es
   clone-de-superficie o worktree temporal.
2. **Máx 1 clone de agente activo por familia.** Familia codex: el canónico es
   el **coordinador** (G-WH-1); `-codex` queda únicamente como padre git hasta
   el desenredo H4 — **nunca ambos dirty**.
3. **Nunca clone nuevo por tarea** (ya firmado en G-WH-1). Worktrees temporales
   con TTL: se borran al mergear su PR (b0004 y b0004-oauth son el caso de
   prueba). Prefijos `.tmp-*` prohibidos salvo registro con fecha+dueño —
   escaparon del censo una vez, no dos.
4. **Auditoría mensual** de worktrees generados por IDEs/CLIs
   (`~/.cursor/worktrees/*`, `~/.codex/worktrees/*`): huérfanos > 30 días se
   triagean.
5. **VPS: main limpio o worktree** — nunca pull sobre dirty; dirty en el
   canónico VPS es incidente con alerta (P-V1/P-V2).
6. **`rescue/*` remotas son intocables** y toda eliminación (local o remota)
   pasa por el checklist §4.1 / checklist-PR §4 H5 el mismo día de ejecutarse.

## 8. Métricas objetivo del programa

| Métrica | Hoy | Post H0–H4 |
|---|---|---|
| Checkouts vivos Windows | 15 | **6** (hub, copilot, coordinador, codex-padre, claude, antigravity) |
| Registros worktree huérfanos | 12+1 | 0 |
| Ramas locales canónico | 216 | ≤ 30 |
| Ramas locales con material sin respaldo | 81 (+2 en clones) | **0** (todo pushed a `rescue/*` o en bundle) |
| Stashes sin triage | 15 | 0 (3 capitalizados, resto descarte firmado) |
| Política VPS | implícita + gaps | firmada (P-V1…P-V5) |

## 9. Criterios PASS de esta corrida

- [x] Inventario cubre 100% de las 15 rutas del audit Cursor (+ hallazgo `.codex/*` documentado).
- [x] Cada REMOVE_DIR tiene prerequisito verificado por agente + verificador adversarial independiente (0 commits únicos, o rescate H1 como precondición explícita).
- [x] Fases separadas: H0 safe sin David; H1+ con GO explícito; flags destructive por fase.
- [x] Sin secretos en YAML/MD (solo paths, shas, conteos; la regla .env preserva sin exponer).
- [x] board.md actualizado con el programa (fila por fase).

---

`REPO_HYGIENE_PLAN_READY | phases=7 | destructive_pending_approval`
