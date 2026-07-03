# Pass V4 — Rescates y propuesta canónica VPS

> Fecha: 2026-07-03 · TODO lo listado aquí es PROPUESTA — **nada se ejecuta sin firma de G-WH-VPS-1**.

## A. Lista RESCUE (5 grupos)

| # | Material | Dónde vive | Unicidad verificada | Acción propuesta (post-gate) |
|---|---|---|---|---|
| R-V1 | **7 commits `rick/vps`** (CAND-PROD001 decision brief + identidad Embudo V2 + scripts vm-ssh + linear improvements; 16 archivos, +542/−32) + stash `windows-fs-b64` | `~/.openclaw/workspace/umbral-agent-stack` | tip no en NINGÚN ref remoto; commit-por-commit no en main | `git push origin rick/vps:rescue/vps-rick-2026-07-03` + PR selectivo (decision brief y docs útiles) o descarte explícito por archivo |
| R-V2 | **~20 commits `rick-delivery/poller-healthcheck-hardening`** (b7f8e41, may-18) | worktree `~/.openclaw/workspaces/rick-delivery/…-poller-hardening` (rama vive en canónico) | NO en origin; la remota homónima `rick-delivery/notion-poller-healthcheck-hardening` NO lo contiene (`merge-base` ✗) | push como `rescue/poller-hardening-2026-07-03` + comparar con el hardening ya mergeado en main (posible superseded) |
| R-V3 | **Commit 18cdc48** `docs: clarify editorial contract artifact paths` | clone backup `…backup-pre-cand001-…` | patch-id ≠ del 5a6b7aa homónimo del canónico; ninguno de los dos en main | rescatar AMBAS variantes (5a6b7aa canónico + 18cdc48 backup) en una rama docs y decidir cuál va a main |
| R-V4 | **5 untracked del canónico**: `00_auditoria_schema_rick_cursor.md` + PIT broker **v2/v3** lanes+spec (v1/v4 sí están en main) | `~/umbral-agent-stack` (espejados en el backup) | no tracked, no en origin | commit en rama `rescue/vps-untracked-2026-07-03` o descarte explícito si los PIT v2/v3 fueron iteraciones desechadas |
| R-V5 | **24 stashes** (may-05→jun-02) + **103 ramas locales con tip no respaldado** (censo: 81 backed / 19 merged / 103 candidatas) | canónico (compartidos por 8 worktrees) | tips ni en remoto ni ancestros de main; mayoría = evidencia F7/F8, lanes `rick/t/*`, stacks editoriales posiblemente capitalizados por otra vía | sesión de triage espejo de Windows Pass 8 (task aparte); NO borrar stashes ni ramas hasta triage |

## B. Propuesta de modelo canónico VPS

**UN checkout canónico**: `/home/rick/umbral-agent-stack` en `main`, actualizado solo con `git pull --ff-only origin main` (protocolo existente). Es donde ya apuntan los 17 crons y los 3 services (Pass V2) — la propuesta formaliza, no cambia runtime.

| Path | Destino propuesto (post-gate) |
|---|---|
| `~/umbral-agent-stack` | **CANÓNICO** — se queda |
| `~/.openclaw/workspace/umbral-agent-stack` | tras R-V1: re-apuntar a `main` (es el workspace vivo de Rick; decidir si Rick necesita clone propio o solo lectura del canónico) |
| `~/umbral-agent-stack.backup-pre-cand001-…` (456M) | tras R-V3/R-V4: `mv` → `~/archive/uas/` |
| `~/umbral-agent-stack-cursor` (390M) | `mv` → `~/archive/uas/` (todo respaldado en origin) |
| `~/umbral-agent-stack-cand001-apply-…` (33M) | `mv` → `~/archive/uas/` (clone temporal de apply, nada único) |
| 6 worktrees `rick/*` (copilot-cli, editorial, activation, postmerge, f7-code, f7-policy) | `git worktree remove` (tips = origin, cero pérdida) |
| worktree lane-sqlite-impl + lanes 434 a/b | `git worktree remove` (contenido en main / tips en origin) |
| dir vacío `…d35-33863db` + `/tmp/lane-b-clean-*` | rm dir vacío + `git worktree prune` |
| `~/.openclaw/workspaces/rick-delivery/…poller-hardening` | tras R-V2: `git worktree remove` |
| `rick-orchestrator.bak-pre-019-…` + `IDENTITY.md.bak.…` | `mv` → `~/archive/uas/openclaw-residues/` |

**Disco recuperable estimado**: ~880 MB en clones + ~50 MB worktrees + 43 MB coord-ag-evidence.

**Config propuesto** (1 línea, bajo gate): ampliar `remote.origin.fetch` del canónico a `+refs/heads/*:refs/remotes/origin/*` para que los censos y `--contains` no den falsos "únicos" (hoy solo trae `main` y `copilot/*`).

## C. Plan de convergencia `rick/vps` (NUNCA merge silencioso)

Estado: local `rick/vps` = 13↑/5↓ vs main, **7↑/141↓ vs `origin/rick/vps`** — tres líneas de historia distintas.

1. (Gate) Push del local como `rescue/vps-rick-2026-07-03` — congela el material.
2. Revisión por archivo del diff +542/−32: decision brief CAND-PROD001 → probablemente PR a `docs/ops/`; identity Embudo V2 → contrastar con `identity/` actual de main (main puede ser superset); scripts vm-ssh → contrastar con `scripts/` de main.
3. Cerrar la rama: `origin/rick/vps` (141 commits que el local no tiene) se evalúa aparte — puede contener su propio material único (fuera de alcance de este pass; anotado en debt).
4. Re-apuntar el workspace clone de Rick a `main` con el protocolo ff-only.

## D. Registro de deudas nuevas (VPS)

| ID | Prioridad | Deuda | Owner sugerido |
|---|---|---|---|
| VPS-P0-1 | P0 | 7 commits `rick/vps` sin respaldo remoto (single point of failure: disco VPS) | Copilot-VPS (post-gate) |
| VPS-P0-2 | P0 | ~20 commits poller-hardening sin respaldo | Copilot-VPS (post-gate) |
| VPS-P1-1 | P1 | 24 stashes + 103 ramas sin triage en canónico | task espejo Pass 8 |
| VPS-P1-2 | P1 | Drift AGENTS/SOUL/VOICE runtime→repo sin capitalizar (override main/ solo tiene IDENTITY) | Copilot-VPS + skill openclaw-vps-operator |
| VPS-P1-3 | P1 | `origin/rick/vps` (141 commits divergentes) sin auditar | task futura |
| VPS-P2-1 | P2 | `mission-control.service` ausente de la tabla de deploy en copilot-instructions | Cursor/docs |
| VPS-P2-2 | P2 | Refspec estrecho en canónico (falsos únicos en censos) | 1 línea config post-gate |
| VPS-P2-3 | P2 | Residuos: `rick-orchestrator.bak`, `IDENTITY.md.bak`, dir d35 vacío, worktree prunable /tmp | post-gate |
| VPS-P2-4 | P2 | Overrides `rick-editorial`/`rick-tech` en repo sin workspace desplegado (¿pendientes o abandonados?) | David decide |

## E. Qué NO se hizo (cumplimiento)

- 0 archivos borrados/movidos · 0 `worktree remove/prune` · 0 restarts · 0 ediciones a `~/.openclaw/*` o units · 0 push de ramas runtime · 0 merges.
- Único write fuera de esta rama de docs: fetch de remote-tracking refs (necesario para el censo; no toca ramas locales ni working trees).
