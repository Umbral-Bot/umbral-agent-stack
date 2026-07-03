# Pass 3 — Hilos GitHub Copilot Windows

> Fuentes: `docs/ops/copilot-handoff-prompts.md`, `.agents/tasks/*`, ramas `copilot/*` locales, `gh pr list --state open`.

## PRs abiertos en Umbral-Bot/umbral-agent-stack (8)

| PR | Rama | Título | Fecha | Draft | Hilo/acción |
|---|---|---|---|---|---|
| **#495** | `copilot/graphify-pilot-f1-f4` | ops(graphify): pilot F1–F4 — .graphifyignore + results | 2026-07-03 | no | **ACTIVO** — GO_PARTIAL S7/R6, **G-GR-1 ya firmado** (commit `367f4d6`); pendiente decisión merge David |
| **#480** | `codex/docs-pit-v2-contract` | docs(pit): contrato v2 broker-real | 2026-06-20 | no | Codex — decidir merge o cierre (hilo PIT pausado) |
| #421 | `evidence/openclaw-e2e-cycle-001` | evidencia E2E OpenClaw | 2026-05-19 | draft | zombi — cerrar o mergear como evidencia |
| #418 | `copilot/feat-o16-2-047-gap-closure` | tests pdf_parser + gap audit | 2026-05-14 | draft | zombi O16.2 — cerrar |
| #413 | `coord-ag-2a/...` | [DO NOT MERGE] aeco-source-crawler pinned | 2026-05-10 | draft | zombi marcado DO-NOT-MERGE — cerrar |
| #389 | `rick/stage7_5-multiformat` | multi-format generation (DRAFT) | 2026-05-08 | draft | zombi — cerrar o re-planificar |
| #379 | `copilot-vps/052-aeco-kb-build-blocked...` | blocked PAT scope GHCR | 2026-05-08 | no | bloqueado desde mayo — cerrar con nota |
| #321 | `copilot/feat-o16-infra-base` | O16 infra base (Bicep + ADR) | 2026-05-07 | no | zombi O16 — decidir rescate de ADRs o cierre |

## Hilos Copilot Windows

| Hilo | Estado | Task/PR | Recomendación |
|---|---|---|---|
| **GR — Graphify F3–F4** | GO_PARTIAL S7/R6; PR #495 abierto SIN merge; G-GR-1 firmado | `2026-07-02-002` / #495 | **MANTENER** hasta merge o cierre explícito |
| **WH — Workspace hygiene audit** (este) | in progress | `2026-07-02-006` / PR de esta rama | **MANTENER** hasta merge |
| CAND-001 unpublish + closeout | done — PR #494 merged, `CAND001_BLOG_EXAMPLE_COMPLETE` | `2026-07-02-001` | **ARCHIVAR** |
| PIT P3/P5/P6/P10/readiness/closure (jun-22) | done — contenido squash-merged en main | clones pit-* | **ARCHIVAR** (clones a DELETE, Pass 1) |
| Hilos históricos D3–D6 / AA–AF / O15 / O16 | ✅ done según `copilot-handoff-prompts.md` | board | **ARCHIVAR** — ya solo valor histórico |
| Azure `oai-umbral-agents-prod` provisioning | done (recurso creado; doc en rescate) | `azure-openai-umbral-agents-provisioning.md` | **ARCHIVAR** doc como referencia |

## Ramas `copilot/*` y `feat/copilot-*` locales en clone canónico

- 20+ ramas locales fósiles (R4–R16, feb–abr) cuyos upstream están `gone` o merged: `copilot/082..092`, `feat/copilot-*` (10), `docs/env-google-keys-example` (ahead 334 — pre-rewrite), `backup/local-untracked-2026-04-29`.
- Recomendación: tras G-WH-1, `git branch -D` de las que tienen upstream `gone`/merged. `backup/local-untracked-2026-04-29` revisar 1 vez y borrar.
- `copilot/pit5-mc-v2-plan` (upstream gone) — plan Mission Control v2: verificar si el doc llegó a main antes de borrar.

## Hallazgos

1. Copilot Windows es hoy la superficie con el clone más sano (`-copilot`, 0 behind) — confirma su rol de clone canónico Windows.
2. 6 de 8 PRs abiertos son zombis de mayo — ninguno del flujo actual. Cerrarlos (sin merge, con comentario) reduce el ruido de `gh pr list` a señal real.
3. El patrón "1 clone nuevo por PR PIT" (jun-22) generó 6 clones desechables en un día — el modelo worktree/rama sobre clone canónico los habría evitado (ver Pass 6).
