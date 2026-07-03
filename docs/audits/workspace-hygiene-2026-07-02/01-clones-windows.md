# Pass 1 — Inventario clones Windows (`C:\GitHub`)

> Auditoría workspace hygiene 2026-07-02 · task `2026-07-02-006` · evidencia capturada en vivo (git fetch + status por clone).
> Todos los remotes apuntan a `https://github.com/Umbral-Bot/umbral-agent-stack.git`.

## Tabla de inventario (17 clones)

| Clone | Branch | Dirty | Behind main | Ahead main | HEAD (fecha) | Clasificación |
|---|---|---:|---:|---:|---|---|
| `umbral-agent-stack` (base) | `codex/cand-prod001-stage2` | **58** | 46 | 2 (**1 sin push**) | 2026-06-06 | **RESCUE** |
| `umbral-agent-stack-copilot` | `copilot/workspace-hygiene-audit-2026-07-02` | 27¹ | 0 | 0 | 2026-07-02 | **KEEP** (canónico Copilot Windows) |
| `umbral-agent-stack-antigravity` | `antigravity/001-rick-recommendations` | 0 | 1438 | 465² | 2026-03-09 | **ARCHIVE** (rama en remote) |
| `umbral-agent-stack-cand001-v31` | `cursor/cand001-magnific-megaprompt` | 1 | 3 | 1 (pushed) | 2026-06-30 | **ARCHIVE** (rescate trivial: `_patch_blog_prompt.py`) |
| `umbral-agent-stack-claude` | `claude/feat-pit-2b-spawn` | 0 | 25 | 1 (ya en main³) | 2026-06-10 | **KEEP** (superficie Claude; re-apuntar a main) |
| `umbral-agent-stack-codex` | `codex/granola-raw-intake-batch` | 14 | 1438 | 701² | 2026-04-13 | **ARCHIVE** (fósil granola; rama en remote; dirty histórico) |
| `umbral-agent-stack-codex-coordinador` | `codex/editorial-linkedin-smoke-rescue` (**local-only**) | **16** | 130 | 0 | 2026-05-30 | **RESCUE** |
| `umbral-agent-stack-codex-pit-v2-contract` | `codex/docs-pit-v2-contract` | 0 | 19 | 1 (pushed, **PR #480 abierto**) | 2026-06-20 | **ARCHIVE** (PR lo preserva) |
| `umbral-agent-stack-config` | `main` (divergida pre-rewrite) | 0 | 1438 | 411² | 2026-03-06 | **ARCHIVE** (fósil marzo) |
| `umbral-agent-stack-copilot-fresh` | `main` (stale) | 0 | 130 | 0 | 2026-05-30 | **DELETE-CANDIDATE** |
| `umbral-agent-stack-p2c-egress-repo` | `codex/fix-pit-p2c-egress-github-meta-requirement` | 0 | 19 | 1 (ya en main³) | 2026-06-21 | **DELETE-CANDIDATE** |
| `umbral-agent-stack-pit-closure` | `copilot/docs-pit-broker-real-pass-handoff-20260622` | 0 | 13 | 1 (ya en main³) | 2026-06-22 | **DELETE-CANDIDATE** |
| `umbral-agent-stack-pit-p10` | `main` (stale) | 0 | 11 | 0 | 2026-06-22 | **DELETE-CANDIDATE** |
| `umbral-agent-stack-pit-p3` | `codex/feat-pit-p3-policy-slugs-aliases` | 0 | 19 | 1 (ya en main³) | 2026-06-22 | **DELETE-CANDIDATE** |
| `umbral-agent-stack-pit-p5` | `copilot/feat-pit-broker-enforce-skill` | 0 | 16 | 1 (ya en main³) | 2026-06-22 | **DELETE-CANDIDATE** |
| `umbral-agent-stack-pit-p6` | `copilot/feat-pit-token-ledger` | 0 | 15 | 1 (ya en main³) | 2026-06-22 | **DELETE-CANDIDATE** |
| `umbral-agent-stack-pit-readiness` | `copilot/docs-pit-readiness-golden-20260622` | 0 | 14 | 1 (ya en main³) | 2026-06-22 | **DELETE-CANDIDATE** |

¹ Los 27 dirty de `-copilot` son los docs/tasks del sprint 2026-07-02 nunca commiteados (megaprompts, tasks 001/003/004/005/006, closeouts) — **se rescatan en el PR de esta auditoría** (excepto `graphify-out/` y `scripts/ops/*` — ver Pass 8).
² Behind/ahead ~1438/400-700 = divergencia de historia pre-rewrite de main (marzo–abril). No son commits "rescatables" uno a uno; son historia antigua ya capitalizada o superada.
³ `git cherry` marca el patch como ya aplicado en main (squash-merge). El commit local difiere en SHA pero no en contenido.

## Checkouts UAS adicionales fuera del patrón `umbral-agent-stack*`

| Path | Branch | HEAD | Nota |
|---|---|---|---|
| `C:\GitHub\copilot-worktrees\umbral-agent-stack\umbralbim-didactic-fortnight` | `umbralbim-didactic-fortnight` | 2026-06-22 (= #488 merged) | DELETE-CANDIDATE |
| `...\umbralbim-legendary-dollop` | `umbralbim-copilot-feat-p10-openclaw-broker` (**local-only**) | 2026-06-22 | commit CI re-trigger sobre #488 ya merged — DELETE-CANDIDATE |
| `...\umbralbim-stunning-fiesta` | `umbralbim-copilot-feat-pit-broker-contract` (**local-only**) | 2026-06-22 | verificar contenido vs main antes de borrar (Pass 8) |
| `C:\GitHub\_wt-editorial-pr-492` | `cursor/editorial-cand001-production-final` | — | worktree editorial CAND-001; PR #492/#494 ciclo cerrado — ARCHIVE |

Dirs `_wt-protocol`, `_wt-q-3`, `uas-l6-worktree` contienen solo fragmentos `.agents/` sin `.git` → basura de worktrees rotos, DELETE-CANDIDATE tras inspección visual rápida.

## Resumen

- **KEEP: 2** (`-copilot` canónico Copilot/Cursor-graphify, `-claude` re-apuntado) + base como lead Cursor **después** del rescate (ver Pass 9).
- **RESCUE: 2 críticos** (base, codex-coordinador) + 1 trivial (cand001-v31) + 1 verificación (stunning-fiesta).
- **ARCHIVE: 4** (antigravity, codex, config, cand001-v31, pit-v2-contract, _wt-editorial-pr-492).
- **DELETE-CANDIDATE: 8** clones pit-*/fresh/p2c + 2 worktrees umbralbim-* (contenido ya en main vía squash-merge, working trees limpios).

**Nada se borra en esta pasada** — gate `G-WH-1` (David) requerido; ver Pass 9 para el plan.
