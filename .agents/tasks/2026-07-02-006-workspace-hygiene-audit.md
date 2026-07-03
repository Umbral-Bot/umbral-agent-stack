---
id: "2026-07-02-006"
title: "Auditoría workspace UAS — clones, hilos multi-IDE, método de trabajo, deudas"
status: done
assigned_to: copilot
created_by: cursor
priority: high
sprint: workspace-hygiene
created_at: "2026-07-02"
updated_at: "2026-07-03T03:15"
---

## Objetivo

Diagnosticar y proponer orden canónico para clones Windows + hilos Cursor/Copilot/Claude/Codex + handoff VPS. Entregable: auditoría multi-pass + tabla hilos activos vs archivar.

## MEGAPROMPT

`docs/ops/MEGAPROMPT-copilot-windows-workspace-hygiene-audit-2026-07-02.md`

## Entregables

- [x] `docs/audits/workspace-hygiene-2026-07-02/` (Pass 1–11)
- [x] `docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt` (generado, no ejecutado)
- [x] Tabla hilos activos/archivar por IDE (Pass 9)
- [x] PR audit docs — **#496 merged**
- [x] Gate G-WH-1 firmado (2026-07-03)
- [x] Pass 8 rescates (base + coordinador) + PRs
- [x] Cierre task + limpieza ramas -copilot

## Log

### [cursor] 2026-07-02 21:10
Task creada post-cierre Graphify GO_PARTIAL. Disparador: 17+ clones Windows locales.

### [copilot] 2026-07-02 ~22:30
Pass 0–11 ejecutados en rama `copilot/workspace-hygiene-audit-2026-07-02` (base origin/main @ `1660538`).

- **Veredicto:** `WORKSPACE_HYGIENE_AUDIT_READY | clones_windows=17 | rescue=4 | hilos_activos=5 | canonical_proposed=YES`
- Índice: `docs/audits/workspace-hygiene-2026-07-02/README.md`
- Hallazgos P0: sprint 2026-07-02 sin commitear (rescatado en este PR), commit sin push + 58 dirty en clone base, colisión IDs task 001/002, board stale en main, PR #495 pendiente decisión.
- MEGAPROMPT VPS generado (NO ejecutado): `docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt`
- Gates para David: **G-WH-1** (modelo canónico + rescates + archivado Fase A), G-WH-2 (borrado a 30 días), decisión PRs #495/#480/zombis mayo.
- Prohibiciones respetadas: 0 clones borrados, 0 acciones VPS, 0 hilos archivados en IDE.

### [cursor] 2026-07-03 01:50
Post-merge #496 + #495:
- **G-WH-1 firmado** por David (modelo canónico Pass 9 aprobado).
- Push `origin/codex/cand-prod001-stage2` con `a85563b8` (stage3 preservado en remote).
- MEGAPROMPT Pass 8: `docs/ops/MEGAPROMPT-copilot-windows-workspace-hygiene-pass8-2026-07-03.md`
- Siguiente: Copilot Windows ejecuta Pass 8A–8E (rescates + PRs + cierre).

### [copilot] 2026-07-03 03:15 — Pass 8A–8E DONE → task CLOSED

`WORKSPACE_HYGIENE_PASS8_DONE | rescue_base_pr=#498 | rescue_coord_pr=#499 | closeout_pr=este`

- **8A** — PR **#498 MERGED**: 29 archivos del stash `pre-rescue-pass8` del base (ADR-009, 3 audits gpt-5.5, VOICE.md + persona voz Rick, handoffs CAND-002, Magnific setup, scripts editorial/ops/vps, p10-sec63 ×2). Descartes con evidencia 3-way: main superset en variants 4:3, CAL-005/006, stage7, q2-plan PIT, prompts/evals/tests; colisión IDs task 001/002; board/settings stale.
- **8B** — PR **#499 MERGED**: 8 archivos del coordinador (+217/−8): editorial-agent-flow contexto-antes-de-BIM, ED-GOLD-011/012, ROLEs comm-director/QA con reglas longitud+consultoría, CAL renumerados **008/009/010**, 3 SKILLs linkedin. Descartes: human-review-contract (main jun-29 más nuevo), smoke-tests (versión #498 superset), artefactos sesión.
- **8C** — verificaciones: `_patch_blog_prompt.py` cand001-v31 = one-shot **ya aplicado en main** (descartado) · stunning-fiesta `git cherry` = `-` (contenido en main, worktree DELETE-ok) · 4 granola audits NOT-IN-MAIN → **rescatados en closeout PR** · config clone: historia R18–R21 pre-rewrite ya capitalizada, sin material único (ARCHIVE-ok).
- **8D** — 13 ramas locales borradas en `-copilot` (5 merged: graphify, audit, pass8-megaprompt, rescue-base, editorial-unpublish[cherry-verificado] · 7 upstream-gone: pit5-mc-v2-plan[doc en main], 6× feat/copilot-* feb–mar · 1 post-merge: rescue-coord). **Conservada** `backup/local-untracked-2026-04-29` (material `.claude/` único — decisión David pendiente).
- **8E** — este PR: task done, board, README veredicto final, debt register (P0-2 ✅, P1-1 ✅, P1-9 ✅ con evaluate-gate.ps1 adjudicado a P10-SEC63 y rescatado).
- Prohibiciones respetadas: 0 clones movidos/borrados (G-WH-2 pendiente), 0 VPS, graphify-out/ sin commitear, sin umbralbim-resource.
- **Pendiente David:** G-WH-2 (30 días) · archivado Fase A · PRs #480 + zombis mayo (#421 #418 #413 #389 #379 #321) · pegar MEGAPROMPT VPS en Copilot-VPS.

### [copilot-vps] 2026-07-03 — Espejo VPS (Pass 10) ejecutado

`WORKSPACE_HYGIENE_VPS_READY | checkouts=15 | rescue=5 | canonical_proposed=YES` (extendido: `crons_repo=17 | drift_openclaw=YES`)

- MEGAPROMPT VPS ejecutado completo (Pass V1–V5), read-only. Reporte: `docs/audits/workspace-hygiene-vps-2026-07-03/` + pointer `10-vps-checkouts.md` en el dir Windows.
- **V1:** 15 checkouts (5 clones + 10 worktrees) + 2 residuos. Canónico `~/umbral-agent-stack` main @ 60f605a sano (0↓/0↑) con 24 stashes y 103 ramas con tip no respaldado (censo contra ls-remote real: 81 backed / 19 merged / 103 candidatas).
- **V2:** SIN P0 runtime — 17 crons + worker/dispatcher/mission-control leen solo el canónico; gateway npm-global como documenta copilot-instructions.
- **V3:** drift OpenClaw runtime→repo: AGENTS (524 líneas), SOUL (386), VOICE (140) evolucionados en `~/.openclaw/workspace/` sin capitalizar; override main/ solo cubre IDENTITY. Overrides rick-editorial/rick-tech sin desplegar.
- **V4 — RESCUE (5 grupos):** R-V1 `rick/vps` 7 commits sin respaldo (CAND-PROD001 brief jun-07 + Embudo V2 + vm-ssh marzo) + stash único · R-V2 poller-healthcheck-hardening ~20 commits no en origin · R-V3 commit 18cdc48 backup (patch-id ≠ variante canónico 5a6b7aa, ambos fuera de main) · R-V4 5 untracked canónico (00_auditoria + PIT broker v2/v3) · R-V5 24 stashes + triage 103 ramas.
- Propuesta canónica: UN checkout (`~/umbral-agent-stack`), resto ARCHIVE→`~/archive/uas/` post-gate; convergencia `rick/vps` vía rama rescue + PR selectivo, NUNCA merge silencioso. ~880 MB recuperables.
- Prohibiciones respetadas: 0 deletes/moves, 0 restarts, 0 push runtime, 0 ediciones `~/.openclaw`, 0 merges.
- **Pendiente David: firma G-WH-VPS-1** (autoriza push ramas rescue + moves + worktree remove/prune) → luego G-WH-VPS-2 (30 días).

### [copilot] 2026-07-03 04:55 — VPS rescue PRs procesados (Windows merge master)

`VPS_RESCUE_PRS_DONE | pr_rick_vps=#502 | pr_stash=n/a-dup | pr_poller=#503 | pr_untracked=#504`

- **#502 MERGED** (rick-vps-orphans, extracción selectiva — rama original sin merge-base): CAND-PROD001 decision brief, linear-first operating model + `.rick/`, `linear_create_issue.py` modo estandarizado. Descartes: `identity/*` byte-igual (cero drift, task 004 safe), vm-ssh + runbook §7.2.1 ya absorbidos, resto main-superset.
- **stash windows-fs-b64 → SIN PR**: `windows.fs.write_bytes_b64` ya en main (`worker/tasks/windows_fs_bin.py`); delta WIP `linear_create_issue.py` == versión orphans (cubierto por #502); README +1 trivial. Rama rescue queda en origin para verificación David.
- **#503 MERGED** (poller-hardening): hardening `check-notion-poller.sh` ya byte-idéntico en main; rescatada la task 2026-05-07-001 versión Log completo, cerrada `done`; 18 commits docs-refresh = ruido blocker gh-auth (descartados), pr-draft + helper descartados.
- **#504 MERGED** (canonical-untracked): auditoría schema editorial 2026-06-16 (reubicada a `docs/audits/`, hallazgo crítico `audience_stage` spec vs código) + specs PIT broker v2/v3 (`pit_spec_validate.py` → pass ×2, completan serie v1–v4; ejemplos ejecutables del contrato #480).
- CI verde (3.11+3.12) en los 3 PRs antes de merge. Ramas `rescue/copilot-vps/*` originales intactas en origin (limpieza = decisión David post-verificación).
- **Pendiente David:** G-WH-VPS-2 (30 días) · borrar ramas rescue origin tras verificar · PR #480 + zombis mayo.
