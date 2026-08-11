# PKG-UAS-PANEL4-EXEC-THEN-HYGIENE — EXEC 4 páginas + higiene fósiles VPS (2026-08-11)

> **Pack:** PKG-UAS-PANEL4-EXEC-THEN-HYGIENE · rama
> `claude/pkg-uas-panel4-exec-then-hygiene-20260811` · base `cc76fe6`
> (`origin/main`, tip = PR #623)
> **GO David (2026-08-10):** "go" = MOVE Bitácora bajo Dashboard Rick + ARCHIVE las
> otras 3 + higiene exigente de fósiles locales VPS.
> **Evidencia:** `~/.coord-ag-evidence/uas-panel4-exec-then-hygiene-20260811/`
> (sin secretos; VM_URL/VM_TOKEN nunca impresos).

## FASE 1 — EXEC 4 páginas Notion: **Y**

Preflight (f1-before.json, 02:47 UTC): 4/4 checks — residual=4, Heartbeats=0, las 4
vivas con parent=Control Room, Dashboard Rick presente como nav allowed.

Ejecución (02:48 UTC):

| Acción | Página | Resultado |
|---|---|---|
| MOVE (MCP `notion-move-pages`, workspace Umbral BIM verificado) | Bitácora Plan Q2-2026 → child de Dashboard Rick | parent=`3265f443…` ✅, `archived=false`, child DB "Entradas Bitácora" accesible ✅ |
| ARCHIVE (API, papelera reversible) | SIM Daily Report 2026-05-07 | `archived=true, in_trash=true` ✅ |
| ARCHIVE | 📊 Pipeline Editorial — Métricas | `archived=true, in_trash=true` ✅ |
| ARCHIVE | Shortlist editorial guiada — Fases A y B | `archived=true, in_trash=true` ✅ |

Probe after (f1-after.json): `residual_child_pages=0`, Heartbeats=0,
**`validation.ok=true` por primera vez desde marzo**, nav allowed 2/2 intactos,
Bitácora ya no es child directo de Control Room.

**`UAS_PANEL_4_EXEC_PASS = Y`**

## FASE 2 — Diagnóstico exigente (read-only, resumen; detalle en `f2-summary.md`)

- **2.1 Origin:** exactamente 2 heads — `main` + `rick/stage7_5-multiformat` (KEEP
  gobernado, no tocado). ✅
- **2.2 Worktrees:** canónico + `poller-hardening` (b7f8e411): 19 commits ahead, no
  ancestro, files únicos (`.agents/*`, `scripts/vps/check-notion-poller.sh`), tree
  limpio → **KEEP** (no cumple condición SAFE_DROP del pack). `/tmp` sin worktrees
  (solo 6 `*worktree.log`); `~/archive/uas` ausente. ✅
- **2.3 Stashes (17):** test de subsunción = reverse-apply contra árbol de
  origin/main + comparación de blobs untracked. 3 `SUBSUMED_IN_MAIN`
  (stash@{3}, @{6}, @{9}) → SAFE_DROP; **14 `WIP_REAL` KEEP** (detalle 1 línea c/u
  en `f2-stashes.txt`); 0 EMPTY.
- **2.4 Ramas locales (193 clasificadas, `f2-branches.csv`):**

  | Clase | n | Evidencia dominante |
  |---|---|---|
  | MERGED_ANCESTOR | 0 | — |
  | PACK_GONE_PR_MERGED | 4 | claude/*, tracking gone, PR mergeada (gh, 537 PRs) |
  | SQUASH_SUBSUMED | 35 | diff de sus files == main hoy, o patch-id 1:1 (git cherry) |
  | UNIQUE_REAL | 152 | 117 historia desconectada + 35 conectadas con diff real |
  | RUNTIME_PROTECTED | 2 | stage7_5 + rama del worktree |

  Hallazgo estructural: el repo fue re-rooteado en algún punto — **117 ramas
  pre-rewrite no tienen merge-base con main** (`rick/t/*` tournament scratch ×41,
  `codex/*` ×29, otras ×47). Su "ahead ~750" es historia vieja, no contenido
  nuevo; su delta real son 1-3 commits tip (subjects + insertions en
  `f2-branches-disconnected-detail.csv`). No caben en ninguna clase SAFE_DROP del
  pack (ni ancestro, ni patch-id computable, ni claude/*) → KEEP honesto, no
  perezoso: quedan cuantificadas y rankeables para GO futuro de David.
- **2.5 Runtime:** crontab sin cambios; exec bits +x en cron scripts del panel y
  dashboard; **HEARTBEAT.md pares SoT byte-idénticos 3/3** (workspace main,
  rick-tracker, rick-qa); servicios **4/4 activos** (mission-control,
  openclaw-dispatcher, openclaw-gateway, umbral-worker); transcripts OpenClaw:
  16G, 16808 jsonl en agents — **DEFER, no se tocó nada**.
- **2.6 Disco:** repo 614M (.git 59M), worktree 13M, heartbeat reports locales 476
  files/2.0M, disco 41%. Nada >500M residual. Observación: `~/notion-governance-git`
  **ya no existe** aunque CLAUDE.md lo cita — corregir doc en pack futuro.
- **2.7 VM pcrick:** worker HTTP `/health` → **200 OK** (`ok:true, version 0.4.0`,
  tasks notion.*+windows.* registradas). Sin SSH. Checklist 5 líneas para Cursor
  Windows en `f2-summary.md` (higiene Windows no se afirma desde VPS).

## FASE 3 — SAFE_DROP ejecutado (inventario previo en `f3-drops.txt`)

- **39 ramas borradas** (35 SQUASH_SUBSUMED + 4 PACK_GONE_PR_MERGED), 0 fallos —
  inventario nombre+SHA+clase escrito ANTES de `git branch -D`.
- **3 stashes dropped** (de mayor a menor índice: @{9}, @{6}, @{3}) — SHAs en
  inventario; 14 WIP_REAL intactos.
- Worktree poller-hardening: **KEEP** (según 2.2, no se removió).
- `git gc --prune=now`: **omitido deliberadamente** — los objetos de ramas/stashes
  dropped quedan recuperables vía reflog/unreachable un tiempo; ventana de
  reversibilidad > ganancia de disco (59M de .git no lo amerita).
- Prohibiciones respetadas: cero `push --delete`, stage7_5 intacto, sin force
  push, sin sessions cleanup, sesión `bd35d75c` intacta, sin delete permanente
  en Notion, sin deploy.

## FASE 4 — Verify + residual para David

- **4.1 Panel:** re-probe → `residual=0`, **`validation.ok=true`** (estable,
  segunda medición; `f4-panel-verify.json`).
- **4.2 Git:** 156 ramas locales (154 + main + rama de este pack;
  `f4-branches-final.txt`), 14 stashes, **origin heads = 2**, 2 worktrees.
- **4.3 Tabla residual (decisión David, NO tocado en este pack):**

  | Residual | n | Detalle |
  |---|---|---|
  | Ramas UNIQUE_REAL | 152 | 117 desconectadas (rick/t/* ×41, codex/* ×29, otras ×47) + 35 conectadas |
  | Stashes WIP_REAL | 14 | `f2-stashes.txt` |
  | Worktree KEEP | 1 | poller-hardening (19 commits, files únicos) |
  | Transcripts defer | 16G | 16808 jsonl — pack aparte si se quiere podar |
  | pcrick | vivo | HTTP 200; higiene Windows vía checklist Cursor |

  Top 15 UNIQUE_REAL conectadas por valor aparente (1 línea c/u):

  | Rama | Valor |
  |---|---|
  | `rick/stage7_5-voice-v4` | iteración voice más avanzada del lane multiformat (14 files) |
  | `rick/stage7_5-voice-v2` | voz v2 previa, base de comparación (14 files) |
  | `rick/stage7_5-notion-ux` | UX Notion del stage 7.5 no mergeada (12 files) |
  | `rick/stage7_5-source-verify` | verificación de fuentes editorial (8 files) |
  | `rick/stage7_5-integration` | glue de integración del lane (3 files) |
  | `rick/stage7_5-copy-writer` | copywriter LLM del stage (3 files) |
  | `rick/stage9bc-linkedin-publish` | publicación LinkedIn stages 9b/c (5 files) |
  | `copilot/feat-s10-publish-guard` | guard de publicación S10 (23 files) |
  | `copilot/docs-editorial-master-plan` | master plan editorial docs (24 files) |
  | `copilot/feat-s2-source-verification` | verificación fuentes S2 (9 files) |
  | `copilot/feat-s0-s1-discovery` | discovery S0/S1 (11 files) |
  | `copilot-vps/013i-blockquote-block` | cadena markdown 013g/h/i más completa (30 files) |
  | `tournament/…440…/lane-backup-impl` | impl backup registry alternativa (16 files) |
  | `tournament/…445…/lane-sync-delivery` | sync skills→VPS alternativo (4 files) |
  | `umbralbim-copilot-feat-p10-openclaw-broker` | broker OpenClaw PIT P10 (12 files) |

- **4.4 Criterio:** (a) FASE 1 = Y ✅, (b) cero SAFE_DROP sobrevivientes ✅,
  (c) origin = 2 ✅, (d) panel residual = 0 ✅, (e) UNIQUE_REAL listados, no
  silenciosos ✅ → quedan UNIQUE_REAL ⇒ **PARTIAL (esperado y honesto)**.

**`UAS_VPS_FOSSIL_HYGIENE_PASS = PARTIAL`**

## Gates

- **`UAS_PANEL_4_EXEC_PASS = Y`**
- **`UAS_VPS_FOSSIL_HYGIENE_PASS = PARTIAL`** — 152 UNIQUE_REAL + 14 stashes
  WIP_REAL + 1 worktree KEEP listados para GO futuro; nada UNIQUE borrado.
- **Gate compuesto del pack: PASS** (EXEC=Y, higiene ≠ BLOCKED).

## TU TURNO (≤3)

1. Cursor mergea la PR de este acta.
2. David mira Control Room (debería ver solo el panel + Dashboard Rick + Alertas;
   la Bitácora ahora vive bajo Dashboard Rick).
3. David decide GO sobre los residuales KEEP (152 ramas UNIQUE_REAL — empezar por
   los grupos rick/t/* y codex/* desconectados —, 14 stashes, worktree poller) —
   no se tocan en este pack.
