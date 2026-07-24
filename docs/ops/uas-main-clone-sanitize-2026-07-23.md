# Sanitización clon canónico `umbral-agent-stack` → main (2026-07-23)

## Objetivo
Volver a dejar `C:\GitHub\umbral-agent-stack` (clon canónico) como carpeta diaria de David, en `main` limpio y sincronizado con `origin/main`, y reducir el ruido de worktrees/ramas locales acumulado (~250 ramas, 4 worktrees, 5 archivos dirty).

## FASE A — Dirty del clon canónico

Estado inicial (`git status -sb` en `claude/plan-sys-diag-openclaw-worksystem-2026-07-17`):

| Path | Clasificación | Motivo |
|---|---|---|
| `.agents/board.md` | Ruido CRLF/LF | `git status` lo marcaba `M` pero `git diff` no mostraba ningún cambio de contenido (mixed line endings bajo `core.autocrlf=true`). No es una edición real. |
| `.agents/skills/secret-output-guard/SKILL.md` | Cambio real | Agrega frontmatter YAML + reordena la lista de ubicaciones mirror (nueva canonical = `notion-governance`). |
| `.agents/skills/umbral-rick-runtime/` (untracked) | Skill nueva legítima | 2 archivos (`SKILL.md`, `reference-gates.md`); coincide con la skill `umbral-rick-runtime` ya registrada en el listado de skills disponibles de la sesión. |
| `.audit-clones-temp.json` (untracked) | Basura temporal | Dump de inventario de clones (`Kind`, `Branch`, `Dirty`, etc.) generado por una auditoría anterior — nombre y contenido confirman que es temp. |
| `docs/plans/post-sys-diag-olas-ejecucion-2026-07-20.md` (untracked) | Doc real | Plan de 86 líneas, contenido sustantivo (post sys-diag). |

**Acción ejecutada** (paste sin "GO limpieza" explícito → default seguro): stash único con `-u`.

```
git -C C:\GitHub\umbral-agent-stack stash push -u -m "pre-main-sanitize-2026-07-23"
```

Resultado: `stash@{0}: On claude/plan-sys-diag-openclaw-worksystem-2026-07-17: pre-main-sanitize-2026-07-23`

Ya existían 5 stashes previos de sesiones anteriores (no tocados):
- `stash@{1}` On cursor/rick-voice-capitalize-mvp: wip-unrelated
- `stash@{2}` On codex/cand-prod001-stage2: pre-rescue-pass8
- `stash@{3}` On main: cursor-local-pre-merge
- `stash@{4}` On codex/audit-qw-worker: temp
- `stash@{5}` On main: board y tasks locales

Tras el push, `pre-main-sanitize-2026-07-23` quedó en `stash@{0}` (el más nuevo). **Para recuperarlo**: `git -C C:\GitHub\umbral-agent-stack stash show -p stash@{0}` (verificar índice actual antes, puede haber corrido más stash pushes desde este informe) o `git stash apply "stash@{pre-main-sanitize-2026-07-23}"` no es sintaxis válida — usar el índice numérico vigente u obtenerlo por mensaje: `git stash list | grep pre-main-sanitize-2026-07-23`.

## FASE B — Checkout main en el clon canónico

Bloqueo encontrado: `git checkout main` falló con `fatal: 'main' is already used by worktree at 'C:/GitHub/uas-main-wt'` — git no permite la misma rama en dos worktrees simultáneamente.

`uas-main-wt` existía, según el propio brief de la tarea, únicamente como "base limpia para orquestar la limpieza" — sin cambios propios, limpio, en la punta exacta de `origin/main` (`2c1018b2`). Se removió ese worktree (no se borró ninguna rama ni commit; `origin/main` queda intacto y el worktree puede recrearse en cualquier momento con `git worktree add`):

```
git -C C:\GitHub\umbral-agent-stack worktree remove C:\GitHub\uas-main-wt
git -C C:\GitHub\umbral-agent-stack checkout main
git -C C:\GitHub\umbral-agent-stack pull --ff-only origin main
```

Resultado: `Already up to date` — el canónico ya estaba exactamente en la punta de `origin/main`.

**Verificación final:**
```
branch: main
status: ## main...origin/main (limpio)
tip:    2c1018b2cbb101cceee9fbffbbf7e77fda11a651
        docs(editorial): smoke E2E P3 — evidencia dry-run A-I (#562)
```

Coincide con el smoke #562 esperado por el brief.

## FASE C — Worktrees

Estado final (`git worktree list`):

| Path | Branch | Estado |
|---|---|---|
| `C:/GitHub/umbral-agent-stack` | `main` | Canónico, limpio, en punta de origin/main |
| `C:/Users/david/.cursor/worktrees/umbral-agent-stack/reo` | detached HEAD @ `bce0754c` | **NEEDS_DAVID** — dirty (5 modified + 4 untracked incl. `update.zip`, `vps_pub_key.txt`), 1429 commits detrás de main |
| `C:/Users/david/.cursor/worktrees/umbral-agent-stack/wah` | detached HEAD @ `bce0754c` | **NEEDS_DAVID** — mismo estado que `reo` (duplicado) |
| `C:/Users/david/.cursor/worktrees/umbral-agent-stack/weo` | detached HEAD @ `bce0754c` | **NEEDS_DAVID** — mismo estado que `reo`/`wah` (duplicado) |

No se tocaron `reo`/`wah`/`weo` — están dirty, detached, y contienen `vps_pub_key.txt` (posible material sensible) sin GO explícito de David. Son 3 worktrees de Cursor aparentemente duplicados del mismo commit (`bce0754c`), 1429 commits detrás de main. **Pendiente:** David decide si son necesarios; si no, requieren revisión manual antes de borrar por el contenido dirty (posible clave/secreto en `vps_pub_key.txt`).

`uas-main-wt`: **removido** (ver FASE B) — era redundante una vez que el canónico está en main; no se borró ninguna rama, solo el checkout de worktree.

## FASE D — Ramas locales

Inventario inicial: 253 ramas locales.

**Borradas (117):** confirmadas por `git branch --merged origin/main` — es decir, su tip es ancestro directo de `origin/main` (merge real o fast-forward), por lo que no se perdió ningún commit único. Lista completa en el log de ejecución de esta sesión (prefijos `antigravity/`, `claude/`, `codex/`, `copilot/`, `cursor/`, `docs/`, `feat/`, `fix/`, `rick/`, y sueltas `integracion-prs-69-70-71-73`, `reconciliation/align-runtime`, `umbralbim-didactic-fortnight`).

**NO borradas — tabla para David (23 ramas con upstream `gone` pero SIN confirmación de containment, probablemente squash-merged o abandonadas; requieren revisión antes de borrar):**

| Rama | Último commit |
|---|---|
| `claude/docs-ola3-editorial-5-pitches` | docs(editorial): Ola 3 — 5 pitches de blog seleccionables |
| `claude/docs-ola3-expand-pitch02-candidate` | docs(editorial): Ola 3 — CAND-OLA3-02 candidato IFC 4.3 |
| `claude/fix-ola2-containment-stage9c-stage8` | fix(vps): B2 guard-fix — redact partial fingerprints |
| `codex/audit-openclaw-foundry-oauth-migration-20260713` | docs: audit Foundry to OpenAI OAuth migration |
| `codex/d36-worker-tournament-lane-github` | feat: add tournament lane github tools |
| `codex/docs-mpd2-closeout-b0004` | docs(editorial): close MP-D2 after PR 523 |
| `codex/eval-harness-obsidian-context` | feat: add core eval harness and obsidian context checks |
| `codex/feat-o2-registry-backup-alert-440` | feat: add registry backup failure alert |
| `codex/fix-aeco-search-doc-keys` | fix: encode AECO search document keys |
| `codex/fix-aeco-verify-runtime` | fix: include AECO verify gate in runtime image |
| `codex/fix-aeco-verify-sample-queries` | fix: make AECO verify sample queries configurable |
| `codex/o8d-granola-gap-check-fix` | fix: handle flattened granola gap check dates |
| `codex/obsidian-spanish-vault-folders` | fix: accept spanish obsidian vault folders |
| `codex/p3-editorial-sanitize-b0004` | docs(report): verify PR 523 b0004 |
| `codex/update-d61e-board` | docs: record D6.1e AECO KB verification |
| `copilot/feat-mission-control-o13-1-rebase` | feat(mission_control): O13.1 scaffold FastAPI + 5 endpoints |
| `cursor/editorial-baseline-deploy` | docs(editorial): deploy canonical editorial baseline to main |
| `cursor/editorial-cand001-production-final` | feat(editorial): CAND-001 final copy ALT1 + GPT-5.5 guardrail |
| `cursor/fix-secret-output-guard-yaml-20260721` | fix(skills): sync secret-output-guard YAML frontmatter |
| `fable/hygiene-h0-h1-close-20260713` | docs(agents): close hygiene H0/H1 logs and board |
| `fable/repo-hygiene-plan-20260713` | docs(hygiene): plan higiene repos Windows+VPS b0004 |
| `umbralbim-copilot-feat-p10-openclaw-broker` | chore(ci): re-trigger Tests on PR #488 HEAD |

Ramas locales restantes tras la limpieza: **136** (253 − 117).

No se tocó `main` ni `claude/plan-sys-diag-openclaw-worksystem-2026-07-17` (dueña del stash nuevo).

## Follow-up ejecutado (2026-07-24, Cursor orquestador — GO David)

1. **Stash** — contenido útil preservado en rama local `backup/pre-main-sanitize-2026-07-23` (`e2dac0e5` + commit `369472c4` con `umbral-rick-runtime/` + `docs/plans/post-sys-diag-olas-ejecucion-2026-07-20.md`). Se omitió `.audit-clones-temp.json`. Stash `pre-main-sanitize-2026-07-23` **dropped** (recuperable vía esa rama). Otros stashes viejos (`stash@{0}`…) intactos.
2. **reo/wah/weo** — `git worktree remove --force` de los tres. No se copió `vps_pub_key.txt` al repo (posible secreto). Si hace falta la clave, buscar backup fuera de git.
3. **23 ramas gone** de la tabla — borradas con `git branch -D` (squash-merge survivors / abandonadas).
4. **Worktrees** — solo queda el canónico en `main`.
5. **Carril n8n** — listo para el megaprompt POST-SMOKE (siguiente).

## Marcador

**UAS_MAIN_CLONE_SANITIZED** (+ follow-up cerrado)

`C:\GitHub\umbral-agent-stack` en `main` limpio @ `2c1018b2`. Backup local: `backup/pre-main-sanitize-2026-07-23`.
