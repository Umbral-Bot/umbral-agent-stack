# Pass 9 — Modelo canónico propuesto (Windows + GitHub)

> **Gate: G-WH-1 (firma David).** Nada de esto se ejecuta hasta la firma. Rescates de Pass 8 van ANTES de cualquier archivado.

## Clone canónico por superficie

| Superficie | Clone canónico | Ramas | Hilos activos máx | Acción previa |
|---|---|---|---|---|
| **Cursor lead** | `umbral-agent-stack` (base) | `cursor/*` | 2 | Rescate Pass 8 → `git checkout main && git pull --ff-only` |
| **Copilot Windows** | `umbral-agent-stack-copilot` | `copilot/*` | 2 | ninguna (ya sano) |
| **Codex** | `umbral-agent-stack-codex-coordinador` | `codex/*` | 2 | Rescate Pass 8 → checkout main |
| **Claude Code** | `umbral-agent-stack-claude` | `claude/*` | 1 | checkout main (sin rescate) |
| **Antigravity** | `umbral-agent-stack-antigravity` | `antigravity/*` | 1 (congelado) | checkout main solo si se reactiva |
| **Archivo** | resto (11) | — | 0 | mover a `C:\GitHub\_archive\uas\` (NO borrar aún) |

Racional: el base sigue siendo el proyecto registrado de Cursor (actividad hoy) → devolverlo al lead en vez de migrar el hilo. `-copilot` es el único clone 100% al día → ancla de Copilot Windows (ya consagrado por megaprompts recientes). Un solo clone Codex mata la triple duplicación.

**Regla de oro post-G-WH-1:** *nunca más un clone nuevo por tarea* — rama nueva sobre el clone canónico de la superficie (worktree `git worktree add` solo si hace falta paralelismo real, y se borra al mergear).

## Archivado propuesto (2 fases, reversible)

1. **Fase A (post-rescate):** `Move-Item` de los 11 a `C:\GitHub\_archive\uas\` + archivo `WHY.md` con la tabla Pass 1. Congelados, cero borrado.
2. **Fase B (a 30 días, gate G-WH-2):** si nadie los tocó → borrar. `pit-p10`, `copilot-fresh`, `p2c-egress` y worktrees `umbralbim-*` verificados pueden saltar directo a B si David quiere.

## TABLA PRINCIPAL — Hilos ACTIVOS vs ARCHIVAR por IDE

### MANTENER (5 hilos activos)

| IDE/superficie | Hilo | Task/PR | Próximo paso |
|---|---|---|---|
| Copilot Windows | **GR — Graphify F3–F4** | `2026-07-02-002` / **PR #495** | David: merge o cierre (G-GR-1 ya firmado, GO_PARTIAL S7/R6) |
| Copilot Windows | **WH — este audit** | `2026-07-02-006` / PR de esta rama | David: revisar + G-WH-1 |
| Cursor | **RV — Rick voz capitalización** | `2026-07-02-004` | ejecutar megaprompt (no rehacer smoke VPS) |
| Codex o Cursor | **NM — Notion MCP audit** | `2026-07-02-005` | hilo nuevo paralelo, read-only |
| Codex | **PIT v2 contrato** | **PR #480** | David: decisión merge/cierre → luego ARCHIVAR |

### ARCHIVAR (recomendación UI de cada IDE — solo David puede hacerlo)

| IDE | Hilos |
|---|---|
| Cursor | CAND-001 closeout (001 done) · Graphify F1–F2 (absorbido por #495) · CAND-001 Magnific (`cand001-v31`) · editorial PR-492 · hilo lead viejo sobre base sucio (re-abrir limpio post-rescate) · ~40 proyectos Temp-* |
| Copilot Windows | CAND-001 unpublish (done) · PIT P3/P5/P6/P10/closure/readiness (jun-22, merged) · históricos D3–D6/AA–AF/O15/O16 · Azure provisioning (done) |
| Claude | PIT-2b spawn (en main) · bitácora/gov/blog (ramas remotas viejas) |
| Codex | Granola intake (abril, superseded) · editorial smoke rescue (tras rescate Pass 8) · CAND-PROD-001 stage2/3 (tras push+rescate) |
| Antigravity | Rick recommendations (marzo) — todo |

### PRs a cerrar sin merge (con comentario, gate David)

#421 · #418 · #413 (`DO NOT MERGE` explícito) · #389 · #379 · decisión aparte para #321 (rescatar ADRs primero) y #480 (merge probable).

## Métricas del veredicto

- clones_windows = **17** (+4 checkouts UAS adyacentes) → objetivo: **5**
- rescue = **4** clones con material único (base, coordinador, cand001-v31 trivial, stunning-fiesta a verificar) + este clone (auto-rescatado en el PR)
- hilos_activos = **5** (GR, WH, RV, NM, PIT-#480)
