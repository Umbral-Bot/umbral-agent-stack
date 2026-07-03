# Pass 4 — Hilos Claude Code

> Fuentes: clone `umbral-agent-stack-claude`, `.claude/` en repo, ramas `claude/*` remotas, tasks con `assigned_to: claude`.

## Estado del clone

| Aspecto | Valor |
|---|---|
| Path | `C:\GitHub\umbral-agent-stack-claude` |
| Rama | `claude/feat-pit-2b-spawn` (**local-only**, no en remote) |
| HEAD | `47db09a` 2026-06-10 — PIT-2b spawn agentes efímeros |
| Dirty | 0 |
| vs main | 25 behind, 1 ahead — pero `git cherry` = patch **ya en main** (squash-merge) |

## Ramas `claude/*` en remote (4)

| Rama | Tema | Estado |
|---|---|---|
| `claude/090-implementar-notion-bitacora` | Bitácora Notion (R16, ~feb-mar) | histórica |
| `claude/audit-creator-tracking-TX9zV` | audit tracking | histórica |
| `claude/feat-azure-editorial-blog-v1` | blog editorial Azure | histórica (ciclo CAND-001 cerrado por otra vía) |
| `claude/task-004-project-governance` | governance | histórica |

Ninguna tiene PR abierto. Candidatas a limpieza remota post-G-WH-1 (verificar 1 vez con `git log origin/main..origin/claude/<rama>`).

## Tooling Claude en repo (valor a conservar)

- `.claude/commands/` — 7 comandos: `e2e`, `linear`, `notion-spec`, `openclaw`, `pr`, `routing`, `vps`.
- `.claude/skills/` + `settings.local.json`.
- El clone base tiene `M .claude/settings.local.json` dirty — diff local de settings, no crítico.

## Hilos Claude

| Hilo | Estado | Recomendación |
|---|---|---|
| PIT-2b spawn efímeros | done (contenido en main vía squash) | **ARCHIVAR** |
| Bitácora/gov/blog (ramas remotas viejas) | done/superseded | **ARCHIVAR** + limpiar ramas |
| Hilo activo actual | **NO HAY** — ninguna task `assigned_to: claude` viva | — |

## Recomendación

1. **KEEP** el clone como superficie Claude (máx 1 hilo), pero **re-apuntarlo a main** (`git checkout main && git pull --ff-only`) antes del próximo uso — está 25 commits atrás en una rama fósil local-only.
2. Claude Code queda **sin hilo activo** hoy: correcto según board (nada asignado). No abrir hilo hasta que Cursor lead asigne task.
3. Los `.claude/commands` son el artefacto de mayor valor de esta superficie — ya versionados en main; no requieren acción.
