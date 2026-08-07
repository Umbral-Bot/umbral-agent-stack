# P1 — Closeout de higiene git (2026-08-07)

> **Pack:** PKG-UAS-P1-HYGIENE-CLOSEOUT · rama
> `claude/pkg-uas-p1-hygiene-closeout-20260807` · base `2921c5e4`
> **GO de David (verbatim):** "ok dame prompt para rematar la limpieza e higiene y quedar 100%
> saneados" — cerrar la deuda git local restante tras P1.2/P1.3.
> **Fuera de alcance:** P1.4 UX, P2.3–P2.5 runtime, Notion/VPS, evento calendar, `umbral-bot-*`.

## 0. Reinventario (Paso 0)

`git ls-remote --heads origin` — **solo 2 heads**, coincide con el estado esperado:

```
2921c5e4  refs/heads/main
a2635398  refs/heads/rick/stage7_5-multiformat
```

Sin heads extra → sin STOP. Reinventario de los 3 repos antes de tocar nada:

| Repo | HEAD pre | Status pre | Stashes | Worktrees |
|---|---|---|---|---|
| SYNC (`C:\GitHub\umbral-agent-stack`) | `2921c5e4` (main) | limpio | 10 | 1 (el propio clone) |
| Clone A (`-copilot`) | `bcff86f6` (main, 1 atrás) | limpio | 4 | 1 (el propio clone) |
| Clone B (`-codex-coordinador`) | `bcff86f6` (detached) | limpio | 4 | 13 (incl. base) |

## 1. Sync de clones al tip de `origin/main`

### Clone A — `C:\GitHub\umbral-agent-stack-copilot`

```
git fetch origin        # bcff86f6..2921c5e main -> origin/main
git checkout main       # ya en main
git reset --hard origin/main
```

**Post [E]:** `## main...origin/main` limpio, `HEAD = 2921c5e4` = `origin/main` exacto.

### Clone B — `C:\GitHub\umbral-agent-stack-codex-coordinador`

Objetivo del pack: working tree en branch `main` (no detached). **Bloqueo real:** la rama `main`
de este repo está tomada por el worktree `C:/Users/david/.codex/worktrees/f8a-prompt-quoting-fix`,
que resultó **dirty** (staged, sin commitear):

```
A  .agents/tasks/2026-05-08-001-copilot-vps-wave1_5-integration.md   (371 líneas, nuevo archivo)
```

`git log` de ese worktree muestra 1057 ahead / 1577 behind de `origin/main` — historia muy vieja
divergida, probablemente un checkout Codex abandonado de mayo 2026. Contenido staged no vacío →
**STOP parcial por regla dura del pack** (`Si DIRTY: STOP parcial — NO discard sin listar`). No se
tocó ese worktree.

Como no se puede reclamar `main` sin tocar ese worktree, el clone B se dejó con **HEAD detached
apuntando exactamente al tip de `origin/main`** (no destructivo, no reclama la rama de nadie):

```
git fetch origin
git checkout --detach origin/main
```

**Post [E]:** `## HEAD (no branch)` limpio, `HEAD = 2921c5e4` = `origin/main` exacto. **Residual
explícito:** clone B sigue detached, no en `main`, hasta que David decida qué hacer con el commit
staged de `f8a-prompt-quoting-fix` (ver §2).

## 2. Worktrees huérfanos del repo coordinador (Clone B)

13 worktrees totales (incluida la base). Chequeo de proceso activo sobre cada path candidato a
remove — `Get-CimInstance Win32_Process` filtrando por `codex` y por el nombre de cada worktree:
único hallazgo real fue `python.exe` corriendo
`C:\GitHub\umbral-agent-stack-codex\scripts\vm\start_primary_worker.py` (PID 21140, activo) sobre
ese path — el resto de matches eran auto-referencias del propio comando de inspección.

| Worktree | Branch/HEAD | Dirty | Proceso activo | Veredicto |
|---|---|---|---|---|
| `C:/GitHub/umbral-agent-stack-codex` | `47ffcae` detached | limpio | **sí** (`start_primary_worker.py`) | **KEEP** — falla criterio (c) |
| `C:/GitHub/umbral-agent-stack-codex-coordinador` | base del clone B | — | — | base, no aplica |
| `.codex/worktrees/69c6/umbral-agent-stack-codex` | `3b10d7e` detached | **dirty** (`?? docs/audits/granola-automation-lineage-2026-04-02.md`) | no | **KEEP** — dirty |
| `.codex/worktrees/79ed/f8a-run6-task` | `codex/f8c-github-meta-egress-resolver-2026-05-07` (upstream gone) | limpio | no | **REMOVE** ✅ |
| `.codex/worktrees/79ed/umbral-agent-stack-codex-coordinador` | `e6128bc` detached | **dirty** (4 archivos modificados: `docs/ops/editorial-agent-flow.md`, `evals/editorial/gold-set-minimum.yaml`, 2× `ROLE.md`) | no | **KEEP** — dirty |
| `.codex/worktrees/copilot-cli-vision-roadmap-doc` | `codex/f8a-real-exec-path-2026-05-05` | limpio | no | **REMOVE** ✅ |
| `.codex/worktrees/f8a-diagnostic-mode` | `codex/f8a-diagnostic-mode-2026-05-06` | limpio | no | **REMOVE** ✅ |
| `.codex/worktrees/f8a-docker-stdin-fix` | `codex/f8a-docker-stdin-fix-2026-05-06` | limpio | no | **REMOVE** ✅ |
| `.codex/worktrees/f8a-drop-no-banner` | `codex/f8a-drop-no-banner-2026-05-06` | limpio | no | **REMOVE** ✅ |
| `.codex/worktrees/f8a-prompt-quoting-fix` | `main` @ `41bfeec` | **dirty** (staged, ver §1) | no | **KEEP** — dirty, STOP parcial |
| `.codex/worktrees/f8g-pin-gpt55-high` | `codex/f8g-pin-gpt55-high-effort` (upstream gone) | limpio | no | **REMOVE** ✅ |
| `.codex/worktrees/fbf4/umbral-agent-stack-codex` | `3b10d7e` detached | **dirty** (`?? .codex-tmp/`) | no | **KEEP** — dirty |
| `C:/Users/david/AppData/Local/Temp/pr269-worktree` | `b5641f9` detached | **dirty** (4 archivos borrados: `.agents/PROTOCOL.md`, `board.md`, `para-claude.md`, `para-rick.md`) | no | **KEEP** — dirty |

Ninguna de estas 13 ramas existe en `origin` (origin solo tiene `main` + `rick/stage7_5-multiformat`),
así que el criterio (a) —detached o rama ausente en origin— se cumple para todas; el filtro real
fue limpieza (b) + sin proceso activo (c).

**Ejecutado:**

```
git worktree remove "C:/Users/david/.codex/worktrees/79ed/f8a-run6-task"
git worktree remove "C:/Users/david/.codex/worktrees/copilot-cli-vision-roadmap-doc"
git worktree remove "C:/Users/david/.codex/worktrees/f8a-diagnostic-mode"
git worktree remove "C:/Users/david/.codex/worktrees/f8a-docker-stdin-fix"
git worktree remove "C:/Users/david/.codex/worktrees/f8a-drop-no-banner"
git worktree remove "C:/Users/david/.codex/worktrees/f8g-pin-gpt55-high"
git worktree prune
```

**Post [E]:** 6/6 removidos sin error, `git worktree prune` sin residuales. 7 worktrees quedan
(base + 6 KEEP documentados arriba). Ninguna rama fue borrada (`git branch -D` no se ejecutó) —
solo se liberó el checkout en disco; las ramas locales `codex/f8c-github-meta-egress-resolver-*`,
`codex/f8a-real-exec-path-*`, `codex/f8a-diagnostic-mode-*`, `codex/f8a-docker-stdin-fix-*`,
`codex/f8a-drop-no-banner-*`, `codex/f8g-pin-gpt55-high-effort` siguen existiendo en el repo local
de Clone B, solo sin working tree propio.

## 3. Stashes — inventario + drop solo seguro

18 stashes en total (10 SYNC + 4 Clone A + 4 Clone B). Regla aplicada: DROP solo si (a) vacío,
(b) contenido confirmado byte/línea-idéntico ya en `origin/main`, o (c) nombre `pre-*hygiene*` de
pack ya cerrado **y** contenido confirmado ruido/docs ya mergeados. Todo lo demás, KEEP.

### SYNC (`C:\GitHub\umbral-agent-stack`)

| stash | resumen | drop/keep | razón |
|---|---|---|---|
| `pre-pkg-uas-openclaw-stubs-20260806-hygiene` | `.agents/board.md` +sección LinkedIn 2026-08-04 | **KEEP** | nombre `-hygiene` pero contenido no confirmado en main (0 matches de `linkedin-invite-2026-08` en `origin/main:.agents/board.md`) |
| `pre-pull-a2-ledger-local` | 1 línea en `ledger-ops-resume.jsonl` (PKG-OPS-RESUME-A2 EMITIDO) | **DROP** ✅ | línea exacta ya presente en `origin/main` (diff byte-idéntico) |
| `pre-pkg-user-e2e-p1-rerun-20260803-hygiene` | 4 líneas ledger (PKG-NG-HYG-CAP3/STASH) | **KEEP** | entradas no presentes en `origin/main` actual del mismo ledger |
| `pre-pkg-user-e2e-p0-20260802-hygiene` | 4 líneas ledger (PKG-OPS-RESUME-A1 ACK/REPORTADO/PASS + B1 EMITIDO) | **KEEP** | entrada B1 EMITIDO única, no confirmada en main |
| `pre-a1-verify` | archivo completo `ledger-ops-resume.jsonl` (11 líneas, creación) | **DROP** ✅ | archivo base ahora commiteado en `origin/main` — diff byte-idéntico línea por línea contra las primeras 11 líneas del ledger actual |
| `wip-unrelated` (on `cursor/rick-voice-capitalize-mvp`) | `docs/11-roadmap-next-steps.md` +23 líneas | **KEEP** | nombre indica WIP intencional |
| `pre-rescue-pass8` (on `codex/cand-prod001-stage2`) | 20 archivos, ADRs + workspace-templates + scripts | **KEEP** | rescate sustancial, sin verificación de supersede |
| `cursor-local-pre-merge` (on `main`) | board.md + para-rick.md + docs VPS, contenido de marzo 2026 | **KEEP** | muy stale pero sin match textual confirmado — no cumple criterio de drop seguro |
| `temp` (on `codex/audit-qw-worker`) | runbook + scripts VM worker setup | **KEEP** | scripts activos (proceso vivo de worker corriendo ahora, ver §2) |
| `board y tasks locales` (on `main`) | board.md + 2 tasks, contenido de marzo 2026 (hackathon S6-S7) | **KEEP** | stale pero sin match textual confirmado |

**SYNC: 2 drop / 8 keep.**

### Clone A (`-copilot`)

| stash | resumen | drop/keep | razón |
|---|---|---|---|
| `pre-p10-sec63-route-a` | `docs/ops/pit-process-index.md` +11 líneas, "Cola de torneos (David — no perder)" | **KEEP** | el propio contenido dice explícitamente "no perder" |
| `claude config changes` (on `docs/env-google-keys-example`) | `.claude/commands/*.md` + `settings.local.json` | **KEEP** | config local, sin match confirmado en main |
| WIP on `main`: `.env.example` +7 líneas (bloque Azure AI Foundry, solo placeholders `CHANGE_ME`) | **KEEP** | bloque no presente en `origin/main:.env.example` |
| WIP on `feat/copilot-quota-report`: `AGENT_INSTRUCTIONS.md` reescritura | **KEEP** | instrucciones operativas viejas (hackathon), sin match confirmado |

**Clone A: 0 drop / 4 keep.**

### Clone B (`-codex-coordinador`)

| stash | resumen | drop/keep | razón |
|---|---|---|---|
| `S2-RESCUE-01 pre-checkout backup` (on `codex/stage1-smoke-referentes-rest`) | 10 archivos: `editorial-agent-flow.md`, `gold-set-minimum.yaml`, 2× `ROLE.md`, `CALIBRATION.md`, 3× `SKILL.md`, `export-vscode-config.ps1` | **DROP** ✅ | mismo set exacto de archivos evaluado hoy por [uas-p1-3-clone-wip-eval-20260807.md](uas-p1-3-clone-wip-eval-20260807.md) §2, veredicto uniforme `DISCARD_SAFE` con evidencia por path; **verificación cruzada propia**: diff de `ROLE.md` (rick-communication-director) contra `origin/main` — cada línea añadida por el stash está presente byte-idéntica en main (líneas 141-165 actuales) |
| WIP on `codex/structured-error-classification`: `docs/68-editorial-phase-1-manual.md` +80 líneas (sección "11. Flujo canonico... editorial", 9 etapas) | **KEEP** | main tiene una sección "11" en la misma posición pero **con contenido divergente** (10 etapas distintas, más reciente — menciona `rick-communication-director`, registro Notion `Borrador`). No es duplicado trivial, es una revisión superada por otra revisión — no cumple el criterio estricto de drop, se cita para limpieza manual futura |
| `codex/pre-main-sync-2026-03-22` (on `codex/umb-131-curar-tareas-granola`) | diagnóstico coordinación + 2 SKILL.md nuevos (`google-agenda-readiness` 158 líneas, `granola-meeting-capitalization` 566 líneas) | **KEEP** | ninguno de los 2 skills existe en `.claude/skills/` de `origin/main` (solo existe `notion-governance-runtime`) |
| `wip-before-task-097` (on `codex/095-actualizar-docs-board`) | `AGENT_INSTRUCTIONS.local.md` (nuevo) + `scripts/vps/supervisor.sh` | **KEEP** | `AGENT_INSTRUCTIONS.local.md` no existe en main |

**Clone B: 1 drop / 3 keep.**

### Total

**18 stashes inventariados → 3 DROP (contenido confirmado ya integrado en `main`) / 15 KEEP
(citados arriba, sin drop masivo).**

## 4. Confirmación `rick/stage7_5-multiformat`

```
git ls-remote --heads origin rick/stage7_5-multiformat
a2635398  refs/heads/rick/stage7_5-multiformat
```

Viva, intacta. **No se ejecutó `push --delete`.** `KEEP_INDEFINITE` (decisión de producto previa,
[uas-p1-2-keep3-archive-runbook-2026-08-06.md](uas-p1-2-keep3-archive-runbook-2026-08-06.md)).

## 5. Estado final [E]

| Repo | HEAD post | Status post | Worktrees | Stashes |
|---|---|---|---|---|
| SYNC | `2921c5e4` (rama del pack, base = `origin/main`) | limpio | 1 (propio) | 8 KEEP |
| Clone A (`-copilot`) | `2921c5e4` (main) | `## main...origin/main` limpio | 1 (propio) | 4 KEEP |
| Clone B (`-codex-coordinador`) | `2921c5e4` (detached) | `## HEAD (no branch)` limpio | 7 (base + 6 KEEP dirty/proceso-activo) | 3 KEEP |
| origin | — | — | — | heads = `{main, rick/stage7_5-multiformat}` — sin cambios |

**Residual explícito (no se toca sin GO adicional de David):**

- Clone B sigue **detached**, no en rama `main` — bloqueado por el worktree
  `f8a-prompt-quoting-fix` (staged, 371 líneas, decisión pendiente: ¿commitear, descartar o
  rescatar ese archivo de tarea de mayo 2026?).
- 6 worktrees de Clone B quedan vivos por estar dirty o tener proceso activo: `umbral-agent-stack-codex`
  (proceso vivo), `69c6/umbral-agent-stack-codex`, `79ed/umbral-agent-stack-codex-coordinador`,
  `f8a-prompt-quoting-fix`, `fbf4/umbral-agent-stack-codex`, `pr269-worktree` (Temp).
- 15 stashes KEEP citados arriba (8 SYNC + 4 Clone A + 3 Clone B).
- `rick/stage7_5-multiformat` KEEP_INDEFINITE, sin tocar.

## 6. Gate

`UAS_P1_HYGIENE_CLOSEOUT_PASS = Y` si se acepta el residual explícito de arriba (detached en
Clone B, 6 worktrees dirty/activos, 15 stashes) como estado saneado — no quedó ningún elemento
**destructible sin decisión humana** pendiente de ejecutar; todo lo que sigue vivo tiene una razón
citada con evidencia.

| Criterio del pack | Resultado |
|---|---|
| A y B en `main` @ tip `origin/main`, status limpio | **Parcial** — A sí (`main` exacto); B en tip exacto pero **detached**, no en `main` (bloqueo documentado §1) |
| Worktrees removibles CLEAN eliminados; dirty documentados KEEP | ✅ 6/6 removidos, 6 KEEP con razón |
| Stashes: solo drops justificados, resto inventariado | ✅ 3/18 drop con evidencia, 15/18 KEEP citados |
| `stage7_5` intacta | ✅ |
| origin heads = `{main, rick/stage7_5-multiformat}` | ✅ |
