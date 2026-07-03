---
id: "2026-07-02-006"
title: "Auditoría workspace UAS — clones, hilos multi-IDE, método de trabajo, deudas"
status: assigned
assigned_to: copilot
created_by: cursor
priority: high
sprint: workspace-hygiene
created_at: "2026-07-02"
updated_at: "2026-07-03T01:50"
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
- [ ] Pass 8 rescates (base + coordinador) + PRs
- [ ] Cierre task + limpieza ramas -copilot

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
