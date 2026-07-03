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
