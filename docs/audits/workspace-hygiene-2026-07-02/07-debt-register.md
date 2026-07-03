# Pass 7 — Registro de deudas (P0/P1/P2)

> Owner sugerido entre paréntesis. Ningún ítem se ejecuta en esta pasada sin gate.

## P0 — riesgo de pérdida o bloqueo de handoffs (esta semana)

| # | Deuda | Detalle | Owner sugerido |
|---|---|---|---|
| P0-1 | **Sprint 2026-07-02 sin commitear** | 27 archivos (tasks 001/003/004/005/006 + 7 megaprompts + closeouts) solo en working tree de `-copilot` | **Resuelto en este PR** (commit rescate) — verificar merge (David) |
| P0-2 | **Commit sin push + 58 dirty en clone base** | `a85563b8` (CAND-PROD-001 stage3) solo local; dirty editorial/OpenClaw overrides desde jun-06 | ✅ **RESUELTO 2026-07-03** — push a `origin/codex/cand-prod001-stage2` (Cursor) + rescate PR #498 merged (Pass 8A) |
| P0-3 | **Colisión IDs task 2026-07-02-001/002** | base vs `-copilot` numeran distinto; handoffs ambiguos | Cursor lead — descartar duplicados base al rescatar; regla: IDs se asignan SOLO desde main actualizado |
| P0-4 | **Board stale en main** | header 2026-06-04/R23; updates viven en ramas sin merge (#495 + este PR tocan board → conflicto seguro) | Cursor lead — tras merges, board refresh único |
| P0-5 | **PR #495 Graphify pendiente decisión** | G-GR-1 firmado, GO_PARTIAL S7/R6; sin merge se pudre como los zombis de mayo | David — merge o cierre esta semana |

## P1 — fricción operativa real (este mes)

| # | Deuda | Detalle | Owner sugerido |
|---|---|---|---|
| P1-1 | **16 dirty editoriales en coordinador** | contratos human-review + calibraciones skills no en main | ✅ **RESUELTO 2026-07-03** — rescate PR #499 merged (Pass 8B): agent-flow, gold-set 011/012, ROLEs, CAL-008/009/010, 3 SKILLs |
| P1-2 | **6 PRs zombi de mayo** (#421 #418 #413 #389 #379 #321) | deciden cerrar/mergear; #321 tiene ADRs potencialmente valiosos | Copilot Windows + David |
| P1-3 | **PR #480 PIT v2 contrato sin decisión** | docs útiles congelados desde jun-20 | David + Codex |
| P1-4 | **11 clones/worktrees DELETE-CANDIDATE** | ~10 GB estimados y confusión de superficie | David firma G-WH-1 → script archivado |
| P1-5 | **Ramas locales fósiles en `-copilot`** | 20+ con upstream gone/merged | ✅ **RESUELTO 2026-07-03** — 13 borradas (Pass 8D); quedan 13 con upstream remoto vivo (limpieza remota = decisión aparte) + `backup/local-untracked-2026-04-29` (material `.claude/` único, decisión David) |
| P1-6 | **Graphify runbooks=0 nodos** (hallazgo GO_PARTIAL S7/R6) | runbooks/ no graphificados; skill no creada | según decisión #495 (Copilot Windows) |
| P1-7 | **Rick voz sin capitalizar en repo** | task 004 assigned, megaprompt listo | Cursor (hilo RV) |
| P1-8 | **Notion REST vs MCP gap** | task 005 auditoría pendiente | Codex/Cursor (hilo NM) |
| P1-9 | **`scripts/ops/*.ps1` huérfanos untracked** | `evaluate-gate.ps1`, `p10-sec63-*.ps1` en `-copilot` sin dueño claro | ✅ **RESUELTO 2026-07-03** — p10-sec63 ×2 en PR #498; `evaluate-gate.ps1` adjudicado a P10-SEC63 (gate evaluator FASE W2) y rescatado en closeout PR |

## P2 — estratégicas (trimestre)

| # | Deuda | Detalle | Owner sugerido |
|---|---|---|---|
| P2-1 | **Modelo canónico de clones no documentado** hasta hoy | resuelto por Pass 9 si David firma G-WH-1 | David |
| P2-2 | **Fósiles pre-rewrite** (`-codex`, `-antigravity`, `-config`) | historia divergida marzo-abril; verificar 1 vez y archivar | Codex |
| P2-3 | **Cutover Azure umbral-bot / oai-umbral-agents-prod** | recurso creado; integración Rick/UAS pendiente de roadmap | Cursor lead (planificar sprint) |
| P2-4 | **Misma enfermedad en umbral-bot-2** | 15+ clones `umbral-bot-*` en C:\GitHub fuera de alcance de este audit | replicar este audit (nuevo task) |
| P2-5 | **Ruido `.cursor/projects` Temp-\*** | ~40 proyectos basura en metadata Cursor | David (limpieza UI Cursor) |
| P2-6 | **VPS workspace sin auditar** | espejo de este audit en VPS | Copilot-VPS — **MEGAPROMPT ya generado** (Pass 10) |
