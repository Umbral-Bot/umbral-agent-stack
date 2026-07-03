# Pass 8 — Candidatos de rescate desde clones obsoletos

> Evidencia `git cherry` + `git status` por clone (2026-07-02). **Ninguna acción ejecutada** — lista para que David/Cursor autoricen. Leyenda: `cherry -` = contenido ya en main (squash); `cherry +` = contenido NO en main.

## 1. `umbral-agent-stack` (base) — RESCUE prioritario

**Commits:**
- `71ea7ad6` (stage2 intake) — pushed a `origin/codex/cand-prod001-stage2` ✅ preservado en remote.
- `a85563b8` (stage3 variants + repo benchmark) — **SOLO LOCAL, sin push** → **acción: `git push origin codex/cand-prod001-stage2`** (1 comando, cero riesgo).

**Dirty (58) — material único no en main:**
- `?? .agents/tasks/2026-07-02-001-rick-voice-tts...` y `002-capitalize...` → **DESCARTAR** (duplicados renumerados; canónicos ya rescatados como 003/004 en el PR de este audit).
- `?? config/editorial-model.yaml`, `?? docs/adr/ADR-009-linkedin-company-api.md`, `?? docs/audits/foundry-gpt-5.5-audit-20260606.md` → **COPIAR MANUAL** a rama nueva desde main (`cursor/rescue-base-clone-2026-07`).
- `M docs/adr/ADR-006/008`, `M docs/editorial-pipeline/*`, `M docs/specs/sistema-editorial-rick-v1.md`, `M prompts/rick/linkedin-copy-system.md`, `M scripts/discovery/lib/variants.py` → **REVISAR DIFF y cherry-pick selectivo** (posible iteración editorial valiosa CAND-PROD-001).
- `M openclaw/workspace-agent-overrides/*` (6) + `workspace-templates/*` (4) → **REVISAR** contra estado VPS antes de decidir (pueden ser ya aplicados en runtime — regla VPS Reality Check).
- `M .agents/board.md`, `M .claude/settings.local.json`, `M docs/ops/q2-core-first-unified-plan...` → descartar (stale locales).

## 2. `umbral-agent-stack-codex-coordinador` — RESCUE

Rama `codex/editorial-linkedin-smoke-rescue` **local-only** pero 0 ahead (sin commits propios) — el valor está TODO en dirty (16):
- `?? docs/ops/editorial-linkedin-quality-smoke-tests.md`, `?? docs/ops/editorial-publicaciones-human-review-contract.md` → **COPIAR MANUAL** (contratos editoriales únicos).
- `M evals/editorial/gold-set-minimum.yaml`, `M docs/ops/editorial-agent-flow.md`, `M openclaw/.../ROLE.md` (x2), `M .../CALIBRATION.md`, `M .../SKILL.md` (x3) → **REVISAR DIFF** — calibraciones editorial/LinkedIn posiblemente posteriores a main.
- `?? *.png` (4 screenshots), `?? .playwright-mcp/`, `?? scripts/export-vscode-config.ps1` → descartar (artefactos de sesión).

## 3. `umbral-agent-stack-cand001-v31` — rescate trivial

- Commit `bba2cf1b` pushed ✅ (`origin/cursor/cand001-magnific-megaprompt`).
- `?? _patch_blog_prompt.py` → revisar 30 segundos; probable descarte (script one-shot ya ejecutado).

## 4. `umbral-agent-stack-codex` (fósil granola) — verificación única, luego ARCHIVE

- Rama en remote ✅. Dirty (14): iteración granola de abril (`worker/app.py`, `worker/sanitize.py`, `scripts/vm/granola_*`, 4 audits night-watch untracked).
- El pipeline Granola fue rediseñado después (V2) → **probable descarte total**, pero: **COPIAR MANUAL solo `docs/audits/granola-*.md`** (4 archivos, valor histórico de auditoría) si no están en main. Código: descartar.

## 5. `copilot-worktrees/.../umbralbim-stunning-fiesta` — verificación única

- Rama local-only `umbralbim-copilot-feat-pit-broker-contract` HEAD `1fb4701e` "copilot_cli lane metadata audit + reasoning_effort contract".
- **Acción:** `git -C <path> cherry origin/main HEAD` — si `-`, DELETE; si `+`, push rama al remote como preservación barata y DELETE del worktree.

## 6. Sin rescate necesario (evidencia cherry `-` o rama en remote, dirty=0)

`-claude`, `-p2c-egress-repo`, `-pit-closure`, `-pit-p3`, `-pit-p5`, `-pit-p6`, `-pit-readiness`, `-pit-p10`, `-copilot-fresh`, `-antigravity`, `-config`¹, `umbralbim-didactic-fortnight`, `umbralbim-legendary-dollop`, `_wt-editorial-pr-492`².

¹ `-config`: 411 "ahead" son historia pre-rewrite de main (mar-06); spot-check recomendado de `git log --oneline origin/main..main -- docs/ | head` antes de archivar. NO borrar sin ese check.
² rama `cursor/editorial-cand001-production-final`: ciclo #492/#494 merged — verificar `git cherry` del worktree antes de borrar (1 comando).

## 7. Este clone (`-copilot`) — rescate ejecutado en este PR

- 24 archivos sprint (tasks + megaprompts + closeouts + 4 M docs/ops) → commiteados en el PR del audit.
- **Excluidos deliberadamente:** `graphify-out/` (prohibido por megaprompt graphify), `scripts/ops/evaluate-gate.ps1` + `p10-sec63-*.ps1` (huérfanos — adjudicar a hilo dueño, P1-9).

## Resumen accionable (para G-WH-1)

| Acción | Comandos | Riesgo |
|---|---|---|
| Push rama base | `git -C C:\GitHub\umbral-agent-stack push origin codex/cand-prod001-stage2` | nulo |
| Rescate base dirty | rama `cursor/rescue-base-clone-2026-07` + copiar 3 nuevos + diff selectivo 12 M | bajo |
| Rescate coordinador | rama `codex/rescue-editorial-contracts-2026-07` + copiar 2 docs + diff 8 M | bajo |
| Verificaciones únicas | cherry stunning-fiesta, `_patch_blog_prompt.py`, granola audits, config spot-check | nulo |
