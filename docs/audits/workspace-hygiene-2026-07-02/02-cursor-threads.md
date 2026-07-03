# Pass 2 — Hilos Cursor

> Fuentes: `C:\Users\david\.cursor\projects\` (metadata, sin volcar transcripts), `.agents/tasks/`, `.agents/board.md`, `docs/ops/*MEGAPROMPT*`, `docs/ops/sprint-2026-07-02-prompts-index.md`.

## Proyectos Cursor con actividad relevante

| Proyecto Cursor | Última actividad | Relación UAS |
|---|---|---|
| `c-GitHub-umbral-agent-stack` | **2026-07-02 20:25** (hoy) | Hilo lead sobre el **clone base** (que está en `codex/cand-prod001-stage2` con 58 dirty — ver Pass 1/8) |
| `c-GitHub-notion-governance` | **2026-07-02 21:15** (hoy) | Gobernanza Notion — repo hermano, mismo universo board |
| `c-GitHub-umbral-bot-cursor` | 2026-07-02 21:16 (hoy) | umbral-bot-2 — fuera de alcance UAS |
| `c-GitHub-notion-governance-cursor` | 2026-04-16 | stale |
| `c-GitHub-cursor-codex-bridge` | 2026-03-30 | stale |
| ~40 proyectos `Temp-*` + IDs numéricos | feb–jun | Ruido de ventanas temporales — sin valor, candidatos a limpieza de recientes en Cursor |

## Hilos Cursor identificados (por task/megaprompt)

| Hilo/tema | Estado inferido | Task/PR | Recomendación |
|---|---|---|---|
| **Rick voz capitalización** | assigned cursor (megaprompt listo, no ejecutado) | `2026-07-02-004` | **MANTENER** — próximo hilo Cursor |
| **Notion MCP audit** | assigned (paralelo, puede ser Codex o Cursor) | `2026-07-02-005` | **MANTENER** (hilo nuevo dedicado) |
| Graphify F1–F2 (Cursor en clone `-copilot`) | done — resultados absorbidos por F3–F4 Copilot | `2026-07-02-002` / PR #495 | **ARCHIVAR** tras merge/cierre de PR #495 |
| CAND-001 closeout (unpublish fixture + bitácora) | done (`CAND001_BLOG_EXAMPLE_COMPLETE`, PR #494 merged) | `2026-07-02-001` | **ARCHIVAR** |
| CAND-001 Magnific megaprompt (clone `cand001-v31`) | done — rama pushed | `cursor/cand001-magnific-megaprompt` | **ARCHIVAR** |
| Editorial CAND-001 production final (`_wt-editorial-pr-492`) | done — ciclo #492/#494 cerrado | — | **ARCHIVAR** |
| Hilo lead board/sprint (base clone) | activo pero **contaminado**: base clone sucio en rama codex | board + sprint index | **MIGRAR** → re-basar el hilo lead sobre clone saneado (Pass 9) y archivar el hilo viejo |

## Hallazgos

1. **El hilo lead de Cursor opera sobre el clone base sucio** (`umbral-agent-stack` en rama `codex/cand-prod001-stage2`, 58 archivos dirty, 1 commit sin push). Todo lo que Cursor cree "guardado" ahí NO está en main.
2. **Colisión de IDs de task 2026-07-02**: el clone base tiene `2026-07-02-001-rick-voice-tts-mvp-restart-smoke.md` y `2026-07-02-002-capitalize-rick-voice-persona-mvp.md` (untracked), mientras el clone `-copilot` usa 001=cand001-closeout, 002=graphify, 003=rick-voice-smoke, 004=capitalize. La numeración canónica es la del clone `-copilot` (es la referenciada por el sprint index); los duplicados del base se descartan en el rescate (mismo contenido renumerado).
3. Los task files y megaprompts del sprint 2026-07-02 estaban **solo en working trees** (ni commit ni push) → un `git pull` de Copilot-VPS jamás los habría visto. Violación directa del PROTOCOL § Handoffs. Rescatados en el PR de esta auditoría.
4. Cursor debería cerrar/archivar en su UI los hilos de proyectos Temp-* y los hilos done listados arriba (acción manual David — este audit solo recomienda).

## Regla aplicada

**MANTENER** = task assigned/in_progress o PR abierto sin merge. **ARCHIVAR** = done/superseded. No se archivó nada en el IDE desde esta auditoría.
