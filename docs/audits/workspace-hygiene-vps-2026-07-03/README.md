# Workspace Hygiene Audit — VPS — 2026-07-03

> Task `2026-07-02-006` (extensión VPS) · Espejo del audit Windows Pass 10 · Ejecutado por Copilot-VPS
> MEGAPROMPT: `docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt` · Modo: **read-only** (0 deletes, 0 restarts, 0 push runtime)
> Base: `main` @ `60f605a` (PR #500 merged)

## Veredicto

```
WORKSPACE_HYGIENE_VPS_READY | checkouts=15 | rescue=5 | canonical_proposed=YES
VPS_WORKSPACE_HYGIENE_READY | checkouts=15 | rescue=5 | crons_repo=17 | drift_openclaw=YES
```

## Índice

| Pass | Doc | Contenido clave |
|---|---|---|
| V1 | [01-checkouts-vps.md](01-checkouts-vps.md) | 15 checkouts git (5 clones + 10 worktrees) + 2 residuos. 1 KEEP, 3 RESCUE, 8 ARCHIVE, 5 DELETE-candidate |
| V2 | [02-runtime-consumers.md](02-runtime-consumers.md) | 17 crons activos + 3 services python → **todos al canónico**. Sin P0 |
| V3 | [03-openclaw-drift.md](03-openclaw-drift.md) | Drift repo→runtime en AGENTS/SOUL/VOICE/IDENTITY (runtime evolucionado); 2 overrides sin desplegar |
| V4 | [04-rescue-and-canonical.md](04-rescue-and-canonical.md) | **TABLA PRINCIPAL**: 5 grupos rescue + propuesta canónica + plan de convergencia `rick/vps` — gate **G-WH-VPS-1** |

## Resumen ejecutivo

1. **El runtime está sano**: los 17 crons y los 3 services systemd (worker, dispatcher, mission-control) leen exclusivamente `/home/rick/umbral-agent-stack` (canónico, main @ 60f605a, 0 ahead/0 behind). El gateway corre desde npm-global (esperado). **Ningún consumidor lee un checkout no canónico.**
2. **Hallazgo P0 (rescue)**: el clone del workspace OpenClaw de Rick (`~/.openclaw/workspace/umbral-agent-stack`) vive en `rick/vps` con **7 commits que no existen en ningún ref remoto** (CAND-PROD001 decision brief jun-07 + identidad Embudo V2 + scripts vm-ssh de marzo) + 1 stash único.
3. **Hallazgo P0 (rescue)**: la rama `rick-delivery/poller-healthcheck-hardening` (worktree en `~/.openclaw/workspaces/rick-delivery/`) tiene ~20 commits no respaldados en origin (la rama remota homónima `notion-poller-*` NO la contiene).
4. **Deuda de ramas**: el canónico acumula **203 ramas locales**, de las cuales 103 tienen tip no respaldado en remoto ni mergeado en main (mayoría: evidencia F7/F8, lanes tournament `rick/t/*`). Triage bajo gate.
5. **24 stashes** en el canónico (may–jun) compartidos por sus 8 worktrees — espejo exacto del problema que Windows Pass 8 rescató. Triage bajo gate.
6. **~880 MB recuperables** archivando backup (456M), clone cursor (390M) y clone temporal cand001 (33M) — todo respaldado u obsoleto tras rescue.
7. **Drift OpenClaw**: runtime (`~/.openclaw/workspace/*.md`) evolucionó por encima de los templates del repo — repo dice base genérica / VPS muestra AGENTS.md +524 líneas de diferencia. No es incidente: es material vivo de Rick aún no capitalizado.

## Gate para David

| Gate | Alcance | Estado |
|---|---|---|
| **G-WH-VPS-1** | Autoriza: push de ramas rescue, moves a `~/archive/uas/`, `git worktree remove/prune`, borrado de residuos vacíos | ⬜ PENDIENTE FIRMA |
| G-WH-VPS-2 | (a 30 días de G-WH-VPS-1) borrado definitivo de lo archivado | ⬜ futuro |

**Nada fue movido, borrado, pusheado (runtime) ni restarteado en esta auditoría.**
