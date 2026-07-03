# Pass 5 — Hilos Codex / Antigravity / otros

> Fuentes: clones `-codex`, `-codex-coordinador`, `-codex-pit-v2-contract`, `-antigravity`, `-config`, `pit-*`, `copilot-worktrees/`, PRs.

## Codex

### Clones (3 + 6 pit-*)

| Clone | Rama | Estado | Veredicto |
|---|---|---|---|
| `-codex` | `codex/granola-raw-intake-batch` (en remote) | HEAD 2026-04-13, 701 ahead/1438 behind (historia pre-rewrite), **14 dirty granola** | **ARCHIVE** — fósil abril; dirty = iteración granola histórica (pipeline ya rediseñado post-V2); verificación única en Pass 8 |
| `-codex-coordinador` | `codex/editorial-linkedin-smoke-rescue` (**local-only**) | HEAD 2026-05-30, 0 ahead, **16 dirty editoriales** | **RESCUE** — dirty incluye contratos editoriales y calibraciones de skills no presentes en main (Pass 8) |
| `-codex-pit-v2-contract` | `codex/docs-pit-v2-contract` (en remote) | 1 ahead = **PR #480 abierto** | **ARCHIVE** — el PR preserva el contenido; decidir merge/cierre de #480 |
| `pit-p3/p5/p6/p10/closure/readiness/p2c-egress` | varias | contenido ya en main (squash) | **DELETE-CANDIDATE** (Pass 1) |

### Hilos Codex

| Hilo | Estado | Recomendación |
|---|---|---|
| PIT v2 contrato (PR #480) | abierto sin actividad desde 2026-06-20 | **DECIDIR**: merge (docs útiles) o cierre; luego ARCHIVAR hilo |
| Notion MCP audit (task `2026-07-02-005`) | assigned — puede ejecutarlo Codex o Cursor | **MANTENER** |
| Granola intake (clone `-codex`) | superseded por pipeline V2 en main | **ARCHIVAR** |
| Editorial linkedin smoke rescue (coordinador) | interrumpido — material en dirty local | **RESCATAR → ARCHIVAR** |
| CAND-PROD-001 stage2/3 (clone base, ramas codex) | 1 commit pushed + 1 SIN push + dirty | **RESCATAR** (Pass 8) — es el hilo editorial soak vivo más reciente en clone base |

## Antigravity

| Aspecto | Valor |
|---|---|
| Clone | `-antigravity`, rama `antigravity/001-rick-recommendations` (en remote) |
| HEAD | 2026-03-09 — fósil de marzo, 465 ahead/1438 behind (pre-rewrite) |
| Dirty | 0 |
| Hilos activos | **NINGUNO** — sin tasks `assigned_to: antigravity` vivas |

**Veredicto:** ARCHIVE del clone. Si Antigravity vuelve a usarse (research), re-clonar fresco o `checkout main` en clone saneado. Las 4 ramas `antigravity/*` remotas son históricas.

## `-config` y `-copilot-fresh`

- `-config`: main divergido pre-rewrite (411/1438), HEAD 2026-03-06, limpio → **ARCHIVE** (no borrar sin una verificación de que la historia pre-rewrite no contenga nada único — baja probabilidad, ver Pass 8).
- `-copilot-fresh`: main stale limpio, 0 ahead → **DELETE-CANDIDATE** puro (cero valor único).

## copilot-worktrees/umbral-agent-stack (3 worktrees jun-22, PIT P10)

| Worktree | Rama | Veredicto |
|---|---|---|
| `umbralbim-didactic-fortnight` | = #488 merged | DELETE-CANDIDATE |
| `umbralbim-legendary-dollop` | local-only, commit CI re-trigger sobre #488 | DELETE-CANDIDATE |
| `umbralbim-stunning-fiesta` | local-only `umbralbim-copilot-feat-pit-broker-contract` | verificar contenido vs main (Pass 8) y luego DELETE |

## Duplicación codex-coordinador vs codex vs base

Confirmada la sospecha del megaprompt: **tres clones "codex" con propósitos solapados**. El de abril (`-codex`) es fósil granola; el coordinador (mayo) quedó con material editorial sin commitear; y el clone base terminó secuestrado por ramas `codex/cand-prod001-*`. Modelo objetivo: **UN clone Codex** (`-codex-coordinador` saneado a main) y el base devuelto a Cursor lead — ver Pass 9.
