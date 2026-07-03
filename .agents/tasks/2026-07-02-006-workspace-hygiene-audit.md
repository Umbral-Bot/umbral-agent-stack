---
id: "2026-07-02-006"
title: "Auditoría workspace UAS — clones, hilos multi-IDE, método de trabajo, deudas"
status: assigned
assigned_to: copilot
created_by: cursor
priority: high
sprint: workspace-hygiene
created_at: "2026-07-02"
updated_at: "2026-07-02T21:10"
---

## Objetivo

Diagnosticar y proponer orden canónico para clones Windows + hilos Cursor/Copilot/Claude/Codex + handoff VPS. Entregable: auditoría multi-pass + tabla hilos activos vs archivar.

## MEGAPROMPT

`docs/ops/MEGAPROMPT-copilot-windows-workspace-hygiene-audit-2026-07-02.md`

## Entregables

- [x] `docs/audits/workspace-hygiene-2026-07-02/` (Pass 1–11)
- [x] `docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt` (generado, no ejecutado)
- [x] Tabla hilos activos/archivar por IDE (Pass 9)
- [x] PR audit docs — sin merge

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
- Prohibiciones respetadas: 0 clones borrados, 0 merges, 0 acciones VPS, 0 hilos archivados en IDE.
