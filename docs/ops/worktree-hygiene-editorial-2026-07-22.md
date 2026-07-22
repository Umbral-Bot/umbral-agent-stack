# Worktree hygiene — barrida post #550/#551/#552 (2026-07-22)

## Veredicto

**Sí, valía limpiar.** 11 de 14 worktrees listados eran huérfanos 100% seguros
(PR ya mergeado a `main` con contenido idéntico + working tree limpio). Se
ejecutó `git worktree remove` sobre los 11 sin tocar el clon principal ni las
ramas locales. Quedan 3 worktrees de Cursor con cambios sin commitear —
**NEEDS_DAVID**, no se tocaron.

## Método de verificación

Para cada worktree candidato:

1. `git merge-base --is-ancestor <rama-local> origin/main` — todas dieron
   `NOT-merged` porque los PRs se **squash-mergearon** (el commit en `main`
   tiene un hash distinto al tip de la rama local).
2. Por eso se verificó con `git diff --stat <rama-local> <commit-en-main>`
   contra el commit de main correspondiente al número de PR — **diff vacío
   en los 11 casos**, confirmando que el contenido del worktree ya está
   100% en `main`.
3. `git status --porcelain=v1 --branch` en cada worktree — **limpio en los
   11 casos** (sin `M`/`??`).

## Tabla — worktrees inventariados

| Path | Rama local | PR / commit main | Estado | Recomendación | Acción |
|---|---|---|---|---|---|
| `C:/GitHub/umbral-agent-stack-editorial-p0` | `docs/editorial-p0-norte-contract` | #550 → `29e512bf` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `.../scratchpad/.../roadmap-wt` (Temp Claude) | `claude/editorial-roadmap-norte-2026-07-22` | #551 → `48216bd4` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-shortlist-mirror` | `docs/editorial-shortlist-schema-mirror` | #552 → `120ffbee` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-claude-ola2` | `claude/fix-ola2-containment-stage9c-stage8` | #544 → `136a1a47` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-claude-ola3` | `claude/docs-ola3-editorial-5-pitches` | #545 → `165f441c` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-claude-ola3-p02` | `claude/docs-ola3-expand-pitch02-candidate` | #546 → `df1bd5f6` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-claude-tanda-a` | `claude/fix-tanda-a-runtime-guardrails` | #542 → `843fb27b` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-claude-tanda-b` | `claude/docs-tanda-b-security-plan` | #543 → `7a174f9b` | merged+clean | CANDIDATE_REMOVE | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-b0004` | `codex/docs-mpd2-closeout-b0004` | #524 → `ac16876b` | merged+clean | CANDIDATE_REMOVE (huérfano, no editorial) | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/umbral-agent-stack-b0004-oauth` | `codex/audit-openclaw-foundry-oauth-migration-20260713` | #525 → `2f797091` | merged+clean | CANDIDATE_REMOVE (huérfano, no editorial) | ✅ `git worktree remove` ejecutado |
| `C:/GitHub/.tmp-gd52-adr-scopes` | `copilot/docs-gd52-adr-scopes` | #438 → `1187eaa9` | merged+clean | CANDIDATE_REMOVE (huérfano, no editorial) | ✅ `git worktree remove` ejecutado |
| `C:/Users/david/.cursor/worktrees/umbral-agent-stack/reo` | — (detached HEAD `bce0754c`) | n/a | **dirty** (5 modificados + 4 sin trackear) | NEEDS_DAVID | ❌ sin tocar |
| `C:/Users/david/.cursor/worktrees/umbral-agent-stack/wah` | — (detached HEAD `bce0754c`) | n/a | **dirty** (mismos cambios que `reo`) | NEEDS_DAVID | ❌ sin tocar |
| `C:/Users/david/.cursor/worktrees/umbral-agent-stack/weo` | — (detached HEAD `bce0754c`) | n/a | **dirty** (mismos cambios que `reo`) | NEEDS_DAVID | ❌ sin tocar |
| `C:/GitHub/umbral-agent-stack` (clon principal) | `claude/plan-sys-diag-openclaw-worksystem-2026-07-17` | n/a | dirty (sesión sys-diag activa) | KEEP | ❌ nunca tocado |

## Detalle: los 3 worktrees de Cursor (reo/wah/weo)

Los tres apuntan al mismo commit (`bce0754c`, detached HEAD) y tienen
**exactamente los mismos cambios sin commitear**:

```
M .env.example
M docs/15-model-quota-policy.md
M runbooks/runbook-full-stack-vps.md
M scripts/get_db_parent.py
M scripts/setup_notion_tasks_db.py
?? update.zip
?? vps_pub_key.txt
?? worker_err.txt
?? worker_out.txt
```

Parecen ser tres clones/sesiones paralelas de Cursor con el mismo trabajo
en progreso (posiblemente duplicado). No se determinó si `update.zip` /
`vps_pub_key.txt` contienen material sensible sin abrirlos — **David debe
revisar y decidir** si son la misma sesión duplicada 3x (candidato a
consolidar a 1) o trabajo genuino en curso.

## Ramas locales — huérfanas tras el remove (contenido ya en `main`)

Los 11 `git worktree remove` **no borran las ramas locales**. Quedan las
ramas apuntando a commits ya squash-mergeados. Verificado con
`git merge-base --is-ancestor` que **no** son ancestros directos de
`origin/main` (por el squash), así que `git branch -d` los va a rechazar
como "not fully merged" aunque el contenido sea idéntico (confirmado con
`git diff --stat` vacío arriba). Si David quiere limpiarlas, el comando
correcto es `-D` (forzado), no `-d`:

```bash
git branch -D claude/fix-ola2-containment-stage9c-stage8
git branch -D claude/docs-ola3-editorial-5-pitches
git branch -D claude/docs-ola3-expand-pitch02-candidate
git branch -D claude/fix-tanda-a-runtime-guardrails
git branch -D claude/docs-tanda-b-security-plan
git branch -D docs/editorial-p0-norte-contract
git branch -D docs/editorial-shortlist-schema-mirror
git branch -D claude/editorial-roadmap-norte-2026-07-22
git branch -D codex/docs-mpd2-closeout-b0004
git branch -D codex/audit-openclaw-foundry-oauth-migration-20260713
git branch -D copilot/docs-gd52-adr-scopes
```

No se ejecutaron — el mandato solo autorizaba `git worktree remove` en
candidatos 100% seguros, no borrado de ramas.

## Ramas remotas — no borradas, siguen vivas en origin

5 de las 11 ramas fuente **no fueron borradas en GitHub tras el merge**
(el resto sí, aparecen `[gone]`):

```
origin/claude/fix-tanda-a-runtime-guardrails
origin/claude/docs-tanda-b-security-plan
origin/docs/editorial-p0-norte-contract
origin/docs/editorial-shortlist-schema-mirror
origin/copilot/docs-gd52-adr-scopes
```

Borrar una rama remota es una acción visible/compartida — **no se ejecutó
sin GO explícito**. Comando propuesto si David lo autoriza:

```bash
git push origin --delete claude/fix-tanda-a-runtime-guardrails
git push origin --delete claude/docs-tanda-b-security-plan
git push origin --delete docs/editorial-p0-norte-contract
git push origin --delete docs/editorial-shortlist-schema-mirror
git push origin --delete copilot/docs-gd52-adr-scopes
```

## Fuera de alcance de esta barrida

El listado completo de ramas remotas (`git branch -r`, ~250+) tiene mucho
más ruido histórico (rick/*, cursor/*, tournament/*, copilot-vps/*, etc.)
que **no** se tocó — el mandato acotaba a lo "obviamente editorial o
huérfano" ligado a #550/#551/#552 y a los worktrees físicos colgados en
disco, no a una auditoría completa del árbol de ramas remotas del repo.

## Resultado final

```
$ git worktree list
C:/GitHub/umbral-agent-stack                             ba9b3486 [claude/plan-sys-diag-openclaw-worksystem-2026-07-17]
C:/Users/david/.cursor/worktrees/umbral-agent-stack/reo   bce0754c (detached HEAD)
C:/Users/david/.cursor/worktrees/umbral-agent-stack/wah   bce0754c (detached HEAD)
C:/Users/david/.cursor/worktrees/umbral-agent-stack/weo   bce0754c (detached HEAD)
```

14 → 4 worktrees. Clon principal intacto (sin cambio de rama, sin stash).
Ningún merge, ningún write a Notion, P2.1 no tocado.

**EDITORIAL_WORKTREE_HYGIENE_READY**
